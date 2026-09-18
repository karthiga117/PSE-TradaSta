"""Authentication and authorization exceptions."""

from app.core.exceptions import ApplicationException


class AuthError(ApplicationException):
    """Base exception for authentication-related failures."""

    def __init__(self, message: str, *, code: str = "AUTH_ERROR", status_code: int = 401) -> None:
        super().__init__(message, code=code, status_code=status_code)


class AuthenticationError(AuthError):
    """Raised when user credentials or tokens are invalid."""

    def __init__(self, message: str = "Authentication failed.") -> None:
        super().__init__(message, code="AUTHENTICATION_ERROR", status_code=401)


class AuthorizationError(AuthError):
    """Raised when a valid identity lacks the required permissions."""

    def __init__(self, message: str = "Access denied.") -> None:
        super().__init__(message, code="AUTHORIZATION_ERROR", status_code=403)


class UserAlreadyExistsError(AuthError):
    """Raised when a registration attempts to reuse an email."""

    def __init__(self, message: str = "An account with this email already exists.") -> None:
        super().__init__(message, code="USER_ALREADY_EXISTS", status_code=409)


class InvalidPasswordError(AuthError):
    """Raised when a user signs up with a weak or mismatched password."""

    def __init__(self, message: str = "Password validation failed.") -> None:
        super().__init__(message, code="INVALID_PASSWORD", status_code=400)
