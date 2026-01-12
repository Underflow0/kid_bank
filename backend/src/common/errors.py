"""
Custom exception classes for Family Bank application.
"""


class FamilyBankError(Exception):
    """Base exception for all Family Bank errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class UnauthorizedError(FamilyBankError):
    """Raised when authentication fails or token is invalid."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, 401)


class ForbiddenError(FamilyBankError):
    """Raised when user doesn't have permission for the requested action."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, 403)


class NotFoundError(FamilyBankError):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)


class BadRequestError(FamilyBankError):
    """Raised when request validation fails."""

    def __init__(self, message: str = "Bad request"):
        super().__init__(message, 400)


class InsufficientFundsError(FamilyBankError):
    """Raised when attempting to withdraw more than available balance."""

    def __init__(self, message: str = "Insufficient funds"):
        super().__init__(message, 400)


class DatabaseError(FamilyBankError):
    """Raised when a database operation fails."""

    def __init__(self, message: str = "Database error"):
        super().__init__(message, 500)


class ConflictError(FamilyBankError):
    """Raised when there's a conflict (e.g., concurrent updates)."""

    def __init__(self, message: str = "Conflict"):
        super().__init__(message, 409)
