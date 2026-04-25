"""Tests for /analytics endpoints."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_overview_admin(client: AsyncClient, admin_token: str):
    resp = await client.get(
        "/analytics/overview",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_tasks" in data
    assert "pending" in data
    assert "overdue" in data


async def test_overview_employee_forbidden(client: AsyncClient, employee_token: str):
    resp = await client.get(
        "/analytics/overview",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 403


async def test_employee_analytics(
    client: AsyncClient, admin_token: str, employee_profile
):
    resp = await client.get(
        f"/analytics/employee/{employee_profile.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["employee_id"] == str(employee_profile.id)
    assert data["total_tasks"] == 0


async def test_department_analytics(
    client: AsyncClient, admin_token: str, department
):
    resp = await client.get(
        f"/analytics/department/{department.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200


async def test_overdue_tasks(client: AsyncClient, admin_token: str):
    resp = await client.get(
        "/analytics/overdue",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
