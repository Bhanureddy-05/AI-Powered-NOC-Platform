"""
app/api/v1/routes/alerts.py
===========================
Alert Engine API Router

WHY THIS FILE EXISTS:
    Exposes endpoints for querying, acknowledging, and resolving alerts.
    Validates user credentials and role-based permissions (RBAC).
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.api.v1.routes.auth import get_current_user, check_role
from app.schemas.alert import AlertCreate, AlertUpdate, AlertResponse, AlertStatsResponse, AlertHistoryResponse
from app.services.alerts import AlertService
from app.services.ws import manager

router = APIRouter(prefix="/alerts", tags=["Alert Management"])

@router.get("/", response_model=dict)
async def list_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    device_id: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Retrieves list of alerts matching optional query filters, with pagination.
    Accessible by Admin, Operator, Viewer roles.
    """
    return await AlertService.get_alerts(db, status, severity, device_id, page, size)

@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Returns total alert statistics categorized by severity and lifecycle states.
    """
    return await AlertService.get_alert_stats(db)

@router.get("/{id}", response_model=AlertResponse)
async def get_alert_by_id(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Fetches details of a specific alert by its UUID.
    """
    alert = await AlertService.get_alert_by_id(db, id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {id} not found."
        )
    return alert

@router.get("/{id}/history", response_model=List[AlertHistoryResponse])
async def get_alert_history(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Retrieves the lifecycle event history for a given alert.
    """
    return await AlertService.get_alert_history(db, id)

@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def trigger_new_alert(
    alert_in: AlertCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator"]))
):
    """
    Triggers/Registers a new alert event (usually called by collector / telemetry scripts).
    Broadcasts the alert creation event to all live WebSocket sessions.
    """
    alert = await AlertService.create_alert(db, alert_in)
    await db.commit()
    await db.refresh(alert)
    
    # Broadcast alert event over WebSockets
    alert_payload = {
        "event": "alert_triggered",
        "data": {
            "id": alert.id,
            "device_id": alert.device_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
            "status": alert.status
        }
    }
    await manager.broadcast(alert_payload)
    
    return alert

@router.patch("/{id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    id: str,
    update_in: AlertUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator"]))
):
    """
    Transition an Alert status to Acknowledged.
    """
    alert = await AlertService.update_alert_status(
        db=db,
        alert_id=id,
        new_status="acknowledged",
        user_id=current_user.id,
        notes=update_in.notes
    )
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found."
        )
        
    # Broadcast status change
    await manager.broadcast({
        "event": "alert_acknowledged",
        "data": {"id": alert.id, "status": "acknowledged", "user": current_user.username}
    })
    
    return alert

@router.patch("/{id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    id: str,
    update_in: AlertUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator"]))
):
    """
    Transition an Alert status to Resolved.
    """
    alert = await AlertService.update_alert_status(
        db=db,
        alert_id=id,
        new_status="resolved",
        user_id=current_user.id,
        notes=update_in.notes
    )
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found."
        )
        
    # Broadcast status change
    await manager.broadcast({
        "event": "alert_resolved",
        "data": {"id": alert.id, "status": "resolved", "user": current_user.username}
    })
    
    return alert
