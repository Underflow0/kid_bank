"""
Unit tests for DynamoDB client.
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from src.common.dynamodb import DynamoDBClient
from src.common.models import UserRole, TransactionType
from src.common.errors import (
    InsufficientFundsError, DatabaseError, NotFoundError, ConflictError
)


@pytest.fixture
def dynamodb_client(dynamodb_table):
    """DynamoDB client with mocked table."""
    return DynamoDBClient()


class TestGetUserProfile:
    def test_get_existing_user(self, dynamodb_client, sample_parent_user):
        dynamodb_client.table.put_item(Item=sample_parent_user)

        result = dynamodb_client.get_user_profile('parent-123')

        assert result is not None
        assert result['userId'] == 'parent-123'
        assert result['email'] == 'parent@example.com'

    def test_get_nonexistent_user(self, dynamodb_client):
        result = dynamodb_client.get_user_profile('nonexistent')
        assert result is None


class TestCreateUserProfile:
    def test_create_parent_profile(self, dynamodb_client):
        profile = dynamodb_client.create_user_profile(
            user_id='parent-new',
            email='new@example.com',
            name='New Parent',
            role=UserRole.PARENT
        )

        assert profile.user_id == 'parent-new'
        assert profile.email == 'new@example.com'
        assert profile.name == 'New Parent'
        assert profile.role == UserRole.PARENT
        assert profile.balance == Decimal('0.00')
        assert profile.parent_id is None

        # Verify in DB
        item = dynamodb_client.get_user_profile('parent-new')
        assert item is not None
        assert item['userId'] == 'parent-new'

    def test_create_child_profile(self, dynamodb_client):
        profile = dynamodb_client.create_user_profile(
            user_id='child-new',
            email='child@example.com',
            name='New Child',
            role=UserRole.CHILD,
            parent_id='parent-123',
            balance=Decimal('50.00'),
            interest_rate=Decimal('0.10')
        )

        assert profile.user_id == 'child-new'
        assert profile.role == UserRole.CHILD
        assert profile.parent_id == 'parent-123'
        assert profile.balance == Decimal('50.00')
        assert profile.interest_rate == Decimal('0.10')

        # Verify GSI attributes
        item = dynamodb_client.get_user_profile('child-new')
        assert item['GSI1PK'] == 'PARENT#parent-123'
        assert item['GSI1SK'] == 'CHILD#child-new'
        assert item['GSI2PK'] == 'ROLE#child'
        assert item['GSI2SK'] == 'USER#child-new'


class TestUpdateUserProfile:
    def test_update_name(self, dynamodb_client, sample_parent_user):
        dynamodb_client.table.put_item(Item=sample_parent_user)

        result = dynamodb_client.update_user_profile(
            user_id='parent-123',
            name='Updated Name'
        )

        assert result['name'] == 'Updated Name'
        assert 'updatedAt' in result

    def test_update_interest_rate(self, dynamodb_client, sample_child_user):
        dynamodb_client.table.put_item(Item=sample_child_user)

        result = dynamodb_client.update_user_profile(
            user_id='child-456',
            interest_rate=Decimal('0.10')
        )

        assert Decimal(str(result['interestRate'])) == Decimal('0.10')

    def test_update_both_fields(self, dynamodb_client, sample_child_user):
        dynamodb_client.table.put_item(Item=sample_child_user)

        result = dynamodb_client.update_user_profile(
            user_id='child-456',
            name='New Name',
            interest_rate=Decimal('0.08')
        )

        assert result['name'] == 'New Name'
        assert Decimal(str(result['interestRate'])) == Decimal('0.08')


class TestGetChildrenForParent:
    def test_get_children(self, dynamodb_client, sample_parent_user, sample_child_user):
        # Create parent and child
        dynamodb_client.table.put_item(Item=sample_parent_user)
        dynamodb_client.table.put_item(Item=sample_child_user)

        # Create another child
        child2 = sample_child_user.copy()
        child2['userId'] = 'child-789'
        child2['PK'] = 'USER#child-789'
        child2['GSI1SK'] = 'CHILD#child-789'
        child2['GSI2SK'] = 'USER#child-789'
        dynamodb_client.table.put_item(Item=child2)

        children = dynamodb_client.get_children_for_parent('parent-123')

        assert len(children) == 2
        child_ids = [c['userId'] for c in children]
        assert 'child-456' in child_ids
        assert 'child-789' in child_ids

    def test_get_children_no_results(self, dynamodb_client):
        children = dynamodb_client.get_children_for_parent('no-children-parent')
        assert children == []


class TestGetTransactions:
    def test_get_transactions(self, dynamodb_client, sample_child_user, sample_transaction):
        # Create user and transaction
        dynamodb_client.table.put_item(Item=sample_child_user)
        dynamodb_client.table.put_item(Item=sample_transaction)

        result = dynamodb_client.get_transactions('child-456')

        assert 'transactions' in result
        assert len(result['transactions']) == 1
        assert result['transactions'][0]['transactionId'] == 'txn-789'

    def test_get_transactions_with_limit(self, dynamodb_client, sample_child_user):
        # Create multiple transactions
        dynamodb_client.table.put_item(Item=sample_child_user)

        for i in range(5):
            txn = {
                'PK': 'USER#child-456',
                'SK': f'TRANS#2024-01-{i+1:02d}T00:00:00Z#txn-{i}',
                'transactionId': f'txn-{i}',
                'userId': 'child-456',
                'amount': Decimal('10.00'),
                'type': 'deposit',
                'description': f'Transaction {i}',
                'balanceAfter': Decimal(str(10.00 * (i + 1))),
                'initiatedBy': 'parent-123',
                'timestamp': f'2024-01-{i+1:02d}T00:00:00Z'
            }
            dynamodb_client.table.put_item(Item=txn)

        result = dynamodb_client.get_transactions('child-456', limit=3)

        assert len(result['transactions']) <= 3

    def test_get_transactions_empty(self, dynamodb_client, sample_child_user):
        dynamodb_client.table.put_item(Item=sample_child_user)

        result = dynamodb_client.get_transactions('child-456')

        assert result['transactions'] == []
        assert 'nextToken' not in result


class TestAdjustBalanceWithTransaction:
    def test_deposit(self, dynamodb_client, sample_child_user):
        dynamodb_client.table.put_item(Item=sample_child_user)

        result = dynamodb_client.adjust_balance_with_transaction(
            user_id='child-456',
            amount=Decimal('50.00'),
            transaction_type=TransactionType.DEPOSIT,
            description='Birthday gift',
            initiated_by='parent-123'
        )

        assert result['amount'] == 50.00
        assert result['type'] == 'deposit'
        assert result['balanceAfter'] == 150.00

        # Verify balance updated
        user = dynamodb_client.get_user_profile('child-456')
        assert user['balance'] == Decimal('150.00')

        # Verify transaction created
        transactions = dynamodb_client.get_transactions('child-456')
        assert len(transactions['transactions']) == 1

    def test_withdrawal(self, dynamodb_client, sample_child_user):
        dynamodb_client.table.put_item(Item=sample_child_user)

        result = dynamodb_client.adjust_balance_with_transaction(
            user_id='child-456',
            amount=Decimal('-30.00'),
            transaction_type=TransactionType.WITHDRAWAL,
            description='Toy purchase',
            initiated_by='child-456'
        )

        assert result['amount'] == -30.00
        assert result['type'] == 'withdrawal'
        assert result['balanceAfter'] == 70.00

    def test_insufficient_funds(self, dynamodb_client, sample_child_user):
        dynamodb_client.table.put_item(Item=sample_child_user)

        with pytest.raises(InsufficientFundsError):
            dynamodb_client.adjust_balance_with_transaction(
                user_id='child-456',
                amount=Decimal('-200.00'),  # More than balance
                transaction_type=TransactionType.WITHDRAWAL,
                description='Too much',
                initiated_by='child-456'
            )

    def test_user_not_found(self, dynamodb_client):
        with pytest.raises(NotFoundError):
            dynamodb_client.adjust_balance_with_transaction(
                user_id='nonexistent',
                amount=Decimal('50.00'),
                transaction_type=TransactionType.DEPOSIT,
                description='Test',
                initiated_by='parent-123'
            )

    def test_interest_payment(self, dynamodb_client, sample_child_user):
        dynamodb_client.table.put_item(Item=sample_child_user)

        result = dynamodb_client.adjust_balance_with_transaction(
            user_id='child-456',
            amount=Decimal('5.00'),
            transaction_type=TransactionType.INTEREST,
            description='Monthly interest',
            initiated_by='system'
        )

        assert result['type'] == 'interest'
        assert result['balanceAfter'] == 105.00


class TestScanAllChildren:
    def test_scan_with_gsi(self, dynamodb_client, sample_child_user):
        # Create multiple children
        dynamodb_client.table.put_item(Item=sample_child_user)

        child2 = sample_child_user.copy()
        child2['userId'] = 'child-789'
        child2['PK'] = 'USER#child-789'
        child2['GSI2SK'] = 'USER#child-789'
        dynamodb_client.table.put_item(Item=child2)

        children = dynamodb_client.scan_all_children()

        assert len(children) == 2
        child_ids = [c['userId'] for c in children]
        assert 'child-456' in child_ids
        assert 'child-789' in child_ids

    def test_scan_no_children(self, dynamodb_client, sample_parent_user):
        # Only create a parent
        dynamodb_client.table.put_item(Item=sample_parent_user)

        children = dynamodb_client.scan_all_children()

        assert len(children) == 0


class TestDatabaseErrors:
    def test_get_user_profile_error(self, dynamodb_client):
        with patch.object(dynamodb_client.table, 'get_item') as mock_get:
            mock_get.side_effect = ClientError(
                {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
                'GetItem'
            )

            with pytest.raises(DatabaseError):
                dynamodb_client.get_user_profile('user-123')

    def test_create_user_profile_error(self, dynamodb_client):
        with patch.object(dynamodb_client.table, 'put_item') as mock_put:
            mock_put.side_effect = ClientError(
                {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
                'PutItem'
            )

            with pytest.raises(DatabaseError):
                dynamodb_client.create_user_profile(
                    user_id='test',
                    email='test@test.com',
                    name='Test',
                    role=UserRole.PARENT
                )
