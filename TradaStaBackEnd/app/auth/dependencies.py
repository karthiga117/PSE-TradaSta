"""Dependency helpers for authentication and role enforcement."""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.exceptions import AuthenticationError, AuthorizationError
from app.auth.models import User, UserRole
from app.auth.service import AuthService
from app.core.config import Settings, get_settings
from app.core.dependencies import settings_dependency
from app.infrastructure.database import get_db

security_scheme = HTTPBearer(auto_error=False)


def get_auth_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dependency),
) -> AuthService:
    """Create a request-scoped auth service bound to the active database session."""
    return AuthService(db, settings)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(settings_dependency),
) -> User | None:
    """Resolve the current user from a valid bearer token when auth is enabled."""
    if credentials is None or not credentials.credentials:
        if settings.require_auth_for_trading:
            raise AuthenticationError("Authentication required.")
        return None

    try:
        return service.get_current_user_from_access_token(credentials.credentials)
    except AuthenticationError:
        if settings.require_auth_for_trading:
            raise
        return None


async def require_authenticated_user(
    current_user: User | None = Depends(get_current_user),
) -> User:
    """Ensure the caller is authenticated before using protected APIs."""
    if current_user is None:
        raise AuthenticationError("Authentication required.")
    return current_user


def require_role(required_role: UserRole):
    """Return a dependency that checks for a specific role on the active user."""

    async def role_dependency(
        current_user: User | None = Depends(get_current_user),
    ) -> User:
        if current_user is None:
            raise AuthenticationError("Authentication required.")
        if current_user.role == UserRole.ADMIN.value:
            return current_user
        if current_user.role != required_role.value:
            raise AuthorizationError(f"This endpoint requires {required_role.value} access.")
        return current_user

    return role_dependency
