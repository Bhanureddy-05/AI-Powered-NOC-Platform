"""
main.py
=======
FastAPI Application Entry Point — AETHER NOC Platform

WHY THIS FILE EXISTS:
    This is the "front door" of the entire backend application.
    When you start the server, it boots from this file.
    All routes, middleware, startup hooks, and background daemons are wired here.
"""

import asyncio
import time
import logging
import os
import math
import random
import socket
import platform
import subprocess
import psutil
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.api.v1.api import api_router
from app.db.session import async_session
from app.services.tickets import TicketService
from ml.train import train_models_from_db
from ml.anomaly_detection import MODEL_PATH as AD_PATH
from ml.failure_prediction import MODEL_PATH as FP_PATH

# ============================================================
# Structured Logging
# ============================================================
logging.basicConfig(
    level=logging.INFO if settings.APP_ENV == "production" else logging.DEBUG,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}'
)
logger = logging.getLogger("noc_platform")

# ============================================================
# FastAPI Application
# ============================================================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise-grade AI-Powered Network Operations Center Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ============================================================
# CORS Middleware
# ============================================================
origins = [
    "https://aether-noc-frontend.onrender.com",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# Allow custom origins from environment
origins_env = os.getenv("ALLOWED_ORIGINS", "")
if origins_env:
    origins.extend([o.strip() for o in origins_env.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else origins,
    allow_origin_regex=r"https://.*\.onrender\.com" if not settings.DEBUG else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Rate Limiting Middleware
# ============================================================
RATE_LIMIT_DURATION = 60
MAX_REQUESTS = 30
ip_request_counts: dict = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/v1/auth/login") or path.startswith("/api/v1/auth/register"):
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        ip_request_counts[client_ip] = [
            t for t in ip_request_counts.get(client_ip, []) if now - t < RATE_LIMIT_DURATION
        ]
        if len(ip_request_counts[client_ip]) >= MAX_REQUESTS:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again in 1 minute."},
            )
        ip_request_counts[client_ip].append(now)
    return await call_next(request)

# ============================================================
# Global Exception Handlers
# ============================================================
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"SQLAlchemy Error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "A database operation failed."})

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "An internal server error occurred."})

# ============================================================
# API Routers
# ============================================================
app.include_router(api_router, prefix="/api/v1")


# ============================================================
# Telemetry Generation Helper
# ============================================================
def _generate_telemetry(device_type: str) -> dict:
    """
    Generates a single realistic metric data point.
    Uses a sine-wave diurnal pattern to simulate business-hour traffic peaks.
    """
    now = datetime.utcnow()
    hour = now.hour + now.minute / 60.0
    diurnal = math.sin((hour - 6) * (2 * math.pi / 24)) * 0.4 + 0.5
    noise = random.uniform(-0.05, 0.05)
    activity = max(0.01, min(0.99, diurnal + noise))

    dtype = device_type.lower()
    if dtype == "router":
        cpu = 15 + activity * 45
        mem = 40 + activity * 15
        bw  = 50 + activity * 400
        lat = 5  + activity * 15
    elif dtype == "firewall":
        cpu = 20 + activity * 60
        mem = 55 + activity * 25
        bw  = 100 + activity * 650
        lat = 2  + activity * 8
    elif dtype == "switch":
        cpu = 5  + activity * 25
        mem = 20 + activity * 10
        bw  = 200 + activity * 800
        lat = 1  + activity * 4
    else:  # server / generic
        cpu = 10 + activity * 75
        mem = 30 + activity * 50
        bw  = 20 + activity * 300
        lat = 3  + activity * 12

    # Occasional latency spike (3% probability)
    if random.random() > 0.97:
        lat += random.uniform(80, 250)

    # Packet loss under high activity
    pkt_loss = 0.0
    if activity > 0.85:
        pkt_loss = round(random.uniform(0.1, 2.5), 2)
    elif random.random() > 0.98:
        pkt_loss = 0.1

    return {
        "cpu_usage":       round(min(cpu, 100.0), 1),
        "memory_usage":    round(min(mem, 100.0), 1),
        "latency":         round(lat, 2),
        "packet_loss":     pkt_loss,
        "bandwidth_usage": round(bw, 2),
    }


