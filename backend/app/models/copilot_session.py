"""
app/models/copilot_session.py
=============================
SQLAlchemy DB Model for the 'copilot_sessions' Table
"""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

class CopilotSession(Base):
    __tablename__ = "copilot_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="copilot_sessions")
    messages = relationship("CopilotMessage", back_populates="session", cascade="all, delete-orphan", order_by="CopilotMessage.timestamp.asc()")
