"""Auth request and response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload used to create a new user account."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)

    model_config = ConfigDict(extra="forbid")


class LoginRequest(BaseModel):
    """Payload used to authenticate a user."""

    email: EmailStr
    password: str

    model_config = ConfigDict(extra="forbid")


class RefreshTokenRequest(BaseModel):
    """Refresh-token request payload."""

    refresh_token: str

    model_config = ConfigDict(extra="forbid")


class LogoutRequest(BaseModel):
    """Logout request payload."""

    refresh_token: str | None = None

    model_config = ConfigDict(extra="forbid")


class TokenResponse(BaseModel):
    """JWT-oriented response sent to clients after login or refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserPublic(BaseModel):
    """Safe user representation for API responses."""

    id: str
    email: str
    username: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
