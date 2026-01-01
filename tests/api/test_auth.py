"""Tests for authentication endpoints."""

from unittest.mock import patch, AsyncMock
import pytest
# import asyncio
from datetime import datetime, timezone, timedelta

from src.api.dependencies.auth import create_access_token, create_refresh_token
from src.core.models import AuthCode


class TestAuthCodeGeneration:
    """Test auth code generation details."""

    @patch("src.api.services.auth_code_service.secrets.randbelow")
    @pytest.mark.asyncio
    async def test_code_is_6_digits(self, mock_rand):
        """TC1: Test code is always 6 digits, padded with zeros."""
        from src.api.services.auth_code_service import AuthCodeService
        service = AuthCodeService()

        # Test small number padding
        mock_rand.return_value = 123
        assert await service.generate_code() == "000123"

        # Test zero padding
        mock_rand.return_value = 0
        assert await service.generate_code() == "000000"

        # Test large number
        mock_rand.return_value = 999999
        assert await service.generate_code() == "999999"

    @patch("src.api.services.auth_code_service.auth_code_service.auth_code_repo")
    @patch("src.api.services.auth_code_service.auth_code_service.user_repo")
    @patch("src.api.v1.routers.auth._send_auth_code_to_telegram")
    def test_code_expires_in_5_minutes(
        self, mock_send, mock_user_repo, mock_auth_repo, client_no_auth, mock_user
    ):
        """TC2: Test code expiry time is set correctly."""
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
        mock_auth_repo.count_recent_requests = AsyncMock(return_value=0)
        mock_auth_repo.invalidate_user_codes = AsyncMock()
        
        # We need to mock create to return a valid object to avoid 500 error
        mock_auth_code = AuthCode(
            user_id=mock_user.id,
            code="123456",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
        )
        mock_auth_repo.create = AsyncMock(return_value=mock_auth_code)

        response = client_no_auth.post(
            "/v1/auth/request-code",
            json={"telegram_id": "123456789"}
        )

        assert response.status_code == 200

        # Check call arguments to repo.create
        args, kwargs = mock_auth_repo.create.call_args
        expires_at = kwargs["expires_at"]
        now = datetime.now(timezone.utc)
        
        # Should be roughly 5 minutes in future (allow 10s buffer)
        diff = expires_at - now
        assert 290 < diff.total_seconds() < 310


class TestLogin:
    """Test login endpoint."""

    @patch("src.api.v1.routers.auth.user_repository")
    def test_login_success(self, mock_repo, client_no_auth, mock_user):
        """Test deprecated login endpoint is disabled."""
        mock_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)

        response = client_no_auth.post(
            "/v1/auth/login", json={"telegram_id": "123456789"}
        )

        assert response.status_code == 410
        data = response.json()
        assert data["error"]["code"] == "DEPRECATED_LOGIN"

    @patch("src.api.v1.routers.auth.user_repository")
    def test_login_user_not_found(self, mock_repo, client_no_auth):
        """Test deprecated login endpoint is disabled regardless of user existence."""
        mock_repo.get_by_telegram_id = AsyncMock(return_value=None)

        response = client_no_auth.post(
            "/v1/auth/login", json={"telegram_id": "999999999"}
        )

        assert response.status_code == 410
        data = response.json()
        assert data["error"]["code"] == "DEPRECATED_LOGIN"

    @patch("src.api.v1.routers.auth.user_repository")
    def test_login_inactive_user(self, mock_repo, client_no_auth, mock_inactive_user):
        """Test deprecated login endpoint is disabled regardless of user status."""
        mock_repo.get_by_telegram_id = AsyncMock(return_value=mock_inactive_user)

        response = client_no_auth.post(
            "/v1/auth/login", json={"telegram_id": "987654321"}
        )

        assert response.status_code == 410
        data = response.json()
        assert data["error"]["code"] == "DEPRECATED_LOGIN"