# ============================================================
# Background Loops
# ============================================================
async def check_sla_breaches_background_loop():
    """Checks for breached SLAs every 60 seconds."""
    logger.info("Starting background SLA tracker daemon...")
    while True:
        await asyncio.sleep(60)
        try:
            async with async_session() as db:
                await TicketService.check_sla_breaches(db)
        except Exception as e:
            logger.error(f"SLA check error: {e}")


async def retrain_models_background_loop():
    """Retrains ML models once every 24 hours."""
    logger.info("Starting background ML retrainer daemon...")
    while True:
        await asyncio.sleep(86400)
        try:
            async with async_session() as db:
                await train_models_from_db(db)
        except Exception as e:
            logger.error(f"ML retrain error: {e}")


async def ping_ip_async(ip: str) -> bool:
    """Runs a non-blocking subprocess ping using asyncio."""
    if ip in ("127.0.0.1", "localhost", "::1"):
        return True

    # Check for empty or invalid IPs
    if not ip or not ip.strip():
        return False

    import platform
    system_name = platform.system().lower()
    if system_name == "windows":
        cmd = f"ping -n 1 -w 1000 {ip.strip()}"
    else:
        cmd = f"ping -c 1 -W 1 {ip.strip()}"

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        return proc.returncode == 0
    except Exception:
        return False


