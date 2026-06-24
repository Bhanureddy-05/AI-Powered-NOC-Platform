"""
app/api/v1/routes/metrics.py
============================
Telemetry Metrics Operations Router

WHY THIS FILE EXISTS:
    Acts as the ingestion and query gateway for network device telemetry.
    Supports:
      - POST /          → Ingest raw telemetry from device agents/simulators
      - GET  /{id}      → Historical metrics for a specific device
      - GET  /system    → Real-time host metrics via psutil
      - GET  /stats     → Aggregate statistics across all devices
    Enforces RBAC on all endpoints.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

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

# psutil for real host system monitoring
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

router = APIRouter(prefix="/metrics", tags=["Telemetry Metrics"])


@router.post("/", response_model=DeviceMetricResponse, status_code=status.HTTP_201_CREATED)
async def ingest_metric(
    metric_in: DeviceMetricCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator"]))
):
    """
    Ingests a new telemetry measurement record from a device.
    Runs ML anomaly detection and triggers alerts if anomalies are found.
    Access Control: Admin, Operator.
    """
    # 1. Verify device exists
    device_check = await db.execute(select(Device).filter(Device.id == metric_in.device_id))
    device = device_check.scalars().first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{metric_in.device_id}' does not exist."
        )

    measurement_time = metric_in.timestamp or datetime.utcnow()

    # 2. ML anomaly detection
    anomaly_res = detect_anomaly(
        metric_in.cpu_usage,
        metric_in.memory_usage,
        metric_in.latency,
        metric_in.packet_loss,
        metric_in.bandwidth_usage
    )

    # 3. Persist metric
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
    await db.flush()

    # 4. Trigger alert on anomaly
    if anomaly_res["anomaly_detected"]:
        alert_in = AlertCreate(
            device_id=metric_in.device_id,
            alert_type="ANOMALY_DETECTED",
            severity="high" if metric_in.cpu_usage > 95.0 or metric_in.packet_loss > 5.0 else "medium",
            message=(
                f"Network anomaly detected (score: {round(anomaly_res['anomaly_score'], 3)}). "
                f"CPU: {metric_in.cpu_usage}%, Memory: {metric_in.memory_usage}%, "
                f"Latency: {metric_in.latency}ms, Packet Loss: {metric_in.packet_loss}%"
            ),
            resolved=False,
            status="open"
        )
        alert = await AlertService.create_alert(db, alert_in)
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

    # 5. Broadcast live metric to dashboard
    await manager.broadcast({
        "event": "metric_ingested",
        "data": {
            "device_id": new_metric.device_id,
            "device_name": device.device_name,
            "device_type": device.device_type,
            "cpu_usage": new_metric.cpu_usage,
            "memory_usage": new_metric.memory_usage,
            "latency": new_metric.latency,
            "packet_loss": new_metric.packet_loss,
            "bandwidth_usage": new_metric.bandwidth_usage,
            "anomaly_detected": new_metric.anomaly_detected,
            "anomaly_score": round(anomaly_res["anomaly_score"], 4),
            "timestamp": new_metric.timestamp.isoformat()
        }
    })

    await db.commit()
    await db.refresh(new_metric)
    return new_metric


@router.get("/system", tags=["Telemetry Metrics"])
async def get_system_metrics(
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Returns real-time host system metrics collected by psutil.
    Exposes CPU, memory, disk I/O, and network stats from the server running this backend.
    Access Control: Admin, Operator, Viewer.
    """
    if not HAS_PSUTIL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="psutil not installed. Run: pip install psutil"
        )

    cpu_pct = psutil.cpu_percent(interval=0.1)
    cpu_freq = psutil.cpu_freq()
    mem = psutil.virtual_memory()

    try:
        disk = psutil.disk_usage("/")
    except Exception:
        try:
            disk = psutil.disk_usage("C:\\")
        except Exception:
            disk = None

    net = psutil.net_io_counters()

    # Top 5 processes by CPU
    processes = []
    try:
        procs = sorted(
            psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
            key=lambda p: p.info.get("cpu_percent") or 0,
            reverse=True,
        )[:5]
        for p in procs:
            processes.append({
                "pid": p.info["pid"],
                "name": p.info["name"],
                "cpu_pct": round(p.info.get("cpu_percent") or 0, 1),
                "mem_pct": round(p.info.get("memory_percent") or 0, 2),
            })
    except Exception:
        pass

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cpu": {
            "usage_pct": cpu_pct,
            "logical_cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "frequency_mhz": round(cpu_freq.current, 1) if cpu_freq else None,
        },
        "memory": {
            "total_gb": round(mem.total / 1e9, 2),
            "available_gb": round(mem.available / 1e9, 2),
            "used_gb": round(mem.used / 1e9, 2),
            "used_pct": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / 1e9, 2) if disk else None,
            "free_gb": round(disk.free / 1e9, 2) if disk else None,
            "used_pct": disk.percent if disk else None,
        },
        "network": {
            "bytes_sent_mb": round(net.bytes_sent / 1e6, 2),
            "bytes_recv_mb": round(net.bytes_recv / 1e6, 2),
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "errors_in": net.errin,
            "errors_out": net.errout,
        },
        "top_processes": processes,
    }


@router.get("/stats", tags=["Telemetry Metrics"])
async def get_metric_aggregates(
    hours: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Returns aggregate metric statistics across all devices for the past N hours.
    Used by the dashboard KPI cards and analytics page.
    Access Control: Admin, Operator, Viewer.
    """
    hours = max(1, min(hours, 168))  # Clamp to 1h-7d
    since = datetime.utcnow() - timedelta(hours=hours)

    agg_stmt = select(
        func.avg(DeviceMetric.cpu_usage).label("avg_cpu"),
        func.avg(DeviceMetric.memory_usage).label("avg_mem"),
        func.avg(DeviceMetric.latency).label("avg_latency"),
        func.avg(DeviceMetric.packet_loss).label("avg_pkt_loss"),
        func.max(DeviceMetric.cpu_usage).label("max_cpu"),
        func.max(DeviceMetric.latency).label("max_latency"),
        func.count(DeviceMetric.id).label("total_readings"),
    ).filter(DeviceMetric.timestamp >= since)

    agg_res = await db.execute(agg_stmt)
    row = agg_res.first()

    return {
        "period_hours": hours,
        "since": since.isoformat(),
        "averages": {
            "cpu_pct": round(row.avg_cpu or 0, 2),
            "memory_pct": round(row.avg_mem or 0, 2),
            "latency_ms": round(row.avg_latency or 0, 2),
            "packet_loss_pct": round(row.avg_pkt_loss or 0, 4),
        },
        "peaks": {
            "max_cpu_pct": round(row.max_cpu or 0, 2),
            "max_latency_ms": round(row.max_latency or 0, 2),
        },
        "total_readings": row.total_readings or 0,
    }


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

    # 2. Build query with optional time range filters
    stmt = select(DeviceMetric).filter(DeviceMetric.device_id == device_id)

    if start_time:
        stmt = stmt.filter(DeviceMetric.timestamp >= start_time)
    if end_time:
        stmt = stmt.filter(DeviceMetric.timestamp <= end_time)

    limit = min(max(1, limit), 1000)
    stmt = stmt.order_by(DeviceMetric.timestamp.desc()).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()
