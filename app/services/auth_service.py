from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
)


async def register_user(data: RegisterRequest, db: AsyncSession) -> User:
    # Check uniqueness
    existing = await db.execute(
        select(User).where(
            (User.email == data.email) | (User.username == data.username)
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictException("Email or username already registered")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        is_verified=True,  # Auto-verify for now; add email flow later
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def login_user(
    data: LoginRequest, db: AsyncSession, ip_address: str = ""
) -> tuple[str, str]:
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise UnauthorizedException("Invalid email or password")

    if not user.is_active:
        raise UnauthorizedException("Account is deactivated")

    # Update last login
    user.last_login = datetime.now(timezone.utc)

    # Create tokens
    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    raw_refresh, hashed_refresh = create_refresh_token()

    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=7),
        ip_address=ip_address,
    )
    db.add(refresh_record)
    await db.flush()

    return access_token, raw_refresh


async def refresh_access_token(raw_token: str, db: AsyncSession) -> str:
    token_hash = hash_refresh_token(raw_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise UnauthorizedException("Invalid refresh token")
    if record.is_revoked:
        raise UnauthorizedException("Refresh token has been revoked")
    # Make expires_at timezone-aware if stored as naive (SQLite compat)
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise UnauthorizedException("Refresh token has expired")

    # Load user
    user_result = await db.execute(select(User).where(User.id == record.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedException("User not found or deactivated")

    # Rotate: revoke old, issue new access token
    record.is_revoked = True

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return access_token


async def logout_user(raw_token: str, db: AsyncSession) -> None:
    token_hash = hash_refresh_token(raw_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()
    if record:
        record.is_revoked = True


async def change_password(
    user: User, data: ChangePasswordRequest, db: AsyncSession
) -> None:
    if not verify_password(data.current_password, user.hashed_password):
        raise BadRequestException("Current password is incorrect")

    user.hashed_password = hash_password(data.new_password)

    # Revoke all refresh tokens (force re-login everywhere)
    tokens_result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.is_revoked == False
        )
    )
    for token in tokens_result.scalars().all():
        token.is_revoked = True
