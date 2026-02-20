"""
Common utilities for Family Bank application.
"""

from .auth import authorize, get_auth_context, is_parent, is_child
from .dynamodb import DynamoDBClient
from .errors import (
    FamilyBankError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    BadRequestError,
    InsufficientFundsError,
    DatabaseError,
    ConflictError,
)
from .logger import get_logger
from .models import (
    UserRole,
    TransactionType,
    CognitoGroup,
    KeyPattern,
    UserProfile,
    Transaction,
    DEFAULT_INTEREST_RATE,
    DEFAULT_CHILD_BALANCE,
    MAX_TRANSACTION_PAGINATION_LIMIT,
)

__all__ = [
    "authorize",
    "get_auth_context",
    "is_parent",
    "is_child",
    "DynamoDBClient",
    "FamilyBankError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "BadRequestError",
    "InsufficientFundsError",
    "DatabaseError",
    "ConflictError",
    "get_logger",
    "UserRole",
    "TransactionType",
    "CognitoGroup",
    "KeyPattern",
    "UserProfile",
    "Transaction",
    "DEFAULT_INTEREST_RATE",
    "DEFAULT_CHILD_BALANCE",
    "MAX_TRANSACTION_PAGINATION_LIMIT",
]
