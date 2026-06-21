"""
app/api/v1/api.py
=================
V1 Router Aggregations

WHY THIS FILE EXISTS:
    As your application scales, mounting dozens of routes directly in main.py
    becomes a bottleneck. This file acts as the central router junction, aggregating
    feature-specific routes (auth, devices, metrics, alerts, tickets) and exposing
    them as a single `/api/v1` router namespace.
"""

from fastapi import APIRouter
from app.api.v1.routes import auth, devices, metrics, alerts, tickets, ml, reports, ws, audit, copilot

api_router = APIRouter()

# Register sub-routers under the main aggregator
api_router.include_router(auth.router)
api_router.include_router(devices.router)
api_router.include_router(metrics.router)
api_router.include_router(alerts.router)
api_router.include_router(tickets.router)
api_router.include_router(ml.router)
api_router.include_router(reports.router)
api_router.include_router(ws.router)
api_router.include_router(audit.router)
api_router.include_router(copilot.router)


