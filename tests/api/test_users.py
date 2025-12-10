"""Tests for user endpoints."""

from unittest.mock import patch, AsyncMock


class TestGetCurrentUser:
    """Test GET /v1/users/me endpoint."""

    def test_get_current_user_success(self, client, mock_user):
        """Test getting current user profile."""
        response = client.get("/v1/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == mock_user.id
        assert data["telegram_id"] == mock_user.telegram_id
        assert data["name"] == mock_user.name
        assert data["language"] == mock_user.language
        assert data["is_active"] == mock_user.is_active

    def test_get_current_user_requires_auth(self, client_no_auth):
        """Test that endpoint requires authentication."""
        response = client_no_auth.get("/v1/users/me")

        assert response.status_code == 401


class TestUpdateCurrentUser:
    """Test PATCH /v1/users/me endpoint."""

    @patch("src.api.v1.routers.users.user_repository")
    def test_update_user_name(self, mock_repo, client, mock_user):
        """Test updating user name."""
        updated_user = mock_user
        updated_user.name = "Updated Name"
        mock_repo.update = AsyncMock(return_value=updated_user)

        response = client.patch("/v1/users/me", json={"name": "Updated Name"})

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        mock_repo.update.assert_called_once_with(mock_user.id, {"name": "Updated Name"})

    @patch("src.api.v1.routers.users.user_repository")
    def test_update_user_language(self, mock_repo, client, mock_user):
        """Test updating user language."""
        updated_user = mock_user
        updated_user.language = "ru"
        mock_repo.update = AsyncMock(return_value=updated_user)

        response = client.patch("/v1/users/me", json={"language": "ru"})

        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "ru"
        mock_repo.update.assert_called_once_with(mock_user.id, {"language": "ru"})

    @patch("src.api.v1.routers.users.user_repository")
    def test_update_user_multiple_fields(self, mock_repo, client, mock_user):
        """Test updating multiple user fields at once."""
        updated_user = mock_user
        updated_user.name = "New Name"
        updated_user.language = "kk"
        mock_repo.update = AsyncMock(return_value=updated_user)

        response = client.patch(
            "/v1/users/me", json={"name": "New Name", "language": "kk"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["language"] == "kk"
        mock_repo.update.assert_called_once_with(
            mock_user.id, {"name": "New Name", "language": "kk"}
        )

    def test_update_user_no_changes(self, client, mock_user):
        """Test updating user with empty payload."""
        response = client.patch("/v1/users/me", json={})

        assert response.status_code == 200
        data = response.json()
        # Should return current user unchanged
        assert data["id"] == mock_user.id
        assert data["name"] == mock_user.name

    def test_update_user_invalid_language(self, client):
        """Test updating user with invalid language."""
        response = client.patch("/v1/users/me", json={"language": "invalid"})

        assert response.status_code == 422  # Validation error

    def test_update_user_requires_auth(self, client_no_auth):
        """Test that endpoint requires authentication."""
        response = client_no_auth.patch("/v1/users/me", json={"name": "Test"})

        assert response.status_code == 401


class TestGetUserSettings:
    """Test GET /v1/users/me/settings endpoint."""

    def test_get_user_settings(self, client, mock_user):
        """Test getting user settings."""
        response = client.get("/v1/users/me/settings")

        assert response.status_code == 200
        data = response.json()
        assert data["language"] == mock_user.language
        assert "timezone" in data

    def test_get_user_settings_requires_auth(self, client_no_auth):
        """Test that endpoint requires authentication."""
        response = client_no_auth.get("/v1/users/me/settings")

        assert response.status_code == 401
