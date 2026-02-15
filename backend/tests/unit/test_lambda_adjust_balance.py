"""
Unit tests for POST /adjust-balance Lambda function.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from decimal import Decimal


@pytest.fixture
def mock_dynamodb():
    with patch("src.lambdas.transactions.adjust_balance.DynamoDBClient") as mock:
        yield mock


@pytest.fixture
def mock_parent_event():
    """Mock event for parent user."""
    return {
        "httpMethod": "POST",
        "path": "/adjust-balance",
        "headers": {
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json",
        },
        "body": json.dumps(
            {"childId": "child-456", "amount": 50.00, "description": "Birthday gift"}
        ),
        "requestContext": {
            "authorizer": {
                "userId": "parent-123",
                "email": "parent@example.com",
                "groups": ["Parents"],
            }
        },
    }


class TestAdjustBalance:
    def test_adjust_balance_success(self, mock_dynamodb, mock_parent_event):
        from src.lambdas.transactions.adjust_balance import lambda_handler

        # Mock DynamoDB
        mock_db_instance = MagicMock()
        mock_db_instance.get_user_profile.return_value = {
            "userId": "child-456",
            "parentId": "parent-123",
            "balance": Decimal("100.00"),
        }
        mock_db_instance.adjust_balance_with_transaction.return_value = {
            "transactionId": "txn-789",
            "userId": "child-456",
            "amount": 50.00,
            "type": "adjustment",
            "description": "Birthday gift",
            "balanceAfter": 150.00,
            "initiatedBy": "parent-123",
            "timestamp": "2024-01-01T00:00:00Z",
        }
        mock_dynamodb.return_value = mock_db_instance

        # Call handler
        response = lambda_handler(mock_parent_event, None)

        # Assertions
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "transaction" in body
        assert body["transaction"]["amount"] == 50.00
        assert body["transaction"]["balanceAfter"] == 150.00

    def test_adjust_balance_negative_amount(self, mock_dynamodb, mock_parent_event):
        from src.lambdas.transactions.adjust_balance import lambda_handler

        # Withdrawal
        body = json.loads(mock_parent_event["body"])
        body["amount"] = -30.00
        mock_parent_event["body"] = json.dumps(body)

        mock_db_instance = MagicMock()
        mock_db_instance.get_user_profile.return_value = {
            "userId": "child-456",
            "parentId": "parent-123",
            "balance": Decimal("100.00"),
        }
        mock_db_instance.adjust_balance_with_transaction.return_value = {
            "transactionId": "txn-789",
            "userId": "child-456",
            "amount": -30.00,
            "type": "adjustment",
            "description": "Birthday gift",
            "balanceAfter": 70.00,
            "initiatedBy": "parent-123",
            "timestamp": "2024-01-01T00:00:00Z",
        }
        mock_dynamodb.return_value = mock_db_instance

        response = lambda_handler(mock_parent_event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["transaction"]["amount"] == -30.00
        assert body["transaction"]["balanceAfter"] == 70.00

    def test_adjust_balance_missing_child_id(self, mock_dynamodb, mock_parent_event):
        from src.lambdas.transactions.adjust_balance import lambda_handler

        body = json.loads(mock_parent_event["body"])
        del body["childId"]
        mock_parent_event["body"] = json.dumps(body)

        response = lambda_handler(mock_parent_event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "childId" in body["error"]

    def test_adjust_balance_missing_amount(self, mock_dynamodb, mock_parent_event):
        from src.lambdas.transactions.adjust_balance import lambda_handler

        body = json.loads(mock_parent_event["body"])
        del body["amount"]
        mock_parent_event["body"] = json.dumps(body)

        response = lambda_handler(mock_parent_event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "amount" in body["error"]

    def test_adjust_balance_invalid_amount(self, mock_dynamodb, mock_parent_event):
        from src.lambdas.transactions.adjust_balance import lambda_handler

        body = json.loads(mock_parent_event["body"])
        body["amount"] = "invalid"
        mock_parent_event["body"] = json.dumps(body)

        response = lambda_handler(mock_parent_event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "valid number" in body["error"]

    def test_adjust_balance_zero_amount(self, mock_dynamodb, mock_parent_event):
        from src.lambdas.transactions.adjust_balance import lambda_handler

        body = json.loads(mock_parent_event["body"])
        body["amount"] = 0
        mock_parent_event["body"] = json.dumps(body)

        response = lambda_handler(mock_parent_event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "cannot be zero" in body["error"]

    def test_adjust_balance_child_not_found(self, mock_dynamodb, mock_parent_event):
        from src.lambdas.transactions.adjust_balance import lambda_handler

        mock_db_instance = MagicMock()
        mock_db_instance.get_user_profile.return_value = None
        mock_dynamodb.return_value = mock_db_instance

        response = lambda_handler(mock_parent_event, None)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "not found" in body["error"]

    def test_adjust_balance_wrong_parent(self, mock_dynamodb, mock_parent_event):
        from src.lambdas.transactions.adjust_balance import lambda_handler

        mock_db_instance = MagicMock()
        mock_db_instance.get_user_profile.return_value = {
            "userId": "child-456",
            "parentId": "different-parent",  # Different parent
            "balance": Decimal("100.00"),
        }
        mock_dynamodb.return_value = mock_db_instance

        response = lambda_handler(mock_parent_event, None)

        assert response["statusCode"] == 403
        body = json.loads(response["body"])
        assert "own children" in body["error"]

    def test_adjust_balance_insufficient_funds(self, mock_dynamodb, mock_parent_event):
        from src.lambdas.transactions.adjust_balance import lambda_handler
        from src.common.errors import InsufficientFundsError

        body = json.loads(mock_parent_event["body"])
        body["amount"] = -200.00  # More than balance
        mock_parent_event["body"] = json.dumps(body)

        mock_db_instance = MagicMock()
        mock_db_instance.get_user_profile.return_value = {
            "userId": "child-456",
            "parentId": "parent-123",
            "balance": Decimal("100.00"),
        }
        mock_db_instance.adjust_balance_with_transaction.side_effect = (
            InsufficientFundsError("Insufficient funds")
        )
        mock_dynamodb.return_value = mock_db_instance

        response = lambda_handler(mock_parent_event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Insufficient funds" in body["error"]

    def test_adjust_balance_with_default_description(
        self, mock_dynamodb, mock_parent_event
    ):
        from src.lambdas.transactions.adjust_balance import lambda_handler

        # Remove description
        body = json.loads(mock_parent_event["body"])
        del body["description"]
        mock_parent_event["body"] = json.dumps(body)

        mock_db_instance = MagicMock()
        mock_db_instance.get_user_profile.return_value = {
            "userId": "child-456",
            "parentId": "parent-123",
            "balance": Decimal("100.00"),
        }
        mock_db_instance.adjust_balance_with_transaction.return_value = {
            "transactionId": "txn-789",
            "userId": "child-456",
            "amount": 50.00,
            "type": "adjustment",
            "description": "Balance adjustment",
            "balanceAfter": 150.00,
            "initiatedBy": "parent-123",
            "timestamp": "2024-01-01T00:00:00Z",
        }
        mock_dynamodb.return_value = mock_db_instance

        response = lambda_handler(mock_parent_event, None)

        assert response["statusCode"] == 200
        mock_db_instance.adjust_balance_with_transaction.assert_called_once()
        call_args = mock_db_instance.adjust_balance_with_transaction.call_args
        assert call_args[1]["description"] == "Balance adjustment"
