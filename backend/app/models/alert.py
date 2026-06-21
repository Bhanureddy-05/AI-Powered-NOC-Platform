"""
app/models/alert.py
===================
SQLAlchemy DB Model for the 'alerts' Table

WHY THIS FILE EXISTS:
    Alert management needs to persist events that require engineer attention.
    This model captures critical triggers (e.g. HIGH_CPU, LATENCY_SPIKE)
    and enables tracking of their resolution states.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), index=True, nullable=False)
    
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)   # e.g., 'CPU_HIGH', 'ANOMALY_DETECTED'
    severity: Mapped[str] = mapped_column(String(20), default="warning", nullable=False) # 'low', 'medium', 'high', 'critical'
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Lifecycle status: open, acknowledged, investigating, resolved
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    device = relationship("Device", back_populates="alerts")
    ticket = relationship("Ticket", back_populates="alert", uselist=False)
    
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])
    resolver = relationship("User", foreign_keys=[resolved_by])
    
    history = relationship("AlertHistory", back_populates="alert", cascade="all, delete-orphan")

