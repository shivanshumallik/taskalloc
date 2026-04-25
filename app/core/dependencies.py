from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_access_token
from app.models.user import Role, User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if not credentials:
        raise UnauthorizedException("Bearer token required")

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise UnauthorizedException("Invalid or expired token")

    user_id: str = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token payload")

    result = await db.execute(
        select(User)
        .options(selectinload(User.employee_profile))
        .where(User.id == UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException("User not found")
    if not user.is_active:
        raise ForbiddenException("Account is deactivated")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: Role):
    async def role_checker(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise ForbiddenException(
                f"This action requires one of: {[r.value for r in roles]}"
            )
        return current_user
    return role_checker


def require_admin():
    return require_role(Role.ADMIN)


def require_admin_or_manager():
    return require_role(Role.ADMIN, Role.MANAGER)