async def live_metric_simulation_loop(interval_seconds: int = 30):
    """
    Core telemetry simulation daemon.

    Every `interval_seconds`:
      1. Fetches all active devices from the database.
      2. Executes non-blocking pings in parallel to check reachability.
      3. Gathers real host system metrics via psutil for the HOST_SERVER node.
      4. Generates realistic telemetry using a diurnal sine-wave model for virtual nodes.
      5. Runs ML Isolation Forest anomaly detection on each data point.
      6. Fires threshold-based alerts:
         - Reachability Fails → DEVICE_UNREACHABLE (critical severity)
         - CPU > 80%  → CPU_SPIKE (critical if > 95%)
         - Memory > 80% → MEMORY_HIGH
         - Disk > 90% → DISK_HIGH
         - Latency > 200ms → LATENCY_SPIKE
         - Packet Loss > 3% → PACKET_LOSS
         - ML anomaly (fallback) → ANOMALY_DETECTED
      7. Broadcasts metric_ingested + alert_triggered events via WebSocket
         so the frontend dashboard updates in real-time without polling.
    """
    from app.models.device import Device
    from app.models.metric import DeviceMetric
    from app.services.alerts import AlertService
    from app.schemas.alert import AlertCreate
    from app.services.ws import manager
    from ml.predict import detect_anomaly

    logger.info(f"[TELEMETRY] Live metric simulation daemon starting (interval={interval_seconds}s)...")
    await asyncio.sleep(5)  # Brief delay so startup completes first

    while True:
        try:
            async with async_session() as db:
                dev_res = await db.execute(select(Device).filter(Device.status == "active"))
                devices = dev_res.scalars().all()

                if not devices:
                    logger.debug("[TELEMETRY] No active devices — skipping cycle.")
                else:
                    now = datetime.utcnow()

                    # Check all device reachabilities in parallel via async pings
                    ping_tasks = [ping_ip_async(device.ip_address) for device in devices]
                    ping_results = await asyncio.gather(*ping_tasks)
                    device_reachabilities = {d.id: res for d, res in zip(devices, ping_results)}

                    for device in devices:
                        is_reachable = device_reachabilities[device.id]

                        # Real telemetry collection for HOST_SERVER
                        if device.device_name == "HOST_SERVER":
                            hostname = socket.gethostname()
                            uptime_sec = time.time() - psutil.boot_time()
                            cpu_val = psutil.cpu_percent(interval=None)
                            mem_val = psutil.virtual_memory().percent
                            try:
                                disk_val = psutil.disk_usage("C:\\" if platform.system().lower() == "windows" else "/").percent
                            except Exception:
                                disk_val = 0.0
                            # Gather total network MBs sent+recv
                            net_io = psutil.net_io_counters()
                            bw_val = (net_io.bytes_sent + net_io.bytes_recv) / 1e6

                            payload = {
                                "cpu_usage": round(cpu_val, 1),
                                "memory_usage": round(mem_val, 1),
                                "latency": 0.0,
                                "packet_loss": 0.0,
                                "bandwidth_usage": round(bw_val, 2),
                                "disk_usage": round(disk_val, 1),
                                "hostname": hostname,
                                "uptime": round(uptime_sec, 1),
                                "reachability": True
                            }
                        else:
                            # Simulated telemetry for other nodes
                            payload = _generate_telemetry(device.device_type)
                            payload["reachability"] = is_reachable
                            payload["disk_usage"] = round(random.uniform(15.0, 55.0), 1)
                            payload["hostname"] = f"{device.device_name}.aethernoc.net"
                            payload["uptime"] = round(random.uniform(5000.0, 500000.0), 1)

                            # Outage behavior for unreachable devices
                            if not is_reachable:
                                payload["cpu_usage"] = 0.0
                                payload["memory_usage"] = 0.0
                                payload["latency"] = 999.0
                                payload["packet_loss"] = 100.0
                                payload["bandwidth_usage"] = 0.0

                        # Run ML anomaly detection
                        anomaly_res = detect_anomaly(
                            payload["cpu_usage"],
                            payload["memory_usage"],
                            payload["latency"],
                            payload["packet_loss"],
                            payload["bandwidth_usage"],
                        )

                        # Save metric to database
                        metric = DeviceMetric(
                            device_id=device.id,
                            cpu_usage=payload["cpu_usage"],
                            memory_usage=payload["memory_usage"],
                            latency=payload["latency"],
                            packet_loss=payload["packet_loss"],
                            bandwidth_usage=payload["bandwidth_usage"],
                            disk_usage=payload["disk_usage"],
                            hostname=payload["hostname"],
                            uptime=payload["uptime"],
                            reachability=payload["reachability"],
                            anomaly_score=anomaly_res["anomaly_score"],
                            anomaly_detected=anomaly_res["anomaly_detected"],
                            timestamp=now,
                        )
                        db.add(metric)
                        await db.flush()

                        # ─── Process & Deduplicate Telemetry Alerts ───────────────────
                        fired_alerts, resolved_alerts = await AlertService.process_device_alerts(
                            db, device, payload, anomaly_res
                        )

                        await db.commit()

                        # Broadcast metric update
                        await manager.broadcast({
                            "event": "metric_ingested",
                            "data": {
                                "device_id": device.id,
                                "device_name": device.device_name,
                                "device_type": device.device_type,
                                "cpu_usage": payload["cpu_usage"],
                                "memory_usage": payload["memory_usage"],
                                "latency": payload["latency"],
                                "packet_loss": payload["packet_loss"],
                                "bandwidth_usage": payload["bandwidth_usage"],
                                "disk_usage": payload["disk_usage"],
                                "hostname": payload["hostname"],
                                "uptime": payload["uptime"],
                                "reachability": payload["reachability"],
                                "anomaly_detected": anomaly_res["anomaly_detected"],
                                "anomaly_score": round(anomaly_res["anomaly_score"], 4),
                                "timestamp": now.isoformat(),
                            },
                        })

                        # Broadcast alert triggers
                        for fired_alert in fired_alerts:
                            logger.info(
                                f"[ALERT] {fired_alert.alert_type} on {device.device_name} "
                                f"(severity={fired_alert.severity}, occurrences={fired_alert.occurrence_count})"
                            )
                            await manager.broadcast({
                                "event": "alert_triggered",
                                "data": {
                                    "id": fired_alert.id,
                                    "device_id": device.id,
                                    "device_name": device.device_name,
                                    "alert_type": fired_alert.alert_type,
                                    "severity": fired_alert.severity,
                                    "message": fired_alert.message,
                                    "timestamp": fired_alert.timestamp.isoformat(),
                                    "status": fired_alert.status,
                                    "occurrence_count": fired_alert.occurrence_count,
                                    "first_seen": fired_alert.first_seen.isoformat() if fired_alert.first_seen else None,
                                    "last_seen": fired_alert.last_seen.isoformat() if fired_alert.last_seen else None,
                                },
                            })

                        # Broadcast alert resolutions
                        for resolved_alert in resolved_alerts:
                            logger.info(
                                f"[ALERT_RESOLVED] {resolved_alert.alert_type} on {device.device_name} cleared."
                            )
                            await manager.broadcast({
                                "event": "alert_resolved",
                                "data": {
                                    "id": resolved_alert.id,
                                    "device_id": device.id,
                                    "device_name": device.device_name,
                                    "alert_type": resolved_alert.alert_type,
                                    "severity": resolved_alert.severity,
                                    "message": resolved_alert.message,
                                    "timestamp": resolved_alert.timestamp.isoformat(),
                                    "status": resolved_alert.status,
                                    "resolved_at": resolved_alert.resolved_at.isoformat() if resolved_alert.resolved_at else None,
                                    "occurrence_count": resolved_alert.occurrence_count,
                                    "first_seen": resolved_alert.first_seen.isoformat() if resolved_alert.first_seen else None,
                                    "last_seen": resolved_alert.last_seen.isoformat() if resolved_alert.last_seen else None,
                                },
                            })

                    logger.debug(f"[TELEMETRY] Cycle done — {len(devices)} device(s) processed.")

        except Exception as e:
            logger.error(f"[TELEMETRY] Simulation loop error: {e}", exc_info=True)

        await asyncio.sleep(interval_seconds)


