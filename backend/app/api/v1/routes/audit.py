"""
app/api/v1/routes/audit.py
==========================
Security Auditing & Activity Tracking API Router

WHY THIS FILE EXISTS:
    Exposes endpoints for querying system audit trails and security analytics.
    Restricted strictly to the Admin role (RBAC).
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.db.session import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.api.v1.routes.auth import get_current_user, check_role
from app.schemas.audit import AuditLogListResponse, AuditLogStatsResponse

router = APIRouter(prefix="/audit", tags=["Security & Auditing"])

@router.get("/", response_model=AuditLogListResponse)
async def list_audit_logs(
    username: Optional[str] = None,
    action: Optional[str] = None,
    ip_address: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin"]))
):
    """
    Retrieves a list of audit logs with paginated offsets and user filters.
    Requires Admin privileges.
    """
    stmt = select(AuditLog, User.username).outerjoin(User, AuditLog.user_id == User.id)
    
    # Apply filters
    if username:
        stmt = stmt.filter(User.username.like(f"%{username}%"))
    if action:
        stmt = stmt.filter(AuditLog.action == action)
    if ip_address:
        stmt = stmt.filter(AuditLog.ip_address == ip_address)
        
    # Count totals
    count_stmt = select(func.count(AuditLog.id)).outerjoin(User, AuditLog.user_id == User.id)
    if username:
        count_stmt = count_stmt.filter(User.username.like(f"%{username}%"))
    if action:
        count_stmt = count_stmt.filter(AuditLog.action == action)
    if ip_address:
        count_stmt = count_stmt.filter(AuditLog.ip_address == ip_address)
        
    count_res = await db.execute(count_stmt)
    total = count_res.scalar() or 0
    
    # Pagination & Sort by newest
    offset = (page - 1) * size
    stmt = stmt.order_by(AuditLog.timestamp.desc()).offset(offset).limit(size)
    
    result = await db.execute(stmt)
    rows = result.all()
    
    logs = []
    for audit, uname in rows:
        logs.append({
            "id": audit.id,
            "user_id": audit.user_id,
            "username": uname or "System / Anonymous",
            "action": audit.action,
            "details": audit.details,
            "ip_address": audit.ip_address,
            "timestamp": audit.timestamp
        })
        
    pages = (total + size - 1) // size if total > 0 else 1
    
    return {
        "logs": logs,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }

@router.get("/stats", response_model=AuditLogStatsResponse)
async def get_audit_log_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin"]))
):
    """
    Computes security audit highlights (logins, failures, actions) over the last 24h.
    Requires Admin privileges.
    """
    yesterday = datetime.utcnow() - timedelta(days=1)
    
    # 1. Total events count
    total_stmt = select(func.count(AuditLog.id))
    total_res = await db.execute(total_stmt)
    total_events = total_res.scalar() or 0
    
    # 2. Logins success (24h)
    success_stmt = select(func.count(AuditLog.id)).filter(AuditLog.action == "login_success").filter(AuditLog.timestamp >= yesterday)
    success_res = await db.execute(success_stmt)
    logins_success = success_res.scalar() or 0
    
    # 3. Logins failed (24h)
    failed_stmt = select(func.count(AuditLog.id)).filter(AuditLog.action == "login_failed").filter(AuditLog.timestamp >= yesterday)
    failed_res = await db.execute(failed_stmt)
    logins_failed = failed_res.scalar() or 0
    
    # 4. Device modifications (24h)
    dev_stmt = select(func.count(AuditLog.id)).filter(AuditLog.action.like("device_%")).filter(AuditLog.timestamp >= yesterday)
    dev_res = await db.execute(dev_stmt)
    device_operations = dev_res.scalar() or 0
    
    # 5. Action category breakdown (all time or top 5)
    breakdown_stmt = select(AuditLog.action, func.count(AuditLog.id)).group_by(AuditLog.action).order_by(func.count(AuditLog.id).desc()).limit(10)
    breakdown_res = await db.execute(breakdown_stmt)
    action_distribution = {action: count for action, count in breakdown_res.all()}
    
    return {
        "total_events": total_events,
        "logins_success_24h": logins_success,
        "logins_failed_24h": logins_failed,
        "device_operations_24h": device_operations,
        "action_distribution": action_distribution
    }
