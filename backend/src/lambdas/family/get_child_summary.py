"""
Lambda function to get child summary with recent transactions.
GET /children/{childId}
"""

import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common import (
    authorize,
    get_auth_context,
    DynamoDBClient,
    get_logger,
    FamilyBankError,
    NotFoundError,
    ForbiddenError,
)

logger = get_logger(__name__)


@authorize(required_groups=["Parents"])
def lambda_handler(event, context):
    """
    Get detailed summary for a specific child including recent transactions.

    Path Parameters:
        childId: Child user ID

    Returns:
        200: Child profile with recent transactions
        403: Not the child's parent
        404: Child not found
        500: Internal error
    """
    try:
        # Get authenticated parent ID
        auth_context = get_auth_context(event)
        parent_id = auth_context["userId"]

        # Get child ID from path parameters
        child_id = event.get("pathParameters", {}).get("childId")
        if not child_id:
            raise NotFoundError("Child ID not provided")

        logger.info(f"Fetching summary for child: {child_id}, parent: {parent_id}")

        # Get child profile and verify parent relationship
        db = DynamoDBClient()
        child_profile = db.get_user_profile(child_id)

        if not child_profile:
            raise NotFoundError(f"Child {child_id} not found")

        if child_profile.get("parentId") != parent_id:
            raise ForbiddenError("You can only view your own children's summaries")

        # Get recent transactions (last 10)
        transactions_result = db.get_transactions(child_id, limit=10)
        transactions = transactions_result["transactions"]

        # Format response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "child": {
                        "userId": child_profile["userId"],
                        "name": child_profile["name"],
                        "email": child_profile["email"],
                        "balance": float(child_profile["balance"]),
                        "interestRate": float(child_profile["interestRate"]),
                        "createdAt": child_profile["createdAt"],
                        "updatedAt": child_profile["updatedAt"],
                    },
                    "recentTransactions": [
                        {
                            "transactionId": tx["transactionId"],
                            "amount": float(tx["amount"]),
                            "type": tx["type"],
                            "description": tx["description"],
                            "balanceAfter": float(tx["balanceAfter"]),
                            "timestamp": tx["timestamp"],
                        }
                        for tx in transactions
                    ],
                }
            ),
        }

    except FamilyBankError as e:
        logger.warning(f"Business logic error: {str(e)}")
        return {
            "statusCode": e.status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": e.message}),
        }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "Internal server error"}),
        }
