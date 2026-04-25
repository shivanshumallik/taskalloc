import math
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.employee import Employee
from app.models.task import Task, TaskStatus
from app.models.user import Role, User
from app.schemas.employee import EmployeeCreate, EmployeeStats, EmployeeUpdate


async def create_employee(data: EmployeeCreate, db: AsyncSession) -> Employee:
    # Check email uniqueness
    existing = await db.execute(
        select(Employee).where(Employee.email == data.email)
    )
    if existing.scalar_one_or_none():
        raise ConflictException(f"Employee with email '{data.email}' already exists")

    # Check user_id uniqueness
    existing_user = await db.execute(
        select(Employee).where(Employee.user_id == data.user_id)
    )
    if existing_user.scalar_one_or_none():
        raise ConflictException("This user already has an employee profile")

    employee = Employee(**data.model_dump())
    db.add(employee)
    await db.flush()
    await db.refresh(employee)
    return employee


async def list_employees(
    db: AsyncSession,
    current_user: User,
    page: int = 1,
    page_size: int = 20,
):
    offset = (page - 1) * page_size
    query = select(Employee).where(Employee.is_active == True)

    # Managers only see their own department
    if current_user.role == Role.MANAGER and current_user.employee_profile:
        query = query.where(
            Employee.department_id == current_user.employee_profile.department_id
        )

    total_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = total_result.scalar_one()

    result = await db.execute(
        query.order_by(Employee.full_name).offset(offset).limit(page_size)
    )
    employees = result.scalars().all()

    return {
        "items": list(employees),
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total else 1,
    }


async def get_employee(employee_id: UUID, db: AsyncSession) -> Employee:
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id, Employee.is_active == True)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise NotFoundException("Employee", str(employee_id))
    return emp


async def update_employee(
    employee_id: UUID, data: EmployeeUpdate, db: AsyncSession
) -> Employee:
    emp = await get_employee(employee_id, db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(emp, field, value)
    await db.flush()
    return emp


async def delete_employee(employee_id: UUID, db: AsyncSession) -> None:
    emp = await get_employee(employee_id, db)
    emp.is_active = False


async def get_employee_tasks(
    employee_id: UUID, db: AsyncSession, page: int = 1, page_size: int = 20
):
    await get_employee(employee_id, db)  # 404 check
    offset = (page - 1) * page_size

    total_result = await db.execute(
        select(func.count())
        .select_from(Task)
        .where(Task.assigned_to == employee_id, Task.is_deleted == False)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(Task)
        .where(Task.assigned_to == employee_id, Task.is_deleted == False)
        .order_by(Task.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    tasks = result.scalars().all()

    return {
        "items": list(tasks),
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total else 1,
    }


async def get_employee_stats(employee_id: UUID, db: AsyncSession) -> EmployeeStats:
    emp = await get_employee(employee_id, db)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Task).where(Task.assigned_to == employee_id, Task.is_deleted == False)
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

    return EmployeeStats(
        employee_id=emp.id,
        full_name=emp.full_name,
        total_tasks=len(tasks),
        pending=stats[TaskStatus.PENDING],
        in_progress=stats[TaskStatus.IN_PROGRESS],
        under_review=stats[TaskStatus.UNDER_REVIEW],
        completed=stats[TaskStatus.COMPLETED],
        cancelled=stats[TaskStatus.CANCELLED],
        overdue=overdue,
    )
