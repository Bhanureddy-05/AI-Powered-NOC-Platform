"""
app/models/audit_log.py
=======================
SQLAlchemy DB Model for the 'audit_logs' Table

WHY THIS FILE EXISTS:
    Compliance and operations audits require listing who performed what action,
    when they did it, and from where. This table tracks administrative events like
    logins, hardware deletions, and configuration updates.
"""

from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Column
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'user_login', 'device_added', 'alert_resolved'
    details: Mapped[str] = mapped_column(Text, nullable=True)        # JSON payload or long string details
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True) # IPv4 or IPv6 string representation
    
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    actor = relationship("User", back_populates="audit_logs")
