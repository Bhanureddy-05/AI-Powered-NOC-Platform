"""
app/schemas/device.py
=====================
Pydantic Schemas for Device Management

WHY THIS FILE EXISTS:
    Validates input telemetry metadata (like standard IPv4/IPv6 addresses)
    before writing network device configurations to the PostgreSQL/SQLite database.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, IPvAnyAddress, field_validator

class DeviceBase(BaseModel):
    """
    Base properties for devices.
    """
    device_name: str = Field(..., min_length=3, max_length=100, description="Host identifier for the device")
    ip_address: str = Field(..., description="Valid IPv4 or IPv6 network address")
    location: Optional[str] = Field(default=None, max_length=100, description="Physical center/datacenter rack location")
    device_type: str = Field(default="router", description="Device class: router, switch, firewall, or server")
    status: str = Field(default="active", description="Device state: active, inactive, or maintenance")

    @field_validator('ip_address')
    @classmethod
    def validate_ip(cls, value: str) -> str:
        """
        Validates that the provided string is a valid IPv4 or IPv6 address.
        """
        import ipaddress
        try:
            ipaddress.ip_address(value)
        except ValueError:
            raise ValueError("Invalid IP address format. Must be a valid IPv4 or IPv6 address.")
        return value

    @field_validator('device_type')
    @classmethod
    def validate_type(cls, value: str) -> str:
        """
        Enforces standard device types in network inventories.
        """
        allowed = {"router", "switch", "firewall", "server"}
        val_lower = value.lower()
        if val_lower not in allowed:
            raise ValueError(f"Invalid device type. Allowed: {', '.join(allowed)}")
        return val_lower

    @field_validator('status')
    @classmethod
    def validate_status(cls, value: str) -> str:
        """
        Enforces standard operations states.
        """
        allowed = {"active", "inactive", "maintenance"}
        val_lower = value.lower()
        if val_lower not in allowed:
            raise ValueError(f"Invalid status. Allowed: {', '.join(allowed)}")
        return val_lower

class DeviceCreate(DeviceBase):
    """
    Request model for registering a new device.
    """
    pass

class DeviceUpdate(BaseModel):
    """
    Request model for updating an existing device's details.
    All parameters are optional to allow partial PATCH/PUT updates.
    """
    device_name: Optional[str] = Field(default=None, min_length=3, max_length=100)
    ip_address: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None, max_length=100)
    device_type: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)

    @field_validator('ip_address')
    @classmethod
    def validate_ip(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        import ipaddress
        try:
            ipaddress.ip_address(value)
        except ValueError:
            raise ValueError("Invalid IP address format. Must be a valid IPv4 or IPv6 address.")
        return value

    @field_validator('device_type')
    @classmethod
    def validate_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        allowed = {"router", "switch", "firewall", "server"}
        val_lower = value.lower()
        if val_lower not in allowed:
            raise ValueError(f"Invalid device type. Allowed: {', '.join(allowed)}")
        return val_lower

    @field_validator('status')
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        allowed = {"active", "inactive", "maintenance"}
        val_lower = value.lower()
        if val_lower not in allowed:
            raise ValueError(f"Invalid status. Allowed: {', '.join(allowed)}")
        return val_lower

class DeviceResponse(DeviceBase):
    """
    Response model for device objects.
    """
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DeviceListResponse(BaseModel):
    """
    Paginated inventory output.
    """
    devices: list[DeviceResponse]
    total: int
    page: int
    size: int
    pages: int
