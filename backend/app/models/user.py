"""
app/models/user.py
==================
SQLAlchemy DB Model for the 'users' Table

WHY THIS FILE EXISTS:
    Every secure, multi-tenant platform needs to represent user accounts.
    This model defines how user credentials, contact details, and role-based
    access control (RBAC) classifications are stored in the database.
"""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Column
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    # id uses standard auto-incrementing integer (Primary Key)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # username and email are unique and indexed for fast query lookups
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    
    # hashed_password stores bcrypt-derived password hashes, NEVER plain text
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # role is used for Role-Based Access Control (RBAC): 'admin', 'operator', 'viewer'
    role: Mapped[str] = mapped_column(String(20), default="operator", nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    tickets = relationship("Ticket", back_populates="assignee")
    audit_logs = relationship("AuditLog", back_populates="actor")
    copilot_sessions = relationship("CopilotSession", back_populates="user", cascade="all, delete-orphan")
