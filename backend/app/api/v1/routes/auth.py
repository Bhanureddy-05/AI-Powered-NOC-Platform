"""
app/api/v1/routes/auth.py
=========================
Authentication & Session Management Routers

WHY THIS FILE EXISTS:
    This file handles user session endpoints (register, login, me).
    It parses incoming JSON payloads, queries PostgreSQL using async SQLAlchemy,
    hashes credentials, generates JWT access keys, and tracks actions via audit logs.
"""

from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.db.session import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token, TokenData

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Define standard OAuth2 password flow scheme.
# Swagger UI will read this token url to automatically enable locked lock icons.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login-form")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency to extract and validate the JWT token from the request headers.
    Returns the authenticated user model instance, or raises 401 if invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode JWT signature
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception

    # Query DB to make sure user still exists
    result = await db.execute(select(User).filter(User.username == token_data.username))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user


def check_role(required_roles: list[str]):
    """
    RBAC dependency helper to enforce role requirements on routes.
    """
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )
        return current_user
    return role_checker


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate, request: Request, db: AsyncSession = Depends(get_db)
):
    """
    Registers a new operations user profile.
    Hashed credentials are saved to PostgreSQL.
    """
    # 1. Check if username exists
    username_check = await db.execute(select(User).filter(User.username == user_in.username))
    if username_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already registered",
        )

    # 2. Check if email exists
    email_check = await db.execute(select(User).filter(User.email == user_in.email))
    if email_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    # 3. Create new user instance
    hashed_pwd = get_password_hash(user_in.password)
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_pwd,
        role=user_in.role or "operator",
    )
    db.add(new_user)
    await db.flush()  # Populate the DB generated auto-increment id

    # 4. Log the registration event in audit log
    audit = AuditLog(
        user_id=new_user.id,
        action="user_registered",
        details=f"Username: {new_user.username}, Role: {new_user.role}",
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
async def login_json(
    credentials: UserLogin, request: Request, db: AsyncSession = Depends(get_db)
):
    """
    JSON-based login endpoint. Returns signed access token.
    """
    # Look up user by username or email
    result = await db.execute(
        select(User).filter(
            (User.username == credentials.username) | (User.email == credentials.username)
        )
    )
    user = result.scalars().first()

    # Validate user credentials
    if not user or not verify_password(credentials.password, user.hashed_password):
        # Log failed login attempt
        audit = AuditLog(
            user_id=None,
            action="login_failed",
            details=f"Failed attempt for user: {credentials.username}",
            ip_address=request.client.host if request.client else "127.0.0.1",
        )
        db.add(audit)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Log successful login
    audit = AuditLog(
        user_id=user.id,
        action="login_success",
        details=f"User {user.username} logged in successfully",
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    db.add(audit)

    # Generate token
    token_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.username, role=user.role, expires_delta=token_expire
    )
    await db.commit()

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """
    Returns the currently active user profile.
    This is a protected route.
    """
    return current_user


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Returns list of all registered user profiles for assignments.
    """
    result = await db.execute(select(User))
    return result.scalars().all()



from fastapi.security import OAuth2PasswordRequestForm

@router.post("/login-form", response_model=Token)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible form login endpoint for Swagger UI.
    """
    result = await db.execute(select(User).filter(User.username == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    token_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.username, role=user.role, expires_delta=token_expire
    )
    return {"access_token": access_token, "token_type": "bearer"}

