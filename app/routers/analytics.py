from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin_or_manager
from app.models.user import User
from app.schemas.analytics import OverdueTask, OverviewStats
from app.schemas.employee import EmployeeStats
from app.schemas.task import TaskRead
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])
AdminOrManager = Annotated[User, Depends(require_admin_or_manager())]


@router.get("/overview", response_model=OverviewStats)
async def get_overview(
    _: AdminOrManager,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await analytics_service.get_overview(db)


@router.get("/employee/{employee_id}", response_model=EmployeeStats)
async def get_employee_analytics(
    employee_id: UUID,
    _: AdminOrManager,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await analytics_service.get_employee_analytics(employee_id, db)


@router.get("/department/{dept_id}", response_model=OverviewStats)
async def get_department_analytics(
    dept_id: UUID,
    _: AdminOrManager,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await analytics_service.get_department_analytics(dept_id, db)


@router.get("/overdue", response_model=list[OverdueTask])
async def get_overdue_tasks(
    _: AdminOrManager,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await analytics_service.get_overdue_tasks(db)
