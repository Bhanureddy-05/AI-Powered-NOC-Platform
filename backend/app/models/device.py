"""
app/models/device.py
====================
SQLAlchemy DB Model for the 'devices' Table

WHY THIS FILE EXISTS:
    To manage and monitor network hardware, we must register each device's metadata.
    This model maps columns like name, IP, type, location, and operations status.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), unique=True, index=True, nullable=False) # IPv4 or IPv6
    location: Mapped[str] = mapped_column(String(100), nullable=True)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., 'router', 'switch', 'firewall'
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False) # e.g., 'active', 'inactive', 'maintenance'

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    metrics = relationship("DeviceMetric", back_populates="device", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="device", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="device", cascade="all, delete-orphan")
