# Backend Tests

This directory contains unit and integration tests for the Virtual Family Bank backend.

## Structure

```
tests/
├── unit/               # Unit tests (fast, mocked dependencies)
│   ├── test_models.py
│   ├── test_auth.py
│   ├── test_dynamodb.py
│   ├── test_lambda_*.py
│   └── ...
├── integration/        # Integration tests (slower, real AWS services)
│   └── ...
├── fixtures/          # Shared test data and fixtures
├── conftest.py        # Pytest configuration and shared fixtures
└── README.md          # This file
```

## Running Tests

### Prerequisites

Install development dependencies:

```bash
cd backend
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run Unit Tests Only

```bash
pytest tests/unit/ -v
```

### Run Integration Tests Only

```bash
pytest tests/integration/ -v
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html --cov-report=term
```

Coverage report will be generated in `htmlcov/index.html`.

### Run Specific Test File

```bash
pytest tests/unit/test_auth.py -v
```

### Run Specific Test

```bash
pytest tests/unit/test_auth.py::TestAuthorizeDecorator::test_authorize_valid_token -v
```

### Run Tests Matching a Pattern

```bash
pytest -k "test_auth" -v
```

## Test Markers

Tests are marked with custom markers for selective running:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow-running tests

Run tests by marker:

```bash
pytest -m unit           # Run only unit tests
pytest -m integration    # Run only integration tests
pytest -m "not slow"     # Skip slow tests
```

## Writing Tests

### Unit Test Example

```python
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.unit
def test_my_function(mock_dynamodb):
    # Arrange
    mock_db = MagicMock()
    mock_db.get_item.return_value = {'key': 'value'}

    # Act
    result = my_function()

    # Assert
    assert result == expected_value
```

### Integration Test Example

```python
import pytest

@pytest.mark.integration
@pytest.mark.slow
def test_full_workflow(dynamodb_table):
    # Test against real DynamoDB table (mocked with moto)
    # ...
```

## Shared Fixtures

Common fixtures are defined in `conftest.py`:

- `aws_credentials` - Mock AWS credentials
- `dynamodb_table` - Mock DynamoDB table with proper schema
- `sample_parent_user` - Sample parent user data
- `sample_child_user` - Sample child user data
- `sample_transaction` - Sample transaction data
- `mock_auth_context` - Mock authorization context
- `api_gateway_event` - Base API Gateway event structure

## Coverage Goals

- **Overall coverage**: >80%
- **Common utilities**: >90%
- **Lambda handlers**: >80%
- **Models**: 100%

View current coverage:

```bash
pytest --cov=src --cov-report=term-missing
```

## CI/CD Integration

Tests run automatically on:
- Every push to any branch
- Every pull request
- Before deployment to any environment

See `.github/workflows/ci.yml` for CI configuration.

## Troubleshooting

### Tests Can't Import Modules

Make sure you're running pytest from the `backend/` directory:

```bash
cd backend
pytest
```

### AWS Credentials Error

The tests use mocked AWS services via `moto`. If you see AWS credential errors, ensure:
1. The `aws_credentials` fixture is being used
2. Environment variables are set in `conftest.py`

### DynamoDB Connection Error

Integration tests use moto to mock DynamoDB. Ensure:
1. `moto[dynamodb]` is installed
2. Tests use the `dynamodb_table` fixture

### Coverage Too Low

To see which lines aren't covered:

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

## Best Practices

1. **Unit tests should be fast** - Mock external dependencies
2. **One test, one assertion (generally)** - Makes failures clear
3. **Use descriptive test names** - `test_adjust_balance_insufficient_funds` not `test_1`
4. **Test edge cases** - Empty lists, None values, negative numbers, etc.
5. **Clean up after tests** - Use fixtures and context managers
6. **Don't test implementation details** - Test behavior, not internals
7. **Keep tests independent** - Each test should run in isolation

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [moto documentation](http://docs.getmoto.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
