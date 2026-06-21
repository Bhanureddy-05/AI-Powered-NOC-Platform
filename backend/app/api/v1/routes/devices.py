"""
app/api/v1/routes/devices.py
===========================
Device Inventory Operations Router

WHY THIS FILE EXISTS:
    This manages the physical/virtual network assets. It handles inventory registration,
    modifications, deletion, filtering, pagination, search queries, audit tracking,
    and enforces role access constraints.
"""

from typing import Optional
import math
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_

from app.db.session import get_db
from app.models.device import Device
from app.models.audit_log import AuditLog
from app.models.user import User
from app.api.v1.routes.auth import get_current_user, check_role
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceResponse, DeviceListResponse

router = APIRouter(prefix="/devices", tags=["Device Inventory"])


@router.post("/", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    device_in: DeviceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator"]))
):
    """
    Registers a new network device.
    Access Control: Admin, Operator.
    """
    # 1. Enforce unique device name
    name_check = await db.execute(select(Device).filter(Device.device_name == device_in.device_name))
    if name_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A device with this name is already registered."
        )

    # 2. Enforce unique IP address
    ip_check = await db.execute(select(Device).filter(Device.ip_address == device_in.ip_address))
    if ip_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A device with this IP address is already registered."
        )

    # 3. Create device
    new_device = Device(
        device_name=device_in.device_name,
        ip_address=device_in.ip_address,
        location=device_in.location,
        device_type=device_in.device_type,
        status=device_in.status
    )
    db.add(new_device)
    await db.flush()  # Generate the unique primary key

    # 4. Generate audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="device_created",
        details=f"Created device: {new_device.device_name} ({new_device.ip_address}), type: {new_device.device_type}",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_device)

    return new_device


@router.get("/", response_model=DeviceListResponse)
async def list_devices(
    q: Optional[str] = None,
    device_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Lists and queries the device inventory with pagination, text search, and state filtering.
    Access Control: Admin, Operator, Viewer.
    """
    if page < 1:
        page = 1
    if size < 1:
        size = 20
    if size > 100:
        size = 100

    # Base query for device select and count
    stmt = select(Device)
    count_stmt = select(func.count()).select_from(Device)

    # Apply filters
    filters = []
    if device_type:
        filters.append(Device.device_type == device_type.lower())
    if status:
        filters.append(Device.status == status.lower())
    if q:
        search_pattern = f"%{q}%"
        filters.append(
            or_(
                Device.device_name.ilike(search_pattern),
                Device.ip_address.ilike(search_pattern),
                Device.location.ilike(search_pattern)
            )
        )

    # Attach filters to statements
    if filters:
        stmt = stmt.filter(*filters)
        count_stmt = count_stmt.filter(*filters)

    # Execute total count query
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Calculate pagination bounds
    offset = (page - 1) * size
    pages = math.ceil(total / size) if total > 0 else 1

    # Execute paginated fetch
    result = await db.execute(stmt.offset(offset).limit(size))
    devices = result.scalars().all()

    return {
        "devices": devices,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }


@router.get("/{id}", response_model=DeviceResponse)
async def get_device(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Retrieves metadata for a specific device by ID.
    Access Control: Admin, Operator, Viewer.
    """
    result = await db.execute(select(Device).filter(Device.id == id))
    device = result.scalars().first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found."
        )
    return device


@router.put("/{id}", response_model=DeviceResponse)
async def update_device(
    id: str,
    device_in: DeviceUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator"]))
):
    """
    Updates configuration details of a specific device.
    Access Control: Admin, Operator.
    """
    result = await db.execute(select(Device).filter(Device.id == id))
    device = result.scalars().first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found."
        )

    changes = []
    # Update fields and log descriptions
    if device_in.device_name is not None and device_in.device_name != device.device_name:
        # Verify unique name constraint
        name_check = await db.execute(
            select(Device).filter(Device.device_name == device_in.device_name, Device.id != id)
        )
        if name_check.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A device with this name is already registered."
            )
        changes.append(f"name: {device.device_name} -> {device_in.device_name}")
        device.device_name = device_in.device_name

    if device_in.ip_address is not None and device_in.ip_address != device.ip_address:
        # Verify unique IP constraint
        ip_check = await db.execute(
            select(Device).filter(Device.ip_address == device_in.ip_address, Device.id != id)
        )
        if ip_check.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A device with this IP address is already registered."
            )
        changes.append(f"IP: {device.ip_address} -> {device_in.ip_address}")
        device.ip_address = device_in.ip_address

    if device_in.location is not None and device_in.location != device.location:
        changes.append(f"location: {device.location} -> {device_in.location}")
        device.location = device_in.location

    if device_in.device_type is not None and device_in.device_type != device.device_type:
        changes.append(f"type: {device.device_type} -> {device_in.device_type}")
        device.device_type = device_in.device_type.lower()

    if device_in.status is not None and device_in.status != device.status:
        changes.append(f"status: {device.status} -> {device_in.status}")
        device.status = device_in.status.lower()

    if changes:
        # Generate audit log
        audit = AuditLog(
            user_id=current_user.id,
            action="device_updated",
            details=f"Updated device {device.device_name} (ID: {id}). Changes: {', '.join(changes)}",
            ip_address=request.client.host if request.client else "127.0.0.1"
        )
        db.add(audit)
        await db.commit()
        await db.refresh(device)

    return device


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin"]))
):
    """
    Deletes a device from inventory.
    Access Control: Admin only.
    """
    result = await db.execute(select(Device).filter(Device.id == id))
    device = result.scalars().first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found."
        )

    # Keep references for logs before deletion
    name = device.device_name
    ip = device.ip_address

    # Execute deletion
    await db.delete(device)

    # Generate audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="device_deleted",
        details=f"Deleted device: {name} ({ip}), ID: {id}",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit)
    await db.commit()

    return
