from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.common import MessageResponse
from app.schemas.task_comment import CommentCreate, CommentRead, CommentUpdate
from app.services import comment_service

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["Comments"])


@router.post("", response_model=CommentRead, status_code=201)
async def add_comment(
    task_id: UUID,
    data: CommentCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await comment_service.add_comment(task_id, data, current_user, db)


@router.get("", response_model=list[CommentRead])
async def list_comments(
    task_id: UUID,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await comment_service.list_comments(task_id, db)


@router.patch("/{comment_id}", response_model=CommentRead)
async def update_comment(
    task_id: UUID,
    comment_id: UUID,
    data: CommentUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await comment_service.update_comment(task_id, comment_id, data, current_user, db)


@router.delete("/{comment_id}", response_model=MessageResponse)
async def delete_comment(
    task_id: UUID,
    comment_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await comment_service.delete_comment(task_id, comment_id, current_user, db)
    return MessageResponse(message="Comment deleted")
