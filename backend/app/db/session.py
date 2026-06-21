"""
app/db/session.py
=================
Database Session & Connection Configuration

WHY THIS FILE EXISTS:
    This file initializes the SQLAlchemy async database engine and defines a
    sessionmaker. It provides a FastAPI dependency function `get_db()` that yields
    a database connection for each API request and ensures it is closed after.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

# 1. Determine DB Connection Details
db_url = settings.DATABASE_URL
if settings.USE_SQLITE:
    db_url = "sqlite+aiosqlite:///./noc_platform.db"

# Create engine arguments
engine_args = {
    "echo": settings.DEBUG,
    "future": True,
}

# Only include pooling options if using a network database like PostgreSQL
if not db_url.startswith("sqlite"):
    engine_args.update({
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    })

engine = create_async_engine(db_url, **engine_args)


# 2. Create the Session Factory
# expire_on_commit=False prevents SQLAlchemy from expiring attributes after a commit,
# which is crucial for async workflows where deferred loading can fail.
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 3. Define the DB Dependency Generator
# This will be injected into our FastAPI path operations.
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency generator for database sessions.
    FastAPI will instantiate a session for each request, yield it,
    and guarantee cleanup (close) even if exceptions occur.
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
