from typing import Optional

class AppException(Exception):
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

class AssignmentNotFoundError(NotFoundError):
    code = "ASSIGNMENT_NOT_FOUND"
    message = "Assignment not found"

class SubmissionNotFoundError(NotFoundError):
    code = "SUBMISSION_NOT_FOUND"
    message = "Submission not found"

class InvalidTokenError(AppException):
    status_code = 401
    code = "INVALID_TOKEN"
    message = "Token is invalid or expired"

class PermissionDeniedError(AppException):
    status_code = 403
    code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action"

class ValidationError(AppException):
    status_code = 422
    code = "VALIDATION_ERROR"
    message = "Request data is invalid"

class ConflictError(AppException):
    status_code = 409
    code = "CONFLICT"
    message = "Resource state conflict"
