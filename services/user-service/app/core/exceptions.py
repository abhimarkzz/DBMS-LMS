"""
Custom Exception Classes

Defines a hierarchy of application exceptions that map cleanly to HTTP responses.
Using custom exceptions instead of HTTPException directly lets us:
  1. Keep error codes consistent across the codebase
  2. Add business context (e.g., which resource was not found)
  3. Handle them centrally in main.py without repeating JSONResponse logic
"""

from typing import Optional


class AppException(Exception):
    """Base class for all application-defined exceptions."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    message: str = "An internal error occurred"

    def __init__(self, message: Optional[str] = None):
        self.message = message or self.__class__.message
        super().__init__(self.message)


class NotFoundError(AppException):
    status_code = 404
    code = "NOT_FOUND"
    message = "Resource not found"


class UserNotFoundError(NotFoundError):
    code = "USER_NOT_FOUND"
    message = "User was not found"


class ConflictError(AppException):
    status_code = 409
    code = "CONFLICT"
    message = "Resource already exists"


class EmailAlreadyExistsError(ConflictError):
    code = "EMAIL_ALREADY_EXISTS"
    message = "An account with this email already exists"


class AuthenticationError(AppException):
    status_code = 401
    code = "AUTHENTICATION_FAILED"
    message = "Invalid credentials"


class InvalidTokenError(AppException):
    status_code = 401
    code = "INVALID_TOKEN"
    message = "Token is invalid or expired"


class TokenExpiredError(AppException):
    status_code = 401
    code = "TOKEN_EXPIRED"
    message = "Token has expired"


class PermissionDeniedError(AppException):
    status_code = 403
    code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action"


class RateLimitExceededError(AppException):
    status_code = 429
    code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests. Please try again later."


class ValidationError(AppException):
    status_code = 422
    code = "VALIDATION_ERROR"
    message = "Request data is invalid"


class AccountInactiveError(AppException):
    status_code = 403
    code = "ACCOUNT_INACTIVE"
    message = "This account has been deactivated"
