"""Authentication and JWT security tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

db_path = Path(__file__).resolve().parents[1] / "test_tradasta_auth.db"
if db_path.exists():
    db_path.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-1234567890-abcdefghijklmnop"

from app.core.config import get_settings
from app.infrastructure.database import init_db
from app.main import app


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set secure JWT configuration for auth tests."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-1234567890-abcdefghijklmnop")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
    monkeypatch.setenv("AUTH_REQUIRED_FOR_TRADING", "false")
    get_settings.cache_clear()
    init_db()


@pytest.mark.asyncio
async def test_auth_register_login_refresh_and_me(auth_env: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "username": "alice",
                "password": "StrongPass1",
                "confirm_password": "StrongPass1",
            },
        )
        assert register_response.status_code == 201, register_response.text
        assert register_response.json()["email"] == "user@example.com"

        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "StrongPass1"},
        )
        assert login_response.status_code == 200, login_response.text
        payload = login_response.json()
        assert payload["token_type"] == "bearer"
        access_token = payload["access_token"]
        refresh_token = payload["refresh_token"]

        me_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_response.status_code == 200, me_response.text
        assert me_response.json()["username"] == "alice"

        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200, refresh_response.text
        refreshed = refresh_response.json()
        assert refreshed["access_token"] != access_token

        logout_response = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refreshed["refresh_token"]},
        )
        assert logout_response.status_code == 200, logout_response.text


@pytest.mark.asyncio
async def test_duplicate_registration_is_rejected(auth_env: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup@example.com",
                "username": "dupuser",
                "password": "StrongPass1",
                "confirm_password": "StrongPass1",
            },
        )
        assert first.status_code == 201

        second = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup@example.com",
                "username": "dupuser2",
                "password": "StrongPass2",
                "confirm_password": "StrongPass2",
            },
        )
        assert second.status_code == 409
