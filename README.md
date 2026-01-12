# Virtual Family Bank

A serverless application that allows parents to manage virtual bank accounts for their children, complete with balance tracking, transaction history, and automated monthly interest calculations.

## Features

- **Authentication**: Amazon Cognito with Google OAuth integration
- **Role-Based Access**: Parents and Children with different permissions
- **Balance Management**: Parents can adjust children's balances with atomic transactions
- **Transaction History**: Complete ledger of all balance changes
- **Interest Calculation**: Automated monthly interest payments via EventBridge
- **DynamoDB Single-Table Design**: Efficient data model with GSI for queries
- **Atomic Transactions**: DynamoDB Transactions ensure data consistency
- **RESTful API**: API Gateway with CORS support

## Architecture

```
┌─────────────────┐
│   React SPA     │
│   (Frontend)    │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐      ┌──────────────┐
│  API Gateway    │◄────►│   Cognito    │
│   (REST API)    │      │  (Auth/AuthZ)│
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  Lambda         │◄────►│  DynamoDB    │
│  Functions (8)  │      │ Single Table │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│  EventBridge    │
│  (Monthly Cron) │
└─────────────────┘
```

## Tech Stack

- **Backend**: Python 3.12, AWS Lambda
- **Infrastructure**: AWS SAM (Serverless Application Model)
- **Database**: DynamoDB (single-table design)
- **Authentication**: Amazon Cognito with Google OAuth
- **API**: API Gateway REST
- **Frontend**: React with Vite (to be implemented)
- **CI/CD**: GitHub Actions (to be configured)

## Project Structure

```
kid_bank/
├── backend/
│   ├── src/
│   │   ├── common/           # Shared utilities
│   │   │   ├── auth.py       # JWT verification & authorization
│   │   │   ├── dynamodb.py   # DynamoDB client with transactions
│   │   │   ├── errors.py     # Custom exceptions
│   │   │   ├── logger.py     # JSON logging
│   │   │   └── models.py     # Data models
│   │   ├── lambdas/
│   │   │   ├── auth/         # User authentication endpoints
│   │   │   ├── family/       # Children management endpoints
│   │   │   ├── transactions/ # Transaction endpoints
│   │   │   └── interest/     # Interest calculation
│   │   └── requirements.txt
│   ├── tests/                # Unit and integration tests
│   ├── template.yaml         # SAM template
│   └── samconfig.toml        # SAM configuration
├── frontend/                 # (To be implemented)
└── README.md
```

## Prerequisites

- Python 3.12 or later
- AWS CLI configured with appropriate credentials
- AWS SAM CLI installed
- Docker (for local development)
- Node.js 18+ (for frontend)
- Google OAuth credentials (optional, for Google login)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd kid_bank
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r src/requirements.txt
```

### 3. Build the Application

```bash
sam build
```

### 4. Deploy to AWS

For first-time deployment:

```bash
sam deploy --guided
```

You'll be prompted for:
- **Stack Name**: `family-bank-dev`
- **AWS Region**: e.g., `us-east-1`
- **Environment**: `dev`
- **GoogleClientId**: (Leave empty for now, or provide your Google OAuth Client ID)
- **GoogleClientSecret**: (Leave empty for now, or provide your Google OAuth Client Secret)

For subsequent deployments:

```bash
sam deploy
```

### 5. Get Stack Outputs

After deployment, retrieve important values:

```bash
aws cloudformation describe-stacks \
  --stack-name family-bank-dev \
  --query 'Stacks[0].Outputs'
