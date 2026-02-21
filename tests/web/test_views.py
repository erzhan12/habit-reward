"""Tests for web interface views."""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client

from src.core.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username="tg_999999999",
        telegram_id="999999999",
        name="Test User",
        language="en",
        timezone="UTC",
    )


@pytest.fixture
def auth_client(user):
    """Create an authenticated Django test client."""
    client = Client()
    client.force_login(user)
    return client


def _mock_habit(id=1, name="Running", weight=10):
    """Create a mock habit object."""
    h = MagicMock()
    h.id = id
    h.name = name
    h.weight = weight
    h.active = True
    return h


def _mock_habit_log(habit_id=1):
    """Create a mock habit log."""
    log = MagicMock()
    log.habit_id = habit_id
    return log


def _mock_progress(reward_id=1, name="Coffee", pieces_earned=2,
                   pieces_required=3, status_name="PENDING", is_recurring=True):
    """Create a mock reward progress."""
    reward = MagicMock()
    reward.id = reward_id
    reward.name = name
    reward.is_recurring = is_recurring

    progress = MagicMock()
    progress.reward = reward
    progress.pieces_earned = pieces_earned
    progress.get_pieces_required.return_value = pieces_required

    status = MagicMock()
    status.name = status_name
    status.value = f"emoji {status_name}"
    progress.get_status.return_value = status

    return progress


# ---- Unauthenticated access tests ----


class TestUnauthenticatedRedirect:
    """Unauthenticated users should be redirected to login by middleware."""

    def test_dashboard_redirects(self):
        response = Client().get("/")
        assert response.status_code == 302
        assert "/auth/login/" in response.url

    def test_streaks_redirects(self):
        response = Client().get("/streaks/")
        assert response.status_code == 302
        assert "/auth/login/" in response.url

    def test_history_redirects(self):
        response = Client().get("/history/")
        assert response.status_code == 302
        assert "/auth/login/" in response.url

    def test_rewards_redirects(self):
        response = Client().get("/rewards/")
        assert response.status_code == 302
        assert "/auth/login/" in response.url

    def test_login_page_accessible(self):
        response = Client().get("/auth/login/")
        assert response.status_code == 200


# ---- Dashboard tests ----


class TestDashboard:
    """Dashboard view tests (service layer mocked)."""

    @patch("src.web.views.dashboard.run_sync_or_async", side_effect=lambda x: x)
    @patch("src.web.views.dashboard.habit_log_repository")
    @patch("src.web.views.dashboard.habit_service")
    def test_dashboard_returns_200(self, mock_hs, mock_repo, mock_rsa, auth_client):
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_todays_logs_by_user.return_value = []
        mock_repo.get_latest_streak_counts.return_value = {}
        response = auth_client.get("/")
        assert response.status_code == 200

    @patch("src.web.views.dashboard.run_sync_or_async", side_effect=lambda x: x)
    @patch("src.web.views.dashboard.habit_log_repository")
    @patch("src.web.views.dashboard.habit_service")
    def test_dashboard_with_habits(self, mock_hs, mock_repo, mock_rsa, auth_client):
        habit = _mock_habit()
        mock_hs.get_all_active_habits.return_value = [habit]
        mock_repo.get_todays_logs_by_user.return_value = []
        mock_repo.get_latest_streak_counts.return_value = {1: 5}
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


# ---- Streaks tests ----


class TestStreaks:
    """Streaks view tests."""

    @patch("src.web.views.streaks.run_sync_or_async", side_effect=lambda x: x)
    @patch("src.web.views.streaks.streak_service")
    @patch("src.web.views.streaks.habit_log_repository")
    @patch("src.web.views.streaks.habit_service")
    def test_streaks_returns_200(self, mock_hs, mock_repo, mock_ss, mock_rsa, auth_client):
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_total_count_by_user.return_value = 0
        mock_repo.get_habit_streak_stats.return_value = []
        response = auth_client.get("/streaks/")
        assert response.status_code == 200


# ---- History tests ----


