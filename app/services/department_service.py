import math
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.department import Department
from app.models.employee import Employee
from app.models.user import User
from app.schemas.department import DepartmentCreate, DepartmentUpdate


async def create_department(
    data: DepartmentCreate, creator: User, db: AsyncSession
) -> Department:
    existing = await db.execute(
        select(Department).where(Department.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise ConflictException(f"Department '{data.name}' already exists")

    dept = Department(
        name=data.name,
        description=data.description,
        created_by=creator.id,
    )
    db.add(dept)
    await db.flush()
    await db.refresh(dept)
    return dept


async def list_departments(db: AsyncSession, page: int = 1, page_size: int = 20):
    offset = (page - 1) * page_size
    total_result = await db.execute(
        select(func.count()).select_from(Department).where(Department.is_active == True)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(Department)
        .where(Department.is_active == True)
        .order_by(Department.name)
        .offset(offset)
        .limit(page_size)
    )
    departments = result.scalars().all()

    return {
        "items": list(departments),
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total else 1,
    }


async def get_department(dept_id: UUID, db: AsyncSession) -> Department:
    result = await db.execute(
        select(Department).where(Department.id == dept_id, Department.is_active == True)
    )
    dept = result.scalar_one_or_none()
    if not dept:
        raise NotFoundException("Department", str(dept_id))
    return dept


async def update_department(
    dept_id: UUID, data: DepartmentUpdate, db: AsyncSession
) -> Department:
    dept = await get_department(dept_id, db)
    if data.name is not None:
        dept.name = data.name
    if data.description is not None:
        dept.description = data.description
    await db.flush()
    return dept


async def delete_department(dept_id: UUID, db: AsyncSession) -> None:
    dept = await get_department(dept_id, db)
    dept.is_active = False


async def get_department_employees(
    dept_id: UUID, db: AsyncSession, page: int = 1, page_size: int = 20
):
    await get_department(dept_id, db)  # 404 check
    offset = (page - 1) * page_size

    total_result = await db.execute(
        select(func.count())
        .select_from(Employee)
        .where(Employee.department_id == dept_id, Employee.is_active == True)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(Employee)
        .where(Employee.department_id == dept_id, Employee.is_active == True)
        .offset(offset)
        .limit(page_size)
    )
    employees = result.scalars().all()

    return {
        "items": list(employees),
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total else 1,
    }
