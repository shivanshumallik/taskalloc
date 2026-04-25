"""Tests for /tasks endpoints — state machine, RBAC, filtering."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def _task_payload(employee_id, department_id):
    return {
        "title": "Build feature X",
        "description": "Implement it well",
        "priority": "HIGH",
        "assigned_to": str(employee_id),
        "department_id": str(department_id),
    }


# ─── Create ──────────────────────────────────────────────────────────────────

async def test_admin_can_create_task(
    client: AsyncClient, admin_token: str, employee_profile, department
):
    resp = await client.post(
        "/tasks",
        json=_task_payload(employee_profile.id, department.id),
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Build feature X"
    assert data["status"] == "PENDING"
    assert data["priority"] == "HIGH"


async def test_employee_cannot_create_task(
    client: AsyncClient, employee_token: str, employee_profile, department
):
    resp = await client.post(
        "/tasks",
        json=_task_payload(employee_profile.id, department.id),
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 403


async def test_create_task_nonexistent_employee(
    client: AsyncClient, admin_token: str, department
):
    fake_id = "00000000-0000-0000-0000-000000000001"
    resp = await client.post(
        "/tasks",
        json={
            "title": "Ghost task",
            "assigned_to": fake_id,
            "department_id": str(department.id),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ─── Read ────────────────────────────────────────────────────────────────────

async def test_list_tasks_admin_sees_all(
    client: AsyncClient, admin_token: str, employee_profile, department
):
    # Create 2 tasks
    for i in range(2):
        await client.post(
            "/tasks",
            json={**_task_payload(employee_profile.id, department.id), "title": f"Task {i}"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    resp = await client.get(
        "/tasks", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2


async def test_employee_sees_only_own_tasks(
    client: AsyncClient,
    admin_token: str,
    employee_token: str,
    employee_profile,
    department,
    manager_user,
    db,
):
    # Create task for employee
    await client.post(
        "/tasks",
        json=_task_payload(employee_profile.id, department.id),
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/tasks", headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    for item in items:
        assert item["assigned_to"] == str(employee_profile.id)


async def test_get_task_detail(
    client: AsyncClient, admin_token: str, employee_profile, department
):
    create = await client.post(
        "/tasks",
        json=_task_payload(employee_profile.id, department.id),
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    task_id = create.json()["id"]

    resp = await client.get(
        f"/tasks/{task_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == task_id


async def test_get_nonexistent_task(client: AsyncClient, admin_token: str):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(
        f"/tasks/{fake_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 404


# ─── Status Machine ───────────────────────────────────────────────────────────

async def _make_task(client, token, employee_id, department_id):
    resp = await client.post(
        "/tasks",
        json=_task_payload(employee_id, department_id),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_valid_status_transition_pending_to_in_progress(
    client: AsyncClient,
    admin_token: str,
    employee_token: str,
    employee_profile,
    department,
):
    task_id = await _make_task(client, admin_token, employee_profile.id, department.id)

    resp = await client.patch(
        f"/tasks/{task_id}/status",
        json={"status": "IN_PROGRESS"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_PROGRESS"
    assert resp.json()["started_at"] is not None


async def test_valid_full_flow(
    client: AsyncClient,
    admin_token: str,
    employee_token: str,
    employee_profile,
    department,
):
    """PENDING → IN_PROGRESS → UNDER_REVIEW → COMPLETED."""
    task_id = await _make_task(client, admin_token, employee_profile.id, department.id)

    transitions = [
        (employee_token, "IN_PROGRESS"),
        (employee_token, "UNDER_REVIEW"),
        (admin_token, "COMPLETED"),
    ]
    for token, status in transitions:
        r = await client.patch(
            f"/tasks/{task_id}/status",
            json={"status": status},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, f"Failed on {status}: {r.text}"
        assert r.json()["status"] == status

    final = await client.get(
        f"/tasks/{task_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert final.json()["completed_at"] is not None


async def test_invalid_transition_pending_to_completed(
    client: AsyncClient, admin_token: str, employee_profile, department
):
    task_id = await _make_task(client, admin_token, employee_profile.id, department.id)
    resp = await client.patch(
        f"/tasks/{task_id}/status",
        json={"status": "COMPLETED"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


async def test_invalid_transition_completed_to_pending(
    client: AsyncClient,
    admin_token: str,
    employee_token: str,
    employee_profile,
    department,
):
    task_id = await _make_task(client, admin_token, employee_profile.id, department.id)
    for status in ["IN_PROGRESS", "UNDER_REVIEW", "COMPLETED"]:
        token = employee_token if status in ("IN_PROGRESS", "UNDER_REVIEW") else admin_token
        await client.patch(
            f"/tasks/{task_id}/status",
            json={"status": status},
            headers={"Authorization": f"Bearer {token}"},
        )

    # Try to go back to PENDING — should fail
    resp = await client.patch(
        f"/tasks/{task_id}/status",
        json={"status": "PENDING"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


async def test_employee_cannot_complete_task_directly(
    client: AsyncClient,
    admin_token: str,
    employee_token: str,
    employee_profile,
    department,
):
    task_id = await _make_task(client, admin_token, employee_profile.id, department.id)
    # Move to IN_PROGRESS (valid employee move)
    await client.patch(
        f"/tasks/{task_id}/status",
        json={"status": "IN_PROGRESS"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    # Employee tries to skip UNDER_REVIEW and jump to COMPLETED.
    # Either 403 (role denied) or 422 (invalid transition) is correct —
    # both properly block the action.
    resp = await client.patch(
        f"/tasks/{task_id}/status",
        json={"status": "COMPLETED"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code in (403, 422), (
        f"Expected 403 or 422, got {resp.status_code}: {resp.text}"
    )


async def test_cancel_task(
    client: AsyncClient, admin_token: str, employee_profile, department
):
    task_id = await _make_task(client, admin_token, employee_profile.id, department.id)
    resp = await client.patch(
        f"/tasks/{task_id}/status",
        json={"status": "CANCELLED"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


# ─── Soft Delete ──────────────────────────────────────────────────────────────

async def test_soft_delete_task(
    client: AsyncClient, admin_token: str, employee_profile, department
):
    task_id = await _make_task(client, admin_token, employee_profile.id, department.id)

    del_resp = await client.delete(
        f"/tasks/{task_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert del_resp.status_code == 200

    get_resp = await client.get(
        f"/tasks/{task_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_resp.status_code == 404


async def test_employee_cannot_delete_task(
    client: AsyncClient,
    admin_token: str,
    employee_token: str,
    employee_profile,
    department,
):
    task_id = await _make_task(client, admin_token, employee_profile.id, department.id)
    resp = await client.delete(
        f"/tasks/{task_id}", headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert resp.status_code == 403


# ─── Activity Log ─────────────────────────────────────────────────────────────

async def test_task_activity_log(
    client: AsyncClient,
    admin_token: str,
    employee_token: str,
    employee_profile,
    department,
):
    task_id = await _make_task(client, admin_token, employee_profile.id, department.id)
    await client.patch(
        f"/tasks/{task_id}/status",
        json={"status": "IN_PROGRESS"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )

    resp = await client.get(
        f"/tasks/{task_id}/activity",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) >= 2  # created + status_changed
    actions = [l["action"] for l in logs]
    assert "created" in actions
    assert "status_changed" in actions


# ─── Filtering ───────────────────────────────────────────────────────────────

async def test_filter_by_status(
    client: AsyncClient, admin_token: str, employee_profile, department
):
    # Create a PENDING task then cancel it
    task_id = await _make_task(client, admin_token, employee_profile.id, department.id)
    await client.patch(
        f"/tasks/{task_id}/status",
        json={"status": "CANCELLED"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/tasks?status=CANCELLED",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(t["status"] == "CANCELLED" for t in items)


async def test_filter_by_priority(
    client: AsyncClient, admin_token: str, employee_profile, department
):
    await client.post(
        "/tasks",
        json={**_task_payload(employee_profile.id, department.id), "priority": "CRITICAL"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/tasks?priority=CRITICAL",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(t["priority"] == "CRITICAL" for t in items)


async def test_search_tasks(
    client: AsyncClient, admin_token: str, employee_profile, department
):
    await client.post(
        "/tasks",
        json={**_task_payload(employee_profile.id, department.id), "title": "UNIQUE_SEARCH_KEYWORD"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/tasks?search=UNIQUE_SEARCH_KEYWORD",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
    assert "UNIQUE_SEARCH_KEYWORD" in resp.json()["items"][0]["title"]


async def test_pagination(
    client: AsyncClient, admin_token: str, employee_profile, department
):
    # Create 5 tasks
    for i in range(5):
        await client.post(
            "/tasks",
            json={**_task_payload(employee_profile.id, department.id), "title": f"Paged Task {i}"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    resp = await client.get(
        "/tasks?page=1&page_size=2",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 5
    assert data["total_pages"] >= 3
