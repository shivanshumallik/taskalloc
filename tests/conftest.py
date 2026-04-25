"""
Test configuration using SQLite in-memory DB for speed.
No real PostgreSQL needed to run tests.
"""
import asyncio
from datetime import date
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.user import Role, User
from app.models.department import Department
from app.models.employee import Employee
from main import app

# ─── SQLite async engine for tests ───────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ─── Override DB dependency ───────────────────────────────────────────────────
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


# ─── Session-scoped event loop ────────────────────────────────────────────────
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ─── Create / drop tables once per session ───────────────────────────────────
@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ─── Fresh DB session per test ───────────────────────────────────────────────
@pytest_asyncio.fixture()
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()
        # Truncate all tables between tests for isolation
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


# ─── HTTP client ─────────────────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ─── User / auth helpers ─────────────────────────────────────────────────────
async def _create_user(
    db: AsyncSession,
    username: str,
    email: str,
    role: Role,
    password: str = "testpass123",
) -> User:
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _get_token(client: AsyncClient, email: str, password: str = "testpass123") -> str:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


# ─── Fixtures: admin, manager, employee users ────────────────────────────────
@pytest_asyncio.fixture()
async def admin_user(db: AsyncSession) -> User:
    return await _create_user(db, "admin", "admin@test.com", Role.ADMIN)


@pytest_asyncio.fixture()
async def manager_user(db: AsyncSession) -> User:
    return await _create_user(db, "manager", "manager@test.com", Role.MANAGER)


@pytest_asyncio.fixture()
async def employee_user(db: AsyncSession) -> User:
    return await _create_user(db, "employee", "employee@test.com", Role.EMPLOYEE)


# ─── Fixtures: tokens ────────────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def admin_token(client: AsyncClient, admin_user: User) -> str:
    return await _get_token(client, "admin@test.com")


@pytest_asyncio.fixture()
async def manager_token(client: AsyncClient, manager_user: User) -> str:
    return await _get_token(client, "manager@test.com")


@pytest_asyncio.fixture()
async def employee_token(client: AsyncClient, employee_user: User) -> str:
    return await _get_token(client, "employee@test.com")


# ─── Fixtures: department + employee profiles ─────────────────────────────────
@pytest_asyncio.fixture()
async def department(db: AsyncSession, admin_user: User) -> Department:
    dept = Department(name="Engineering", created_by=admin_user.id)
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


@pytest_asyncio.fixture()
async def employee_profile(
    db: AsyncSession, employee_user: User, department: Department
) -> Employee:
    emp = Employee(
        full_name="Test Employee",
        email=employee_user.email,
        department_id=department.id,
        designation="Developer",
        date_joined=date.today(),
        user_id=employee_user.id,
    )
    db.add(emp)
    await db.commit()
    await db.refresh(emp)
    return emp
