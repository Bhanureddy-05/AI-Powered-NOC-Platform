"""
app/models/ticket.py
====================
SQLAlchemy DB Model for the 'tickets' Table

WHY THIS FILE EXISTS:
    NOC operators need a ticketing system to assign, track, and close issues
    discovered by telemetry analysis. This table logs incident titles, descriptions,
    assignees, and resolving status.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Column
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    alert_id: Mapped[str] = mapped_column(String(36), ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True)
    
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Status lifecycle: open, assigned, in_progress, escalated, resolved, closed
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    # Severity & Priority levels: critical, high, medium, low
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    
    assigned_to: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # SLA Tracking
    sla_deadline: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    sla_status: Mapped[str] = mapped_column(String(20), default="active", nullable=False) # active, met, breached
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Dynamic ORM relationships to other tables
    device = relationship("Device", back_populates="tickets")
    alert = relationship("Alert", back_populates="ticket")
    assignee = relationship("User", back_populates="tickets")
    
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan")
    history = relationship("TicketHistory", back_populates="ticket", cascade="all, delete-orphan")

