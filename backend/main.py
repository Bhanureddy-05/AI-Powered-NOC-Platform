"""
app/main.py
===========
FastAPI Application Entry Point

WHY THIS FILE EXISTS:
    This is the "front door" of your entire backend application.
    When you start the server, it boots from this file.
    All routes, middleware, and startup logic are wired here.

WHAT IS FastAPI?
    FastAPI is a modern Python web framework that automatically:
    - Generates API documentation (Swagger UI) at /docs
    - Validates request/response data using Python type hints
    - Handles async operations efficiently
"""

import asyncio
import time
import logging
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.api.v1.api import api_router
from app.db.session import async_session
from app.services.tickets import TicketService
from ml.train import train_models_from_db
from ml.anomaly_detection import MODEL_PATH as AD_PATH
from ml.failure_prediction import MODEL_PATH as FP_PATH

# ============================================================
# Setup Structured / Console Logging Configuration
# ============================================================
logging.basicConfig(
    level=logging.INFO if settings.APP_ENV == "production" else logging.DEBUG,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}'
)
logger = logging.getLogger("noc_platform")

# ============================================================
# Create the FastAPI Application Instance
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Rate Limiting Middleware (Custom In-Memory Implementation)
# ============================================================
RATE_LIMIT_DURATION = 60 # 1 minute window
MAX_REQUESTS = 30        # Max 30 requests per minute
ip_request_counts = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    # Only rate limit auth endpoints (login and register) to prevent brute-force
    if path.startswith("/api/v1/auth/login") or path.startswith("/api/v1/auth/register"):
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        
        # Clean older requests from registry window
        ip_request_counts[client_ip] = [t for t in ip_request_counts.get(client_ip, []) if now - t < RATE_LIMIT_DURATION]
        
        if len(ip_request_counts[client_ip]) >= MAX_REQUESTS:
            logger.warning(f"Rate limit exceeded for client: {client_ip} on path: {path}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many login/registration attempts. Please try again in 1 minute."}
            )
            
        ip_request_counts[client_ip].append(now)
        
    return await call_next(request)


# ============================================================
# Global Exception Handlers
# ============================================================
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"SQLAlchemy Database Error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "A database operation failed. Transaction rolled back."}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Server Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."}
    )


# ============================================================
# API Routers Mount
# ============================================================
app.include_router(api_router, prefix="/api/v1")


# ============================================================
# Background Loops
# ============================================================
async def check_sla_breaches_background_loop():
    """
    Periodic task running every 60 seconds to search for breached ticket SLAs.
    """
    logger.info("Starting background SLA tracker daemon...")
    while True:
        await asyncio.sleep(60)
        try:
            async with async_session() as db:
                await TicketService.check_sla_breaches(db)
        except Exception as e:
            logger.error(f"Error checking SLA breaches in background: {e}")

async def retrain_models_background_loop():
    """
    Periodic task running daily to retrain isolation forest and random forest models.
    """
    logger.info("Starting background ML retrainer daemon...")
    while True:
        await asyncio.sleep(86400) # Daily (24h)
        try:
            async with async_session() as db:
                await train_models_from_db(db)
        except Exception as e:
            logger.error(f"Error retraining ML models in background: {e}")


# ============================================================
# Application Lifecycle Events
# ============================================================
@app.on_event("startup")
async def on_startup():
    """
    Runs ONCE when the server starts.
    Bootstraps background loops and trains initial ML models if missing.
    """
    logger.info(f"[STARTUP] {settings.APP_NAME} v{settings.APP_VERSION} is starting...")
    
    # 1. Initialize ML saved models if they are missing
    if not os.path.exists(AD_PATH) or not os.path.exists(FP_PATH):
        logger.info("[STARTUP] Persisted ML model binaries not found. Bootstrapping training...")
        async with async_session() as db:
            try:
                await train_models_from_db(db)
            except Exception as e:
                logger.error(f"[STARTUP] Error training initial models: {e}")
                
    # 2. Start background tasks
    asyncio.create_task(check_sla_breaches_background_loop())
    asyncio.create_task(retrain_models_background_loop())
    
    # 3. Initialize the Copilot RAG Vector Store
    try:
        from app.services.copilot import vector_store
        vector_store.initialize_store()
        logger.info("[STARTUP] Copilot RAG Vector Store initialized.")
    except Exception as e:
        logger.error(f"[STARTUP] Error initializing Copilot RAG Vector Store: {e}")

    logger.info(f"[STARTUP] API Docs available at: http://localhost:{settings.PORT}/docs")


@app.on_event("shutdown")
async def on_shutdown():
    """
    Runs ONCE when the server shuts down.
    """
    logger.info(f"[SHUTDOWN] {settings.APP_NAME} is shutting down...")


# ============================================================
# Root Route — Health Check Endpoint
# ============================================================
@app.get(
    "/",
    tags=["Health"],
    summary="Root endpoint",
    description="Returns a simple welcome message to confirm the API is running.",
)
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "status": "operational",
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Returns the health status of the API. Used by load balancers and monitoring tools.",
)
async def health_check():
    # Database connectivity test
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