async def seed_initial_metrics():
    """
    Seeds 2 hours of historical metrics on first startup when the database is empty.
    Ensures charts and the dashboard are populated immediately on fresh installs
    or Render cold-start deployments.
    """
    from app.models.device import Device
    from app.models.metric import DeviceMetric

    try:
        async with async_session() as db:
            count_res = await db.execute(select(func.count(DeviceMetric.id)))
            existing = count_res.scalar() or 0

            if existing > 0:
                logger.info(f"[STARTUP] {existing} metrics already in database — skipping seed.")
                return

            dev_res = await db.execute(select(Device))
            devices = dev_res.scalars().all()

            if not devices:
                logger.info("[STARTUP] No devices registered — skipping metric seed.")
                return

            logger.info(f"[STARTUP] Seeding 2h of historical metrics for {len(devices)} device(s)...")
            now = datetime.utcnow()
            total = 0

            for device in devices:
                # 24 intervals × 5 minutes = 2 hours of history
                for i in range(24, 0, -1):
                    ts = now - timedelta(minutes=i * 5)
                    p = _generate_telemetry(device.device_type)
                    db.add(DeviceMetric(
                        device_id=device.id,
                        cpu_usage=p["cpu_usage"],
                        memory_usage=p["memory_usage"],
                        latency=p["latency"],
                        packet_loss=p["packet_loss"],
                        bandwidth_usage=p["bandwidth_usage"],
                        anomaly_score=0.0,
                        anomaly_detected=False,
                        timestamp=ts,
                    ))
                    total += 1

            await db.commit()
            logger.info(f"[STARTUP] Seeded {total} historical metric records.")

    except Exception as e:
        logger.error(f"[STARTUP] Metric seed error: {e}", exc_info=True)


