#!/bin/bash
# Helper script to run tests with proper environment setup

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Activate virtual environment
source venv/bin/activate

# Set Python path
export PYTHONPATH=/home/under/dev/kid_bank/backend/src:$PYTHONPATH

# Parse command line arguments
case "$1" in
    "")
        echo -e "${GREEN}Running all unit tests...${NC}"
        pytest tests/unit/ -v
        ;;
    "coverage")
        echo -e "${GREEN}Running tests with coverage report...${NC}"
        pytest tests/unit/ --cov=src --cov-report=html --cov-report=term
        echo -e "${YELLOW}Coverage report saved to htmlcov/index.html${NC}"
        ;;
    "quick")
        echo -e "${GREEN}Running tests without coverage (faster)...${NC}"
        pytest tests/unit/ -v --no-cov
        ;;
    "models")
        echo -e "${GREEN}Running model tests only...${NC}"
        pytest tests/unit/test_models.py -v
        ;;
    "auth")
        echo -e "${GREEN}Running auth tests only...${NC}"
        pytest tests/unit/test_auth.py -v
        ;;
    "dynamodb")
        echo -e "${GREEN}Running DynamoDB tests only...${NC}"
        pytest tests/unit/test_dynamodb.py -v
        ;;
    "passing")
        echo -e "${GREEN}Running only passing tests...${NC}"
        pytest tests/unit/test_models.py tests/unit/test_auth.py tests/unit/test_dynamodb.py -v
        ;;
    "watch")
        echo -e "${GREEN}Running tests in watch mode...${NC}"
        pytest-watch tests/unit/
        ;;
    *)
        echo "Usage: ./run_tests.sh [option]"
        echo ""
        echo "Options:"
        echo "  (none)      Run all tests with default settings"
        echo "  coverage    Run with full coverage report"
        echo "  quick       Run without coverage (faster)"
        echo "  models      Run only model tests"
        echo "  auth        Run only auth tests"
        echo "  dynamodb    Run only DynamoDB tests"
        echo "  passing     Run only currently passing tests"
        echo "  watch       Run in watch mode (re-run on file changes)"
        ;;
esac
