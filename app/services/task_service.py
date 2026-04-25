import math
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ForbiddenException,
    InvalidStatusTransitionException,
    NotFoundException,
)
from app.models.employee import Employee
from app.models.task import Task, TaskPriority, TaskStatus, is_valid_transition
from app.models.task_activity import TaskActivityLog
from app.models.user import Role, User
from app.schemas.task import (
    TaskAssignUpdate,
    TaskCreate,
    TaskFilter,
    TaskStatusUpdate,
    TaskUpdate,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_task(task_id: UUID, db: AsyncSession) -> Task:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.is_deleted == False)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundException("Task", str(task_id))
    return task


async def _log_activity(
    db: AsyncSession,
    task: Task,
    actor: User,
    action: str,
    old_value: str | None = None,
    new_value: str | None = None,
):
    log = TaskActivityLog(
        task_id=task.id,
        actor_id=actor.id,
        action=action,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(log)


# ─── Create ──────────────────────────────────────────────────────────────────

async def create_task(data: TaskCreate, creator: User, db: AsyncSession) -> Task:
    # Verify the assigned employee exists
    emp_result = await db.execute(
        select(Employee).where(Employee.id == data.assigned_to, Employee.is_active == True)
    )
    if not emp_result.scalar_one_or_none():
        raise NotFoundException("Employee", str(data.assigned_to))

    task = Task(
        **data.model_dump(),
        assigned_by=creator.id,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    await _log_activity(db, task, creator, "created", new_value=task.title)
    return task


# ─── Read ────────────────────────────────────────────────────────────────────

async def list_tasks(filters: TaskFilter, current_user: User, db: AsyncSession):
    query = select(Task).where(Task.is_deleted == False)

    # Scope: employee only sees own tasks; manager sees dept tasks
    if current_user.role == Role.EMPLOYEE:
        if current_user.employee_profile:
            query = query.where(Task.assigned_to == current_user.employee_profile.id)
        else:
            query = query.where(Task.id == None)  # no profile → no tasks

    elif current_user.role == Role.MANAGER and current_user.employee_profile:
        query = query.where(
            Task.department_id == current_user.employee_profile.department_id
        )

    # Filters
    if filters.status:
        query = query.where(Task.status == filters.status)
    if filters.priority:
        query = query.where(Task.priority == filters.priority)
    if filters.assigned_to:
        query = query.where(Task.assigned_to == filters.assigned_to)
    if filters.department_id:
        query = query.where(Task.department_id == filters.department_id)
    if filters.due_before:
        query = query.where(Task.due_date <= filters.due_before)
    if filters.due_after:
        query = query.where(Task.due_date >= filters.due_after)
    if filters.search:
        term = f"%{filters.search}%"
        query = query.where(
            or_(Task.title.ilike(term), Task.description.ilike(term))
        )

    # Sort
    sort_col = {
        "due_date": Task.due_date,
        "created_at": Task.created_at,
        "priority": Task.priority,
    }.get(filters.sort_by, Task.created_at)

    order_fn = asc if filters.sort_order == "asc" else desc
    query = query.order_by(order_fn(sort_col))

    # Count
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    # Paginate
    offset = (filters.page - 1) * filters.page_size
    result = await db.execute(query.offset(offset).limit(filters.page_size))
    tasks = result.scalars().all()

    return {
        "items": list(tasks),
        "total": total,
        "page": filters.page,
        "page_size": filters.page_size,
        "total_pages": math.ceil(total / filters.page_size) if total else 1,
    }


async def get_task(task_id: UUID, current_user: User, db: AsyncSession) -> Task:
    task = await _get_task(task_id, db)

    # Access control
    if current_user.role == Role.EMPLOYEE:
        if not current_user.employee_profile or task.assigned_to != current_user.employee_profile.id:
            raise ForbiddenException("You can only view your own tasks")

    return task


# ─── Update ──────────────────────────────────────────────────────────────────

async def update_task(
    task_id: UUID, data: TaskUpdate, current_user: User, db: AsyncSession
) -> Task:
    task = await _get_task(task_id, db)

    for field, value in data.model_dump(exclude_none=True).items():
        old_val = str(getattr(task, field))
        setattr(task, field, value)
        await _log_activity(db, task, current_user, f"updated_{field}", old_val, str(value))

    await db.flush()
    return task


async def update_task_status(
    task_id: UUID, data: TaskStatusUpdate, current_user: User, db: AsyncSession
) -> Task:
    task = await _get_task(task_id, db)
    new_status = data.status

    # Validate transition
    if not is_valid_transition(task.status, new_status):
        raise InvalidStatusTransitionException(task.status.value, new_status.value)

    # Role-based permission on specific transitions
    if current_user.role == Role.EMPLOYEE:
        emp_profile = current_user.employee_profile
        if not emp_profile or task.assigned_to != emp_profile.id:
            raise ForbiddenException("Employees can only update status of their own tasks")
        # Employees can only move PENDING→IN_PROGRESS and IN_PROGRESS→UNDER_REVIEW
        allowed_for_employee = {
            TaskStatus.PENDING: TaskStatus.IN_PROGRESS,
            TaskStatus.IN_PROGRESS: TaskStatus.UNDER_REVIEW,
        }
        if allowed_for_employee.get(task.status) != new_status:
            raise ForbiddenException(
                f"Employees cannot perform this status transition: {task.status.value} → {new_status.value}"
            )

    # Auto-timestamp fields
    if new_status == TaskStatus.IN_PROGRESS and not task.started_at:
        task.started_at = datetime.now(timezone.utc)
    if new_status == TaskStatus.COMPLETED:
        task.completed_at = datetime.now(timezone.utc)

    old_status = task.status.value
    task.status = new_status

    await _log_activity(db, task, current_user, "status_changed", old_status, new_status.value)
    await db.flush()
    return task


async def reassign_task(
    task_id: UUID, data: TaskAssignUpdate, current_user: User, db: AsyncSession
) -> Task:
    task = await _get_task(task_id, db)

    emp_result = await db.execute(
        select(Employee).where(Employee.id == data.assigned_to, Employee.is_active == True)
    )
    if not emp_result.scalar_one_or_none():
        raise NotFoundException("Employee", str(data.assigned_to))

    old_assignee = str(task.assigned_to)
    task.assigned_to = data.assigned_to
    await _log_activity(
        db, task, current_user, "reassigned", old_assignee, str(data.assigned_to)
    )
    await db.flush()
    return task


async def delete_task(task_id: UUID, current_user: User, db: AsyncSession) -> None:
    task = await _get_task(task_id, db)
    task.is_deleted = True
    await _log_activity(db, task, current_user, "deleted")


async def get_task_activity(task_id: UUID, db: AsyncSession) -> list[TaskActivityLog]:
    await _get_task(task_id, db)  # 404 check
    result = await db.execute(
        select(TaskActivityLog)
        .where(TaskActivityLog.task_id == task_id)
        .order_by(TaskActivityLog.timestamp.asc())
    )
    return list(result.scalars().all())
