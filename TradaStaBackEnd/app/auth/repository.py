"""Repository layer for auth persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import RefreshToken, User


class UserRepository:
    """Manage persisted user records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, user_id: str) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.session.execute(statement).scalar_one_or_none()

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update(self, user: User) -> User:
        user.updated_at = datetime.now(UTC)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user


class RefreshTokenRepository:
    """Manage server-side refresh-token state and rotation."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, user_id: str, token_hash: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.session.add(token)
        self.session.commit()
        self.session.refresh(token)
        return token

    def get_active_for_user(self, user_id: str, token_hash: str) -> RefreshToken | None:
        statement = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
        return self.session.execute(statement).scalar_one_or_none()

    def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(UTC)
        self.session.add(token)
        self.session.commit()

    def revoke_all_for_user(self, user_id: str) -> None:
        statement = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        tokens = self.session.execute(statement).scalars().all()
        for token in tokens:
            token.revoked_at = datetime.now(UTC)
        self.session.commit()
