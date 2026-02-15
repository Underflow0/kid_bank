"""
Unit tests for GET /children Lambda function.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from decimal import Decimal


@pytest.fixture
def mock_dynamodb():
    with patch("src.lambdas.family.list_children.DynamoDBClient") as mock:
        yield mock


@pytest.fixture
def mock_parent_event():
    """Mock event for parent user."""
    return {
        "httpMethod": "GET",
        "path": "/children",
        "headers": {"Authorization": "Bearer test-token"},
        "requestContext": {
            "authorizer": {
                "userId": "parent-123",
                "email": "parent@example.com",
                "groups": ["Parents"],
            }
        },
    }


class TestListChildren:
    def test_list_children_success(self, mock_dynamodb, mock_parent_event):
        from src.lambdas.family.list_children import lambda_handler

        # Mock DynamoDB response
        mock_db_instance = MagicMock()
        mock_db_instance.get_children_for_parent.return_value = [
            {
                "userId": "child-1",
                "name": "Alice",
                "email": "alice@example.com",
                "balance": Decimal("100.00"),
                "interestRate": Decimal("0.05"),
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-01T00:00:00Z",
            },
            {
                "userId": "child-2",
                "name": "Bob",
                "email": "bob@example.com",
                "balance": Decimal("50.00"),
                "interestRate": Decimal("0.05"),
                "createdAt": "2024-01-02T00:00:00Z",
                "updatedAt": "2024-01-02T00:00:00Z",
            },
        ]
        mock_dynamodb.return_value = mock_db_instance

        # Call handler
        response = lambda_handler(mock_parent_event, None)

        # Assertions
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "children" in body
        assert body["count"] == 2
        assert len(body["children"]) == 2
        assert body["children"][0]["name"] == "Alice"
        assert body["children"][0]["balance"] == 100.00
        assert body["children"][1]["name"] == "Bob"

    def test_list_children_empty(self, mock_dynamodb, mock_parent_event):
        from src.lambdas.family.list_children import lambda_handler

        mock_db_instance = MagicMock()
        mock_db_instance.get_children_for_parent.return_value = []
        mock_dynamodb.return_value = mock_db_instance

        response = lambda_handler(mock_parent_event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["children"] == []
        assert body["count"] == 0

    def test_list_children_database_error(self, mock_dynamodb, mock_parent_event):
        from src.lambdas.family.list_children import lambda_handler
        from src.common.errors import DatabaseError

        mock_db_instance = MagicMock()
        mock_db_instance.get_children_for_parent.side_effect = DatabaseError("DB error")
        mock_dynamodb.return_value = mock_db_instance

        response = lambda_handler(mock_parent_event, None)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body

    def test_list_children_unexpected_error(self, mock_dynamodb, mock_parent_event):
        from src.lambdas.family.list_children import lambda_handler

        mock_db_instance = MagicMock()
        mock_db_instance.get_children_for_parent.side_effect = Exception("Unexpected")
        mock_dynamodb.return_value = mock_db_instance

        response = lambda_handler(mock_parent_event, None)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["error"] == "Internal server error"

    def test_list_children_correct_parent_id(self, mock_dynamodb, mock_parent_event):
        from src.lambdas.family.list_children import lambda_handler

        mock_db_instance = MagicMock()
        mock_db_instance.get_children_for_parent.return_value = []
        mock_dynamodb.return_value = mock_db_instance

        lambda_handler(mock_parent_event, None)

        # Verify the correct parent ID was used
        mock_db_instance.get_children_for_parent.assert_called_once_with("parent-123")
