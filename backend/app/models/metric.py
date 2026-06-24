"""
app/models/metric.py
====================
SQLAlchemy DB Model for the 'device_metrics' Table

WHY THIS FILE EXISTS:
    High-frequency network performance telemetry must be stored efficiently.
    This model maps the telemetry payload parameters (CPU usage, memory usage,
    latency, packet loss, and bandwidth) alongside ML anomaly flags.
"""

from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

class DeviceMetric(Base):
    __tablename__ = "device_metrics"

    # BigInteger for primary key because metrics scale rapidly over time
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), index=True, nullable=False)
    
    # Telemetry Metrics
    cpu_usage: Mapped[float] = mapped_column(Float, nullable=False)       # Percentage (0.0 to 100.0)
    memory_usage: Mapped[float] = mapped_column(Float, nullable=False)    # Percentage (0.0 to 100.0)
    latency: Mapped[float] = mapped_column(Float, nullable=False)         # Milliseconds (ms)
    packet_loss: Mapped[float] = mapped_column(Float, nullable=False)     # Percentage (0.0 to 100.0)
    bandwidth_usage: Mapped[float] = mapped_column(Float, nullable=False) # Mbps
    
    # Real Telemetry additions (Phase 2)
    disk_usage: Mapped[float] = mapped_column(Float, nullable=True)       # Percentage (0.0 to 100.0)
    hostname: Mapped[str] = mapped_column(String(100), nullable=True)
    uptime: Mapped[float] = mapped_column(Float, nullable=True)           # Seconds
    reachability: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Anomaly Detection results (populated by Isolation Forest)
    anomaly_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    anomaly_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Time-series index timestamp
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    # Relationships
    device = relationship("Device", back_populates="metrics")
