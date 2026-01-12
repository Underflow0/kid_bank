"""
Lambda function to create a new child account.
POST /children
"""
import json
import sys
import os
import boto3
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
    UserRole,
    DEFAULT_CHILD_BALANCE,
    DEFAULT_INTEREST_RATE
)

logger = get_logger(__name__)


@authorize(required_groups=['Parents'])
def lambda_handler(event, context):
    """
    Create a new child account.
    Creates user in Cognito and DynamoDB.

    Body:
        {
            "name": "Child Name",
            "email": "child@example.com",
            "initialBalance": 0.00,          # Optional
            "interestRate": 0.05             # Optional
        }

    Returns:
        201: Created child profile
        400: Bad request (missing fields)
        403: Not a parent
        500: Internal error
    """
    try:
        # Get authenticated parent ID
        auth_context = get_auth_context(event)
        parent_id = auth_context['userId']

        # Parse request body
        body = json.loads(event.get('body', '{}'))
        name = body.get('name')
        email = body.get('email')
        initial_balance = Decimal(str(body.get('initialBalance', DEFAULT_CHILD_BALANCE)))
        interest_rate = Decimal(str(body.get('interestRate', DEFAULT_INTEREST_RATE)))

        # Validate required fields
        if not name or not email:
            raise BadRequestError("Both 'name' and 'email' are required")

        logger.info(f"Creating child account for parent: {parent_id}, email: {email}")

        # Create user in Cognito
        cognito = boto3.client('cognito-idp')
        user_pool_id = os.environ['COGNITO_USER_POOL_ID']

        # Create user with temporary password
        import uuid
        temp_password = f"Temp{uuid.uuid4().hex[:8]}!"

        try:
            cognito_response = cognito.admin_create_user(
                UserPoolId=user_pool_id,
                Username=email,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'},
                    {'Name': 'name', 'Value': name}
                ],
                TemporaryPassword=temp_password,
                MessageAction='SUPPRESS'  # Don't send welcome email
            )

            # Get the sub (user ID) from Cognito response
            child_id = None
            for attr in cognito_response['User']['Attributes']:
                if attr['Name'] == 'sub':
                    child_id = attr['Value']
                    break

            if not child_id:
                raise Exception("Failed to get user ID from Cognito")

            # Add user to Children group
            cognito.admin_add_user_to_group(
                UserPoolId=user_pool_id,
                Username=email,
                GroupName='Children'
            )

            logger.info(f"Created Cognito user: {child_id}")

        except cognito.exceptions.UsernameExistsException:
            raise BadRequestError(f"User with email {email} already exists")
        except Exception as e:
            logger.error(f"Failed to create Cognito user: {str(e)}")
            raise Exception(f"Failed to create user in authentication system: {str(e)}")

        # Create user profile in DynamoDB
        try:
            db = DynamoDBClient()
            child_profile = db.create_user_profile(
                user_id=child_id,
                email=email,
                name=name,
                role=UserRole.CHILD,
                parent_id=parent_id,
                balance=initial_balance,
                interest_rate=interest_rate
            )

            logger.info(f"Created DynamoDB profile for child: {child_id}")

            return {
                'statusCode': 201,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'child': child_profile.to_dict(),
                    'temporaryPassword': temp_password,
                    'message': 'Child account created successfully. Please share the temporary password securely.'
                })
            }

        except Exception as e:
            # If DynamoDB creation fails, try to clean up Cognito user
            try:
                cognito.admin_delete_user(
                    UserPoolId=user_pool_id,
                    Username=email
                )
                logger.warning(f"Cleaned up Cognito user after DynamoDB failure")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up Cognito user: {str(cleanup_error)}")

            raise e

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
