"""Tests for dashboard views (habits, streaks, completions, reverts)."""

from datetime import date
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from tests.web.conftest import (
    INERTIA_HEADERS,
    _inertia_props,
    _mock_habit,
    _mock_habit_log,
    _mock_progress,
)


class TestDashboard:
    """Dashboard view tests (service layer mocked)."""

    @patch("src.web.views.dashboard.streak_service")
    @patch("src.web.views.dashboard.habit_log_repository")
    @patch("src.web.views.dashboard.habit_service")
    def test_dashboard_returns_200(self, mock_hs, mock_repo, mock_ss, auth_client):
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_todays_logs_by_user = AsyncMock(return_value=[])
        mock_ss.get_validated_streak_map.return_value = {}
        response = auth_client.get("/")
        assert response.status_code == 200

    @patch("src.web.views.dashboard.streak_service")
    @patch("src.web.views.dashboard.habit_log_repository")
    @patch("src.web.views.dashboard.habit_service")
    def test_dashboard_with_habits(self, mock_hs, mock_repo, mock_ss, auth_client):
        habit = _mock_habit()
        mock_hs.get_all_active_habits.return_value = [habit]
        mock_repo.get_todays_logs_by_user = AsyncMock(return_value=[])
        mock_ss.get_validated_streak_map.return_value = {1: 5}
        response = auth_client.get("/")
        assert response.status_code == 200

    @patch("src.web.views.dashboard.habit_service")
    def test_complete_habit_redirects(self, mock_hs, auth_client):
        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.process_habit_completion.return_value = MagicMock()
        response = auth_client.post("/habits/1/complete/")
        assert response.status_code == 302
        assert response.url == "/"

    @patch("src.web.views.dashboard.habit_service")
    def test_complete_habit_sets_reward_message(self, mock_hs, auth_client):
        result = MagicMock()
        result.got_reward = True
        result.reward = MagicMock(name="reward")
        result.reward.name = "Coffee"
        result.cumulative_progress = MagicMock()
        result.cumulative_progress.pieces_earned = 2
        result.cumulative_progress.get_pieces_required.return_value = 5

        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.process_habit_completion.return_value = result

        auth_client.post("/habits/1/complete/")

        flash = auth_client.session.get("_completion_flash")
        assert flash is not None
        assert flash["got_reward"] is True
        assert "Reward: Coffee (2/5)" in flash["text"]

    @patch("src.web.views.dashboard.habit_service")
    def test_complete_habit_sets_no_reward_message(self, mock_hs, auth_client):
        result = MagicMock()
        result.got_reward = False
        result.reward = None
        result.cumulative_progress = None

        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.process_habit_completion.return_value = result

        auth_client.post("/habits/1/complete/")

        flash = auth_client.session.get("_completion_flash")
        assert flash is not None
        assert flash["got_reward"] is False
        assert "No reward this time." in flash["text"]

    @patch("src.web.views.dashboard.habit_service")
    def test_complete_nonexistent_habit_redirects(self, mock_hs, auth_client):
        mock_hs.get_habit_by_id.return_value = None
        response = auth_client.post("/habits/99999/complete/")
        assert response.status_code == 302
        assert response.url == "/"

    @patch("src.web.views.dashboard.habit_service")
    def test_revert_habit_redirects(self, mock_hs, auth_client):
        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.revert_habit_completion.return_value = MagicMock()
        response = auth_client.post("/habits/1/revert/")
        assert response.status_code == 302
        assert response.url == "/"

    @patch("src.web.views.dashboard.messages")
    @patch("src.web.views.dashboard.habit_service")
    def test_revert_habit_sets_reward_removed_message(self, mock_hs, mock_messages, auth_client):
        result = MagicMock()
        result.reward_reverted = True
        result.reward_name = "Coffee"
        result.reward_progress = MagicMock()
        result.reward_progress.pieces_earned = 0
        result.reward_progress.get_pieces_required.return_value = 5

        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.revert_habit_completion.return_value = result

        auth_client.post("/habits/1/revert/")

        mock_messages.info.assert_called_once()
        assert "Reward removed: Coffee (0/5)" in str(mock_messages.info.call_args)
        mock_messages.success.assert_not_called()

    @patch("src.web.views.dashboard.messages")
    @patch("src.web.views.dashboard.habit_service")
    def test_revert_habit_sets_plain_success_when_no_reward(self, mock_hs, mock_messages, auth_client):
        result = MagicMock()
        result.reward_reverted = False
        result.reward_name = None
        result.reward_progress = None

        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.revert_habit_completion.return_value = result

        auth_client.post("/habits/1/revert/")

        mock_messages.success.assert_called_once()
        assert "Habit undone." in str(mock_messages.success.call_args)
        mock_messages.info.assert_not_called()

    @patch("src.web.views.dashboard.habit_service")
    def test_revert_nonexistent_habit_redirects(self, mock_hs, auth_client):
        mock_hs.get_habit_by_id.return_value = None
        response = auth_client.post("/habits/99999/revert/")
        assert response.status_code == 302
        assert response.url == "/"

    @patch("src.web.views.dashboard.habit_service")
    def test_revert_failure_still_redirects(self, mock_hs, auth_client):
        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.revert_habit_completion.side_effect = ValueError("No log found")
        response = auth_client.post("/habits/1/revert/")
        assert response.status_code == 302
        assert response.url == "/"

    @patch("src.web.views.dashboard.messages")
    @patch("src.web.views.dashboard.habit_service")
    def test_complete_habit_twice_second_raises_error_flash(self, mock_hs, mock_messages, auth_client):
        """Second completion attempt is rejected by service; both calls still redirect cleanly."""
        first_result = MagicMock()
        first_result.got_reward = False
        first_result.reward = None
        first_result.cumulative_progress = None

        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.process_habit_completion.side_effect = [
            first_result,
            ValueError("Habit already completed today"),
        ]

        response1 = auth_client.post("/habits/1/complete/")
        assert response1.status_code == 302

        response2 = auth_client.post("/habits/1/complete/")
        assert response2.status_code == 302

        assert mock_hs.process_habit_completion.call_count == 2
        mock_messages.error.assert_called_once()
        assert "already completed" in str(mock_messages.error.call_args).lower()

    @patch("src.web.views.dashboard.messages")
    @patch("src.web.views.dashboard._dashboard_action_ratelimited", return_value=True)
    def test_complete_habit_when_rate_limited_redirects_with_error(
        self, _mock_rl, mock_messages, auth_client
    ):
        """Rate-limited complete request redirects home with an error flash; service is not called."""
        response = auth_client.post("/habits/1/complete/")
        assert response.status_code == 302
        assert response.url == "/"
        mock_messages.error.assert_called_once()
        assert "Too many requests" in str(mock_messages.error.call_args)

    @patch("src.web.views.dashboard.messages")
    @patch("src.web.views.dashboard._dashboard_action_ratelimited", return_value=True)
    def test_revert_habit_when_rate_limited_redirects_with_error(
        self, _mock_rl, mock_messages, auth_client
    ):
        """Rate-limited revert request redirects home with an error flash; service is not called."""
        response = auth_client.post("/habits/1/revert/")
        assert response.status_code == 302
        assert response.url == "/"
        mock_messages.error.assert_called_once()
        assert "Too many requests" in str(mock_messages.error.call_args)


