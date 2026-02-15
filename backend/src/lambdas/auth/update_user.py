"""
Lambda function to update user profile.
POST /user
"""

import json
import sys
import os
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common import (
    authorize,
    get_auth_context,
    is_parent,
    DynamoDBClient,
    get_logger,
    FamilyBankError,
    BadRequestError,
    ForbiddenError,
)

logger = get_logger(__name__)


@authorize()
def lambda_handler(event, context):
    """
    Update user profile (name, interest rate).
    Parents can update their own profile or their children's profiles.
    Children can only update their own name.

    Body:
        {
            "userId": "optional-user-id",  # If not provided, updates current user
            "name": "new-name",            # Optional
            "interestRate": 0.05           # Optional, parent only
        }

    Returns:
        200: Updated user profile
        400: Bad request
        403: Forbidden
        500: Internal error
    """
    try:
        # Get authenticated user
        auth_context = get_auth_context(event)
        current_user_id = auth_context["userId"]
        groups = auth_context["groups"]

        # Parse request body
        body = json.loads(event.get("body", "{}"))
        target_user_id = body.get("userId", current_user_id)
        name = body.get("name")
        interest_rate = body.get("interestRate")

        # Validate at least one field to update
        if name is None and interest_rate is None:
            raise BadRequestError(
                "At least one of 'name' or 'interestRate' must be provided"
            )

        # Authorization checks
        db = DynamoDBClient()

        if target_user_id != current_user_id:
            # User is trying to update someone else's profile
            if not is_parent(groups):
                raise ForbiddenError("Only parents can update other users' profiles")

            # Verify target user is a child of current user
            target_profile = db.get_user_profile(target_user_id)
            if not target_profile:
                raise BadRequestError(f"User {target_user_id} not found")

            if target_profile.get("parentId") != current_user_id:
                raise ForbiddenError("You can only update your own children's profiles")

        # Children cannot set interest rate
        if interest_rate is not None and not is_parent(groups):
            raise ForbiddenError("Only parents can set interest rate")

        # Update profile
        update_params = {}
        if name:
            update_params["name"] = name
        if interest_rate is not None:
            update_params["interest_rate"] = Decimal(str(interest_rate))

        updated_profile = db.update_user_profile(target_user_id, **update_params)

        logger.info(f"Updated profile for user: {target_user_id}")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "user": {
                        "userId": updated_profile["userId"],
                        "email": updated_profile["email"],
                        "name": updated_profile["name"],
                        "role": updated_profile["role"],
                        "balance": float(updated_profile["balance"]),
                        "interestRate": float(updated_profile["interestRate"]),
                        "parentId": updated_profile.get("parentId"),
                        "updatedAt": updated_profile["updatedAt"],
                    }
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
