"""
Data models and constants for Family Bank application.
"""
from enum import Enum
from typing import Optional
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime


class UserRole(str, Enum):
    """User role enum."""
    PARENT = "parent"
    CHILD = "child"


class TransactionType(str, Enum):
    """Transaction type enum."""
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    INTEREST = "interest"
    ADJUSTMENT = "adjustment"


class CognitoGroup(str, Enum):
    """Cognito group names."""
    PARENTS = "Parents"
    CHILDREN = "Children"


# DynamoDB key patterns
class KeyPattern:
    """DynamoDB key patterns for single-table design."""

    @staticmethod
    def user_pk(user_id: str) -> str:
        """Generate user partition key."""
        return f"USER#{user_id}"

    @staticmethod
    def profile_sk() -> str:
        """Generate profile sort key."""
        return "PROFILE"

    @staticmethod
    def transaction_sk(timestamp: str, transaction_id: str) -> str:
        """Generate transaction sort key."""
        return f"TRANS#{timestamp}#{transaction_id}"

    @staticmethod
    def parent_gsi1_pk(parent_id: str) -> str:
        """Generate GSI1 partition key for parent-child relationship."""
        return f"PARENT#{parent_id}"

    @staticmethod
    def child_gsi1_sk(child_id: str) -> str:
        """Generate GSI1 sort key for parent-child relationship."""
        return f"CHILD#{child_id}"

    @staticmethod
    def role_gsi2_pk(role: UserRole) -> str:
        """Generate GSI2 partition key for role-based queries."""
        return f"ROLE#{role.value}"

    @staticmethod
    def user_gsi2_sk(user_id: str) -> str:
        """Generate GSI2 sort key for role-based queries."""
        return f"USER#{user_id}"


@dataclass
class UserProfile:
    """User profile data model."""
    user_id: str
    email: str
    name: str
    role: UserRole
    balance: Decimal
    interest_rate: Decimal
    created_at: str
    updated_at: str
    parent_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for DynamoDB."""
        return {
            'userId': self.user_id,
            'email': self.email,
            'name': self.name,
            'role': self.role.value,
            'balance': float(self.balance),
            'interestRate': float(self.interest_rate),
            'createdAt': self.created_at,
            'updatedAt': self.updated_at,
            'parentId': self.parent_id,
        }

    @classmethod
    def from_dynamodb_item(cls, item: dict) -> 'UserProfile':
        """Create from DynamoDB item."""
        return cls(
            user_id=item['userId'],
            email=item['email'],
            name=item['name'],
            role=UserRole(item['role']),
            balance=Decimal(str(item['balance'])),
            interest_rate=Decimal(str(item['interestRate'])),
            created_at=item['createdAt'],
            updated_at=item['updatedAt'],
            parent_id=item.get('parentId'),
        )


@dataclass
class Transaction:
    """Transaction data model."""
    transaction_id: str
    user_id: str
    amount: Decimal
    type: TransactionType
    description: str
    balance_after: Decimal
    initiated_by: str
    timestamp: str

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            'transactionId': self.transaction_id,
            'userId': self.user_id,
            'amount': float(self.amount),
            'type': self.type.value,
            'description': self.description,
            'balanceAfter': float(self.balance_after),
            'initiatedBy': self.initiated_by,
            'timestamp': self.timestamp,
        }

    @classmethod
    def from_dynamodb_item(cls, item: dict) -> 'Transaction':
        """Create from DynamoDB item."""
        return cls(
            transaction_id=item['transactionId'],
            user_id=item['userId'],
            amount=Decimal(str(item['amount'])),
            type=TransactionType(item['type']),
            description=item['description'],
            balance_after=Decimal(str(item['balanceAfter'])),
            initiated_by=item['initiatedBy'],
            timestamp=item['timestamp'],
        )


# Constants
DEFAULT_INTEREST_RATE = Decimal('0.05')  # 5%
DEFAULT_CHILD_BALANCE = Decimal('0.00')
TRANSACTION_PAGINATION_LIMIT = 50
MAX_TRANSACTION_PAGINATION_LIMIT = 100
