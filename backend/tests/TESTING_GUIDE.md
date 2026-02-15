# Testing Guide - Virtual Family Bank

## Overview

We've implemented comprehensive unit tests for the Virtual Family Bank backend. This document provides guidance on running and understanding the test suite.

## Test Coverage Summary

### ✅ Unit Tests Created

1. **test_models.py** - Data model tests (100% coverage)
   - UserRole, TransactionType, CognitoGroup enums
   - KeyPattern utilities
   - UserProfile and Transaction models
   - Serialization/deserialization

2. **test_auth.py** - Authentication & authorization tests
   - JWT verification and parsing
   - Token group extraction
   - Authorization decorator
   - JWKS caching
   - Group-based access control

3. **test_dynamodb.py** - DynamoDB client tests
   - User profile CRUD operations
   - Transaction management
   - Balance adjustments with atomic transactions
   - Children queries (GSI)
   - Error handling
   - Insufficient funds protection

4. **test_lambda_get_user.py** - GET /user endpoint
   - Successful user retrieval
   - User not found scenarios
   - Database error handling
   - Parent and child users

5. **test_lambda_adjust_balance.py** - POST /adjust-balance endpoint
   - Balance adjustments (deposits/withdrawals)
   - Input validation
   - Parent authorization
   - Insufficient funds protection
   - Zero amount rejection
   - Default description handling

6. **test_lambda_list_children.py** - GET /children endpoint
   - Listing children for parent
   - Empty results
   - Error handling
   - Correct parent ID usage

## Running the Tests

### Install Dependencies

```bash
cd backend
pip install -r requirements-dev.txt
```

### Run All Unit Tests

```bash
pytest tests/unit/ -v
```

### Run with Coverage

```bash
pytest tests/unit/ --cov=src --cov-report=html --cov-report=term-missing
```

Then open `htmlcov/index.html` in your browser to see detailed coverage.

### Run Specific Test File

```bash
pytest tests/unit/test_auth.py -v
```

### Run Tests in Watch Mode

```bash
pytest-watch tests/unit/
```

## Expected Test Results

When you run the unit tests, you should see output similar to:

```
tests/unit/test_models.py::TestUserRole::test_parent_role PASSED
tests/unit/test_models.py::TestUserRole::test_child_role PASSED
tests/unit/test_auth.py::TestAuthorizeDecorator::test_authorize_valid_token PASSED
tests/unit/test_dynamodb.py::TestAdjustBalanceWithTransaction::test_deposit PASSED
...

======= X passed in X.XXs =======
```

## Test Structure

Each test file follows this pattern:

```python
"""
Module docstring explaining what's being tested
"""
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_dependency():
    """Fixture for mocking dependencies"""
    # Setup
    yield mock
    # Teardown (if needed)

class TestFeature:
    """Group related tests in a class"""

    def test_successful_case(self, mock_dependency):
        """Test the happy path"""
        # Arrange
        # Act
        # Assert

    def test_error_case(self, mock_dependency):
        """Test error handling"""
        # Arrange
        # Act
        # Assert
```

## Key Testing Patterns

### 1. Mocking AWS Services

We use `moto` to mock AWS services like DynamoDB:

```python
@pytest.fixture
def dynamodb_table(aws_credentials):
    with mock_aws():
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.create_table(...)
        yield table
```

### 2. Mocking Lambda Event Context

API Gateway events are mocked with proper structure:

```python
event = {
    'httpMethod': 'POST',
    'body': json.dumps({'key': 'value'}),
    'headers': {'Authorization': 'Bearer token'},
    'requestContext': {
        'authorizer': {
            'userId': 'user-123',
            'groups': ['Parents']
        }
    }
}
```

### 3. Testing Authorization

The `@authorize` decorator is tested by mocking JWT verification:

```python
@patch('src.common.auth.verify_jwt')
def test_authorization(mock_verify):
    mock_verify.return_value = {'sub': 'user-123', 'cognito:groups': ['Parents']}
    # Test the handler
```

### 4. Testing Atomic Transactions

DynamoDB transactions are tested with moto's full transaction support:

```python
def test_atomic_transaction(dynamodb_client):
    # Create initial state
    dynamodb_client.table.put_item(Item=user)

    # Perform atomic operation
    result = dynamodb_client.adjust_balance_with_transaction(...)

    # Verify both user and transaction records updated
    assert result['balanceAfter'] == expected
```

## Next Steps

### Integration Tests (Task #3)

Integration tests will:
- Test full request/response flows
- Use SAM local or deployed test stack
- Test actual AWS service interactions
- Verify end-to-end scenarios

### CI/CD Integration (Task #10)

Tests will run automatically in GitHub Actions:
- On every push and PR
- Before deployments
- With coverage reporting
- Fail the build if tests fail

## Troubleshooting

### Import Errors

Make sure you're in the `backend/` directory when running tests:

```bash
cd backend
pytest
```

### Mock Not Working

Ensure you're patching the right import path. Patch where the object is used, not where it's defined:

```python
# If get_user.py imports: from common import DynamoDBClient
# Patch it as:
@patch('src.lambdas.auth.get_user.DynamoDBClient')
```

### DynamoDB Errors

If you see DynamoDB connection errors:
1. Ensure `moto[dynamodb]` is installed
2. Use the `dynamodb_table` fixture
3. Check that AWS credentials are mocked

### Coverage Too Low

To find uncovered lines:

```bash
pytest --cov=src --cov-report=term-missing
```

Look for lines marked with `!!!!` in the output.

## Best Practices

1. ✅ **Write tests first** (TDD) when adding new features
2. ✅ **Keep tests independent** - Each test should run in isolation
3. ✅ **Use descriptive names** - Test names should explain what's being tested
4. ✅ **Test edge cases** - Empty inputs, None values, boundaries
5. ✅ **Mock external dependencies** - Unit tests should be fast
6. ✅ **One logical assertion per test** - Makes failures easier to debug
7. ✅ **Clean up after tests** - Use fixtures for setup/teardown

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [moto AWS mocking](http://docs.getmoto.org/)
- [AWS Lambda Python testing](https://docs.aws.amazon.com/lambda/latest/dg/python-test.html)
- [Testing best practices](https://docs.pytest.org/en/latest/goodpractices.html)
