"""
app/schemas/ticket.py
=====================
Pydantic Schemas for Incident Ticket Validation & Serialization

WHY THIS FILE EXISTS:
    Validates ticket payload structure (attributes, assignees, comments, SLA updates)
    and formats JSON responses returned to client browsers.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

# Comments Schemas
class TicketCommentBase(BaseModel):
    comment: str

class TicketCommentCreate(TicketCommentBase):
    pass

class TicketCommentResponse(BaseModel):
    id: int
    ticket_id: str
    user_id: int
    comment: str
    created_at: datetime
    author_username: Optional[str] = None

    class Config:
        from_attributes = True

# History Schemas
class TicketHistoryResponse(BaseModel):
    id: int
    ticket_id: str
    field_changed: str
    old_value: Optional[str]
    new_value: Optional[str]
    changed_by: Optional[int]
    changed_at: datetime
    user_username: Optional[str] = None

    class Config:
        from_attributes = True

# Core Ticket Schemas
class TicketBase(BaseModel):
    device_id: str
    alert_id: Optional[str] = None
    title: str
    description: str
    status: str = Field(default="open", description="open, assigned, in_progress, escalated, resolved, closed")
    severity: str = Field(default="medium", description="critical, high, medium, low")
    priority: str = Field(default="medium", description="critical, high, medium, low")
    assigned_to: Optional[int] = None
    sla_deadline: Optional[datetime] = None
    sla_status: str = Field(default="active", description="active, met, breached")

class TicketCreate(TicketBase):
    pass

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[int] = None
    sla_status: Optional[str] = None
    sla_deadline: Optional[datetime] = None

class TicketResponse(TicketBase):
    id: str
    created_at: datetime
    updated_at: datetime
    device_name: Optional[str] = None
    assignee_username: Optional[str] = None

    class Config:
        from_attributes = True

class TicketStatsResponse(BaseModel):
    total: int
    open: int
    assigned: int
    in_progress: int
    escalated: int
    resolved: int
    closed: int
    sla_active: int
    sla_met: int
    sla_breached: int
