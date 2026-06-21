"""
app/db/base.py
==============
Declarative Base for SQLAlchemy Models

WHY THIS FILE EXISTS:
    SQLAlchemy requires a base class that registers all ORM models. This base class
    maintains a registry of tables and schemas, allowing us to generate DDL (SQL)
    and manage database transactions.
"""

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    Unified Base class for all ORM models.
    Provides standard metadata registration.
    """
    pass