class TestPropStructure:
    """Verify prop shapes returned by Inertia views."""

    @patch("src.web.views.dashboard.streak_service")
    @patch("src.web.views.dashboard.habit_log_repository")
    @patch("src.web.views.dashboard.habit_service")
    def test_dashboard_prop_structure(self, mock_hs, mock_repo, mock_ss, auth_client):
        habit = _mock_habit(id=1, name="Running", weight=10)
        mock_hs.get_all_active_habits.return_value = [habit]
        log = _mock_habit_log(habit_id=1)
        mock_repo.get_todays_logs_by_user = AsyncMock(return_value=[log])
        mock_ss.get_validated_streak_map.return_value = {1: 3}

        response = auth_client.get("/", **INERTIA_HEADERS)
        component, props = _inertia_props(response)

        assert component == "Dashboard"
        assert len(props["habits"]) == 1
        h = props["habits"][0]
        assert "name" in h and "streak" in h and "completedToday" in h
        assert h["name"] == "Running"
        assert h["streak"] == 3
        assert h["completedToday"] is True
        assert props["stats"]["completedToday"] == 1
        assert props["stats"]["totalToday"] == 1

    @patch("src.web.views.rewards.reward_service")
    def test_rewards_prop_structure(self, mock_rs, auth_client):
        progress = _mock_progress(pieces_earned=2, pieces_required=5, status_name="PENDING")
        mock_rs.get_user_reward_progress.return_value = [progress]
        mock_rs.get_claimed_rewards.return_value = []

        response = auth_client.get("/rewards/", **INERTIA_HEADERS)
        component, props = _inertia_props(response)

        assert component == "Rewards"
        assert len(props["rewards"]) == 1
        r = props["rewards"][0]
        assert r["piecesEarned"] == 2
        assert r["piecesRequired"] == 5
        assert r["status"] == "PENDING"

    @patch("src.web.views.history.habit_log_repository")
    @patch("src.web.views.history.habit_service")
    def test_history_prop_structure(self, mock_hs, mock_repo, auth_client):
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_logs_in_daterange = AsyncMock(return_value=[])

        response = auth_client.get("/history/", **INERTIA_HEADERS)
        component, props = _inertia_props(response)

        assert component == "History"
        assert "currentMonth" in props
        assert "completions" in props
        assert "userToday" in props


