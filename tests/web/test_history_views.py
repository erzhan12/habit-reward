"""Tests for history and streaks views."""

from unittest.mock import AsyncMock, patch

from src.services.streak_service import StreakState
from tests.web.conftest import INERTIA_HEADERS, _inertia_props, _mock_habit


class TestStreaks:
    """Streaks view tests."""

    @patch("src.web.views.streaks.streak_service")
    @patch("src.web.views.streaks.habit_log_repository")
    @patch("src.web.views.streaks.habit_service")
    def test_streaks_returns_200(self, mock_hs, mock_repo, mock_ss, auth_client):
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_total_count_by_user = AsyncMock(return_value=0)
        mock_repo.get_habit_streak_stats = AsyncMock(return_value=[])
        response = auth_client.get("/streaks/")
        assert response.status_code == 200


    @patch("src.web.views.streaks.streak_service")
    @patch("src.web.views.streaks.habit_log_repository")
    @patch("src.web.views.streaks.habit_service")
    def test_streaks_use_batch_states_with_freeze_count(self, mock_hs, mock_repo, mock_ss, auth_client):
        mock_hs.get_all_active_habits.return_value = [_mock_habit(id=1), _mock_habit(id=2)]
        mock_repo.get_total_count_by_user = AsyncMock(return_value=0)
        mock_repo.get_habit_streak_stats = AsyncMock(return_value=[])
        mock_ss.get_streak_states.return_value = {
            1: StreakState(3, 4, 1, None, False),
            2: StreakState(0, 1, 0, None, False),
        }

        _, props = _inertia_props(auth_client.get("/streaks/", **INERTIA_HEADERS))
        by_id = {h["id"]: h for h in props["habits"]}
        assert (by_id[1]["currentStreak"], by_id[1]["freezeCount"]) == (3, 1)
        assert (by_id[2]["currentStreak"], by_id[2]["freezeCount"]) == (0, 0)
        mock_ss.get_current_streak.assert_not_called()


class TestHistory:
    """History view tests."""

    @patch("src.web.views.history.habit_log_repository")
    @patch("src.web.views.history.habit_service")
    def test_history_returns_200(self, mock_hs, mock_repo, auth_client):
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_logs_in_daterange = AsyncMock(return_value=[])
        response = auth_client.get("/history/")
        assert response.status_code == 200

    @patch("src.web.views.history.habit_log_repository")
    @patch("src.web.views.history.habit_service")
    def test_history_custom_month(self, mock_hs, mock_repo, auth_client):
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_logs_in_daterange = AsyncMock(return_value=[])
        response = auth_client.get("/history/?month=2026-01")
        assert response.status_code == 200

    @patch("src.web.views.history.habit_log_repository")
    @patch("src.web.views.history.habit_service")
    def test_history_invalid_month_fallback(self, mock_hs, mock_repo, auth_client):
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_logs_in_daterange = AsyncMock(return_value=[])
        response = auth_client.get("/history/?month=invalid")
        assert response.status_code == 200

    @patch("src.web.views.history.habit_log_repository")
    @patch("src.web.views.history.habit_service")
    def test_history_habit_filter(self, mock_hs, mock_repo, auth_client):
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_logs_in_daterange = AsyncMock(return_value=[])
        response = auth_client.get("/history/?habit=1")
        assert response.status_code == 200
