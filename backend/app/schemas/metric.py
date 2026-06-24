"""
app/schemas/metric.py
=====================
Pydantic Schemas for Device Metrics

WHY THIS FILE EXISTS:
    Validates high-frequency network telemetry data (e.g. CPU, memory, packet loss)
    before it is persisted to the database. This acts as a firewall against corrupt
    or logically invalid telemetry data.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class DeviceMetricBase(BaseModel):
    """
    Common properties for telemetry metrics.
    """
    device_id: str = Field(..., description="Target device unique identifier")
    cpu_usage: float = Field(..., description="CPU utilization percentage (0.0 to 100.0)")
    memory_usage: float = Field(..., description="Memory utilization percentage (0.0 to 100.0)")
    latency: float = Field(..., description="Network latency in milliseconds (>= 0.0)")
    packet_loss: float = Field(..., description="Packet loss percentage (0.0 to 100.0)")
    bandwidth_usage: float = Field(..., description="Interface bandwidth usage in Mbps (>= 0.0)")
    disk_usage: Optional[float] = Field(default=None, description="Disk utilization percentage (0.0 to 100.0)")
    hostname: Optional[str] = Field(default=None, description="Host system name")
    uptime: Optional[float] = Field(default=None, description="System uptime in seconds")
    reachability: bool = Field(default=True, description="Ping status connectivity indicator")
    timestamp: Optional[datetime] = Field(default=None, description="Time of measurement. Defaults to database insertion time.")

    @field_validator("cpu_usage", "memory_usage", "packet_loss")
    @classmethod
    def validate_percentages(cls, value: float, info) -> float:
        """
        Validates that percentage parameters remain between 0% and 100%.
        """
        if not (0.0 <= value <= 100.0):
            raise ValueError(f"{info.field_name} must be a percentage between 0.0 and 100.0")
        return value

    @field_validator("latency", "bandwidth_usage")
    @classmethod
    def validate_non_negative(cls, value: float, info) -> float:
        """
        Validates that physical network counts or sizes are non-negative.
        """
        if value < 0.0:
            raise ValueError(f"{info.field_name} cannot be negative")
        return value

class DeviceMetricCreate(DeviceMetricBase):
    """
    Schema for API requests to ingest new telemetry.
    """
    # Anomaly values are optional during raw collection.
    # They will be populated automatically by our ML services in Phase 7.
    anomaly_score: Optional[float] = Field(default=0.0)
    anomaly_detected: Optional[bool] = Field(default=False)

class DeviceMetricResponse(DeviceMetricBase):
    """
    Schema representing serialized telemetry rows returned to clients.
    """
    id: int
    anomaly_score: float
    anomaly_detected: bool
    timestamp: datetime

    class Config:
        from_attributes = True