class TestErrorFlashMessages:
    """Verify error flash messages are set on failure paths."""

    @patch("src.web.views.dashboard.messages")
    @patch("src.web.views.dashboard.habit_service")
    def test_complete_habit_error_sets_flash(self, mock_hs, mock_messages, auth_client):
        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.process_habit_completion.side_effect = ValueError("Already completed")

        auth_client.post("/habits/1/complete/")

        mock_messages.error.assert_called_once()
        assert "Already completed" in str(mock_messages.error.call_args)

    @patch("src.web.views.dashboard.messages")
    @patch("src.web.views.dashboard.habit_service")
    def test_revert_habit_error_sets_flash(self, mock_hs, mock_messages, auth_client):
        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.revert_habit_completion.side_effect = ValueError("No log found")

        auth_client.post("/habits/1/revert/")

        mock_messages.error.assert_called_once()
        assert "No log found" in str(mock_messages.error.call_args)

    @patch("src.web.views.rewards.reward_repository")
    @patch("src.web.views.rewards.messages")
    @patch("src.web.views.rewards.reward_service")
    def test_claim_non_achieved_shows_error_message(self, mock_rs, mock_messages, mock_repo, auth_client, user):
        reward = MagicMock()
        reward.user_id = user.id
        mock_repo.get_by_id = AsyncMock(return_value=reward)
        mock_rs.mark_reward_claimed.side_effect = ValueError("Not achieved yet")

        auth_client.post("/rewards/1/claim/")

        mock_messages.error.assert_called_once()
        assert "Not achieved yet" in str(mock_messages.error.call_args)


class TestDashboardTimezone:
    """Dashboard must use user.timezone when computing today's date for log queries."""

    @pytest.mark.parametrize("tz", ["UTC", "America/New_York", "Asia/Tokyo"])
    @patch("src.web.views.dashboard.get_user_today")
    @patch("src.web.views.dashboard.streak_service")
    @patch("src.web.views.dashboard.habit_log_repository")
    @patch("src.web.views.dashboard.habit_service")
    def test_dashboard_uses_user_timezone(
        self, mock_hs, mock_repo, mock_ss, mock_today, auth_client, user, tz
    ):
        """Dashboard passes user.timezone to get_user_today and forwards the returned
        date to habit_log_repository so that habit completion is scoped to the correct
        calendar day for every timezone.
        """
        fake_date = date(2026, 1, 15)
        mock_today.return_value = fake_date
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_todays_logs_by_user = AsyncMock(return_value=[])
        mock_ss.get_validated_streak_map.return_value = {}

        user.timezone = tz
        user.save()

        response = auth_client.get("/")

        assert response.status_code == 200
        mock_today.assert_called_once_with(tz)
        mock_repo.get_todays_logs_by_user.assert_called_once_with(
            ANY, target_date=fake_date
        )