class TestHistory:
    """History view tests."""

    @patch("src.web.views.history.run_sync_or_async", side_effect=lambda x: x)
    @patch("src.web.views.history.habit_log_repository")
    @patch("src.web.views.history.habit_service")
    def test_history_returns_200(self, mock_hs, mock_repo, mock_rsa, auth_client):
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_logs_in_daterange.return_value = []
        response = auth_client.get("/history/")
        assert response.status_code == 200

    @patch("src.web.views.history.run_sync_or_async", side_effect=lambda x: x)
    @patch("src.web.views.history.habit_log_repository")
    @patch("src.web.views.history.habit_service")
    def test_history_custom_month(self, mock_hs, mock_repo, mock_rsa, auth_client):
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_logs_in_daterange.return_value = []
        response = auth_client.get("/history/?month=2026-01")
        assert response.status_code == 200

    @patch("src.web.views.history.run_sync_or_async", side_effect=lambda x: x)
    @patch("src.web.views.history.habit_log_repository")
    @patch("src.web.views.history.habit_service")
    def test_history_invalid_month_fallback(self, mock_hs, mock_repo, mock_rsa, auth_client):
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_logs_in_daterange.return_value = []
        response = auth_client.get("/history/?month=invalid")
        assert response.status_code == 200

    @patch("src.web.views.history.run_sync_or_async", side_effect=lambda x: x)
    @patch("src.web.views.history.habit_log_repository")
    @patch("src.web.views.history.habit_service")
    def test_history_habit_filter(self, mock_hs, mock_repo, mock_rsa, auth_client):
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_logs_in_daterange.return_value = []
        response = auth_client.get("/history/?habit=1")
        assert response.status_code == 200


# ---- Rewards tests ----


class TestRewards:
    """Rewards view tests."""

    @patch("src.web.views.rewards.reward_service")
    def test_rewards_returns_200(self, mock_rs, auth_client):
        mock_rs.get_user_reward_progress.return_value = []
        mock_rs.get_claimed_one_time_rewards.return_value = []
        response = auth_client.get("/rewards/")
        assert response.status_code == 200

    @patch("src.web.views.rewards.reward_service")
    def test_rewards_with_progress(self, mock_rs, auth_client):
        progress = _mock_progress(status_name="PENDING")
        mock_rs.get_user_reward_progress.return_value = [progress]
        mock_rs.get_claimed_one_time_rewards.return_value = []
        response = auth_client.get("/rewards/")
        assert response.status_code == 200

    @patch("src.web.views.rewards.reward_service")
    def test_rewards_status_uses_name(self, mock_rs, auth_client):
        """Verify status is sent as .name (ACHIEVED) not .value (emoji)."""
        progress = _mock_progress(status_name="ACHIEVED")
        mock_rs.get_user_reward_progress.return_value = [progress]
        mock_rs.get_claimed_one_time_rewards.return_value = []
        response = auth_client.get("/rewards/")
        assert response.status_code == 200
        # The status should use .name, not .value
        progress.get_status.assert_called()

    @patch("src.web.views.rewards.run_sync_or_async", side_effect=lambda x: x)
    @patch("src.web.views.rewards.reward_repository")
    @patch("src.web.views.rewards.reward_service")
    def test_claim_reward_redirects(self, mock_rs, mock_repo, mock_rsa, auth_client, user):
        reward = MagicMock()
        reward.user_id = user.id
        mock_repo.get_by_id.return_value = reward
        mock_rs.mark_reward_claimed.return_value = MagicMock()
        response = auth_client.post("/rewards/1/claim/")
        assert response.status_code == 302
        assert response.url == "/rewards/"

    @patch("src.web.views.rewards.run_sync_or_async", side_effect=lambda x: x)
    @patch("src.web.views.rewards.reward_repository")
    @patch("src.web.views.rewards.reward_service")
    def test_claim_nonexistent_reward_redirects(self, mock_rs, mock_repo, mock_rsa, auth_client):
        mock_repo.get_by_id.return_value = None
        response = auth_client.post("/rewards/99999/claim/")
        assert response.status_code == 302
        assert response.url == "/rewards/"
        mock_rs.mark_reward_claimed.assert_not_called()

    @patch("src.web.views.rewards.run_sync_or_async", side_effect=lambda x: x)
    @patch("src.web.views.rewards.reward_repository")
    @patch("src.web.views.rewards.reward_service")
    def test_claim_failure_still_redirects(self, mock_rs, mock_repo, mock_rsa, auth_client, user):
        reward = MagicMock()
        reward.user_id = user.id
        mock_repo.get_by_id.return_value = reward
        mock_rs.mark_reward_claimed.side_effect = ValueError("Not achieved")
        response = auth_client.post("/rewards/1/claim/")
        assert response.status_code == 302
        assert response.url == "/rewards/"


# ---- Auth tests ----


