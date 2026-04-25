import math
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.user import Role, User
from app.schemas.user import UserRoleUpdate, UserUpdate


async def list_users(db: AsyncSession, page: int = 1, page_size: int = 20):
    offset = (page - 1) * page_size
    total_result = await db.execute(select(func.count()).select_from(User))
    total = total_result.scalar_one()

    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size)
    )
    users = result.scalars().all()

    return {
        "items": list(users),
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total else 1,
    }


async def get_user(user_id: UUID, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User", str(user_id))
    return user


async def activate_user(user_id: UUID, db: AsyncSession) -> User:
    user = await get_user(user_id, db)
    user.is_active = True
    await db.flush()
    return user


async def deactivate_user(user_id: UUID, db: AsyncSession) -> User:
    user = await get_user(user_id, db)
    user.is_active = False
    await db.flush()
    return user


async def update_user_role(user_id: UUID, data: UserRoleUpdate, db: AsyncSession) -> User:
    user = await get_user(user_id, db)
    user.role = data.role
    await db.flush()
    return user