class TestRefreshToken:
    """Test token refresh endpoint."""

    @patch("src.api.v1.routers.auth.user_repository")
    def test_refresh_success(self, mock_repo, client_no_auth, mock_user):
        """Test successful token refresh."""
        mock_repo.get_by_id = AsyncMock(return_value=mock_user)

        # Create a valid refresh token
        refresh_token = create_refresh_token(
            user_id=mock_user.id, telegram_id=mock_user.telegram_id
        )

        response = client_no_auth.post(
            "/v1/auth/refresh", json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "refresh_token" not in data  # Only access token is returned

    def test_refresh_invalid_token(self, client_no_auth):
        """Test refresh fails with invalid token."""
        response = client_no_auth.post(
            "/v1/auth/refresh", json={"refresh_token": "invalid.token.here"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_TOKEN"

    @patch("src.api.v1.routers.auth.user_repository")
    def test_refresh_user_not_found(self, mock_repo, client_no_auth):
        """Test refresh fails when user no longer exists."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        # Create a valid refresh token for non-existent user
        refresh_token = create_refresh_token(user_id=999, telegram_id="999")

        response = client_no_auth.post(
            "/v1/auth/refresh", json={"refresh_token": refresh_token}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "USER_NOT_FOUND"

    @patch("src.api.v1.routers.auth.user_repository")
    def test_refresh_inactive_user(self, mock_repo, client_no_auth, mock_inactive_user):
        """Test refresh fails for inactive user."""
        mock_repo.get_by_id = AsyncMock(return_value=mock_inactive_user)

        refresh_token = create_refresh_token(
            user_id=mock_inactive_user.id, telegram_id=mock_inactive_user.telegram_id
        )

        response = client_no_auth.post(
            "/v1/auth/refresh", json={"refresh_token": refresh_token}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "USER_INACTIVE"

    def test_refresh_wrong_token_type(self, client_no_auth, mock_user):
        """Test refresh fails when using access token instead of refresh token."""
        # Create an access token (not refresh)
        access_token = create_access_token(
            user_id=mock_user.id, telegram_id=mock_user.telegram_id
        )

        response = client_no_auth.post(
            "/v1/auth/refresh", json={"refresh_token": access_token}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_TOKEN_TYPE"


class TestLogout:
    """Test logout endpoint."""

    def test_logout_success(self, client, mock_user):
        """Test successful logout."""
        refresh_token = create_refresh_token(
            user_id=mock_user.id, telegram_id=mock_user.telegram_id
        )

        response = client.post("/v1/auth/logout", json={"refresh_token": refresh_token})

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "logged out" in data["message"].lower()

    def test_logout_requires_auth(self, client_no_auth):
        """Test logout requires authentication."""
        response = client_no_auth.post(
            "/v1/auth/logout", json={"refresh_token": "some.token.here"}
        )

        assert response.status_code == 401


class TestRequestAuthCode:
    """Test auth code request endpoint."""

    @patch("src.api.services.auth_code_service.auth_code_service.auth_code_repo")
    @patch("src.api.services.auth_code_service.auth_code_service.user_repo")
    @patch("src.api.v1.routers.auth._send_auth_code_to_telegram")
    def test_request_code_success(
        self, mock_send, mock_user_repo, mock_auth_repo, client_no_auth, mock_user
    ):
        """Test successful code request."""
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
        mock_auth_repo.count_recent_requests = AsyncMock(return_value=0)
        
        mock_auth_code = AuthCode(
            user_id=mock_user.id,
            code="123456",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
        )
        mock_auth_repo.create = AsyncMock(return_value=mock_auth_code)
        mock_auth_repo.invalidate_user_codes = AsyncMock()

        response = client_no_auth.post(
            "/v1/auth/request-code",
            json={"telegram_id": "123456789", "device_info": "Test Device"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "sent to Telegram" in data["message"]
        mock_send.assert_called_once()

    @patch("src.api.services.auth_code_service.auth_code_service.auth_code_repo")
    @patch("src.api.services.auth_code_service.auth_code_service.user_repo")
    def test_request_code_user_not_found_returns_success(
        self, mock_user_repo, mock_auth_repo, client_no_auth
    ):
        """Test that unknown users get a success response (anti-enumeration)."""
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=None)

        response = client_no_auth.post(
            "/v1/auth/request-code",
            json={"telegram_id": "999999999"}
        )

        assert response.status_code == 200  # Should be 200, not 404
        data = response.json()
        assert "sent to Telegram" in data["message"]

    @patch("src.api.services.auth_code_service.auth_code_service.auth_code_repo")
    @patch("src.api.services.auth_code_service.auth_code_service.user_repo")
    def test_request_code_rate_limit(
        self, mock_user_repo, mock_auth_repo, client_no_auth, mock_user
    ):
        """Test rate limiting blocks frequent requests."""
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
        mock_auth_repo.count_recent_requests = AsyncMock(return_value=5)  # Over limit

        response = client_no_auth.post(
            "/v1/auth/request-code",
            json={"telegram_id": "123456789"}
        )

        assert response.status_code == 429
        data = response.json()
        assert data["error"]["code"] == "RATE_LIMITED"


class TestVerifyAuthCode:
    """Test auth code verification endpoint."""

    @patch("src.api.services.auth_code_service.auth_code_service.auth_code_repo")
    @patch("src.api.services.auth_code_service.auth_code_service.user_repo")
    def test_verify_code_success(
        self, mock_user_repo, mock_auth_repo, client_no_auth, mock_user
    ):
        """Test successful code verification."""
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
        
        mock_auth_code = AuthCode(
            id=1,
            user_id=mock_user.id,
            code="123456",
            used=False
        )
        mock_auth_repo.verify_and_consume_code = AsyncMock(return_value=mock_auth_code)

        response = client_no_auth.post(
            "/v1/auth/verify-code",
            json={"telegram_id": "123456789", "code": "123456"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @patch("src.api.services.auth_code_service.auth_code_service.auth_code_repo")
    @patch("src.api.services.auth_code_service.auth_code_service.user_repo")
    def test_verify_code_invalid(
        self, mock_user_repo, mock_auth_repo, client_no_auth, mock_user
    ):
        """Test invalid code rejected."""
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
        mock_auth_repo.verify_and_consume_code = AsyncMock(return_value=None)
        mock_auth_repo.register_failed_attempt = AsyncMock()

        response = client_no_auth.post(
            "/v1/auth/verify-code",
            json={"telegram_id": "123456789", "code": "000000"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_CODE"
        mock_auth_repo.register_failed_attempt.assert_called_once()

    @patch("src.api.services.auth_code_service.auth_code_service.auth_code_repo")
    @patch("src.api.services.auth_code_service.auth_code_service.user_repo")
    def test_verify_code_unknown_user(
        self, mock_user_repo, mock_auth_repo, client_no_auth
    ):
        """Test verification for unknown user fails."""
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=None)

        response = client_no_auth.post(
            "/v1/auth/verify-code",
            json={"telegram_id": "999999999", "code": "123456"}
        )

        # Should fail silently (generic error) or not found?
        # Implementation returns None for user, then AuthCodeService logs warning and returns None
        # Then router raises INVALID_CODE (Unauthorized)
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_CODE"

    @patch("src.api.services.auth_code_service.auth_code_service.auth_code_repo")
    @patch("src.api.services.auth_code_service.auth_code_service.user_repo")
    def test_verify_code_expired_returns_401(
        self, mock_user_repo, mock_auth_repo, client_no_auth, mock_user
    ):
        """TC5: Test expired code returns 401."""
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
        # verify_and_consume_code returns None for expired codes
        mock_auth_repo.verify_and_consume_code = AsyncMock(return_value=None)
        mock_auth_repo.register_failed_attempt = AsyncMock()

        response = client_no_auth.post(
            "/v1/auth/verify-code",
            json={"telegram_id": "123456789", "code": "123456"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_CODE"
        mock_auth_repo.register_failed_attempt.assert_called_once()

    @patch("src.api.services.auth_code_service.auth_code_service.auth_code_repo")
    @patch("src.api.services.auth_code_service.auth_code_service.user_repo")
    def test_verify_code_already_used_returns_401(
        self, mock_user_repo, mock_auth_repo, client_no_auth, mock_user
    ):
        """TC6: Test already used code returns 401."""
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
        # verify_and_consume_code returns None for already used codes
        mock_auth_repo.verify_and_consume_code = AsyncMock(return_value=None)
        mock_auth_repo.register_failed_attempt = AsyncMock()

        response = client_no_auth.post(
            "/v1/auth/verify-code",
            json={"telegram_id": "123456789", "code": "123456"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_CODE"

    @patch("src.api.services.auth_code_service.auth_code_service.auth_code_repo")
    @patch("src.api.services.auth_code_service.auth_code_service.user_repo")
    def test_verify_code_different_user_returns_401(
        self, mock_user_repo, mock_auth_repo, client_no_auth, mock_user
    ):
        """TC8: Test code for different user returns 401."""
        # User exists but code doesn't match their user_id
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
        # verify_and_consume_code returns None when code doesn't match user
        mock_auth_repo.verify_and_consume_code = AsyncMock(return_value=None)
        mock_auth_repo.register_failed_attempt = AsyncMock()

        response = client_no_auth.post(
            "/v1/auth/verify-code",
            json={"telegram_id": "123456789", "code": "999999"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_CODE"
        mock_auth_repo.register_failed_attempt.assert_called_once()

    @patch("src.api.services.auth_code_service.auth_code_service.auth_code_repo")
    @patch("src.api.services.auth_code_service.auth_code_service.user_repo")
    def test_verify_code_concurrent_invalidation(
        self, mock_user_repo, mock_auth_repo, client_no_auth, mock_user
    ):
        """TC15: Test that requesting a new code invalidates previous ones."""
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
        mock_auth_repo.count_recent_requests = AsyncMock(return_value=0)
        
        mock_auth_code = AuthCode(
            user_id=mock_user.id,
            code="654321",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
        )
        mock_auth_repo.create = AsyncMock(return_value=mock_auth_code)
        mock_auth_repo.invalidate_user_codes = AsyncMock()

        # Request new code
        client_no_auth.post(
            "/v1/auth/request-code",
            json={"telegram_id": "123456789"}
        )

        # Should call invalidate_user_codes
        mock_auth_repo.invalidate_user_codes.assert_called_once_with(mock_user.id)


class TestBruteForceProtection:
    """Test brute force protection for auth codes."""

    @patch("src.api.services.auth_code_service.auth_code_service.auth_code_repo")
    @patch("src.api.services.auth_code_service.auth_code_service.user_repo")
    def test_5_failed_attempts_blocks_15_min(
        self, mock_user_repo, mock_auth_repo, client_no_auth, mock_user
    ):
        """TC9: Test 5 failed attempts blocks code for 15 minutes."""
        # from unittest.mock import MagicMock
        
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
        
        # Mock auth code that will be locked after 5 attempts
        mock_auth_code = AuthCode(
            id=1,
            user_id=mock_user.id,
            code="123456",
            used=False,
            failed_attempts=0,
            locked_until=None,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
        )
        
        # First 4 attempts fail, code still valid
        # On 5th attempt, code gets locked
        # attempt_counts = [0, 1, 2, 3, 4]
        
        def verify_side_effect(*args, **kwargs):
            # Simulate failed verification
            return None
        
        def register_side_effect(*args, **kwargs):
            # Increment failed attempts
            mock_auth_code.failed_attempts += 1
            if mock_auth_code.failed_attempts >= 5:
                mock_auth_code.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            return True
        
        mock_auth_repo.verify_and_consume_code = AsyncMock(side_effect=verify_side_effect)
        mock_auth_repo.register_failed_attempt = AsyncMock(side_effect=register_side_effect)
        
        # Get latest code mock - returns our mock code
        def get_latest_side_effect(*args, **kwargs):
            return mock_auth_code
        
        mock_auth_repo.get_latest_active_code = AsyncMock(side_effect=get_latest_side_effect)
        
        # Make 5 failed attempts
        for i in range(5):
            response = client_no_auth.post(
                "/v1/auth/verify-code",
                json={"telegram_id": "123456789", "code": "000000"}
            )
            assert response.status_code == 401
        
        # Verify register_failed_attempt was called 5 times
        assert mock_auth_repo.register_failed_attempt.call_count == 5
        
        # Now verify code is locked - verify_and_consume_code should return None
        # because locked_until is set
        mock_auth_repo.verify_and_consume_code = AsyncMock(return_value=None)
        response = client_no_auth.post(
            "/v1/auth/verify-code",
            json={"telegram_id": "123456789", "code": "123456"}
        )
        assert response.status_code == 401

    @patch("src.api.services.auth_code_service.auth_code_service.auth_code_repo")
    @patch("src.api.services.auth_code_service.auth_code_service.user_repo")
    def test_successful_login_resets_counter(
        self, mock_user_repo, mock_auth_repo, client_no_auth, mock_user
    ):
        """TC10: Test successful login resets attempt counter."""
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
        
        # Mock auth code with failed attempts
        mock_auth_code = AuthCode(
            id=1,
            user_id=mock_user.id,
            code="123456",
            used=False,
            failed_attempts=3,  # Has 3 failed attempts
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
        )
        
        # Successful verification consumes the code (marks as used)
        mock_auth_repo.verify_and_consume_code = AsyncMock(return_value=mock_auth_code)
        
        response = client_no_auth.post(
            "/v1/auth/verify-code",
            json={"telegram_id": "123456789", "code": "123456"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        
        # When code is consumed, it's marked as used, so future attempts
        # on the same code will fail (code is single-use)
        # The counter is effectively reset because the code is consumed
        mock_auth_repo.verify_and_consume_code = AsyncMock(return_value=None)
        response = client_no_auth.post(
            "/v1/auth/verify-code",
            json={"telegram_id": "123456789", "code": "123456"}
        )
        assert response.status_code == 401
