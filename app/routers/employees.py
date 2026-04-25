from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_admin, require_admin_or_manager
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeStats, EmployeeUpdate
from app.schemas.task import TaskRead
from app.services import employee_service

router = APIRouter(prefix="/employees", tags=["Employees"])
AdminUser = Annotated[User, Depends(require_admin())]
AdminOrManager = Annotated[User, Depends(require_admin_or_manager())]


@router.post("", response_model=EmployeeRead, status_code=201)
async def create_employee(
    data: EmployeeCreate,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await employee_service.create_employee(data, db)


@router.get("", response_model=PaginatedResponse[EmployeeRead])
async def list_employees(
    current_user: AdminOrManager,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return await employee_service.list_employees(db, current_user, page, page_size)


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: UUID,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await employee_service.get_employee(employee_id, db)


@router.patch("/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    employee_id: UUID,
    data: EmployeeUpdate,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await employee_service.update_employee(employee_id, data, db)


@router.delete("/{employee_id}", response_model=MessageResponse)
async def delete_employee(
    employee_id: UUID,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await employee_service.delete_employee(employee_id, db)
    return MessageResponse(message="Employee deactivated")


@router.get("/{employee_id}/tasks", response_model=PaginatedResponse[TaskRead])
async def get_employee_tasks(
    employee_id: UUID,
    _: AdminOrManager,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return await employee_service.get_employee_tasks(employee_id, db, page, page_size)


@router.get("/{employee_id}/stats", response_model=EmployeeStats)
async def get_employee_stats(
    employee_id: UUID,
    _: AdminOrManager,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await employee_service.get_employee_stats(employee_id, db)
