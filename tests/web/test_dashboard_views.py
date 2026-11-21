"""Tests for dashboard views (habits, streaks, completions, reverts)."""

from datetime import date
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from src.services.streak_service import StreakState
from tests.web.conftest import (
    INERTIA_HEADERS,
    _inertia_props,
    _mock_habit,
    _mock_habit_log,
    _mock_progress,
)


def _state(streak, **freeze):
    """StreakState as get_streak_states returns it (streak 0 = broken)."""
    return StreakState(
        streak=streak,
        next_streak=streak + 1 if streak > 0 else 1,
        freeze_count=freeze.get("freeze_count", 0),
        freeze_used_for=freeze.get("freeze_used_for"),
        freeze_at_risk=freeze.get("freeze_at_risk", False),
    )


class TestDashboard:
    """Dashboard view tests (service layer mocked)."""

    @patch("src.web.views.dashboard.streak_service")
    @patch("src.web.views.dashboard.habit_log_repository")
    @patch("src.web.views.dashboard.habit_service")
    def test_dashboard_returns_200(self, mock_hs, mock_repo, mock_ss, auth_client):
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_todays_logs_by_user = AsyncMock(return_value=[])
        mock_ss.get_streak_states.return_value = {}
        response = auth_client.get("/")
        assert response.status_code == 200

    @patch("src.web.views.dashboard.streak_service")
    @patch("src.web.views.dashboard.habit_log_repository")
    @patch("src.web.views.dashboard.habit_service")
    def test_dashboard_with_habits(self, mock_hs, mock_repo, mock_ss, auth_client):
        habit = _mock_habit()
        mock_hs.get_all_active_habits.return_value = [habit]
        mock_repo.get_todays_logs_by_user = AsyncMock(return_value=[])
        mock_ss.get_streak_states.return_value = {1: _state(5)}
        response = auth_client.get("/")
        assert response.status_code == 200

    @patch("src.web.views.dashboard.habit_service")
    def test_complete_habit_redirects(self, mock_hs, auth_client):
        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.process_habit_completion.return_value = MagicMock(
            got_reward=False, reward=None, cumulative_progress=None
        )
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
    def test_complete_habit_freeze_flash(self, mock_hs, auth_client):
        """Feature 0048: freeze fields are JSON-safe and the text names the covered day."""
        from datetime import date

        from src.models.habit_completion_result import HabitCompletionResult

        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.process_habit_completion.return_value = HabitCompletionResult(
            habit_confirmed=True, habit_name="Walk", streak_count=4, total_weight_applied=70.0,
            freeze_used=True, freeze_won=True, freeze_covered_date=date(2026, 11, 17),
        )
        auth_client.post("/habits/1/complete/")

        flash = auth_client.session.get("_completion_flash")
        assert flash["freeze_used"] is True and flash["freeze_won"] is True
        assert flash["freeze_burned"] is False
        assert flash["freeze_covered_date"] == "2026-11-17"
        assert "Freeze covered 17 Nov" in flash["text"]
        assert "You earned a streak freeze!" in flash["text"]

    @patch("src.web.views.dashboard.habit_service")
    def test_complete_habit_freeze_burned_flash(self, mock_hs, auth_client):
        from datetime import date

        from src.models.habit_completion_result import HabitCompletionResult

        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.process_habit_completion.return_value = HabitCompletionResult(
            habit_confirmed=True, habit_name="Walk", streak_count=1, total_weight_applied=80.0,
            freeze_burned=True, freeze_covered_date=date(2026, 11, 17),
        )
        auth_client.post("/habits/1/complete/")

        flash = auth_client.session.get("_completion_flash")
        assert flash["freeze_burned"] is True
        assert "used for 17 Nov" in flash["text"] and "streak reset" in flash["text"]

    @patch("src.web.views.dashboard.habit_service")
    def test_complete_habit_mock_result_has_no_freeze_text(self, mock_hs, auth_client):
        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.process_habit_completion.return_value = MagicMock(
            got_reward=False, reward=None, cumulative_progress=None
        )
        auth_client.post("/habits/1/complete/")

        flash = auth_client.session.get("_completion_flash")
        assert "❄️" not in flash["text"]
        assert flash["freeze_won"] is False and flash["freeze_covered_date"] is None

    @patch("src.web.views.dashboard.messages")
    @patch("src.web.views.dashboard.habit_service")
    def test_revert_habit_mentions_revoked_freeze(self, mock_hs, mock_messages, auth_client):
        from src.models.habit_revert_result import HabitRevertResult

        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.revert_habit_completion.return_value = HabitRevertResult(
            habit_id=1, habit_name="Walk", freeze_revoked=True
        )
        auth_client.post("/habits/1/revert/")

        assert "Habit undone. Earned freeze removed." in str(mock_messages.success.call_args)

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
    def test_complete_habit_busy_shows_retry_message(self, mock_hs, mock_messages, auth_client):
        """Feature 0048: ServiceBusyError becomes a "try again" flash, not a 500."""
        from src.services.transactions import ServiceBusyError

        mock_hs.get_habit_by_id.return_value = _mock_habit()
        mock_hs.process_habit_completion.side_effect = ServiceBusyError("busy")

        response = auth_client.post("/habits/1/complete/")

        assert response.status_code == 302
        assert "try again" in str(mock_messages.error.call_args).lower()

    @patch("src.web.views.dashboard.messages")
    @patch("src.web.views.dashboard.habit_service")
    def test_revert_habit_busy_shows_retry_message(self, mock_hs, mock_messages, auth_client):
        from src.services.transactions import ServiceBusyError

        mock_hs.revert_habit_completion.side_effect = ServiceBusyError("busy")
        response = auth_client.post("/habits/1/revert/")
        assert response.status_code == 302
        assert "try again" in str(mock_messages.error.call_args).lower()

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
        mock_ss.get_streak_states.return_value = {1: _state(3)}

        response = auth_client.get("/", **INERTIA_HEADERS)
        component, props = _inertia_props(response)

        assert component == "Dashboard"
        assert len(props["habits"]) == 1
        h = props["habits"][0]
        assert "name" in h and "streak" in h and "completedToday" in h
        assert h["name"] == "Running"
        assert h["streak"] == 3
        assert h["completedToday"] is True
        assert h["todayResult"] == {"gotReward": False, "rewardName": None}
        assert props["stats"]["completedToday"] == 1
        assert props["stats"]["totalToday"] == 1

    @patch("src.web.views.dashboard.streak_service")
    @patch("src.web.views.dashboard.habit_log_repository")
    @patch("src.web.views.dashboard.habit_service")
    def test_dashboard_includes_today_result_for_completed_habit(
        self, mock_hs, mock_repo, mock_ss, auth_client
    ):
        habit = _mock_habit(id=1, name="Running", weight=10)
        mock_hs.get_all_active_habits.return_value = [habit]
        log = _mock_habit_log(habit_id=1, got_reward=True, reward_name="Coffee")
        mock_repo.get_todays_logs_by_user = AsyncMock(return_value=[log])
        mock_ss.get_streak_states.return_value = {1: _state(3)}

        response = auth_client.get("/", **INERTIA_HEADERS)
        _, props = _inertia_props(response)

        h = props["habits"][0]
        assert h["todayResult"] == {"gotReward": True, "rewardName": "Coffee"}

    @pytest.mark.parametrize(
        "streak,weight,expected",
        [(0, 0, 20), (0, 30, 20), (1, 0, 25), (3, 30, 33), (6, 10, 40), (40, 0, 50)],
    )
    @patch("src.web.views.dashboard.streak_service")
    @patch("src.web.views.dashboard.habit_log_repository")
    @patch("src.web.views.dashboard.habit_service")
    def test_reward_chance_is_for_next_completion(
        self, mock_hs, mock_repo, mock_ss, auth_client, streak, weight, expected
    ):
        """Not completed today: chance of the next completion (streak + 1, or 1 if broken).
        Weight and user.no_reward_probability play no part (feature 0048)."""
        mock_hs.get_all_active_habits.return_value = [_mock_habit(id=1, weight=weight)]
        mock_repo.get_todays_logs_by_user = AsyncMock(return_value=[])
        mock_ss.get_streak_states.return_value = {1: _state(streak)}

        _, props = _inertia_props(auth_client.get("/", **INERTIA_HEADERS))
        assert props["habits"][0]["rewardChance"] == expected

    @patch("src.web.views.dashboard.streak_service")
    @patch("src.web.views.dashboard.habit_log_repository")
    @patch("src.web.views.dashboard.habit_service")
    def test_reward_chance_completed_today_uses_stored_snapshot(
        self, mock_hs, mock_repo, mock_ss, auth_client
    ):
        """Completed today: show the chance that actually applied (100 - stored no-reward %)."""
        mock_hs.get_all_active_habits.return_value = [_mock_habit(id=1)]
        log = _mock_habit_log(habit_id=1, total_weight_applied=13.0)  # pre-deploy log: 87%
        mock_repo.get_todays_logs_by_user = AsyncMock(return_value=[log])
        mock_ss.get_streak_states.return_value = {1: _state(1)}

        _, props = _inertia_props(auth_client.get("/", **INERTIA_HEADERS))
        assert props["habits"][0]["rewardChance"] == 87

    @patch("src.web.views.dashboard.streak_service")
    @patch("src.web.views.dashboard.habit_log_repository")
    @patch("src.web.views.dashboard.habit_service")
    def test_dashboard_freeze_props(self, mock_hs, mock_repo, mock_ss, auth_client):
        """Freeze fields come from get_streak_states (feature 0048 §7)."""
        mock_hs.get_all_active_habits.return_value = [_mock_habit(id=1), _mock_habit(id=2)]
        mock_repo.get_todays_logs_by_user = AsyncMock(return_value=[])
        mock_ss.get_streak_states.return_value = {
            1: _state(4, freeze_used_for=date(2026, 11, 17)),
            2: _state(2, freeze_count=1, freeze_at_risk=True),
        }

        _, props = _inertia_props(auth_client.get("/", **INERTIA_HEADERS))
        by_id = {h["id"]: h for h in props["habits"]}
        assert (by_id[1]["freezeCount"], by_id[1]["freezeUsedFor"], by_id[1]["freezeAtRisk"]) == (0, "2026-11-17", False)
        assert (by_id[2]["freezeCount"], by_id[2]["freezeUsedFor"], by_id[2]["freezeAtRisk"]) == (1, None, True)
        assert (by_id[1]["rewardChance"], by_id[2]["rewardChance"]) == (36, 29)

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
        mock_ss.get_streak_states.return_value = {}

        user.timezone = tz
        user.save()

        response = auth_client.get("/")

        assert response.status_code == 200
        mock_today.assert_called_once_with(tz)
        mock_repo.get_todays_logs_by_user.assert_called_once_with(
            ANY, target_date=fake_date
        )
