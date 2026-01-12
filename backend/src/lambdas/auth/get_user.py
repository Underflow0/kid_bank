"""
Lambda function to get current user profile.
GET /user
"""
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from common import (
    authorize,
    get_auth_context,
    DynamoDBClient,
    get_logger,
    FamilyBankError,
    NotFoundError
)

logger = get_logger(__name__)


@authorize()
def lambda_handler(event, context):
    """
    Get current authenticated user's profile.

    Returns:
        200: User profile
        404: User not found
        401: Unauthorized
        500: Internal error
    """
    try:
        # Get authenticated user ID
        auth_context = get_auth_context(event)
        user_id = auth_context['userId']

        logger.info(f"Fetching profile for user: {user_id}")

        # Get user profile from DynamoDB
        db = DynamoDBClient()
        user_profile = db.get_user_profile(user_id)

        if not user_profile:
            raise NotFoundError(f"User profile not found for {user_id}")

        # Return user profile
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'user': {
                    'userId': user_profile['userId'],
                    'email': user_profile['email'],
                    'name': user_profile['name'],
                    'role': user_profile['role'],
                    'balance': float(user_profile['balance']),
                    'interestRate': float(user_profile['interestRate']),
                    'parentId': user_profile.get('parentId'),
                    'createdAt': user_profile['createdAt'],
                    'updatedAt': user_profile['updatedAt']
                }
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
