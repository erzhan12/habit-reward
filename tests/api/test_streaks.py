"""Tests for streak endpoints."""

from datetime import date
from unittest.mock import patch, AsyncMock, MagicMock


class TestGetAllStreaks:
    """Test GET /v1/streaks endpoint."""

    @patch("src.api.v1.routers.streaks.streak_service")
    @patch("src.api.v1.routers.streaks.habit_repository")
    def test_get_all_streaks(
        self, mock_habit_repo, mock_streak_service, client, mock_user, mock_habit
    ):
        """Test getting streaks for all habits."""
        mock_habit_repo.get_all_active = AsyncMock(return_value=[mock_habit])
        mock_streak_service.get_current_streak = AsyncMock(return_value=5)
        mock_streak_service.get_last_completed_date = AsyncMock(
            return_value=date.today()
        )

        response = client.get("/v1/streaks")

        assert response.status_code == 200
        data = response.json()
        assert "streaks" in data
        assert "total" in data
        assert data["total"] == 1
        assert len(data["streaks"]) == 1
        assert data["streaks"][0]["habit_id"] == mock_habit.id
        assert data["streaks"][0]["habit_name"] == mock_habit.name
        assert data["streaks"][0]["current_streak"] == 5

    @patch("src.api.v1.routers.streaks.streak_service")
    @patch("src.api.v1.routers.streaks.habit_repository")
    def test_get_all_streaks_no_habits(
        self, mock_habit_repo, mock_streak_service, client
    ):
        """Test getting streaks when user has no habits."""
        mock_habit_repo.get_all_active = AsyncMock(return_value=[])

        response = client.get("/v1/streaks")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["streaks"]) == 0

    @patch("src.api.v1.routers.streaks.streak_service")
    @patch("src.api.v1.routers.streaks.habit_repository")
    def test_get_all_streaks_multiple_habits(
        self, mock_habit_repo, mock_streak_service, client, mock_habit
    ):
        """Test getting streaks for multiple habits."""
        habit2 = MagicMock()
        habit2.id = 2
        habit2.name = "Evening Meditation"
        habit2.user_id = mock_habit.user_id

        mock_habit_repo.get_all_active = AsyncMock(return_value=[mock_habit, habit2])

        # Different streaks for different habits
        def get_streak_side_effect(user_id, habit_id):
            return 5 if habit_id == 1 else 10

        mock_streak_service.get_current_streak = AsyncMock(
            side_effect=get_streak_side_effect
        )
        mock_streak_service.get_last_completed_date = AsyncMock(
            return_value=date.today()
        )

        response = client.get("/v1/streaks")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["streaks"]) == 2

    @patch("src.api.v1.routers.streaks.streak_service")
    @patch("src.api.v1.routers.streaks.habit_repository")
    def test_get_all_streaks_no_completions(
        self, mock_habit_repo, mock_streak_service, client, mock_habit
    ):
        """Test getting streaks for habits with no completions."""
        mock_habit_repo.get_all_active = AsyncMock(return_value=[mock_habit])
        mock_streak_service.get_current_streak = AsyncMock(return_value=0)
        mock_streak_service.get_last_completed_date = AsyncMock(return_value=None)

        response = client.get("/v1/streaks")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["streaks"][0]["current_streak"] == 0
        assert data["streaks"][0]["last_completed"] is None

    def test_get_all_streaks_requires_auth(self, client_no_auth):
        """Test that endpoint requires authentication."""
        response = client_no_auth.get("/v1/streaks")

        assert response.status_code == 401


