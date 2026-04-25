"""Tests for /employees endpoints."""
import pytest
from datetime import date
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _create_emp_payload(department_id, user_id, email="emp2@test.com"):
    return {
        "full_name": "Test Emp",
        "email": email,
        "department_id": str(department_id),
        "designation": "Developer",
        "date_joined": str(date.today()),
        "user_id": str(user_id),
    }


async def test_create_employee_as_admin(
    client: AsyncClient, admin_token: str, department, manager_user
):
    payload = await _create_emp_payload(department.id, manager_user.id, "emp_new@test.com")
    resp = await client.post(
        "/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["full_name"] == "Test Emp"


async def test_create_employee_as_employee_forbidden(
    client: AsyncClient, employee_token: str, department, admin_user
):
    payload = await _create_emp_payload(department.id, admin_user.id, "x@test.com")
    resp = await client.post(
        "/employees",
        json=payload,
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 403


async def test_create_employee_duplicate_user(
    client: AsyncClient, admin_token: str, employee_profile
):
    """Creating another employee profile for same user_id should fail."""
    payload = await _create_emp_payload(
        employee_profile.department_id,
        employee_profile.user_id,
        "dup@test.com",
    )
    resp = await client.post(
        "/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


async def test_list_employees_admin(
    client: AsyncClient, admin_token: str, employee_profile
):
    resp = await client.get(
        "/employees", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


async def test_list_employees_employee_forbidden(
    client: AsyncClient, employee_token: str
):
    resp = await client.get(
        "/employees", headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert resp.status_code == 403


async def test_get_employee(client: AsyncClient, admin_token: str, employee_profile):
    resp = await client.get(
        f"/employees/{employee_profile.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Test Employee"


async def test_soft_delete_employee(
    client: AsyncClient, admin_token: str, employee_profile
):
    resp = await client.delete(
        f"/employees/{employee_profile.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    get_resp = await client.get(
        f"/employees/{employee_profile.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404


async def test_employee_stats(
    client: AsyncClient, admin_token: str, employee_profile
):
    resp = await client.get(
        f"/employees/{employee_profile.id}/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_tasks" in data
    assert data["total_tasks"] == 0
