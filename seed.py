"""
Seed script — run once after `alembic upgrade head` to create the first admin
user and sample data so you can log in and test immediately.

    python seed.py
"""
import asyncio
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models.department import Department
from app.models.employee import Employee
from app.models.user import Role, User

engine = create_async_engine(settings.DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def seed():
    async with SessionLocal() as db:
        admin = User(
            username="admin",
            email="admin@taskalloc.com",
            hashed_password=hash_password("Admin@1234"),
            role=Role.ADMIN,
            is_active=True,
            is_verified=True,
        )
        db.add(admin)
        await db.flush()

        engineering = Department(name="Engineering", description="Software development team", created_by=admin.id)
        hr = Department(name="Human Resources", description="People operations", created_by=admin.id)
        db.add_all([engineering, hr])
        await db.flush()

        manager_user = User(
            username="eng_manager",
            email="manager@taskalloc.com",
            hashed_password=hash_password("Manager@1234"),
            role=Role.MANAGER,
            is_active=True,
            is_verified=True,
        )
        db.add(manager_user)
        await db.flush()

        db.add(Employee(
            full_name="Jane Manager",
            email="manager@taskalloc.com",
            department_id=engineering.id,
            designation="Engineering Manager",
            date_joined=date(2022, 1, 15),
            user_id=manager_user.id,
        ))

        emp_user = User(
            username="john_dev",
            email="john@taskalloc.com",
            hashed_password=hash_password("Employee@1234"),
            role=Role.EMPLOYEE,
            is_active=True,
            is_verified=True,
        )
        db.add(emp_user)
        await db.flush()

        db.add(Employee(
            full_name="John Developer",
            email="john@taskalloc.com",
            department_id=engineering.id,
            designation="Senior Developer",
            date_joined=date(2023, 3, 1),
            user_id=emp_user.id,
        ))
        await db.commit()

    print("\n✅  Seed complete!")
    print("─" * 48)
    print("  ADMIN    → admin@taskalloc.com   / Admin@1234")
    print("  MANAGER  → manager@taskalloc.com / Manager@1234")
    print("  EMPLOYEE → john@taskalloc.com    / Employee@1234")
    print("─" * 48)
    print("  Swagger UI → http://localhost:8000/docs\n")


if __name__ == "__main__":
    asyncio.run(seed())
