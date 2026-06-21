"""
app/services/tickets.py
=======================
Ticket Service Layer

WHY THIS FILE EXISTS:
    Encapsulates database interactions for the Ticketing workflow.
    Handles user assignments, SLA breach tracking, historical auditing,
    and comment streams.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, update

from app.models.ticket import Ticket
from app.models.ticket_comment import TicketComment
from app.models.ticket_history import TicketHistory
from app.models.device import Device
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.ticket import TicketCreate, TicketUpdate

class TicketService:
    @staticmethod
    async def get_tickets(
        db: AsyncSession,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[int] = None,
        device_id: Optional[str] = None,
        page: int = 1,
        size: int = 50
    ) -> Dict:
        """
        Retrieves a list of tickets filterable by status, priority, assignee, and device.
        Joins Device name and User assignee username.
        """
        stmt = (
            select(Ticket, Device.device_name, User.username)
            .join(Device, Ticket.device_id == Device.id)
            .outerjoin(User, Ticket.assigned_to == User.id)
        )
        
        # Apply filters
        if status:
            stmt = stmt.filter(Ticket.status == status)
        if priority:
            stmt = stmt.filter(Ticket.priority == priority)
        if assigned_to is not None:
            stmt = stmt.filter(Ticket.assigned_to == assigned_to)
        if device_id:
            stmt = stmt.filter(Ticket.device_id == device_id)
            
        # Count total matches
        count_stmt = select(func.count(Ticket.id))
        if status:
            count_stmt = count_stmt.filter(Ticket.status == status)
        if priority:
            count_stmt = count_stmt.filter(Ticket.priority == priority)
        if assigned_to is not None:
            count_stmt = count_stmt.filter(Ticket.assigned_to == assigned_to)
        if device_id:
            count_stmt = count_stmt.filter(Ticket.device_id == device_id)
            
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0
        
        # Apply ordering and pagination
        offset = (page - 1) * size
        stmt = stmt.order_by(Ticket.created_at.desc()).offset(offset).limit(size)
        
        result = await db.execute(stmt)
        rows = result.all()
        
        tickets_list = []
        for ticket, dev_name, username in rows:
            # Map columns
            ticket_dict = {
                "id": ticket.id,
                "device_id": ticket.device_id,
                "alert_id": ticket.alert_id,
                "title": ticket.title,
                "description": ticket.description,
                "status": ticket.status,
                "severity": ticket.severity,
                "priority": ticket.priority,
                "assigned_to": ticket.assigned_to,
                "sla_deadline": ticket.sla_deadline,
                "sla_status": ticket.sla_status,
                "created_at": ticket.created_at,
                "updated_at": ticket.updated_at,
                "device_name": dev_name,
                "assignee_username": username
            }
            tickets_list.append(ticket_dict)
            
        pages = (total + size - 1) // size if total > 0 else 1
        
        return {
            "tickets": tickets_list,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }

    @staticmethod
    async def get_ticket_by_id(db: AsyncSession, ticket_id: str) -> Optional[Ticket]:
        """
        Retrieves a ticket by UUID.
        """
        result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
        return result.scalars().first()

    @staticmethod
    async def create_ticket(db: AsyncSession, ticket_in: TicketCreate, user_id: Optional[int] = None) -> Ticket:
        """
        Creates a new ticket, sets SLA deadline based on priority,
        and logs the creation event in history.
        """
        # SLA calculation: critical = 2 hours, high = 4 hours, medium = 12 hours, low = 24 hours
        sla_hours = 12
        prio = ticket_in.priority.lower() if ticket_in.priority else "medium"
        if prio == "critical":
            sla_hours = 2
        elif prio == "high":
            sla_hours = 4
        elif prio == "low":
            sla_hours = 24
            
        sla_deadline = datetime.utcnow() + timedelta(hours=sla_hours)
        
        new_ticket = Ticket(
            device_id=ticket_in.device_id,
            alert_id=ticket_in.alert_id,
            title=ticket_in.title,
            description=ticket_in.description,
            status=ticket_in.status or "open",
            severity=ticket_in.severity or "medium",
            priority=ticket_in.priority or "medium",
            assigned_to=ticket_in.assigned_to,
            sla_deadline=sla_deadline,
            sla_status="active"
        )
        db.add(new_ticket)
        await db.flush() # Populate the generated UUID ID
        
        # Log to TicketHistory
        history = TicketHistory(
            ticket_id=new_ticket.id,
            field_changed="status",
            old_value=None,
            new_value=new_ticket.status,
            changed_by=user_id
        )
        db.add(history)
        
        # Also log audit event
        audit = AuditLog(
            user_id=user_id,
            action="ticket_created",
            details=f"Ticket: {new_ticket.id} | Title: {new_ticket.title}",
            ip_address="127.0.0.1"
        )
        db.add(audit)
        
        await db.commit()
        return new_ticket

    @staticmethod
    async def update_ticket(
        db: AsyncSession,
        ticket_id: str,
        ticket_up: TicketUpdate,
        user_id: int
    ) -> Optional[Ticket]:
        """
        Updates a ticket's fields, tracking changes in TicketHistory.
        Logs actions in AuditLog.
        """
        ticket = await TicketService.get_ticket_by_id(db, ticket_id)
        if not ticket:
            return None
            
        changes = []
        
        # Helper to apply fields and collect changes
        def apply_field(field_name, new_val):
            old_val = getattr(ticket, field_name)
            if new_val is not None and old_val != new_val:
                setattr(ticket, field_name, new_val)
                changes.append((field_name, str(old_val), str(new_val)))
                
        apply_field("title", ticket_up.title)
        apply_field("description", ticket_up.description)
        apply_field("status", ticket_up.status)
        apply_field("severity", ticket_up.severity)
        apply_field("priority", ticket_up.priority)
        apply_field("assigned_to", ticket_up.assigned_to)
        apply_field("sla_status", ticket_up.sla_status)
        apply_field("sla_deadline", ticket_up.sla_deadline)
        
        # If status resolves the ticket, flag SLA met if not already breached
        if ticket_up.status in ["resolved", "closed"] and ticket.sla_status == "active":
            ticket.sla_status = "met"
            changes.append(("sla_status", "active", "met"))
            
        # Save changes to history
        for field, old_v, new_v in changes:
            hist = TicketHistory(
                ticket_id=ticket.id,
                field_changed=field,
                old_value=old_v,
                new_value=new_v,
                changed_by=user_id
            )
            db.add(hist)
            
        if changes:
            ticket.updated_at = datetime.utcnow()
            
            # Log audit event
            audit = AuditLog(
                user_id=user_id,
                action="ticket_updated",
                details=f"Ticket: {ticket.id} changes: " + ", ".join([f"{f}: {ov}->{nv}" for f, ov, nv in changes]),
                ip_address="127.0.0.1"
            )
            db.add(audit)
            await db.commit()
            await db.refresh(ticket)
            
        return ticket

    @staticmethod
    async def add_comment(db: AsyncSession, ticket_id: str, comment_text: str, user_id: int) -> TicketComment:
        """
        Adds a comment log to the ticket.
        """
        comment = TicketComment(
            ticket_id=ticket_id,
            user_id=user_id,
            comment=comment_text
        )
        db.add(comment)
        
        # Audit logging
        audit = AuditLog(
            user_id=user_id,
            action="ticket_comment_added",
            details=f"Comment added to ticket: {ticket_id}",
            ip_address="127.0.0.1"
        )
        db.add(audit)
        
        await db.commit()
        return comment

    @staticmethod
    async def get_comments(db: AsyncSession, ticket_id: str) -> List[Dict]:
        """
        Retrieves all comments associated with a ticket, including author username.
        """
        stmt = (
            select(TicketComment, User.username)
            .join(User, TicketComment.user_id == User.id)
            .filter(TicketComment.ticket_id == ticket_id)
            .order_by(TicketComment.created_at.asc())
        )
        result = await db.execute(stmt)
        rows = result.all()
        
        comments_list = []
        for comment, username in rows:
            comments_list.append({
                "id": comment.id,
                "ticket_id": comment.ticket_id,
                "user_id": comment.user_id,
                "comment": comment.comment,
                "created_at": comment.created_at,
                "author_username": username
            })
        return comments_list

    @staticmethod
    async def get_ticket_history(db: AsyncSession, ticket_id: str) -> List[Dict]:
        """
        Retrieves full history modifications for a ticket.
        """
        stmt = (
            select(TicketHistory, User.username)
            .outerjoin(User, TicketHistory.changed_by == User.id)
            .filter(TicketHistory.ticket_id == ticket_id)
            .order_by(TicketHistory.changed_at.asc())
        )
        result = await db.execute(stmt)
        rows = result.all()
        
        history_list = []
        for hist, username in rows:
            history_list.append({
                "id": hist.id,
                "ticket_id": hist.ticket_id,
                "field_changed": hist.field_changed,
                "old_value": hist.old_value,
                "new_value": hist.new_value,
                "changed_by": hist.changed_by,
                "changed_at": hist.changed_at,
                "user_username": username or "System"
            })
        return history_list

    @staticmethod
    async def get_ticket_stats(db: AsyncSession) -> Dict:
        """
        Aggregates ticket stats by status and SLA state.
        """
        stats = {
            "total": 0,
            "open": 0,
            "assigned": 0,
            "in_progress": 0,
            "escalated": 0,
            "resolved": 0,
            "closed": 0,
            "sla_active": 0,
            "sla_met": 0,
            "sla_breached": 0
        }
        
        # Check counts by status
        status_stmt = select(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status)
        status_res = await db.execute(status_stmt)
        for stat, count in status_res.all():
            mapped_stat = stat.replace("-", "_") # Handle "in-progress" to "in_progress"
            if mapped_stat in stats:
                stats[mapped_stat] = count
                
        # Check counts by SLA status
        sla_stmt = select(Ticket.sla_status, func.count(Ticket.id)).group_by(Ticket.sla_status)
        sla_res = await db.execute(sla_stmt)
        for status_val, count in sla_res.all():
            key = f"sla_{status_val}"
            if key in stats:
                stats[key] = count
                
        total_stmt = select(func.count(Ticket.id))
        total_res = await db.execute(total_stmt)
        stats["total"] = total_res.scalar() or 0
        
        return stats

    @staticmethod
    async def check_sla_breaches(db: AsyncSession):
        """
        Cron or daemon task that flags tickets where current time exceeds sla_deadline
        but status is active.
        """
        now = datetime.utcnow()
        stmt = (
            update(Ticket)
            .where(Ticket.sla_status == "active")
            .where(Ticket.sla_deadline < now)
            .values(sla_status="breached")
        )
        await db.execute(stmt)
        await db.commit()
