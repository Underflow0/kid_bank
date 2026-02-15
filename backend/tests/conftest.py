"""
Pytest configuration and shared fixtures.
"""

import os
import pytest
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any
from moto import mock_aws

# Set up environment variables for testing
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["DYNAMODB_TABLE_NAME"] = "FamilyBank-test"
os.environ["COGNITO_USER_POOL_ID"] = "us-east-1_test123"
os.environ["COGNITO_CLIENT_ID"] = "test-client-id"
os.environ["COGNITO_REGION"] = "us-east-1"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["USE_ROLE_GSI"] = "true"


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture
def dynamodb_table(aws_credentials):
    """Create a mock DynamoDB table for testing."""
    with mock_aws():
        import boto3

        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        table = dynamodb.create_table(
            TableName="FamilyBank-test",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
                {"AttributeName": "GSI2PK", "AttributeType": "S"},
                {"AttributeName": "GSI2SK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 1,
                        "WriteCapacityUnits": 1,
                    },
                },
                {
                    "IndexName": "GSI2",
                    "KeySchema": [
                        {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 1,
                        "WriteCapacityUnits": 1,
                    },
                },
            ],
            BillingMode="PROVISIONED",
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )

        yield table


@pytest.fixture
def sample_parent_user() -> Dict[str, Any]:
    """Sample parent user data."""
    return {
        "PK": "USER#parent-123",
        "SK": "PROFILE",
        "userId": "parent-123",
        "email": "parent@example.com",
        "name": "John Doe",
        "role": "parent",
        "balance": Decimal("0.00"),
        "interestRate": Decimal("0.00"),
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_child_user() -> Dict[str, Any]:
    """Sample child user data."""
    return {
        "PK": "USER#child-456",
        "SK": "PROFILE",
        "GSI1PK": "PARENT#parent-123",
        "GSI1SK": "CHILD#child-456",
        "GSI2PK": "ROLE#child",
        "GSI2SK": "USER#child-456",
        "userId": "child-456",
        "email": "child@example.com",
        "name": "Jane Doe",
        "role": "child",
        "balance": Decimal("100.00"),
        "interestRate": Decimal("0.05"),
        "parentId": "parent-123",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_transaction() -> Dict[str, Any]:
    """Sample transaction data."""
    return {
        "PK": "USER#child-456",
        "SK": "TRANS#2024-01-15T10:00:00Z#txn-789",
        "transactionId": "txn-789",
        "userId": "child-456",
        "amount": Decimal("50.00"),
        "type": "deposit",
        "description": "Birthday money",
        "balanceAfter": Decimal("150.00"),
        "initiatedBy": "parent-123",
        "timestamp": "2024-01-15T10:00:00Z",
    }


@pytest.fixture
def mock_jwt_token() -> str:
    """Mock JWT token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImVtYWlsIjoidGVzdEB0ZXN0LmNvbSJ9.test"


@pytest.fixture
def mock_auth_context() -> Dict[str, Any]:
    """Mock authorization context from API Gateway."""
    return {
        "userId": "parent-123",
        "email": "parent@example.com",
        "groups": ["Parents"],
    }


@pytest.fixture
def api_gateway_event() -> Dict[str, Any]:
    """Base API Gateway event structure."""
    return {
        "httpMethod": "GET",
        "path": "/test",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer test-token",
        },
        "queryStringParameters": None,
        "pathParameters": None,
        "body": None,
        "requestContext": {
            "requestId": "test-request-id",
            "authorizer": {
                "userId": "parent-123",
                "email": "parent@example.com",
                "groups": ["Parents"],
            },
        },
    }
