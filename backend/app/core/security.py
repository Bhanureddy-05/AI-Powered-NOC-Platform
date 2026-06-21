"""
app/core/security.py
===================
Cryptography and Authentication Helper Utilities

WHY THIS FILE EXISTS:
    To keep application handlers clean, we centralize password encryption
    and JSON Web Token (JWT) management here. This ensures that passwords
    are salted and hashed using standard bcrypt techniques and tokens are
    signed using HMACS.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
import bcrypt
from app.core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compares a plain text password with its database hash using salted comparison.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """
    Computes a secure Bcrypt hash of the user's password.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def create_access_token(
    subject: Union[str, Any], role: str, expires_delta: timedelta = None
) -> str:
    """
    Generates a secure, signed JWT token to authenticate subsequent API client calls.
    
    Args:
        subject (str): The identifier for the user (usually their username).
        role (str): The user's role scope (e.g., admin, operator).
        expires_delta (timedelta): Duration for token validity.
        
    Returns:
        str: Signed JWT string.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Pack username (sub), role, and expiration (exp) into claims
    to_encode = {"sub": str(subject), "role": role, "exp": expire}
    
    # Sign token using HS256 algorithm with our secret key
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
