"""Authentication module for user sign-in and JWT protection."""

from app.auth.dependencies import (
    get_current_user,
    require_authenticated_user,
    require_role,
)
from app.auth.models import User, UserRole
from app.auth.service import AuthService

__all__ = [
    "AuthService",
    "User",
    "UserRole",
    "get_current_user",
    "require_authenticated_user",
    "require_role",
]
