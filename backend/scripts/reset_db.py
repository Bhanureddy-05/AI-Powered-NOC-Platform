"""
scripts/reset_db.py
===================
Database Schema Reset Helper

WHY THIS FILE EXISTS:
    To accommodate updates to Alert and Ticket schemas (adding SLA columns, 
    comment tables, and history logs) during development, this script drops 
    the local SQLite database file and rebuilds all registered tables.
"""

import asyncio
import os
import sys

# Adjust python path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import Base
from app.db.session import engine
from app.models import User, Device, DeviceMetric, Alert, AlertHistory, Ticket, TicketComment, TicketHistory, AuditLog, CopilotSession, CopilotMessage

async def reset_db():
    print("[RESET] Starting database reset sequence...")
    
    # SQLite cleanup: remove the file if it exists to clean constraints
    db_file = "noc_platform.db"
    if os.path.exists(db_file):
        try:
            # Close the engine first to release file locks
            await engine.dispose()
            os.remove(db_file)
            print(f"[RESET] Deleted SQLite database file: {db_file}")
        except Exception as e:
            print(f"[RESET] Warning: Could not delete {db_file} file: {e}. Attempting drop_all...")
            
    try:
        async with engine.begin() as conn:
            # Fallback metadata drops if SQLite file wasn't deleted
            await conn.run_sync(Base.metadata.drop_all)
            print("[RESET] Dropped existing schemas using SQLAlchemy.")
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            print("[RESET] Created new database tables successfully!")
            
        print("[RESET] Database reset complete! Ready for seeder metrics.")
    except Exception as e:
        print(f"[ERROR] Database reset sequence failed: {e}", file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(reset_db())
