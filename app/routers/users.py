from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import UserListResponse, UserRoleUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])
AdminUser = Annotated[User, Depends(require_admin())]


@router.get("", response_model=PaginatedResponse[UserListResponse])
async def list_users(
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return await user_service.list_users(db, page, page_size)


@router.get("/{user_id}", response_model=UserListResponse)
async def get_user(
    user_id: UUID,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await user_service.get_user(user_id, db)


@router.patch("/{user_id}/activate", response_model=MessageResponse)
async def activate_user(
    user_id: UUID,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await user_service.activate_user(user_id, db)
    return MessageResponse(message="User activated")


@router.patch("/{user_id}/deactivate", response_model=MessageResponse)
async def deactivate_user(
    user_id: UUID,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await user_service.deactivate_user(user_id, db)
    return MessageResponse(message="User deactivated")


@router.patch("/{user_id}/role", response_model=MessageResponse)
async def update_role(
    user_id: UUID,
    data: UserRoleUpdate,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await user_service.update_user_role(user_id, data, db)
    return MessageResponse(message="Role updated")
