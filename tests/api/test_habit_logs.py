"""Tests for habit log endpoints."""

from datetime import date, timedelta
from unittest.mock import patch, AsyncMock, MagicMock


class TestListHabitLogs:
    """Test GET /v1/habit-logs endpoint."""

    @patch("src.api.v1.routers.habit_logs.habit_log_repository")
    def test_list_habit_logs(self, mock_repo, client, mock_user, mock_habit_log):
        """Test listing habit logs."""
        mock_repo.get_logs_by_user = AsyncMock(return_value=[mock_habit_log])

        response = client.get("/v1/habit-logs")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["logs"]) == 1
        assert data["logs"][0]["id"] == mock_habit_log.id

    @patch("src.api.v1.routers.habit_logs.habit_log_repository")
    def test_list_habit_logs_with_date_range(self, mock_repo, client, mock_habit_log):
        """Test listing logs with date range filter."""
        mock_repo.get_logs_by_user = AsyncMock(return_value=[mock_habit_log])

        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        response = client.get(
            f"/v1/habit-logs?start_date={start_date}&end_date={end_date}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data

    @patch("src.api.v1.routers.habit_logs.habit_repository")
    @patch("src.api.v1.routers.habit_logs.habit_log_repository")
    def test_list_habit_logs_filter_by_habit(
        self,
        mock_log_repo,
        mock_habit_repo,
        client,
        mock_user,
        mock_habit,
        mock_habit_log,
    ):
        """Test listing logs filtered by habit ID."""
        mock_habit_repo.get_by_id = AsyncMock(return_value=mock_habit)
        mock_log_repo.get_logs_for_habit_in_daterange = AsyncMock(
            return_value=[mock_habit_log]
        )

        response = client.get(f"/v1/habit-logs?habit_id={mock_habit.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 1

    @patch("src.api.v1.routers.habit_logs.habit_repository")
    def test_list_habit_logs_habit_not_found(self, mock_repo, client):
        """Test listing logs for non-existent habit."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        response = client.get("/v1/habit-logs?habit_id=999")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "HABIT_NOT_FOUND"

    @patch("src.api.v1.routers.habit_logs.habit_repository")
    def test_list_habit_logs_forbidden(self, mock_repo, client, mock_habit):
        """Test listing logs for habit belonging to another user."""
        mock_habit.user_id = 999  # Different user
        mock_repo.get_by_id = AsyncMock(return_value=mock_habit)

        response = client.get(f"/v1/habit-logs?habit_id={mock_habit.id}")

        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "NOT_OWNER"

    @patch("src.api.v1.routers.habit_logs.habit_log_repository")
    def test_list_habit_logs_pagination(self, mock_repo, client, mock_habit_log):
        """Test pagination with limit and offset."""
        mock_repo.get_logs_by_user = AsyncMock(return_value=[mock_habit_log] * 5)

        response = client.get("/v1/habit-logs?limit=2&offset=1")

        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) <= 2


class TestGetHabitLog:
    """Test GET /v1/habit-logs/{log_id} endpoint."""

    @patch("src.api.v1.routers.habit_logs.habit_log_repository")
    def test_get_habit_log_success(self, mock_repo, client, mock_user, mock_habit_log):
        """Test getting a single habit log."""
        mock_repo.get_by_id = AsyncMock(return_value=mock_habit_log)

        response = client.get(f"/v1/habit-logs/{mock_habit_log.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == mock_habit_log.id
        assert data["habit_id"] == mock_habit_log.habit_id
        assert data["habit_name"] == mock_habit_log.habit.name

    @patch("src.api.v1.routers.habit_logs.habit_log_repository")
    def test_get_habit_log_not_found(self, mock_repo, client):
        """Test getting non-existent habit log."""
        mock_repo.get_by_id = AsyncMock(return_value=None)

        response = client.get("/v1/habit-logs/999")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "LOG_NOT_FOUND"

    @patch("src.api.v1.routers.habit_logs.habit_log_repository")
    def test_get_habit_log_forbidden(self, mock_repo, client, mock_habit_log):
        """Test getting log belonging to another user."""
        mock_habit_log.user_id = 999  # Different user
        mock_repo.get_by_id = AsyncMock(return_value=mock_habit_log)

        response = client.get(f"/v1/habit-logs/{mock_habit_log.id}")

        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "NOT_OWNER"


class TestRevertHabitLog:
    """Test DELETE /v1/habit-logs/{log_id} endpoint."""

    @patch("src.api.v1.routers.habit_logs.habit_service")
    def test_revert_habit_log_success(
        self, mock_service, client, mock_user, mock_habit_log
    ):
        """Test successfully reverting a habit log."""
        # Mock revert result
        result = MagicMock()
        result.success = True
        result.habit_name = "Morning Exercise"
        result.reward_reverted = False
        result.reward_name = None
        mock_service.revert_habit_completion_by_log_id = AsyncMock(return_value=result)

        response = client.delete(f"/v1/habit-logs/{mock_habit_log.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["habit_name"] == "Morning Exercise"
        assert data["reward_reverted"] is False
        mock_service.revert_habit_completion_by_log_id.assert_called_once_with(
            user_id=mock_user.id, log_id=mock_habit_log.id
        )

    @patch("src.api.v1.routers.habit_logs.habit_service")
    def test_revert_habit_log_with_reward(self, mock_service, client, mock_habit_log):
        """Test reverting a habit log that had a reward."""
        # Mock revert result with reward
        result = MagicMock()
        result.success = True
        result.habit_name = "Morning Exercise"
        result.reward_reverted = True
        result.reward_name = "Coffee"
        mock_service.revert_habit_completion_by_log_id = AsyncMock(return_value=result)

        response = client.delete(f"/v1/habit-logs/{mock_habit_log.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["reward_reverted"] is True
        assert data["reward_name"] == "Coffee"

    @patch("src.api.v1.routers.habit_logs.habit_service")
    def test_revert_habit_log_not_found(self, mock_service, client):
        """Test reverting non-existent habit log."""
        mock_service.revert_habit_completion_by_log_id = AsyncMock(
            side_effect=ValueError("Habit log 999 not found")
        )

        response = client.delete("/v1/habit-logs/999")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "LOG_NOT_FOUND"

    @patch("src.api.v1.routers.habit_logs.habit_service")
    def test_revert_habit_log_forbidden(self, mock_service, client):
        """Test reverting log belonging to another user."""
        mock_service.revert_habit_completion_by_log_id = AsyncMock(
            side_effect=ValueError("Access denied")
        )

        response = client.delete("/v1/habit-logs/1")

        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "NOT_OWNER"

    def test_revert_habit_log_requires_auth(self, client_no_auth):
        """Test that revert requires authentication."""
        response = client_no_auth.delete("/v1/habit-logs/1")

        assert response.status_code == 401
