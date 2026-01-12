"""
Lambda function to list all children for a parent.
GET /children
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
    FamilyBankError
)

logger = get_logger(__name__)


@authorize(required_groups=['Parents'])
def lambda_handler(event, context):
    """
    List all children for the authenticated parent.

    Returns:
        200: List of children profiles
        403: Not a parent
        500: Internal error
    """
    try:
        # Get authenticated parent ID
        auth_context = get_auth_context(event)
        parent_id = auth_context['userId']

        logger.info(f"Fetching children for parent: {parent_id}")

        # Get children from DynamoDB
        db = DynamoDBClient()
        children = db.get_children_for_parent(parent_id)

        # Format response
        children_list = [
            {
                'userId': child['userId'],
                'name': child['name'],
                'email': child['email'],
                'balance': float(child['balance']),
                'interestRate': float(child['interestRate']),
                'createdAt': child['createdAt'],
                'updatedAt': child['updatedAt']
            }
            for child in children
        ]

        logger.info(f"Found {len(children_list)} children for parent {parent_id}")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'children': children_list,
                'count': len(children_list)
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
