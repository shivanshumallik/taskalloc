"""Tests for task comment endpoints."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _create_task(client, token, employee_id, department_id):
    resp = await client.post(
        "/tasks",
        json={
            "title": "Commented Task",
            "assigned_to": str(employee_id),
            "department_id": str(department_id),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_admin_can_comment(
    client: AsyncClient, admin_token: str, employee_profile, department
):
    task_id = await _create_task(client, admin_token, employee_profile.id, department.id)
    resp = await client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "Great progress!"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["content"] == "Great progress!"
    assert resp.json()["is_edited"] is False


async def test_employee_can_comment_own_task(
    client: AsyncClient,
    admin_token: str,
    employee_token: str,
    employee_profile,
    department,
):
    task_id = await _create_task(client, admin_token, employee_profile.id, department.id)
    resp = await client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "Started working on it"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 201


async def test_list_comments(
    client: AsyncClient, admin_token: str, employee_profile, department
):
    task_id = await _create_task(client, admin_token, employee_profile.id, department.id)
    await client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "First comment"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "Second comment"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        f"/tasks/{task_id}/comments",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


async def test_edit_own_comment(
    client: AsyncClient, admin_token: str, employee_profile, department
):
    task_id = await _create_task(client, admin_token, employee_profile.id, department.id)
    comment = await client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "Original"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    comment_id = comment.json()["id"]

    resp = await client.patch(
        f"/tasks/{task_id}/comments/{comment_id}",
        json={"content": "Edited content"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "Edited content"
    assert resp.json()["is_edited"] is True


async def test_delete_own_comment(
    client: AsyncClient, admin_token: str, employee_profile, department
):
    task_id = await _create_task(client, admin_token, employee_profile.id, department.id)
    comment = await client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "To be deleted"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    comment_id = comment.json()["id"]

    resp = await client.delete(
        f"/tasks/{task_id}/comments/{comment_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
