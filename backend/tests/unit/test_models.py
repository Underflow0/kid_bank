"""
Unit tests for data models.
"""
import pytest
from decimal import Decimal
from src.common.models import (
    UserRole, TransactionType, CognitoGroup, KeyPattern,
    UserProfile, Transaction,
    DEFAULT_INTEREST_RATE, DEFAULT_CHILD_BALANCE
)


class TestUserRole:
    def test_parent_role(self):
        assert UserRole.PARENT.value == "parent"

    def test_child_role(self):
        assert UserRole.CHILD.value == "child"


class TestTransactionType:
    def test_all_types(self):
        assert TransactionType.DEPOSIT.value == "deposit"
        assert TransactionType.WITHDRAWAL.value == "withdrawal"
        assert TransactionType.INTEREST.value == "interest"
        assert TransactionType.ADJUSTMENT.value == "adjustment"


class TestCognitoGroup:
    def test_group_names(self):
        assert CognitoGroup.PARENTS.value == "Parents"
        assert CognitoGroup.CHILDREN.value == "Children"


class TestKeyPattern:
    def test_user_pk(self):
        assert KeyPattern.user_pk("user-123") == "USER#user-123"

    def test_profile_sk(self):
        assert KeyPattern.profile_sk() == "PROFILE"

    def test_transaction_sk(self):
        result = KeyPattern.transaction_sk("2024-01-01T00:00:00Z", "txn-123")
        assert result == "TRANS#2024-01-01T00:00:00Z#txn-123"

    def test_parent_gsi1_pk(self):
        assert KeyPattern.parent_gsi1_pk("parent-123") == "PARENT#parent-123"

    def test_child_gsi1_sk(self):
        assert KeyPattern.child_gsi1_sk("child-456") == "CHILD#child-456"

    def test_role_gsi2_pk(self):
        assert KeyPattern.role_gsi2_pk(UserRole.CHILD) == "ROLE#child"

    def test_user_gsi2_sk(self):
        assert KeyPattern.user_gsi2_sk("user-123") == "USER#user-123"


class TestUserProfile:
    def test_to_dict(self):
        profile = UserProfile(
            user_id="user-123",
            email="test@test.com",
            name="Test User",
            role=UserRole.PARENT,
            balance=Decimal("100.50"),
            interest_rate=Decimal("0.05"),
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            parent_id=None
        )

        result = profile.to_dict()

        assert result['userId'] == "user-123"
        assert result['email'] == "test@test.com"
        assert result['name'] == "Test User"
        assert result['role'] == "parent"
        assert result['balance'] == 100.50
        assert result['interestRate'] == 0.05
        assert result['createdAt'] == "2024-01-01T00:00:00Z"
        assert result['updatedAt'] == "2024-01-01T00:00:00Z"
        assert result['parentId'] is None

    def test_to_dict_with_parent_id(self):
        profile = UserProfile(
            user_id="child-456",
            email="child@test.com",
            name="Child User",
            role=UserRole.CHILD,
            balance=Decimal("50.00"),
            interest_rate=Decimal("0.05"),
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            parent_id="parent-123"
        )

        result = profile.to_dict()
        assert result['parentId'] == "parent-123"

    def test_from_dynamodb_item(self):
        item = {
            'userId': 'user-123',
            'email': 'test@test.com',
            'name': 'Test User',
            'role': 'parent',
            'balance': Decimal('100.50'),
            'interestRate': Decimal('0.05'),
            'createdAt': '2024-01-01T00:00:00Z',
            'updatedAt': '2024-01-01T00:00:00Z',
        }

        profile = UserProfile.from_dynamodb_item(item)

        assert profile.user_id == "user-123"
        assert profile.email == "test@test.com"
        assert profile.name == "Test User"
        assert profile.role == UserRole.PARENT
        assert profile.balance == Decimal("100.50")
        assert profile.interest_rate == Decimal("0.05")
        assert profile.parent_id is None


class TestTransaction:
    def test_to_dict(self):
        txn = Transaction(
            transaction_id="txn-123",
            user_id="user-456",
            amount=Decimal("50.00"),
            type=TransactionType.DEPOSIT,
            description="Test deposit",
            balance_after=Decimal("150.00"),
            initiated_by="parent-123",
            timestamp="2024-01-01T00:00:00Z"
        )

        result = txn.to_dict()

        assert result['transactionId'] == "txn-123"
        assert result['userId'] == "user-456"
        assert result['amount'] == 50.00
        assert result['type'] == "deposit"
        assert result['description'] == "Test deposit"
        assert result['balanceAfter'] == 150.00
        assert result['initiatedBy'] == "parent-123"
        assert result['timestamp'] == "2024-01-01T00:00:00Z"

    def test_from_dynamodb_item(self):
        item = {
            'transactionId': 'txn-123',
            'userId': 'user-456',
            'amount': Decimal('50.00'),
            'type': 'deposit',
            'description': 'Test deposit',
            'balanceAfter': Decimal('150.00'),
            'initiatedBy': 'parent-123',
            'timestamp': '2024-01-01T00:00:00Z'
        }

        txn = Transaction.from_dynamodb_item(item)

        assert txn.transaction_id == "txn-123"
        assert txn.user_id == "user-456"
        assert txn.amount == Decimal("50.00")
        assert txn.type == TransactionType.DEPOSIT
        assert txn.description == "Test deposit"
        assert txn.balance_after == Decimal("150.00")
        assert txn.initiated_by == "parent-123"
        assert txn.timestamp == "2024-01-01T00:00:00Z"


class TestConstants:
    def test_default_interest_rate(self):
        assert DEFAULT_INTEREST_RATE == Decimal('0.05')

    def test_default_child_balance(self):
        assert DEFAULT_CHILD_BALANCE == Decimal('0.00')
