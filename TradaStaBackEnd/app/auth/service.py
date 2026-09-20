"""Business-logic layer for registration, login, refresh, and logout."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.auth.exceptions import AuthenticationError, AuthorizationError, UserAlreadyExistsError
from app.auth.models import RefreshToken, User, UserRole
from app.auth.repository import RefreshTokenRepository, UserRepository
from app.auth.schemas import TokenResponse, UserPublic
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    validate_email,
    validate_password,
    verify_password,
)
from app.core.config import Settings

logger = logging.getLogger(__name__)


class AuthService:
    """Coordinate identity, token, and password operations."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    def register_user(self, *, email: str, username: str, password: str, confirm_password: str) -> UserPublic:
        """Register a new user while safeguarding password semantics."""
        normalized_email = validate_email(email)
        clean_username = username.strip()
        if not clean_username:
            raise AuthenticationError("Username is required.")
        if password != confirm_password:
            raise AuthenticationError("Password confirmation does not match.")
        validate_password(password)

        if self.users.get_by_email(normalized_email) is not None:
            raise UserAlreadyExistsError()

        user = User(
            email=normalized_email,
            username=clean_username,
            password_hash=hash_password(password),
            role=UserRole.USER.value,
            is_active=True,
            is_verified=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created = self.users.create(user)
        logger.info("user_registered user_id=%s", created.id)
        return UserPublic.model_validate(created)

    def login_user(self, *, email: str, password: str) -> TokenResponse:
        """Authenticate a user, update last login, and issue fresh JWTs."""
        normalized_email = validate_email(email)
        user = self.users.get_by_email(normalized_email)
        if user is None or not verify_password(password, user.password_hash):
            logger.warning("user_login_failed email=%s", normalized_email)
            raise AuthenticationError("Invalid email or password.")
        if not user.is_active:
            raise AuthenticationError("Account is inactive.")

        access_token = create_access_token(user.id, user.role)
        refresh_token = create_refresh_token(user.id, user.role)
        refresh_hash = hash_token(refresh_token)
        self.refresh_tokens.revoke_all_for_user(user.id)
        self.refresh_tokens.create(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=datetime.now(UTC) + timedelta(days=self.settings.jwt_refresh_token_expire_days),
        )

        user.last_login_at = datetime.now(UTC)
        self.users.update(user)
        logger.info("user_login_success user_id=%s", user.id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.settings.jwt_access_token_expire_minutes * 60,
        )

    def refresh_user_token(self, *, refresh_token: str) -> TokenResponse:
        """Validate a refresh token and rotate it in a secure way."""
        claims = decode_token(refresh_token, expected_type="refresh")
        user_id = claims.get("sub")
        if not user_id:
            raise AuthenticationError("Refresh token payload is invalid.")

        user = self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Refresh token is invalid.")

        refresh_hash = hash_token(refresh_token)
        existing = self.refresh_tokens.get_active_for_user(user.id, refresh_hash)
        if existing is None:
            raise AuthenticationError("Refresh token is invalid or revoked.")

        self.refresh_tokens.revoke(existing)
        new_refresh = create_refresh_token(user.id, user.role)
        new_refresh_hash = hash_token(new_refresh)
        self.refresh_tokens.create(
            user_id=user.id,
            token_hash=new_refresh_hash,
            expires_at=datetime.now(UTC) + timedelta(days=self.settings.jwt_refresh_token_expire_days),
        )

        logger.info("token_refreshed user_id=%s", user.id)
        return TokenResponse(
            access_token=create_access_token(user.id, user.role),
            refresh_token=new_refresh,
            token_type="bearer",
            expires_in=self.settings.jwt_access_token_expire_minutes * 60,
        )

    def logout_user(self, *, refresh_token: str | None) -> None:
        """Log a user out by invalidating the provided refresh token."""
        if not refresh_token:
            raise AuthenticationError("A refresh token is required to log out.")

        claims = decode_token(refresh_token, expected_type="refresh")
        user_id = claims.get("sub")
        if not user_id:
            raise AuthenticationError("Refresh token payload is invalid.")

        token = self.refresh_tokens.get_active_for_user(user_id, hash_token(refresh_token))
        if token is not None:
            self.refresh_tokens.revoke(token)
        logger.info("user_logout user_id=%s", user_id)

    def get_current_user_from_access_token(self, access_token: str) -> User:
        """Resolve a valid access token into the authenticated user."""
        claims = decode_token(access_token, expected_type="access")
        user = self.users.get_by_id(claims.get("sub"))
        if user is None:
            raise AuthenticationError("User no longer exists.")
        if not user.is_active:
            raise AuthenticationError("User account is inactive.")
        return user

    def get_user_profile(self, user_id: str) -> UserPublic:
        """Return the safe profile for a specific user."""
        user = self.users.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("User was not found.")
        return UserPublic.model_validate(user)

    def require_role(self, user: User, *, required_role: str) -> User:
        """Ensure a user holds the requested role or higher."""
        if user.role == UserRole.ADMIN.value:
            return user
        if user.role != required_role:
            raise AuthorizationError(f"Required role: {required_role}.")
        return user

    def ensure_user_can_query_trading(self, user: User | None) -> User | None:
        """Allow optional trading access when auth is disabled by configuration."""
        if user is None:
            return None
        return user
