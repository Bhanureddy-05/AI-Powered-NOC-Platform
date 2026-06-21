"""
app/db/init_db.py
=================
Database Initialization Script

WHY THIS FILE EXISTS:
    Instead of manually running SQL CREATE TABLE scripts, SQLAlchemy allows us to
    generate the database tables directly from our python models using metadata.
    This script provides an async helper to build all the registered tables in PostgreSQL.
"""

import asyncio
import sys
from app.db.base import Base
from app.db.session import engine

# Import all models so they register on Base.metadata before creation
from app.models import User, Device, DeviceMetric, Alert, Ticket, AuditLog

async def create_tables():
    """
    Connects to the database and builds all registered ORM tables asynchronously.
    """
    print("[DATABASE] Connecting to database and creating tables...")
    try:
        async with engine.begin() as conn:
            # run_sync executes sync functions (metadata.create_all) in an async context
            await conn.run_sync(Base.metadata.create_all)
        print("[DATABASE] Database tables generated successfully!")
    except Exception as e:
        print(f"[ERROR] Error creating database tables: {e}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(create_tables())
