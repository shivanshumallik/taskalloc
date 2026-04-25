from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_admin
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.schemas.employee import EmployeeRead
from app.services import department_service

router = APIRouter(prefix="/departments", tags=["Departments"])
AdminUser = Annotated[User, Depends(require_admin())]


@router.post("", response_model=DepartmentRead, status_code=201)
async def create_department(
    data: DepartmentCreate,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await department_service.create_department(data, current_user, db)


@router.get("", response_model=PaginatedResponse[DepartmentRead])
async def list_departments(
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return await department_service.list_departments(db, page, page_size)


@router.get("/{dept_id}", response_model=DepartmentRead)
async def get_department(
    dept_id: UUID,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await department_service.get_department(dept_id, db)


@router.patch("/{dept_id}", response_model=DepartmentRead)
async def update_department(
    dept_id: UUID,
    data: DepartmentUpdate,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await department_service.update_department(dept_id, data, db)


@router.delete("/{dept_id}", response_model=MessageResponse)
async def delete_department(
    dept_id: UUID,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await department_service.delete_department(dept_id, db)
    return MessageResponse(message="Department deactivated")


@router.get("/{dept_id}/employees", response_model=PaginatedResponse[EmployeeRead])
async def get_department_employees(
    dept_id: UUID,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return await department_service.get_department_employees(dept_id, db, page, page_size)
