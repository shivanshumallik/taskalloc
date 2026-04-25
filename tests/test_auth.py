"""Tests for all /auth endpoints and edge cases."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ─── Register ────────────────────────────────────────────────────────────────

async def test_register_success(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "username": "newuser",
        "email": "new@example.com",
        "password": "securepass1",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["username"] == "newuser"
    assert "hashed_password" not in data


async def test_register_duplicate_email(client: AsyncClient, admin_user):
    resp = await client.post("/auth/register", json={
        "username": "another",
        "email": "admin@test.com",  # already exists
        "password": "securepass1",
    })
    assert resp.status_code == 409


async def test_register_duplicate_username(client: AsyncClient, admin_user):
    resp = await client.post("/auth/register", json={
        "username": "admin",  # already exists
        "email": "unique@example.com",
        "password": "securepass1",
    })
    assert resp.status_code == 409


async def test_register_weak_password(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "username": "weakuser",
        "email": "weak@example.com",
        "password": "short",
    })
    assert resp.status_code == 422


async def test_register_invalid_username(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "username": "ab",  # too short
        "email": "x@example.com",
        "password": "goodpassword",
    })
    assert resp.status_code == 422


# ─── Login ───────────────────────────────────────────────────────────────────

async def test_login_success(client: AsyncClient, admin_user):
    resp = await client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "testpass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient, admin_user):
    resp = await client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


async def test_login_unknown_email(client: AsyncClient):
    resp = await client.post("/auth/login", json={
        "email": "nobody@example.com",
        "password": "testpass123",
    })
    assert resp.status_code == 401


async def test_login_deactivated_user(client: AsyncClient, db, admin_user):
    admin_user.is_active = False
    db.add(admin_user)
    await db.commit()

    resp = await client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "testpass123",
    })
    assert resp.status_code == 401


# ─── /auth/me ────────────────────────────────────────────────────────────────

async def test_get_me(client: AsyncClient, admin_token: str):
    resp = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.com"


async def test_get_me_no_token(client: AsyncClient):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


async def test_get_me_invalid_token(client: AsyncClient):
    resp = await client.get(
        "/auth/me", headers={"Authorization": "Bearer this.is.garbage"}
    )
    assert resp.status_code == 401


# ─── Refresh ─────────────────────────────────────────────────────────────────

async def test_refresh_token(client: AsyncClient, admin_user):
    login = await client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "testpass123",
    })
    refresh_token = login.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_refresh_invalid_token(client: AsyncClient):
    resp = await client.post("/auth/refresh", json={"refresh_token": "bad-token"})
    assert resp.status_code == 401


# ─── Logout ──────────────────────────────────────────────────────────────────

async def test_logout(client: AsyncClient, admin_user):
    login = await client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "testpass123",
    })
    refresh_token = login.json()["refresh_token"]

    logout_resp = await client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout_resp.status_code == 200

    # Using same refresh token again should fail
    refresh_resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 401


# ─── Change Password ──────────────────────────────────────────────────────────

async def test_change_password_success(client: AsyncClient, admin_user, admin_token):
    resp = await client.patch(
        "/auth/me/password",
        json={"current_password": "testpass123", "new_password": "newpassword99"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    # Can now log in with new password
    login = await client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "newpassword99",
    })
    assert login.status_code == 200


async def test_change_password_wrong_current(client: AsyncClient, admin_token):
    resp = await client.patch(
        "/auth/me/password",
        json={"current_password": "wrong_current", "new_password": "newpassword99"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
