"""
Authentication and authorization utilities for Family Bank application.
Handles JWT verification and group-based authorization.
"""

import json
import os
import time
from functools import wraps
from typing import List, Optional, Dict
import requests
from jose import jwt, JWTError
from .errors import UnauthorizedError, ForbiddenError
from .logger import get_logger
from .models import CognitoGroup

logger = get_logger(__name__)

# Cache for JWKS (JSON Web Key Set)
_jwks_cache: Optional[Dict] = None
_jwks_cache_time: float = 0
JWKS_CACHE_DURATION = 3600  # 1 hour


def get_jwks() -> Dict:
    """
    Fetch and cache JWKS from Cognito.

    Returns:
        JWKS dictionary with public keys
    """
    global _jwks_cache, _jwks_cache_time

    current_time = time.time()

    # Return cached JWKS if still valid
    if _jwks_cache and (current_time - _jwks_cache_time) < JWKS_CACHE_DURATION:
        return _jwks_cache

    # Fetch new JWKS
    cognito_region = os.environ["COGNITO_REGION"]
    user_pool_id = os.environ["COGNITO_USER_POOL_ID"]

    jwks_url = (
        f"https://cognito-idp.{cognito_region}.amazonaws.com/"
        f"{user_pool_id}/.well-known/jwks.json"
    )

    try:
        response = requests.get(jwks_url, timeout=5)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cache_time = current_time
        logger.info("JWKS fetched and cached successfully")
        return _jwks_cache
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {str(e)}")
        # If we have a stale cache, use it as fallback
        if _jwks_cache:
            logger.warning("Using stale JWKS cache")
            return _jwks_cache
        raise UnauthorizedError("Unable to verify token")


def verify_jwt(token: str) -> dict:
    """
    Verify JWT token from Cognito.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        UnauthorizedError: If token is invalid or expired
    """
    cognito_region = os.environ["COGNITO_REGION"]
    user_pool_id = os.environ["COGNITO_USER_POOL_ID"]
    client_id = os.environ["COGNITO_CLIENT_ID"]

    try:
        # Get JWKS
        jwks = get_jwks()

        # Get the key ID from token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header["kid"]

        # Find the matching key in JWKS
        key = None
        for jwk in jwks["keys"]:
            if jwk["kid"] == kid:
                key = jwk
                break

        if not key:
            raise UnauthorizedError("Public key not found in JWKS")

        # Verify the token
        issuer = f"https://cognito-idp.{cognito_region}.amazonaws.com/{user_pool_id}"

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=issuer,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )

        # Verify token_use claim
        if payload.get("token_use") != "id":
            raise UnauthorizedError("Token is not an ID token")

        return payload

    except JWTError as e:
        logger.warning(f"JWT verification failed: {str(e)}")
        raise UnauthorizedError(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(
            f"Unexpected error during JWT verification: {str(e)}", exc_info=True
        )
        raise UnauthorizedError("Token verification failed")


def get_user_groups(token_payload: dict) -> List[str]:
    """
    Extract Cognito groups from token payload.

    Args:
        token_payload: Decoded JWT payload

    Returns:
        List of group names
    """
    return token_payload.get("cognito:groups", [])


def get_user_id(token_payload: dict) -> str:
    """
    Extract user ID (sub claim) from token payload.

    Args:
        token_payload: Decoded JWT payload

    Returns:
        User ID (UUID)
    """
    return token_payload.get("sub")


def get_user_email(token_payload: dict) -> str:
    """
    Extract email from token payload.

    Args:
        token_payload: Decoded JWT payload

    Returns:
        User email
    """
    return token_payload.get("email", "")


def is_parent(groups: List[str]) -> bool:
    """Check if user is in Parents group."""
    return CognitoGroup.PARENTS.value in groups


def is_child(groups: List[str]) -> bool:
    """Check if user is in Children group."""
    return CognitoGroup.CHILDREN.value in groups


def authorize(required_groups: Optional[List[str]] = None):
    """
    Decorator to verify JWT and check group membership.

    Args:
        required_groups: List of required Cognito group names (e.g., ['Parents'])
                        If None, any authenticated user is allowed

    Usage:
        @authorize(required_groups=['Parents'])
        def lambda_handler(event, context):
            auth_context = event['requestContext']['authorizer']
            user_id = auth_context['userId']
            groups = auth_context['groups']
            # ... business logic

    The decorator adds an 'authorizer' dict to event['requestContext'] with:
        - userId: User ID (sub claim)
        - groups: List of Cognito groups
        - email: User email
        - claims: Full JWT payload
    """

    def decorator(func):
        @wraps(func)
        def wrapper(event, context):
            try:
                # Extract token from Authorization header
                headers = event.get("headers", {})

                # Handle case-insensitive headers (API Gateway may lowercase)
                auth_header = (
                    headers.get("Authorization") or headers.get("authorization") or ""
                )

                if not auth_header.startswith("Bearer "):
                    raise UnauthorizedError("Missing or invalid Authorization header")

                token = auth_header.replace("Bearer ", "")

                # Verify JWT
                payload = verify_jwt(token)

                # Extract user info
                user_id = get_user_id(payload)
                groups = get_user_groups(payload)
                email = get_user_email(payload)

                logger.info(f"Authenticated user: {user_id}, groups: {groups}")

                # Check required groups
                if required_groups:
                    if not any(group in groups for group in required_groups):
                        raise ForbiddenError(
                            f"User does not have required group membership. "
                            f"Required: {required_groups}, Has: {groups}"
                        )

                # Add auth context to event for downstream use
                if "requestContext" not in event:
                    event["requestContext"] = {}
                event["requestContext"]["authorizer"] = {
                    "userId": user_id,
                    "groups": groups,
                    "email": email,
                    "claims": payload,
                }

                # Call the actual handler
                return func(event, context)

            except (UnauthorizedError, ForbiddenError) as e:
                logger.warning(f"Authorization failed: {str(e)}")
                return {
                    "statusCode": e.status_code,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                    "body": json.dumps({"error": e.message}),
                }
            except Exception as e:
                logger.error(
                    f"Unexpected error in authorization: {str(e)}", exc_info=True
                )
                return {
                    "statusCode": 500,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                    "body": json.dumps({"error": "Internal server error"}),
                }

        return wrapper

    return decorator


def get_auth_context(event: dict) -> dict:
    """
    Extract auth context from event.

    Args:
        event: Lambda event dict

    Returns:
        Auth context dict with userId, groups, email, claims
    """
    return event.get("requestContext", {}).get("authorizer", {})
