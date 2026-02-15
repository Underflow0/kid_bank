"""
Unit tests for GET /user Lambda function.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from decimal import Decimal


@pytest.fixture
def mock_dynamodb():
    with patch("src.lambdas.auth.get_user.DynamoDBClient") as mock:
        yield mock


@pytest.fixture
def mock_auth_event():
    """Mock event with auth context already added by @authorize decorator."""
    return {
        "httpMethod": "GET",
        "path": "/user",
        "headers": {"Authorization": "Bearer test-token"},
        "requestContext": {
            "authorizer": {
                "userId": "user-123",
                "email": "test@example.com",
                "groups": ["Parents"],
            }
        },
    }


class TestGetUser:
    def test_get_user_success(self, mock_dynamodb, mock_auth_event):
        from src.lambdas.auth.get_user import lambda_handler

        # Mock DynamoDB response
        mock_db_instance = MagicMock()
        mock_db_instance.get_user_profile.return_value = {
            "userId": "user-123",
            "email": "test@example.com",
            "name": "Test User",
            "role": "parent",
            "balance": Decimal("100.00"),
            "interestRate": Decimal("0.05"),
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
        }
        mock_dynamodb.return_value = mock_db_instance

        # Call handler
        response = lambda_handler(mock_auth_event, None)

        # Assertions
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "user" in body
        assert body["user"]["userId"] == "user-123"
        assert body["user"]["email"] == "test@example.com"
        assert body["user"]["balance"] == 100.00

    def test_get_user_with_parent_id(self, mock_dynamodb, mock_auth_event):
        from src.lambdas.auth.get_user import lambda_handler

        # Child user with parentId
        mock_auth_event["requestContext"]["authorizer"]["userId"] = "child-456"
        mock_auth_event["requestContext"]["authorizer"]["groups"] = ["Children"]

        mock_db_instance = MagicMock()
        mock_db_instance.get_user_profile.return_value = {
            "userId": "child-456",
            "email": "child@example.com",
            "name": "Child User",
            "role": "child",
            "balance": Decimal("50.00"),
            "interestRate": Decimal("0.05"),
            "parentId": "parent-123",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
        }
        mock_dynamodb.return_value = mock_db_instance

        response = lambda_handler(mock_auth_event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["user"]["parentId"] == "parent-123"

    def test_get_user_not_found(self, mock_dynamodb, mock_auth_event):
        from src.lambdas.auth.get_user import lambda_handler

        mock_db_instance = MagicMock()
        mock_db_instance.get_user_profile.return_value = None
        mock_dynamodb.return_value = mock_db_instance

        response = lambda_handler(mock_auth_event, None)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "error" in body

    def test_get_user_database_error(self, mock_dynamodb, mock_auth_event):
        from src.lambdas.auth.get_user import lambda_handler
        from src.common.errors import DatabaseError

        mock_db_instance = MagicMock()
        mock_db_instance.get_user_profile.side_effect = DatabaseError(
            "DB connection failed"
        )
        mock_dynamodb.return_value = mock_db_instance

        response = lambda_handler(mock_auth_event, None)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body

    def test_get_user_unexpected_error(self, mock_dynamodb, mock_auth_event):
        from src.lambdas.auth.get_user import lambda_handler

        mock_db_instance = MagicMock()
        mock_db_instance.get_user_profile.side_effect = Exception("Unexpected error")
        mock_dynamodb.return_value = mock_db_instance

        response = lambda_handler(mock_auth_event, None)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["error"] == "Internal server error"
