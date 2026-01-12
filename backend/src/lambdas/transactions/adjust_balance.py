"""
Lambda function to adjust child's balance (parent only).
POST /adjust-balance
"""
import json
import sys
import os
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from common import (
    authorize,
    get_auth_context,
    DynamoDBClient,
    get_logger,
    FamilyBankError,
    BadRequestError,
    ForbiddenError,
    NotFoundError,
    TransactionType
)

logger = get_logger(__name__)


@authorize(required_groups=['Parents'])
def lambda_handler(event, context):
    """
    Adjust a child's balance atomically.
    Uses DynamoDB Transactions to ensure balance and transaction record
    are updated together.

    Body:
        {
            "childId": "child-user-id",
            "amount": 50.00,              # Positive or negative
            "description": "Birthday gift" # Optional
        }

    Returns:
        200: Transaction details
        400: Bad request (invalid amount, insufficient funds)
        403: Not the child's parent
        404: Child not found
        409: Conflict (concurrent update)
        500: Internal error
    """
    try:
        # Get authenticated parent ID
        auth_context = get_auth_context(event)
        parent_id = auth_context['userId']

        # Parse request body
        body = json.loads(event.get('body', '{}'))
        child_id = body.get('childId')
        amount = body.get('amount')
        description = body.get('description', 'Balance adjustment')

        # Validate input
        if not child_id:
            raise BadRequestError("'childId' is required")

        if amount is None:
            raise BadRequestError("'amount' is required")

        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            raise BadRequestError("'amount' must be a valid number")

        if amount == 0:
            raise BadRequestError("'amount' cannot be zero")

        logger.info(
            f"Adjusting balance: parent={parent_id}, child={child_id}, "
            f"amount={float(amount)}"
        )

        # Get DynamoDB client
        db = DynamoDBClient()

        # Verify child belongs to parent
        child = db.get_user_profile(child_id)
        if not child:
            raise NotFoundError(f"Child {child_id} not found")

        if child.get('parentId') != parent_id:
            raise ForbiddenError("You can only adjust your own children's balances")

        # Adjust balance with atomic transaction
        transaction = db.adjust_balance_with_transaction(
            user_id=child_id,
            amount=amount,
            transaction_type=TransactionType.ADJUSTMENT,
            description=description,
            initiated_by=parent_id
        )

        logger.info(
            f"Balance adjusted successfully: child={child_id}, "
            f"new_balance={transaction['balanceAfter']}"
        )

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'transaction': transaction,
                'message': 'Balance adjusted successfully'
            })
        }

    except FamilyBankError as e:
        logger.warning(f"Business logic error: {str(e)}")
        return {
            'statusCode': e.status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': e.message})
        }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }
