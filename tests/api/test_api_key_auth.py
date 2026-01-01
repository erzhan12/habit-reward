"""Tests for API key authentication."""

from unittest.mock import patch, AsyncMock, MagicMock
# import pytest
# from datetime import datetime, timezone, timedelta, date

# from src.core.models import APIKey, User
from src.api.dependencies.auth import create_access_token


class TestAPIKeyGeneration:
    """Test API key generation details."""

    def test_key_has_hrk_prefix(self):
        """TC16: Test generated key has hrk_ prefix."""
        from src.api.services.auth_code_service import APIKeyService
        
        service = APIKeyService()
        key = service.generate_key()
        
        assert key.startswith("hrk_")
        assert len(key) > len("hrk_")  # Should have content after prefix

    def test_key_is_hashed_in_database(self):
        """TC17: Test key is hashed before storage."""
        from src.api.services.auth_code_service import APIKeyService
        
        service = APIKeyService()
        raw_key = service.generate_key()
        key_hash = service.hash_key(raw_key)
        
        # Hash should be SHA256 hex (64 chars)
        assert len(key_hash) == 64
        assert raw_key != key_hash  # Should be different
        assert not raw_key.startswith("hrk_") or raw_key != key_hash  # Hash doesn't contain prefix

    def test_same_key_hashes_consistently(self):
        """TC18: Test same key string hashes to same value."""
        from src.api.services.auth_code_service import APIKeyService
        
        service = APIKeyService()
        raw_key = "hrk_test_key_12345"
        
        hash1 = service.hash_key(raw_key)
        hash2 = service.hash_key(raw_key)
        
        assert hash1 == hash2