class TestGetHabitStreak:
    """Test GET /v1/streaks/{habit_id} endpoint."""

    @patch("src.api.v1.routers.streaks.habit_log_repository")
    @patch("src.api.v1.routers.streaks.streak_service")
    @patch("src.api.v1.routers.streaks.habit_repository")
    def test_get_habit_streak_success(
        self,
        mock_habit_repo,
        mock_streak_service,
        mock_log_repo,
        client,
        mock_user,
        mock_habit,
        mock_habit_log,
    ):
        """Test getting detailed streak for a specific habit."""
        mock_habit_repo.get_by_id = AsyncMock(return_value=mock_habit)
        mock_streak_service.get_current_streak = AsyncMock(return_value=5)
        mock_streak_service.get_last_completed_date = AsyncMock(
            return_value=date.today()
        )

        # Mock habit logs with streak counts
        log1 = MagicMock()
        log1.habit_id = mock_habit.id
        log1.streak_count = 10
        log2 = MagicMock()
        log2.habit_id = mock_habit.id
        log2.streak_count = 5

        mock_log_repo.get_logs_by_user = AsyncMock(return_value=[log1, log2])

        response = client.get(f"/v1/streaks/{mock_habit.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["habit_id"] == mock_habit.id
        assert data["habit_name"] == mock_habit.name
        assert data["current_streak"] == 5
        assert data["longest_streak"] == 10  # Max of all streak_counts
        assert "last_completed" in data

    @patch("src.api.v1.routers.streaks.habit_repository")
    def test_get_habit_streak_not_found(self, mock_repo, client):
        """Test getting streak for non-existent habit."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        response = client.get("/v1/streaks/999")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "HABIT_NOT_FOUND"

    @patch("src.api.v1.routers.streaks.habit_repository")
    def test_get_habit_streak_forbidden(self, mock_repo, client, mock_habit):
        """Test getting streak for habit belonging to another user."""
        mock_habit.user_id = 999  # Different user
        mock_repo.get_by_id = AsyncMock(return_value=mock_habit)

        response = client.get(f"/v1/streaks/{mock_habit.id}")

        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "NOT_OWNER"

    @patch("src.api.v1.routers.streaks.habit_log_repository")
    @patch("src.api.v1.routers.streaks.streak_service")
    @patch("src.api.v1.routers.streaks.habit_repository")
    def test_get_habit_streak_no_completions(
        self, mock_habit_repo, mock_streak_service, mock_log_repo, client, mock_habit
    ):
        """Test getting streak for habit with no completions."""
        mock_habit_repo.get_by_id = AsyncMock(return_value=mock_habit)
        mock_streak_service.get_current_streak = AsyncMock(return_value=0)
        mock_streak_service.get_last_completed_date = AsyncMock(return_value=None)
        mock_log_repo.get_logs_by_user = AsyncMock(return_value=[])

        response = client.get(f"/v1/streaks/{mock_habit.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["current_streak"] == 0
        assert data["longest_streak"] == 0
        assert data["last_completed"] is None

    @patch("src.api.v1.routers.streaks.habit_log_repository")
    @patch("src.api.v1.routers.streaks.streak_service")
    @patch("src.api.v1.routers.streaks.habit_repository")
    def test_get_habit_streak_with_mixed_logs(
        self, mock_habit_repo, mock_streak_service, mock_log_repo, client, mock_habit
    ):
        """Test that longest streak calculation only considers the specific habit."""
        mock_habit_repo.get_by_id = AsyncMock(return_value=mock_habit)
        mock_streak_service.get_current_streak = AsyncMock(return_value=3)
        mock_streak_service.get_last_completed_date = AsyncMock(
            return_value=date.today()
        )

        # Logs for multiple habits - only habit 1 should be counted
        log1 = MagicMock()
        log1.habit_id = 1
        log1.streak_count = 7
        log2 = MagicMock()
        log2.habit_id = 2  # Different habit
        log2.streak_count = 20
        log3 = MagicMock()
        log3.habit_id = 1
        log3.streak_count = 5

        mock_log_repo.get_logs_by_user = AsyncMock(return_value=[log1, log2, log3])

        response = client.get(f"/v1/streaks/{mock_habit.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["current_streak"] == 3
        assert data["longest_streak"] == 7  # Max for habit 1 only, not 20

    def test_get_habit_streak_requires_auth(self, client_no_auth):
        """Test that endpoint requires authentication."""
        response = client_no_auth.get("/v1/streaks/1")

        assert response.status_code == 401
