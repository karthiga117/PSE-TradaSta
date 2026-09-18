"""Authentication API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_auth_service, get_current_user
from app.auth.models import User
from app.auth.schemas import LoginRequest, LogoutRequest, RefreshTokenRequest, RegisterRequest, TokenResponse, UserPublic
from app.auth.service import AuthService

router = APIRouter(tags=["authentication"])


@router.post("/auth/register", status_code=201)
async def register(
    payload: RegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserPublic:
    """Register a new account with a hashed password and USER role."""
    return service.register_user(
        email=payload.email,
        username=payload.username,
        password=payload.password,
        confirm_password=payload.confirm_password,
    )


@router.post("/auth/login")
async def login(
    payload: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Authenticate a user and issue a short-lived access token plus refresh token."""
    return service.login_user(email=payload.email, password=payload.password)


@router.post("/auth/refresh")
async def refresh(
    payload: RefreshTokenRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Exchange a valid refresh token for a new access token and rotated refresh token."""
    return service.refresh_user_token(refresh_token=payload.refresh_token)


@router.post("/auth/logout")
async def logout(
    payload: LogoutRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict[str, str]:
    """Invalidate a refresh token and end the current server-side session."""
    service.logout_user(refresh_token=payload.refresh_token)
    return {"status": "logged_out"}


@router.get("/auth/me")
async def me(
    current_user: Annotated[User | None, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserPublic:
    """Return the safe profile for the current authenticated user."""
    if current_user is None:
        raise ValueError("Authentication required.")
    return service.get_user_profile(current_user.id)


__all__ = ["router"]