# ============================================================
# Application Lifecycle Helper Functions (Phase 2 additions)
# ============================================================
async def patch_database_schema():
    """
    Ensures that device_metrics and alerts tables have all the required columns for
    real telemetry and alert deduplication.
    """
    from sqlalchemy import text
    try:
        async with async_session() as db:
            # 1. Patch device_metrics table
            metrics_cols = [
                ("disk_usage", "FLOAT NULL"),
                ("hostname", "VARCHAR(100) NULL"),
                ("uptime", "FLOAT NULL"),
                ("reachability", "BOOLEAN NOT NULL DEFAULT 1")
            ]
            for col_name, col_type in metrics_cols:
                try:
                    await db.execute(text(f"ALTER TABLE device_metrics ADD COLUMN {col_name} {col_type}"))
                    logger.info(f"[DB_PATCH] Added column {col_name} to device_metrics table.")
                except Exception as e:
                    logger.debug(f"[DB_PATCH] device_metrics column {col_name} check: {e}")

            # 2. Patch alerts table for deduplication
            alerts_cols = [
                ("occurrence_count", "INTEGER NOT NULL DEFAULT 1"),
                ("first_seen", "DATETIME NULL"),
                ("last_seen", "DATETIME NULL")
            ]
            for col_name, col_type in alerts_cols:
                try:
                    await db.execute(text(f"ALTER TABLE alerts ADD COLUMN {col_name} {col_type}"))
                    logger.info(f"[DB_PATCH] Added column {col_name} to alerts table.")
                except Exception as e:
                    logger.debug(f"[DB_PATCH] alerts column {col_name} check: {e}")

            # 3. Deduplicate any legacy active alerts in the database
            try:
                stmt = text(
                    "SELECT device_id, alert_type, COUNT(*) as cnt "
                    "FROM alerts WHERE status != 'resolved' "
                    "GROUP BY device_id, alert_type HAVING cnt > 1"
                )
                res = await db.execute(stmt)
                duplicates = res.all()
                if duplicates:
                    logger.info(f"[DB_PATCH] Found {len(duplicates)} unique groups of duplicate active alerts to deduplicate.")
                    for device_id, alert_type, cnt in duplicates:
                        # Get all active alerts of this type for this device, sorted by timestamp ascending
                        stmt_alerts = text(
                            "SELECT id, occurrence_count, timestamp, first_seen, last_seen "
                            "FROM alerts WHERE device_id = :device_id AND alert_type = :alert_type AND status != 'resolved' "
                            "ORDER BY timestamp ASC"
                        )
                        res_alerts = await db.execute(stmt_alerts, {"device_id": device_id, "alert_type": alert_type})
                        alerts_list = res_alerts.all()
                        
                        master_alert = alerts_list[0]
                        master_id = master_alert.id
                        
                        total_occurrences = 0
                        earliest_seen = master_alert.timestamp
                        latest_seen = master_alert.timestamp
                        
                        # Support cases where timestamp/first_seen is string (sqlite returning raw text)
                        from datetime import datetime
                        def parse_dt(val):
                            if isinstance(val, str):
                                # SQLite datetime formats can vary
                                for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                                    try:
                                        return datetime.strptime(val, fmt)
                                    except ValueError:
                                        continue
                            return val or datetime.utcnow()

                        earliest_seen = parse_dt(earliest_seen)
                        latest_seen = parse_dt(latest_seen)
                        
                        for a in alerts_list:
                            total_occurrences += (a.occurrence_count or 1)
                            t = parse_dt(a.timestamp)
                            if t < earliest_seen:
                                earliest_seen = t
                            if t > latest_seen:
                                latest_seen = t
                        
                        # Update master alert
                        stmt_update = text(
                            "UPDATE alerts SET occurrence_count = :occ, "
                            "first_seen = :first, last_seen = :last "
                            "WHERE id = :id"
                        )
                        await db.execute(stmt_update, {
                            "occ": total_occurrences,
                            "first": earliest_seen.strftime("%Y-%m-%d %H:%M:%S.%f"),
                            "last": latest_seen.strftime("%Y-%m-%d %H:%M:%S.%f"),
                            "id": master_id
                        })
                        
                        # Delete the other duplicate records
                        other_ids = [a.id for a in alerts_list[1:]]
                        for other_id in other_ids:
                            await db.execute(text("DELETE FROM alert_history WHERE alert_id = :id"), {"id": other_id})
                            await db.execute(text("DELETE FROM alerts WHERE id = :id"), {"id": other_id})
                            
                    logger.info("[DB_PATCH] Completed deduplication of legacy active alerts.")
            except Exception as e:
                logger.error(f"[DB_PATCH] Error deduplicating legacy alerts: {e}", exc_info=True)

            await db.commit()
    except Exception as e:
        logger.error(f"[DB_PATCH] Error patching database schema: {e}")


