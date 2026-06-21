"""
app/schemas/user.py
===================
Pydantic Schemas for User Operations

WHY THIS FILE EXISTS:
    While database models (SQLAlchemy) handle storage layout, Pydantic schemas
    handle input/output validation, parsing, and serialization. This separates 
    how data is validated over the network from how it resides in the database,
    protecting the app against SQL injection, wrong data types, and leakage of
    password hashes in responses.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    """
    Shared properties for user input.
    """
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="User's professional email address")

class UserCreate(UserBase):
    """
    Validation schema for new registration requests.
    Includes the raw password field.
    """
    password: str = Field(..., min_length=8, description="Minimum 8-character password")
    role: Optional[str] = Field(default="operator", description="Access scope: admin, operator, or viewer")

class UserResponse(UserBase):
    """
    Serialization schema for returning user data.
    Does NOT include the password or password hash.
    """
    id: int
    role: str
    created_at: datetime

    class Config:
        """
        Tells Pydantic to read data from ORM objects (like SQLAlchemy instances)
        instead of only parsing dictionary inputs.
        """
        from_attributes = True

class UserLogin(BaseModel):
    """
    Validation schema for login requests.
    """
    username: str = Field(..., description="Username or email address")
    password: str = Field(..., description="Raw password")

class Token(BaseModel):
    """
    Response schema containing the authentication token.
    """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """
    Internal token payload structure.
    """
    username: Optional[str] = None
    role: Optional[str] = None