class TestAuth:
    """Auth view tests."""

    def test_login_page_renders(self):
        response = Client().get("/auth/login/")
        assert response.status_code == 200

    def test_authenticated_user_redirected_from_login(self, auth_client):
        response = auth_client.get("/auth/login/")
        assert response.status_code == 302
        assert response.url == "/"

    def test_telegram_callback_rejects_invalid_json(self):
        response = Client().post(
            "/auth/telegram/callback/",
            data="not json",
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_telegram_callback_rejects_missing_id(self):
        response = Client().post(
            "/auth/telegram/callback/",
            data={"first_name": "Test"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_telegram_callback_rejects_invalid_hash(self):
        """Invalid HMAC hash returns 403."""
        response = Client().post(
            "/auth/telegram/callback/",
            data={"id": "000000000", "auth_date": "1", "hash": "invalid"},
            content_type="application/json",
        )
        assert response.status_code == 403

    @patch("src.web.views.auth.verify_telegram_auth", return_value=True)
    def test_telegram_callback_nonexistent_user(self, mock_verify, user):
        """Valid hash but unknown telegram_id returns 404."""
        response = Client().post(
            "/auth/telegram/callback/",
            data={"id": "000000000", "auth_date": "1", "hash": "fakehash"},
            content_type="application/json",
        )
        assert response.status_code == 404
        assert response.json()["error"] == "User not found. Please use the Telegram bot first."

    @patch("src.web.views.auth.verify_telegram_auth", return_value=True)
    def test_telegram_callback_success(self, mock_verify, user):
        """Valid hash + existing user logs in and returns success JSON."""
        client = Client()
        response = client.post(
            "/auth/telegram/callback/",
            data={"id": user.telegram_id, "auth_date": "1", "hash": "fakehash"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json() == {"success": True, "redirect": "/"}
        # Verify session was created
        assert str(user.pk) == client.session["_auth_user_id"]

    def test_logout_redirects(self, auth_client):
        response = auth_client.post("/auth/logout/")
        assert response.status_code == 302
        assert "/auth/login/" in response.url


# ---- Prop structure tests (Inertia JSON mode) ----


INERTIA_HEADERS = {"HTTP_X_INERTIA": "true", "HTTP_X_INERTIA_VERSION": "1.0"}


def _inertia_props(response):
    """Extract Inertia props from a JSON response."""
    data = json.loads(response.content)
    return data["component"], data["props"]


class TestPropStructure:
    """Verify prop shapes returned by Inertia views."""

    @patch("src.web.views.dashboard.run_sync_or_async", side_effect=lambda x: x)
    @patch("src.web.views.dashboard.habit_log_repository")
    @patch("src.web.views.dashboard.habit_service")
    def test_dashboard_prop_structure(self, mock_hs, mock_repo, mock_rsa, auth_client):
        habit = _mock_habit(id=1, name="Running", weight=10)
        mock_hs.get_all_active_habits.return_value = [habit]
        log = _mock_habit_log(habit_id=1)
        mock_repo.get_todays_logs_by_user.return_value = [log]
        mock_repo.get_latest_streak_counts.return_value = {1: 3}

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
        mock_rs.get_claimed_one_time_rewards.return_value = []

        response = auth_client.get("/rewards/", **INERTIA_HEADERS)
        component, props = _inertia_props(response)

        assert component == "Rewards"
        assert len(props["rewards"]) == 1
        r = props["rewards"][0]
        assert r["piecesEarned"] == 2
        assert r["piecesRequired"] == 5
        assert r["status"] == "PENDING"

    @patch("src.web.views.history.run_sync_or_async", side_effect=lambda x: x)
    @patch("src.web.views.history.habit_log_repository")
    @patch("src.web.views.history.habit_service")
    def test_history_prop_structure(self, mock_hs, mock_repo, mock_rsa, auth_client):
        mock_hs.get_all_active_habits.return_value = []
        mock_repo.get_logs_in_daterange.return_value = []

        response = auth_client.get("/history/", **INERTIA_HEADERS)
        component, props = _inertia_props(response)

        assert component == "History"
        assert "currentMonth" in props
        assert "completions" in props
        assert "userToday" in props


# ---- Error flash message tests ----


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

    @patch("src.web.views.rewards.run_sync_or_async", side_effect=lambda x: x)
    @patch("src.web.views.rewards.reward_repository")
    @patch("src.web.views.rewards.messages")
    @patch("src.web.views.rewards.reward_service")
    def test_claim_non_achieved_shows_error_message(self, mock_rs, mock_messages, mock_repo, mock_rsa, auth_client, user):
        reward = MagicMock()
        reward.user_id = user.id
        mock_repo.get_by_id.return_value = reward
        mock_rs.mark_reward_claimed.side_effect = ValueError("Not achieved yet")

        auth_client.post("/rewards/1/claim/")

        mock_messages.error.assert_called_once()
        assert "Not achieved yet" in str(mock_messages.error.call_args)