```

You'll need:
- **ApiEndpoint**: API Gateway URL
- **UserPoolId**: Cognito User Pool ID
- **UserPoolClientId**: Cognito Client ID
- **CognitoHostedUIDomain**: Cognito Hosted UI URL

## API Endpoints

### Authentication

- `GET /user` - Get current user profile
- `POST /user` - Update user profile

### Family Management (Parents only)

- `GET /children` - List all children
- `GET /children/{childId}` - Get child summary with recent transactions
- `POST /children` - Create new child account

### Transactions

- `GET /transactions` - List transactions (with pagination)
- `POST /adjust-balance` - Adjust child's balance (Parents only)

## DynamoDB Single-Table Design

### Table: FamilyBank

| PK | SK | GSI1PK | GSI1SK | GSI2PK | GSI2SK | Attributes |
|----|-------|--------|--------|--------|--------|------------|
| USER#\{id\} | PROFILE | PARENT#\{pid\} | CHILD#\{id\} | ROLE#child | USER#\{id\} | userId, email, name, role, balance, interestRate, parentId |
| USER#\{id\} | TRANS#\{timestamp\}#\{tid\} | - | - | - | - | transactionId, amount, type, description, balanceAfter, initiatedBy, timestamp |

### Access Patterns

1. **Get User Profile**: Query by PK=USER#{id}, SK=PROFILE
2. **Get Transactions**: Query by PK=USER#{id}, SK begins_with TRANS#
3. **List Children**: Query GSI1 by GSI1PK=PARENT#{parentId}
4. **Scan All Children**: Query GSI2 by GSI2PK=ROLE#child (for interest calculation)

## Key Features

### 1. Atomic Transactions

Balance adjustments use DynamoDB Transactions to atomically update both the user balance and create a transaction record:

```python
db.adjust_balance_with_transaction(
    user_id=child_id,
    amount=Decimal('50.00'),
    transaction_type=TransactionType.ADJUSTMENT,
    description='Birthday gift',
    initiated_by=parent_id
)
```

### 2. Negative Balance Prevention

Condition expressions prevent withdrawals that would result in negative balances:

```python
ConditionExpression='attribute_exists(PK) AND balance = :current_balance'
```

### 3. Authorization Decorator

Every Lambda function uses the `@authorize()` decorator for JWT verification:

```python
@authorize(required_groups=['Parents'])
def lambda_handler(event, context):
    auth_context = event['requestContext']['authorizer']
    user_id = auth_context['userId']
    groups = auth_context['groups']
    # ... business logic
```

### 4. Interest Calculation

EventBridge triggers the interest calculation Lambda on the 1st of each month:

- Scans all children using GSI2
- Calculates interest: `balance * interestRate`
- Rounds to 2 decimal places
- Applies interest using atomic transactions
- Logs success/failure summary

## Testing

### Unit Tests

```bash
cd backend
pytest tests/unit/ -v --cov=src
```

### Integration Tests

```bash
pytest tests/integration/ -v
```

## Local Development

### Run SAM Local API

```bash
cd backend
sam local start-api --docker-network sam-local
```

The API will be available at `http://localhost:3000`

### Test Endpoints

```bash
# Get user (requires valid JWT token)
curl http://localhost:3000/user \
  -H "Authorization: Bearer <token>"

# List children (requires parent token)
curl http://localhost:3000/children \
  -H "Authorization: Bearer <parent-token>"
```

## Security Considerations

1. **JWT Verification**: All endpoints verify JWT signatures using Cognito JWKS
2. **Group-Based Authorization**: Parent vs. Child permissions enforced
3. **Parent-Child Validation**: Parents can only access their own children's data
4. **Atomic Operations**: DynamoDB Transactions prevent race conditions
5. **Input Validation**: All user inputs are validated before processing

## Environment Variables

Lambda functions use these environment variables (set by SAM template):

- `DYNAMODB_TABLE_NAME`: DynamoDB table name
- `COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `COGNITO_CLIENT_ID`: Cognito Client ID
- `COGNITO_REGION`: AWS region for Cognito
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `USE_ROLE_GSI`: Enable GSI2 for children queries (true/false)

## Deployment Environments

The application supports multiple environments:

- **dev**: Development environment
- **staging**: Staging environment
- **prod**: Production environment

Deploy to different environments:

```bash
sam deploy --config-env staging
sam deploy --config-env prod
```

## Cost Estimates

Estimated monthly costs for small-scale usage:

- **DynamoDB**: On-demand, ~$1-2/month
- **Lambda**: Free tier covers development, ~$0.20/month in production
- **API Gateway**: Free tier covers development, ~$3.50/1M requests
- **Cognito**: 50,000 MAU free, then $0.0055/MAU
- **EventBridge**: $1/million events (essentially free for monthly cron)

**Total**: ~$5-10/month for small family use

## Troubleshooting

### Lambda Function Errors

Check CloudWatch Logs:

```bash
aws logs tail /aws/lambda/family-bank-dev-GetUserFunction --follow
```

### DynamoDB Issues

Verify table exists:

```bash
aws dynamodb describe-table --table-name FamilyBank-dev
```

### Cognito Authentication Issues

Test Cognito JWT verification:

```bash
# Decode JWT token
echo "<token>" | cut -d. -f2 | base64 -d | jq
```

## Next Steps

1. **Frontend Implementation**: Build React application with Vite
2. **Testing**: Add comprehensive unit and integration tests
3. **CI/CD**: Set up GitHub Actions workflows
4. **Monitoring**: Configure CloudWatch alarms
5. **Documentation**: Add API documentation with examples

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions or issues, please open an issue on GitHub or contact the maintainers.
