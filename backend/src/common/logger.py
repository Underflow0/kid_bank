"""
Structured logging configuration for Family Bank application.
Formats logs as JSON for CloudWatch Logs Insights.
"""
import logging
import json
import os
from typing import Any, Dict
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """Format logs as JSON for structured logging in CloudWatch."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add custom fields if present
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'transaction_id'):
            log_data['transaction_id'] = record.transaction_id

        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger with JSON formatting for CloudWatch.

    Args:
        name: Name of the logger (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        level = os.environ.get('LOG_LEVEL', 'INFO')
        logger.setLevel(level)

        handler = logging.StreamHandler()

        # Use JSON formatter for production, simple formatter for local dev
        if os.environ.get('AWS_SAM_LOCAL') == 'true':
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        else:
            formatter = JsonFormatter()

        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Prevent propagation to avoid duplicate logs
        logger.propagate = False

    return logger
