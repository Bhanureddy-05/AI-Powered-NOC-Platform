# app/models/__init__.py
# Register and expose all database models for clean package-level imports

from app.models.user import User
from app.models.device import Device
from app.models.metric import DeviceMetric
from app.models.alert import Alert
from app.models.alert_history import AlertHistory
from app.models.ticket import Ticket
from app.models.ticket_comment import TicketComment
from app.models.ticket_history import TicketHistory
from app.models.audit_log import AuditLog
from app.models.copilot_session import CopilotSession
from app.models.copilot_message import CopilotMessage

__all__ = [
    "User",
    "Device",
    "DeviceMetric",
    "Alert",
    "AlertHistory",
    "Ticket",
    "TicketComment",
    "TicketHistory",
    "AuditLog",
    "CopilotSession",
    "CopilotMessage",
]

