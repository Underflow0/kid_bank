"""
Unit tests for authentication and authorization.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from src.common.auth import (
    get_user_groups,
    get_user_id,
    get_user_email,
    is_parent,
    is_child,
    get_auth_context,
    authorize,
)
from src.common.errors import UnauthorizedError, ForbiddenError


class TestTokenParsing:
    def test_get_user_groups(self):
        payload = {"cognito:groups": ["Parents", "Admins"]}
        assert get_user_groups(payload) == ["Parents", "Admins"]

    def test_get_user_groups_empty(self):
        payload = {}
        assert get_user_groups(payload) == []

    def test_get_user_id(self):
        payload = {"sub": "user-123"}
        assert get_user_id(payload) == "user-123"

    def test_get_user_id_none(self):
        payload = {}
        assert get_user_id(payload) is None

    def test_get_user_email(self):
        payload = {"email": "test@example.com"}
        assert get_user_email(payload) == "test@example.com"

    def test_get_user_email_empty(self):
        payload = {}
        assert get_user_email(payload) == ""


class TestGroupChecks:
    def test_is_parent_true(self):
        assert is_parent(["Parents"]) is True
        assert is_parent(["Parents", "Children"]) is True

    def test_is_parent_false(self):
        assert is_parent(["Children"]) is False
        assert is_parent([]) is False

    def test_is_child_true(self):
        assert is_child(["Children"]) is True
        assert is_child(["Children", "Parents"]) is True

    def test_is_child_false(self):
        assert is_child(["Parents"]) is False
        assert is_child([]) is False


class TestAuthContext:
    def test_get_auth_context(self):
        event = {
            "requestContext": {
                "authorizer": {
                    "userId": "user-123",
                    "groups": ["Parents"],
                    "email": "test@example.com",
                }
            }
        }
        context = get_auth_context(event)
        assert context["userId"] == "user-123"
        assert context["groups"] == ["Parents"]
        assert context["email"] == "test@example.com"

    def test_get_auth_context_missing(self):
        event = {}
        context = get_auth_context(event)
        assert context == {}


class TestAuthorizeDecorator:
    @pytest.fixture
    def mock_verify_jwt(self):
        with patch("src.common.auth.verify_jwt") as mock:
            mock.return_value = {
                "sub": "user-123",
                "email": "test@example.com",
                "cognito:groups": ["Parents"],
                "token_use": "id",
            }
            yield mock

    def test_authorize_valid_token(self, mock_verify_jwt):
        @authorize()
        def handler(event, context):
            return {"statusCode": 200, "body": json.dumps({"message": "success"})}

        event = {"headers": {"Authorization": "Bearer valid-token"}}

        result = handler(event, None)

        assert result["statusCode"] == 200
        assert "authorizer" in event["requestContext"]
        assert event["requestContext"]["authorizer"]["userId"] == "user-123"
        assert event["requestContext"]["authorizer"]["groups"] == ["Parents"]

    def test_authorize_required_groups_match(self, mock_verify_jwt):
        @authorize(required_groups=["Parents"])
        def handler(event, context):
            return {"statusCode": 200, "body": "{}"}

        event = {"headers": {"Authorization": "Bearer valid-token"}}

        result = handler(event, None)
        assert result["statusCode"] == 200

    def test_authorize_required_groups_mismatch(self, mock_verify_jwt):
        mock_verify_jwt.return_value["cognito:groups"] = ["Children"]

        @authorize(required_groups=["Parents"])
        def handler(event, context):
            return {"statusCode": 200, "body": "{}"}

        event = {"headers": {"Authorization": "Bearer valid-token"}}

        result = handler(event, None)
        assert result["statusCode"] == 403
        body = json.loads(result["body"])
        assert "error" in body

    def test_authorize_missing_header(self):
        @authorize()
        def handler(event, context):
            return {"statusCode": 200, "body": "{}"}

        event = {"headers": {}}

        result = handler(event, None)
        assert result["statusCode"] == 401
        body = json.loads(result["body"])
        assert "error" in body

    def test_authorize_invalid_header_format(self):
        @authorize()
        def handler(event, context):
            return {"statusCode": 200, "body": "{}"}

        event = {"headers": {"Authorization": "Invalid token"}}

        result = handler(event, None)
        assert result["statusCode"] == 401

    def test_authorize_case_insensitive_header(self, mock_verify_jwt):
        @authorize()
        def handler(event, context):
            return {"statusCode": 200, "body": "{}"}

        event = {"headers": {"authorization": "Bearer valid-token"}}

        result = handler(event, None)
        assert result["statusCode"] == 200

    def test_authorize_jwt_verification_fails(self):
        with patch("src.common.auth.verify_jwt") as mock_verify:
            mock_verify.side_effect = UnauthorizedError("Invalid token")

            @authorize()
            def handler(event, context):
                return {"statusCode": 200, "body": "{}"}

            event = {"headers": {"Authorization": "Bearer invalid-token"}}

            result = handler(event, None)
            assert result["statusCode"] == 401

    def test_authorize_unexpected_error(self, mock_verify_jwt):
        @authorize()
        def handler(event, context):
            raise Exception("Unexpected error")

        event = {"headers": {"Authorization": "Bearer valid-token"}}

        result = handler(event, None)
        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "error" in body


class TestGetJWKS:
    @patch("src.common.auth.requests.get")
    def test_get_jwks_success(self, mock_get):
        from src.common.auth import get_jwks, _jwks_cache

        mock_response = MagicMock()
        mock_response.json.return_value = {"keys": [{"kid": "test-key"}]}
        mock_get.return_value = mock_response

        result = get_jwks()

        assert result == {"keys": [{"kid": "test-key"}]}
        assert mock_get.called

    @patch("src.common.auth.requests.get")
    def test_get_jwks_uses_cache(self, mock_get):
        from src.common.auth import get_jwks, _jwks_cache, _jwks_cache_time
        import src.common.auth as auth_module

        # Set up cache
        auth_module._jwks_cache = {"keys": [{"kid": "cached-key"}]}
        auth_module._jwks_cache_time = float("inf")  # Never expire

        result = get_jwks()

        assert result == {"keys": [{"kid": "cached-key"}]}
        assert not mock_get.called

        # Reset cache
        auth_module._jwks_cache = None
        auth_module._jwks_cache_time = 0

    @patch("src.common.auth.requests.get")
    def test_get_jwks_fetch_failure_with_cache(self, mock_get):
        from src.common.auth import get_jwks
        import src.common.auth as auth_module

        # Set up stale cache
        auth_module._jwks_cache = {"keys": [{"kid": "stale-key"}]}
        auth_module._jwks_cache_time = 0  # Expired

        # Make request fail
        mock_get.side_effect = Exception("Network error")

        result = get_jwks()

        # Should return stale cache as fallback
        assert result == {"keys": [{"kid": "stale-key"}]}

        # Reset
        auth_module._jwks_cache = None
        auth_module._jwks_cache_time = 0

    @patch("src.common.auth.requests.get")
    def test_get_jwks_fetch_failure_no_cache(self, mock_get):
        from src.common.auth import get_jwks
        import src.common.auth as auth_module

        # Clear cache
        auth_module._jwks_cache = None
        auth_module._jwks_cache_time = 0

        # Make request fail
        mock_get.side_effect = Exception("Network error")

        with pytest.raises(UnauthorizedError):
            get_jwks()


class TestVerifyJWT:
    @patch("src.common.auth.get_jwks")
    @patch("src.common.auth.jwt.get_unverified_header")
    @patch("src.common.auth.jwt.decode")
    def test_verify_jwt_success(self, mock_decode, mock_header, mock_get_jwks):
        mock_get_jwks.return_value = {
            "keys": [{"kid": "test-key-id", "kty": "RSA", "use": "sig"}]
        }
        mock_header.return_value = {"kid": "test-key-id"}
        mock_decode.return_value = {
            "sub": "user-123",
            "email": "test@example.com",
            "token_use": "id",
        }

        from src.common.auth import verify_jwt

        result = verify_jwt("fake-token")

        assert result["sub"] == "user-123"
        assert result["email"] == "test@example.com"
        assert mock_decode.called

    @patch("src.common.auth.get_jwks")
    @patch("src.common.auth.jwt.get_unverified_header")
    def test_verify_jwt_key_not_found(self, mock_header, mock_get_jwks):
        mock_get_jwks.return_value = {
            "keys": [{"kid": "different-key-id", "kty": "RSA", "use": "sig"}]
        }
        mock_header.return_value = {"kid": "test-key-id"}

        from src.common.auth import verify_jwt

        with pytest.raises(UnauthorizedError, match="Public key not found"):
            verify_jwt("fake-token")

    @patch("src.common.auth.get_jwks")
    @patch("src.common.auth.jwt.get_unverified_header")
    @patch("src.common.auth.jwt.decode")
    def test_verify_jwt_wrong_token_use(self, mock_decode, mock_header, mock_get_jwks):
        mock_get_jwks.return_value = {"keys": [{"kid": "test-key-id", "kty": "RSA"}]}
        mock_header.return_value = {"kid": "test-key-id"}
        mock_decode.return_value = {
            "sub": "user-123",
            "token_use": "access",  # Should be 'id'
        }

        from src.common.auth import verify_jwt

        with pytest.raises(UnauthorizedError, match="not an ID token"):
            verify_jwt("fake-token")
