"""
app/api/v1/routes/metrics.py
============================
Telemetry Metrics Operations Router

WHY THIS FILE EXISTS:
    Acts as the ingestion and query gateway for network device telemetry.
    Supports POST metrics (for collectors/simulators) and GET metrics (for UI charts),
    enforcing user access control lists (RBAC).
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.models.device import Device
from app.models.metric import DeviceMetric
from app.models.user import User
from app.api.v1.routes.auth import get_current_user, check_role
from app.schemas.metric import DeviceMetricCreate, DeviceMetricResponse

# ML and alert integration
from ml.predict import detect_anomaly
from app.services.alerts import AlertService
from app.schemas.alert import AlertCreate
from app.services.ws import manager

router = APIRouter(prefix="/metrics", tags=["Telemetry Metrics"])


@router.post("/", response_model=DeviceMetricResponse, status_code=status.HTTP_201_CREATED)
async def ingest_metric(
    metric_in: DeviceMetricCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator"]))
):
    """
    Ingests a new telemetry measurement record from a device.
    Access Control: Admin, Operator.
    """
    # 1. Verify that the target device exists in the inventory
    device_check = await db.execute(select(Device).filter(Device.id == metric_in.device_id))
    device = device_check.scalars().first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with ID '{metric_in.device_id}' does not exist in inventory."
        )

    # 2. Map schema to database model
    measurement_time = metric_in.timestamp or datetime.utcnow()
    
    # Run ML anomaly detection inference
    anomaly_res = detect_anomaly(
        metric_in.cpu_usage,
        metric_in.memory_usage,
        metric_in.latency,
        metric_in.packet_loss,
        metric_in.bandwidth_usage
    )
    
    new_metric = DeviceMetric(
        device_id=metric_in.device_id,
        cpu_usage=metric_in.cpu_usage,
        memory_usage=metric_in.memory_usage,
        latency=metric_in.latency,
        packet_loss=metric_in.packet_loss,
        bandwidth_usage=metric_in.bandwidth_usage,
        anomaly_score=anomaly_res["anomaly_score"],
        anomaly_detected=anomaly_res["anomaly_detected"],
        timestamp=measurement_time
    )
    db.add(new_metric)
    await db.flush() # Populate generated ID
    
    # 3. Trigger Alert if an anomaly is detected
    if anomaly_res["anomaly_detected"]:
        alert_in = AlertCreate(
            device_id=metric_in.device_id,
            alert_type="ANOMALY_DETECTED",
            severity="high" if metric_in.cpu_usage > 95.0 or metric_in.packet_loss > 5.0 else "medium",
            message=f"Network anomaly detected (score: {round(anomaly_res['anomaly_score'], 3)}). CPU: {metric_in.cpu_usage}%, Memory: {metric_in.memory_usage}%, Latency: {metric_in.latency}ms, Packet Loss: {metric_in.packet_loss}%",
            resolved=False,
            status="open"
        )
        # Create alert (registers in db and history)
        alert = await AlertService.create_alert(db, alert_in)
        
        # Broadcast alert to all clients
        await manager.broadcast({
            "event": "alert_triggered",
            "data": {
                "id": alert.id,
                "device_id": alert.device_id,
                "device_name": device.device_name,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "status": alert.status
            }
        })
        
    # 4. Broadcast the new telemetry metric to live dashboard charts
    await manager.broadcast({
        "event": "metric_ingested",
        "data": {
            "device_id": new_metric.device_id,
            "device_name": device.device_name,
            "cpu_usage": new_metric.cpu_usage,
            "memory_usage": new_metric.memory_usage,
            "latency": new_metric.latency,
            "packet_loss": new_metric.packet_loss,
            "bandwidth_usage": new_metric.bandwidth_usage,
            "anomaly_detected": new_metric.anomaly_detected,
            "timestamp": new_metric.timestamp.isoformat()
        }
    })
    
    await db.commit()
    await db.refresh(new_metric)

    return new_metric



@router.get("/{device_id}", response_model=List[DeviceMetricResponse])
async def get_device_metrics_history(
    device_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Retrieves historical metrics for a specific device. Used to plot frontend charts.
    Access Control: Admin, Operator, Viewer.
    """
    # 1. Verify device exists
    device_check = await db.execute(select(Device).filter(Device.id == device_id))
    if not device_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found."
        )

    # 2. Build query
    stmt = select(DeviceMetric).filter(DeviceMetric.device_id == device_id)
    
    if start_time:
        stmt = stmt.filter(DeviceMetric.timestamp >= start_time)
    if end_time:
        stmt = stmt.filter(DeviceMetric.timestamp <= end_time)
        
    # Order by newest measurements first and enforce a page size ceiling
    limit = min(max(1, limit), 1000)
    stmt = stmt.order_by(DeviceMetric.timestamp.desc()).limit(limit)

    result = await db.execute(stmt)
    metrics = result.scalars().all()
    
    return metrics
