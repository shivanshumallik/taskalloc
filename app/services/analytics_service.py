from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.models.employee import Employee
from app.models.task import Task, TaskStatus
from app.schemas.analytics import OverdueTask, OverviewStats
from app.schemas.employee import EmployeeStats


async def get_overview(db: AsyncSession) -> OverviewStats:
    now = datetime.now(timezone.utc)

    result = await db.execute(select(Task).where(Task.is_deleted == False))
    tasks = result.scalars().all()

    stats = {s: 0 for s in TaskStatus}
    overdue = 0

    for t in tasks:
        stats[t.status] += 1
        if (
            t.due_date
            and t.due_date < now
            and t.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
        ):
            overdue += 1

    return OverviewStats(
        total_tasks=len(tasks),
        pending=stats[TaskStatus.PENDING],
        in_progress=stats[TaskStatus.IN_PROGRESS],
        under_review=stats[TaskStatus.UNDER_REVIEW],
        completed=stats[TaskStatus.COMPLETED],
        cancelled=stats[TaskStatus.CANCELLED],
        overdue=overdue,
    )


async def get_employee_analytics(employee_id: UUID, db: AsyncSession) -> EmployeeStats:
    from app.services.employee_service import get_employee_stats
    return await get_employee_stats(employee_id, db)


async def get_department_analytics(dept_id: UUID, db: AsyncSession) -> OverviewStats:
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Task).where(Task.department_id == dept_id, Task.is_deleted == False)
    )
    tasks = result.scalars().all()

    stats = {s: 0 for s in TaskStatus}
    overdue = 0

    for t in tasks:
        stats[t.status] += 1
        if (
            t.due_date
            and t.due_date < now
            and t.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
        ):
            overdue += 1

    return OverviewStats(
        total_tasks=len(tasks),
        pending=stats[TaskStatus.PENDING],
        in_progress=stats[TaskStatus.IN_PROGRESS],
        under_review=stats[TaskStatus.UNDER_REVIEW],
        completed=stats[TaskStatus.COMPLETED],
        cancelled=stats[TaskStatus.CANCELLED],
        overdue=overdue,
    )


async def get_overdue_tasks(db: AsyncSession) -> list[Task]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Task).where(
            Task.due_date < now,
            Task.is_deleted == False,
            Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
        ).order_by(Task.due_date.asc())
    )
    return list(result.scalars().all())
