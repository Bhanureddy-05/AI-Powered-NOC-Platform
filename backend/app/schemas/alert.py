"""
app/schemas/alert.py
====================
Pydantic Schemas for Alert Data Validation & Serialization

WHY THIS FILE EXISTS:
    Ensures that input data parsed in Alert HTTP requests is valid, 
    and serializes output payloads correctly.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class AlertBase(BaseModel):
    device_id: str
    alert_type: str = Field(..., description="e.g. CPU_HIGH, MEMORY_HIGH, LATENCY_SPIKE, ANOMALY_DETECTED")
    severity: str = Field(..., description="critical, high, medium, low")
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
    status: str = Field(default="open", description="open, acknowledged, investigating, resolved")

class AlertCreate(AlertBase):
    pass

class AlertUpdate(BaseModel):
    status: Optional[str] = None
    resolved: Optional[bool] = None
    notes: Optional[str] = None

class AlertHistoryResponse(BaseModel):
    id: int
    alert_id: str
    status_from: Optional[str]
    status_to: str
    changed_by: Optional[int]
    changed_at: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True

class AlertResponse(AlertBase):
    id: str
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    
    device_name: Optional[str] = None
    device_ip: Optional[str] = None

    class Config:
        from_attributes = True

class AlertStatsResponse(BaseModel):
    total: int
    open: int
    acknowledged: int
    investigating: int
    resolved: int
    critical: int
    high: int
    medium: int
    low: int
