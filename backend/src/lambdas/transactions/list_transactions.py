"""
Lambda function to list transactions for a user.
GET /transactions?userId={userId}&limit={limit}&nextToken={token}
"""

import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common import (
    authorize,
    get_auth_context,
    is_parent,
    DynamoDBClient,
    get_logger,
    FamilyBankError,
    ForbiddenError,
    MAX_TRANSACTION_PAGINATION_LIMIT,
)

logger = get_logger(__name__)


@authorize()
def lambda_handler(event, context):
    """
    List transactions for a user.
    Users can see their own transactions.
    Parents can see their children's transactions.

    Query Parameters:
        userId: User ID (optional, defaults to current user)
        limit: Max results per page (default 50, max 100)
        nextToken: Pagination token

    Returns:
        200: List of transactions with optional nextToken
        403: Forbidden
        500: Internal error
    """
    try:
        # Get authenticated user
        auth_context = get_auth_context(event)
        current_user_id = auth_context["userId"]
        groups = auth_context["groups"]

        # Get query parameters
        query_params = event.get("queryStringParameters") or {}
        target_user_id = query_params.get("userId", current_user_id)
        limit = int(query_params.get("limit", 50))
        next_token = query_params.get("nextToken")

        # Validate limit
        if limit > MAX_TRANSACTION_PAGINATION_LIMIT:
            limit = MAX_TRANSACTION_PAGINATION_LIMIT

        # Authorization check
        db = DynamoDBClient()

        if target_user_id != current_user_id:
            # User is trying to view someone else's transactions
            if not is_parent(groups):
                raise ForbiddenError("You can only view your own transactions")

            # Verify target user is a child of current user
            target_profile = db.get_user_profile(target_user_id)
            if not target_profile:
                raise ForbiddenError("User not found")

            if target_profile.get("parentId") != current_user_id:
                raise ForbiddenError(
                    "You can only view your own children's transactions"
                )

        logger.info(
            f"Fetching transactions for user: {target_user_id}, "
            f"limit: {limit}, requested by: {current_user_id}"
        )

        # Get transactions
        result = db.get_transactions(target_user_id, limit=limit, next_token=next_token)
        transactions = result["transactions"]

        # Format response
        transactions_list = [
            {
                "transactionId": tx["transactionId"],
                "userId": tx["userId"],
                "amount": float(tx["amount"]),
                "type": tx["type"],
                "description": tx["description"],
                "balanceAfter": float(tx["balanceAfter"]),
                "initiatedBy": tx["initiatedBy"],
                "timestamp": tx["timestamp"],
            }
            for tx in transactions
        ]

        response_body = {
            "transactions": transactions_list,
            "count": len(transactions_list),
        }

        if "nextToken" in result:
            response_body["nextToken"] = result["nextToken"]

        logger.info(f"Returning {len(transactions_list)} transactions")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(response_body),
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
