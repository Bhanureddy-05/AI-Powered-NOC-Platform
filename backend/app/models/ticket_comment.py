"""
app/models/ticket_comment.py
===========================
SQLAlchemy DB Model for the 'ticket_comments' Table

WHY THIS FILE EXISTS:
    NOC engineers need to add comments and logs to incident tickets
    during investigations to document findings and collaborate on resolution.
"""

from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User")
