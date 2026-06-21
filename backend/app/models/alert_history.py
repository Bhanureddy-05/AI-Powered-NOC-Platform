"""
app/models/alert_history.py
===========================
SQLAlchemy DB Model for the 'alert_history' Table

WHY THIS FILE EXISTS:
    NOC operations audits require tracking the exact sequence of events
    when an alert status is modified, e.g., when it was acknowledged, 
    by whom, and when it was resolved.
"""

from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

class AlertHistory(Base):
    __tablename__ = "alert_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(36), ForeignKey("alerts.id", ondelete="CASCADE"), index=True, nullable=False)
    
    status_from: Mapped[str] = mapped_column(String(20), nullable=True)
    status_to: Mapped[str] = mapped_column(String(20), nullable=False)
    
    changed_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    alert = relationship("Alert", back_populates="history")
    user = relationship("User", foreign_keys=[changed_by])
