"""
app/models/ticket_history.py
===========================
SQLAlchemy DB Model for the 'ticket_history' Table

WHY THIS FILE EXISTS:
    Logs status modifications, user assignments, priority adjustments, 
    and SLA changes on ticket records to support full tracking of ticket lifecycle.
"""

from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

class TicketHistory(Base):
    __tablename__ = "ticket_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), index=True, nullable=False)
    
    field_changed: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. 'status', 'assigned_to', 'priority'
    old_value: Mapped[str] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=True)
    
    changed_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    ticket = relationship("Ticket", back_populates="history")
    user = relationship("User", foreign_keys=[changed_by])
