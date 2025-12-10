"""Tests for authentication endpoints."""

from unittest.mock import patch, AsyncMock

from src.api.dependencies.auth import create_access_token, create_refresh_token


class TestLogin:
    """Test login endpoint."""

    @patch("src.api.v1.routers.auth.user_repository")
    def test_login_success(self, mock_repo, client_no_auth, mock_user):
        """Test successful login with valid telegram_id."""
        mock_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)

        response = client_no_auth.post(
            "/v1/auth/login", json={"telegram_id": "123456789"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        mock_repo.get_by_telegram_id.assert_called_once_with("123456789")

    @patch("src.api.v1.routers.auth.user_repository")
    def test_login_user_not_found(self, mock_repo, client_no_auth):
        """Test login fails when user doesn't exist."""
        mock_repo.get_by_telegram_id = AsyncMock(return_value=None)

        response = client_no_auth.post(
            "/v1/auth/login", json={"telegram_id": "999999999"}
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "USER_NOT_FOUND"
        assert "not found" in data["error"]["message"].lower()

    @patch("src.api.v1.routers.auth.user_repository")
    def test_login_inactive_user(self, mock_repo, client_no_auth, mock_inactive_user):
        """Test login fails for inactive user."""
        mock_repo.get_by_telegram_id = AsyncMock(return_value=mock_inactive_user)

        response = client_no_auth.post(
            "/v1/auth/login", json={"telegram_id": "987654321"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "USER_INACTIVE"
        assert "inactive" in data["error"]["message"].lower()


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
