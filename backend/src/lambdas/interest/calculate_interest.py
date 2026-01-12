"""
Lambda function to calculate and apply monthly interest for all children.
Triggered by EventBridge on the 1st of each month at midnight UTC.
"""
import sys
import os
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from common import (
    DynamoDBClient,
    get_logger,
    DatabaseError,
    TransactionType
)

logger = get_logger(__name__)


def lambda_handler(event, context):
    """
    Calculate and apply monthly interest for all child accounts.

    Algorithm:
        1. Scan/Query all children from DynamoDB
        2. For each child:
           - Calculate interest: balance * interestRate
           - Round to 2 decimal places
           - Skip if interest is 0
           - Apply interest using atomic transaction
        3. Log summary of successful/failed operations

    Returns:
        200: Summary of interest calculation
        500: Internal error
    """
    db = DynamoDBClient()

    logger.info("Starting monthly interest calculation")
    start_time = datetime.utcnow()

    try:
        # Get all child accounts
        children = db.scan_all_children()
        total_children = len(children)

        logger.info(f"Found {total_children} child accounts to process")

        successful = 0
        skipped = 0
        failed = 0
        failed_details = []

        for child in children:
            try:
                user_id = child['userId']
                name = child.get('name', 'Unknown')
                current_balance = Decimal(str(child.get('balance', 0)))
                interest_rate = Decimal(str(child.get('interestRate', 0)))

                # Skip if no interest rate or zero balance
                if interest_rate == 0:
                    logger.debug(
                        f"Skipping {user_id} ({name}): interest rate is 0"
                    )
                    skipped += 1
                    continue

                if current_balance == 0:
                    logger.debug(
                        f"Skipping {user_id} ({name}): balance is 0"
                    )
                    skipped += 1
                    continue

                # Calculate interest: balance * rate
                # Round to 2 decimal places (cents)
                interest_amount = (current_balance * interest_rate).quantize(
                    Decimal('0.01'),
                    rounding=ROUND_HALF_UP
                )

                if interest_amount == 0:
                    logger.debug(
                        f"Skipping {user_id} ({name}): "
                        f"calculated interest is 0 (balance={float(current_balance)}, "
                        f"rate={float(interest_rate)})"
                    )
                    skipped += 1
                    continue

                # Apply interest as a transaction
                result = db.adjust_balance_with_transaction(
                    user_id=user_id,
                    amount=interest_amount,
                    transaction_type=TransactionType.INTEREST,
                    description=f'Monthly interest ({float(interest_rate * 100):.2f}%)',
                    initiated_by='SYSTEM'
                )

                logger.info(
                    f"Applied interest for {user_id} ({name}): "
                    f"${float(interest_amount):.2f} @ {float(interest_rate * 100):.2f}% "
                    f"on ${float(current_balance):.2f} -> "
                    f"${float(result['balanceAfter']):.2f}"
                )

                successful += 1

            except DatabaseError as e:
                logger.error(
                    f"Failed to apply interest for {child.get('userId', 'unknown')}: {str(e)}"
                )
                failed += 1
                failed_details.append({
                    'userId': child.get('userId', 'unknown'),
                    'name': child.get('name', 'Unknown'),
                    'error': str(e)
                })

            except Exception as e:
                logger.error(
                    f"Unexpected error processing {child.get('userId', 'unknown')}: {str(e)}",
                    exc_info=True
                )
                failed += 1
                failed_details.append({
                    'userId': child.get('userId', 'unknown'),
                    'name': child.get('name', 'Unknown'),
                    'error': f"Unexpected error: {str(e)}"
                })

        end_time = datetime.utcnow()
        duration_seconds = (end_time - start_time).total_seconds()

        summary = {
            'timestamp': end_time.isoformat() + 'Z',
            'totalChildren': total_children,
            'successful': successful,
            'skipped': skipped,
            'failed': failed,
            'durationSeconds': duration_seconds
        }

        if failed > 0:
            summary['failures'] = failed_details

        logger.info(f"Interest calculation complete: {summary}")

        return {
            'statusCode': 200,
            'body': summary
        }

    except Exception as e:
        logger.error(f"Interest calculation failed: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }
