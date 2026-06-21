"""
app/api/v1/routes/tickets.py
============================
Incident Tickets API Router

WHY THIS FILE EXISTS:
    Exposes endpoints for creating tickets from alerts, assigning operators,
    tracking SLA statuses, adding comment notes, and logging audits.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.api.v1.routes.auth import get_current_user, check_role
from app.schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketCommentCreate,
    TicketCommentResponse,
    TicketHistoryResponse,
    TicketStatsResponse
)
from app.services.tickets import TicketService
from app.services.ws import manager

router = APIRouter(prefix="/tickets", tags=["Incident Management"])

@router.get("/", response_model=dict)
async def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[int] = None,
    device_id: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Query system tickets with pagination and filters.
    """
    return await TicketService.get_tickets(db, status, priority, assigned_to, device_id, page, size)

@router.get("/stats", response_model=TicketStatsResponse)
async def get_ticket_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Calculates incident ticket counts across states and SLA status.
    """
    return await TicketService.get_ticket_stats(db)

@router.get("/{id}", response_model=TicketResponse)
async def get_ticket(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Fetches details of a specific ticket by UUID.
    """
    ticket = await TicketService.get_ticket_by_id(db, id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {id} not found."
        )
    return ticket

@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_new_ticket(
    ticket_in: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator"]))
):
    """
    Creates a new incident ticket. Broadcasts event over WebSocket.
    """
    ticket = await TicketService.create_ticket(db, ticket_in, current_user.id)
    
    # Broadcast ticket creation event
    await manager.broadcast({
        "event": "ticket_created",
        "data": {
            "id": ticket.id,
            "title": ticket.title,
            "priority": ticket.priority,
            "status": ticket.status,
            "assigned_to": ticket.assigned_to
        }
    })
    
    return ticket

@router.put("/{id}", response_model=TicketResponse)
async def update_ticket_details(
    id: str,
    ticket_up: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator"]))
):
    """
    Modifies status, priority, or assignee on a ticket.
    Registers edits to the historical log, and broadcasts websocket updates.
    """
    ticket = await TicketService.update_ticket(db, id, ticket_up, current_user.id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found."
        )
        
    # Broadcast status change
    await manager.broadcast({
        "event": "ticket_updated",
        "data": {
            "id": ticket.id,
            "title": ticket.title,
            "priority": ticket.priority,
            "status": ticket.status,
            "assigned_to": ticket.assigned_to
        }
    })
    
    return ticket

# Comment Endpoints
@router.post("/{id}/comments", response_model=TicketCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment_to_ticket(
    id: str,
    comment_in: TicketCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator"]))
):
    """
    Appends an operational log or note comment to a ticket.
    """
    ticket = await TicketService.get_ticket_by_id(db, id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found."
        )
    comment = await TicketService.add_comment(db, id, comment_in.comment, current_user.id)
    
    # Broadcast comment addition
    await manager.broadcast({
        "event": "ticket_comment_added",
        "data": {
            "ticket_id": id,
            "comment": comment.comment,
            "author_username": current_user.username
        }
    })
    
    return {
        "id": comment.id,
        "ticket_id": comment.ticket_id,
        "user_id": comment.user_id,
        "comment": comment.comment,
        "created_at": comment.created_at,
        "author_username": current_user.username
    }

@router.get("/{id}/comments", response_model=List[TicketCommentResponse])
async def list_ticket_comments(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Retrieves the commentary history stream for a ticket.
    """
    return await TicketService.get_comments(db, id)

# History Endpoints
@router.get("/{id}/history", response_model=List[TicketHistoryResponse])
async def list_ticket_history(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Retrieves full audit trails of lifecycle fields modified for this ticket.
    """
    return await TicketService.get_ticket_history(db, id)