class TestAPIKeyAuthentication:
    """Test API key authentication using habit completion endpoint."""

    @patch("src.api.services.auth_code_service.api_key_service")
    @patch("src.api.v1.routers.habits.habit_repository")
    @patch("src.api.v1.routers.habits.habit_service")
    def test_valid_api_key_returns_user(
        self, mock_habit_service, mock_habit_repo, mock_api_key_service, 
        client_no_auth, mock_user, mock_habit
    ):
        """TC19: Test valid API key authenticates and returns user."""
        mock_api_key_service.verify_api_key = AsyncMock(return_value=mock_user)
        mock_habit_repo.get_by_id = AsyncMock(return_value=mock_habit)
        
        # Mock habit service completion result (matching test_habits.py pattern)
        mock_result = MagicMock()
        mock_result.habit_confirmed = True
        mock_result.habit_name = mock_habit.name
        mock_result.streak_count = 5
        mock_result.got_reward = False
        mock_result.total_weight_applied = 1.5
        mock_result.reward = None
        mock_result.cumulative_progress = None
        mock_habit_service.process_habit_completion = AsyncMock(return_value=mock_result)
        
        response = client_no_auth.post(
            "/v1/habits/1/complete",
            headers={"X-API-Key": "hrk_valid_key_12345"},
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["habit_confirmed"] is True
        mock_api_key_service.verify_api_key.assert_called_once_with("hrk_valid_key_12345")

    @patch("src.api.services.auth_code_service.api_key_service")
    def test_invalid_key_returns_401(self, mock_api_key_service, client_no_auth):
        """TC20: Test invalid API key returns 401."""
        mock_api_key_service.verify_api_key = AsyncMock(return_value=None)
        
        response = client_no_auth.post(
            "/v1/habits/1/complete",
            headers={"X-API-Key": "hrk_invalid_key"},
            json={}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_API_KEY"

    @patch("src.api.services.auth_code_service.api_key_service")
    def test_expired_key_returns_401(self, mock_api_key_service, client_no_auth):
        """TC21: Test expired API key returns 401."""
        # Service returns None for expired keys
        mock_api_key_service.verify_api_key = AsyncMock(return_value=None)
        
        response = client_no_auth.post(
            "/v1/habits/1/complete",
            headers={"X-API-Key": "hrk_expired_key"},
            json={}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_API_KEY"

    @patch("src.api.services.auth_code_service.api_key_service")
    def test_revoked_key_returns_401(self, mock_api_key_service, client_no_auth):
        """TC22: Test revoked (is_active=False) key returns 401."""
        # Service returns None for revoked keys
        mock_api_key_service.verify_api_key = AsyncMock(return_value=None)
        
        response = client_no_auth.post(
            "/v1/habits/1/complete",
            headers={"X-API-Key": "hrk_revoked_key"},
            json={}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_API_KEY"

    def test_missing_key_returns_401(self, client_no_auth):
        """TC23: Test missing API key returns 401."""
        response = client_no_auth.post(
            "/v1/habits/1/complete",
            json={}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTH_REQUIRED"

    @patch("src.api.services.auth_code_service.api_key_service")
    def test_api_key_auth_works_for_users_me(self, mock_api_key_service, client_no_auth, mock_user):
        """TC23a: Test API key authenticates on /v1/users/me."""
        mock_api_key_service.verify_api_key = AsyncMock(return_value=mock_user)

        response = client_no_auth.get(
            "/v1/users/me",
            headers={"X-API-Key": "hrk_valid_key_12345"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == mock_user.id
        assert data["telegram_id"] == mock_user.telegram_id
        assert data["is_active"] is True
        mock_api_key_service.verify_api_key.assert_called_once_with("hrk_valid_key_12345")


class TestCombinedAuth:
    """Test combined JWT and API key authentication."""

    @patch("src.api.services.auth_code_service.api_key_service")
    @patch("src.api.v1.routers.habits.habit_repository")
    @patch("src.api.v1.routers.habits.habit_service")
    @patch("src.api.dependencies.auth.user_repository")
    def test_jwt_priority_over_api_key(
        self, mock_user_repo, mock_habit_service, mock_habit_repo, mock_api_key_service,
        client_no_auth, mock_user, mock_habit
    ):
        """TC24: Test JWT takes priority when both are present."""
        # Mock user repository to return user for JWT lookup
        mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
        
        # Create a valid JWT token
        access_token = create_access_token(
            user_id=mock_user.id, telegram_id=mock_user.telegram_id
        )
        
        # Mock habit service completion result
        mock_result = MagicMock()
        mock_result.habit_confirmed = True
        mock_result.habit_name = mock_habit.name
        mock_result.streak_count = 5
        mock_result.got_reward = False
        mock_result.total_weight_applied = 1.5
        mock_result.reward = None
        mock_result.cumulative_progress = None
        mock_habit_service.process_habit_completion = AsyncMock(return_value=mock_result)
        mock_habit_repo.get_by_id = AsyncMock(return_value=mock_habit)
        
        # Mock API key service (should not be called)
        mock_api_key_service.verify_api_key = AsyncMock(return_value=None)
        
        response = client_no_auth.post(
            "/v1/habits/1/complete",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-Key": "hrk_some_key"
            },
            json={}
        )
        
        assert response.status_code == 200
        # API key service should not be called when JWT is present
        mock_api_key_service.verify_api_key.assert_not_called()

    @patch("src.api.services.auth_code_service.api_key_service")
    @patch("src.api.v1.routers.habits.habit_repository")
    @patch("src.api.v1.routers.habits.habit_service")
    def test_api_key_works_without_jwt(
        self, mock_habit_service, mock_habit_repo, mock_api_key_service,
        client_no_auth, mock_user, mock_habit
    ):
        """TC25: Test API key works when JWT is missing."""
        mock_api_key_service.verify_api_key = AsyncMock(return_value=mock_user)
        mock_habit_repo.get_by_id = AsyncMock(return_value=mock_habit)
        
        # Mock habit service completion result
        mock_result = MagicMock()
        mock_result.habit_confirmed = True
        mock_result.habit_name = mock_habit.name
        mock_result.streak_count = 5
        mock_result.got_reward = False
        mock_result.total_weight_applied = 1.5
        mock_result.reward = None
        mock_result.cumulative_progress = None
        mock_habit_service.process_habit_completion = AsyncMock(return_value=mock_result)
        
        response = client_no_auth.post(
            "/v1/habits/1/complete",
            headers={"X-API-Key": "hrk_valid_key"},
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["habit_confirmed"] is True
        mock_api_key_service.verify_api_key.assert_called_once()

    def test_no_auth_returns_401(self, client_no_auth):
        """TC26: Test no authentication returns 401."""
        response = client_no_auth.post(
            "/v1/habits/1/complete",
            json={}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTH_REQUIRED"


class TestHabitCompletionWithAPIKey:
    """Test habit completion using API key authentication."""
    
    @patch("src.api.services.auth_code_service.api_key_service")
    @patch("src.api.v1.routers.habits.habit_repository")
    @patch("src.api.v1.routers.habits.habit_service")
    def test_complete_habit_with_valid_api_key(
        self, mock_habit_service, mock_habit_repo, mock_api_key_service,
        client_no_auth, mock_user, mock_habit
    ):
        """TC27: Test complete habit with valid API key succeeds."""
        mock_api_key_service.verify_api_key = AsyncMock(return_value=mock_user)
        mock_habit_repo.get_by_id = AsyncMock(return_value=mock_habit)
        
        # Mock habit service completion result
        mock_result = MagicMock()
        mock_result.habit_confirmed = True
        mock_result.habit_name = mock_habit.name
        mock_result.streak_count = 5
        mock_result.got_reward = False
        mock_result.total_weight_applied = 1.5
        mock_result.reward = None
        mock_result.cumulative_progress = None
        mock_habit_service.process_habit_completion = AsyncMock(return_value=mock_result)
        
        response = client_no_auth.post(
            "/v1/habits/1/complete",
            headers={"X-API-Key": "hrk_valid_key"},
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["habit_confirmed"] is True
        mock_api_key_service.verify_api_key.assert_called_once()

    @patch("src.api.services.auth_code_service.api_key_service")
    def test_complete_habit_with_invalid_api_key(
        self, mock_api_key_service, client_no_auth
    ):
        """TC28: Test complete habit with invalid API key fails."""
        mock_api_key_service.verify_api_key = AsyncMock(return_value=None)
        
        response = client_no_auth.post(
            "/v1/habits/1/complete",
            headers={"X-API-Key": "hrk_invalid_key"},
            json={"target_date": "2025-01-01"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_API_KEY"
    
    @patch("src.api.services.auth_code_service.api_key_service")
    @patch("src.api.v1.routers.habits.habit_repository")
    def test_cannot_complete_other_users_habit(
        self, mock_habit_repo, mock_api_key_service, client_no_auth, mock_user
    ):
        """TC29: Test cannot complete another user's habit with API key."""
        # User 1's API key
        mock_api_key_service.verify_api_key = AsyncMock(return_value=mock_user)
        
        # Habit belongs to User 2
        other_user_habit = MagicMock()
        other_user_habit.id = 999
        other_user_habit.user_id = 999  # Different user
        other_user_habit.name = "Other User Habit"
        mock_habit_repo.get_by_id = AsyncMock(return_value=other_user_habit)
        
        response = client_no_auth.post(
            "/v1/habits/999/complete",
            headers={"X-API-Key": "hrk_user1_key"},
            json={}
        )
        
        # Should return 403 (Forbidden) because habit belongs to different user
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "NOT_OWNER"
