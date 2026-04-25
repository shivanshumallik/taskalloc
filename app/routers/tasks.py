from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_admin, require_admin_or_manager
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.task import (
    TaskAssignUpdate,
    TaskCreate,
    TaskFilter,
    TaskRead,
    TaskStatusUpdate,
    TaskUpdate,
    TaskPriority,
    TaskStatus,
)
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])
AdminOrManager = Annotated[User, Depends(require_admin_or_manager())]
AdminUser = Annotated[User, Depends(require_admin())]


@router.post("", response_model=TaskRead, status_code=201)
async def create_task(
    data: TaskCreate,
    current_user: AdminOrManager,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await task_service.create_task(data, current_user, db)


@router.get("", response_model=PaginatedResponse[TaskRead])
async def list_tasks(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    status: TaskStatus | None = Query(None),
    priority: TaskPriority | None = Query(None),
    assigned_to: UUID | None = Query(None),
    department_id: UUID | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
):
    filters = TaskFilter(
        status=status,
        priority=priority,
        assigned_to=assigned_to,
        department_id=department_id,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return await task_service.list_tasks(filters, current_user, db)


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await task_service.get_task(task_id, current_user, db)


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: UUID,
    data: TaskUpdate,
    current_user: AdminOrManager,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await task_service.update_task(task_id, data, current_user, db)


@router.patch("/{task_id}/status", response_model=TaskRead)
async def update_task_status(
    task_id: UUID,
    data: TaskStatusUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await task_service.update_task_status(task_id, data, current_user, db)


@router.patch("/{task_id}/assign", response_model=TaskRead)
async def reassign_task(
    task_id: UUID,
    data: TaskAssignUpdate,
    current_user: AdminOrManager,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await task_service.reassign_task(task_id, data, current_user, db)


@router.delete("/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: UUID,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await task_service.delete_task(task_id, current_user, db)
    return MessageResponse(message="Task deleted")


@router.get("/{task_id}/activity")
async def get_task_activity(
    task_id: UUID,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logs = await task_service.get_task_activity(task_id, db)
    return [
        {
            "id": str(log.id),
            "actor_id": str(log.actor_id),
            "action": log.action,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "timestamp": log.timestamp.isoformat(),
        }
        for log in logs
    ]