async def seed_host_device():
    """
    Registers a HOST_SERVER device with IP 127.0.0.1 in the devices table if not already present,
    so that we have a real target for host metric collection.
    """
    from app.models.device import Device
    try:
        async with async_session() as db:
            res = await db.execute(select(Device).filter(Device.device_name == "HOST_SERVER"))
            host_dev = res.scalars().first()
            if not host_dev:
                new_dev = Device(
                    id="host-server-id",
                    device_name="HOST_SERVER",
                    ip_address="127.0.0.1",
                    location="Local host hypervisor",
                    device_type="server",
                    status="active"
                )
                db.add(new_dev)
                await db.commit()
                logger.info("[STARTUP] Registered HOST_SERVER device for real host telemetry.")
    except Exception as e:
        logger.error(f"[STARTUP] Error seeding host device: {e}")


# ============================================================
# Application Lifecycle
# ============================================================
@app.on_event("startup")
async def on_startup():
    """
    Runs once when the server starts. Bootstraps ML models, seeds data,
    and launches all background daemons.
    """
    logger.info(f"[STARTUP] {settings.APP_NAME} v{settings.APP_VERSION} is starting...")

    # 0. Patch database schema and seed host server device
    await patch_database_schema()
    await seed_host_device()

    # 1. Train ML models if binaries are missing
    if not os.path.exists(AD_PATH) or not os.path.exists(FP_PATH):
        logger.info("[STARTUP] ML model binaries missing — bootstrapping training...")
        async with async_session() as db:
            try:
                await train_models_from_db(db)
            except Exception as e:
                logger.error(f"[STARTUP] ML bootstrap error: {e}")

    # 2. Seed initial metrics if database is empty
    await seed_initial_metrics()

    # 3. Launch background daemons
    asyncio.create_task(check_sla_breaches_background_loop())
    asyncio.create_task(retrain_models_background_loop())
    asyncio.create_task(live_metric_simulation_loop(interval_seconds=30))

    # 4. Initialize Copilot RAG vector store
    try:
        from app.services.copilot import vector_store
        vector_store.initialize_store()
        logger.info("[STARTUP] Copilot RAG Vector Store initialized.")
    except Exception as e:
        logger.error(f"[STARTUP] Copilot RAG init error: {e}")

    logger.info(f"[STARTUP] API Docs: http://localhost:{settings.PORT}/docs")
    logger.info("[STARTUP] Live telemetry daemon active (30s interval).")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info(f"[SHUTDOWN] {settings.APP_NAME} shutting down...")


# ============================================================
# Health Check Routes
# ============================================================
@app.get("/", tags=["Health"], summary="Root")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "status": "operational",
    }


@app.get("/health", tags=["Health"], summary="Health Check")
async def health_check():
    db_ok = True
    try:
        async with async_session() as db:
            await db.execute(select(1))
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }
