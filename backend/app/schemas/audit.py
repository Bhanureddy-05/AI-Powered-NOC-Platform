"""
app/schemas/audit.py
====================
Pydantic Schemas for Security Audit Logs

WHY THIS FILE EXISTS:
    Validates log listing outputs, query filters, and security stat structures.
"""

from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class AuditLogListResponse(BaseModel):
    logs: list[AuditLogResponse]
    total: int
    page: int
    size: int
    pages: int

class AuditLogStatsResponse(BaseModel):
    total_events: int
    logins_success_24h: int
    logins_failed_24h: int
    device_operations_24h: int
    action_distribution: Dict[str, int]
