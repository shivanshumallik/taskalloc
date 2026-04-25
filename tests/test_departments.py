"""Tests for /departments endpoints."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_create_department_as_admin(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/departments",
        json={"name": "Engineering", "description": "Tech dept"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Engineering"
    assert data["is_active"] is True


async def test_create_department_as_employee_forbidden(
    client: AsyncClient, employee_token: str
):
    resp = await client.post(
        "/departments",
        json={"name": "Sales"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 403


async def test_create_department_as_manager_forbidden(
    client: AsyncClient, manager_token: str
):
    resp = await client.post(
        "/departments",
        json={"name": "Sales"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 403


async def test_create_duplicate_department(client: AsyncClient, admin_token: str):
    await client.post(
        "/departments",
        json={"name": "HR"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.post(
        "/departments",
        json={"name": "HR"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


async def test_list_departments(client: AsyncClient, department, admin_token: str):
    resp = await client.get(
        "/departments", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


async def test_get_department(client: AsyncClient, department, admin_token: str):
    resp = await client.get(
        f"/departments/{department.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Engineering"


async def test_get_department_not_found(client: AsyncClient, admin_token: str):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(
        f"/departments/{fake_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


async def test_update_department(client: AsyncClient, department, admin_token: str):
    resp = await client.patch(
        f"/departments/{department.id}",
        json={"description": "Updated description"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated description"


async def test_soft_delete_department(client: AsyncClient, department, admin_token: str):
    resp = await client.delete(
        f"/departments/{department.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    # Should now be 404
    get_resp = await client.get(
        f"/departments/{department.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404
