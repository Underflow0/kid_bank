"""
DynamoDB client with atomic transaction support for Family Bank application.
"""

import boto3
import os
import uuid
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional
from botocore.exceptions import ClientError
from .errors import InsufficientFundsError, DatabaseError, NotFoundError, ConflictError
from .logger import get_logger
from .models import (
    KeyPattern,
    UserProfile,
    Transaction,
    UserRole,
    TransactionType,
    DEFAULT_INTEREST_RATE,
    DEFAULT_CHILD_BALANCE,
    TRANSACTION_PAGINATION_LIMIT,
)

logger = get_logger(__name__)


class DynamoDBClient:
    """DynamoDB client for Family Bank application."""

    def __init__(self):
        self.table_name = os.environ["DYNAMODB_TABLE_NAME"]

        # Support for local DynamoDB
        if os.environ.get("AWS_SAM_LOCAL") == "true":
            self.dynamodb = boto3.resource(
                "dynamodb", endpoint_url="http://dynamodb-local:8000"
            )
            self.client = boto3.client(
                "dynamodb", endpoint_url="http://dynamodb-local:8000"
            )
        else:
            self.dynamodb = boto3.resource("dynamodb")
            self.client = boto3.client("dynamodb")

        self.table = self.dynamodb.Table(self.table_name)

    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """
        Get user profile by ID.

        Args:
            user_id: User ID (UUID)

        Returns:
            User profile dict or None if not found
        """
        try:
            response = self.table.get_item(
                Key={"PK": KeyPattern.user_pk(user_id), "SK": KeyPattern.profile_sk()}
            )
            return response.get("Item")
        except ClientError as e:
            logger.error(f"Failed to get user profile: {str(e)}")
            raise DatabaseError(f"Failed to retrieve user profile: {str(e)}")

    def create_user_profile(
        self,
        user_id: str,
        email: str,
        name: str,
        role: UserRole,
        parent_id: Optional[str] = None,
        balance: Decimal = Decimal("0.00"),
        interest_rate: Decimal = DEFAULT_INTEREST_RATE,
    ) -> UserProfile:
        """
        Create a new user profile.

        Args:
            user_id: User ID (UUID)
            email: User email
            name: User name
            role: User role (parent or child)
            parent_id: Parent ID if user is a child
            balance: Initial balance (default 0)
            interest_rate: Interest rate (default 5%)

        Returns:
            Created UserProfile
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        item = {
            "PK": KeyPattern.user_pk(user_id),
            "SK": KeyPattern.profile_sk(),
            "userId": user_id,
            "email": email,
            "name": name,
            "role": role.value,
            "balance": balance,
            "interestRate": interest_rate,
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }

        # Add parent_id and GSI attributes for children
        if role == UserRole.CHILD and parent_id:
            item["parentId"] = parent_id
            item["GSI1PK"] = KeyPattern.parent_gsi1_pk(parent_id)
            item["GSI1SK"] = KeyPattern.child_gsi1_sk(user_id)
            item["GSI2PK"] = KeyPattern.role_gsi2_pk(UserRole.CHILD)
            item["GSI2SK"] = KeyPattern.user_gsi2_sk(user_id)

        try:
            self.table.put_item(Item=item)
            logger.info(f"Created user profile: {user_id}, role: {role.value}")
            return UserProfile.from_dynamodb_item(item)
        except ClientError as e:
            logger.error(f"Failed to create user profile: {str(e)}")
            raise DatabaseError(f"Failed to create user profile: {str(e)}")

    def update_user_profile(
        self,
        user_id: str,
        name: Optional[str] = None,
        interest_rate: Optional[Decimal] = None,
    ) -> Dict:
        """
        Update user profile fields.

        Args:
            user_id: User ID
            name: New name (optional)
            interest_rate: New interest rate (optional)

        Returns:
            Updated user profile dict
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        update_expression_parts = ["updatedAt = :timestamp"]
        expression_values = {":timestamp": timestamp}

        if name is not None:
            update_expression_parts.append("#name = :name")
            expression_values[":name"] = name

        if interest_rate is not None:
            update_expression_parts.append("interestRate = :rate")
            expression_values[":rate"] = interest_rate

        update_kwargs = {
            "Key": {"PK": KeyPattern.user_pk(user_id), "SK": KeyPattern.profile_sk()},
            "UpdateExpression": "SET " + ", ".join(update_expression_parts),
            "ExpressionAttributeValues": expression_values,
            "ReturnValues": "ALL_NEW",
        }
        if name is not None:
            update_kwargs["ExpressionAttributeNames"] = {"#name": "name"}

        try:
            response = self.table.update_item(**update_kwargs)
            return response["Attributes"]
        except ClientError as e:
            logger.error(f"Failed to update user profile: {str(e)}")
            raise DatabaseError(f"Failed to update user profile: {str(e)}")

    def get_children_for_parent(self, parent_id: str) -> List[Dict]:
        """
        Get all children for a parent using GSI1.

        Args:
            parent_id: Parent user ID

        Returns:
            List of child profile dicts
        """
        try:
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :pk",
                ExpressionAttributeValues={":pk": KeyPattern.parent_gsi1_pk(parent_id)},
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Failed to get children: {str(e)}")
            raise DatabaseError(f"Failed to retrieve children: {str(e)}")

    def get_transactions(
        self,
        user_id: str,
        limit: int = TRANSACTION_PAGINATION_LIMIT,
        next_token: Optional[str] = None,
    ) -> Dict:
        """
        Get transactions for a user.

        Args:
            user_id: User ID
            limit: Maximum number of transactions to return
            next_token: Pagination token (base64-encoded LastEvaluatedKey)

        Returns:
            Dict with 'transactions' list and optional 'nextToken'
        """
        query_params = {
            "KeyConditionExpression": "PK = :pk AND begins_with(SK, :sk)",
            "ExpressionAttributeValues": {
                ":pk": KeyPattern.user_pk(user_id),
                ":sk": "TRANS#",
            },
            "Limit": limit,
            "ScanIndexForward": False,  # Most recent first
        }

        if next_token:
            import json
            import base64

            try:
                decoded = json.loads(base64.b64decode(next_token))
                query_params["ExclusiveStartKey"] = decoded
            except Exception as e:
                logger.warning(f"Invalid pagination token: {str(e)}")

        try:
            response = self.table.query(**query_params)

            result = {"transactions": response.get("Items", [])}

            if "LastEvaluatedKey" in response:
                import json
                import base64

                encoded = base64.b64encode(
                    json.dumps(response["LastEvaluatedKey"]).encode()
                ).decode()
                result["nextToken"] = encoded

            return result

        except ClientError as e:
            logger.error(f"Failed to get transactions: {str(e)}")
            raise DatabaseError(f"Failed to retrieve transactions: {str(e)}")

    def adjust_balance_with_transaction(
        self,
        user_id: str,
        amount: Decimal,
        transaction_type: TransactionType,
        description: str,
        initiated_by: str,
    ) -> Dict:
        """
        Atomically adjust user balance and create transaction record.
        Uses DynamoDB Transactions for ACID guarantees.
        Prevents negative balances with condition expression.

        Args:
            user_id: User ID
            amount: Amount to adjust (positive for deposit, negative for withdrawal)
            transaction_type: Type of transaction
            description: Transaction description
            initiated_by: User ID who initiated the transaction

        Returns:
            Transaction dict

        Raises:
            InsufficientFundsError: If balance would become negative
            DatabaseError: If transaction fails
            NotFoundError: If user not found
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        transaction_id = str(uuid.uuid4())

        # Get current balance
        user_profile = self.get_user_profile(user_id)
        if not user_profile:
            raise NotFoundError(f"User {user_id} not found")

        current_balance = Decimal(str(user_profile.get("balance", 0)))
        new_balance = current_balance + amount

        # Prevent negative balance
        if new_balance < 0:
            raise InsufficientFundsError(
                f"Insufficient funds. Current: ${float(current_balance)}, "
                f"Requested change: ${float(amount)}, "
                f"Would result in: ${float(new_balance)}"
            )

        try:
            # Execute transactional write
            self.client.transact_write_items(
                TransactItems=[
                    {
                        # Update user balance
                        "Update": {
                            "TableName": self.table_name,
                            "Key": {
                                "PK": {"S": KeyPattern.user_pk(user_id)},
                                "SK": {"S": KeyPattern.profile_sk()},
                            },
                            "UpdateExpression": (
                                "SET balance = :new_balance, updatedAt = :timestamp"
                            ),
                            "ConditionExpression": (
                                "attribute_exists(PK) AND balance = :current_balance"
                            ),
                            "ExpressionAttributeValues": {
                                ":new_balance": {"N": str(new_balance)},
                                ":current_balance": {"N": str(current_balance)},
                                ":timestamp": {"S": timestamp},
                            },
                        }
                    },
                    {
                        # Create transaction record
                        "Put": {
                            "TableName": self.table_name,
                            "Item": {
                                "PK": {"S": KeyPattern.user_pk(user_id)},
                                "SK": {
                                    "S": KeyPattern.transaction_sk(
                                        timestamp, transaction_id
                                    )
                                },
                                "transactionId": {"S": transaction_id},
                                "userId": {"S": user_id},
                                "amount": {"N": str(amount)},
                                "type": {"S": transaction_type.value},
                                "description": {"S": description},
                                "balanceAfter": {"N": str(new_balance)},
                                "initiatedBy": {"S": initiated_by},
                                "timestamp": {"S": timestamp},
                            },
                        }
                    },
                ]
            )

            logger.info(
                f"Transaction successful: user={user_id}, "
                f"amount={float(amount)}, new_balance={float(new_balance)}, "
                f"type={transaction_type.value}"
            )

            return {
                "transactionId": transaction_id,
                "userId": user_id,
                "amount": float(amount),
                "type": transaction_type.value,
                "description": description,
                "balanceAfter": float(new_balance),
                "initiatedBy": initiated_by,
                "timestamp": timestamp,
            }

        except self.client.exceptions.TransactionCanceledException as e:
            # Check cancellation reasons
            reasons = e.response.get("CancellationReasons", [])
            for reason in reasons:
                code = reason.get("Code")
                if code == "ConditionalCheckFailed":
                    logger.warning(
                        f"Balance changed during transaction for user {user_id}. "
                        "Possible concurrent modification."
                    )
                    raise ConflictError(
                        "Balance was modified by another transaction. Please retry."
                    )

            logger.error(f"Transaction cancelled: {str(e)}")
            raise DatabaseError(f"Transaction failed: {str(e)}")

        except ClientError as e:
            logger.error(f"Transaction failed: {str(e)}", exc_info=True)
            raise DatabaseError(f"Transaction failed: {str(e)}")

    def scan_all_children(self) -> List[Dict]:
        """
        Scan all child accounts for interest calculation.
        Uses GSI2 if USE_ROLE_GSI is enabled, otherwise falls back to Scan.

        Returns:
            List of child profile dicts
        """
        use_gsi = os.environ.get("USE_ROLE_GSI", "true").lower() == "true"

        try:
            if use_gsi:
                # Use GSI2 for better performance
                items = []
                query_params = {
                    "IndexName": "GSI2",
                    "KeyConditionExpression": "GSI2PK = :pk",
                    "ExpressionAttributeValues": {
                        ":pk": KeyPattern.role_gsi2_pk(UserRole.CHILD)
                    },
                }

                while True:
                    response = self.table.query(**query_params)
                    items.extend(response.get("Items", []))

                    if "LastEvaluatedKey" not in response:
                        break

                    query_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]

                return items
            else:
                # Fallback to scan with filter
                items = []
                scan_params = {
                    "FilterExpression": "#role = :role AND SK = :sk",
                    "ExpressionAttributeNames": {"#role": "role"},
                    "ExpressionAttributeValues": {
                        ":role": UserRole.CHILD.value,
                        ":sk": KeyPattern.profile_sk(),
                    },
                }

                while True:
                    response = self.table.scan(**scan_params)
                    items.extend(response.get("Items", []))

                    if "LastEvaluatedKey" not in response:
                        break

                    scan_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]

                return items

        except ClientError as e:
            logger.error(f"Failed to scan children: {str(e)}")
            raise DatabaseError(f"Failed to retrieve children: {str(e)}")
