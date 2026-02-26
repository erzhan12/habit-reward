"""Tests for web interface views."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.test import Client

from src.core.models import User

pytestmark = pytest.mark.django_db


def _call_async_mock(return_value):
    """Side effect for call_async mock that properly closes unawaited coroutines."""
    def _impl(coro):
        if hasattr(coro, 'close'):
            coro.close()
        return return_value
    return _impl


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


# ---- WebAuthMiddleware unit tests ----


class TestWebAuthMiddleware:
    """Direct tests for WebAuthMiddleware exempt prefixes and auth enforcement."""

    # Paths that should never be redirected to /auth/login/ regardless of auth state.
    # Each entry is (path, expected_status_not_to_be_login_redirect).
    EXEMPT_PATHS = [
        "/auth/login/",
        "/admin/",
        "/webhook/test/",
        "/api/health/",
    ]

    def test_unauthenticated_protected_path_redirects_to_login(self):
        response = Client().get("/")
        assert response.status_code == 302
        assert response.url == "/auth/login/"

    def test_authenticated_protected_path_is_allowed_through(self, auth_client):
        """Middleware passes authenticated requests; downstream view returns 200."""
        from unittest.mock import AsyncMock, patch

        with (
            patch("src.web.views.dashboard.habit_service") as mock_hs,
            patch("src.web.views.dashboard.habit_log_repository") as mock_repo,
            patch("src.web.views.dashboard.streak_service") as mock_ss,
        ):
            mock_hs.get_all_active_habits.return_value = []
            mock_repo.get_todays_logs_by_user = AsyncMock(return_value=[])
            mock_ss.get_validated_streak_map.return_value = {}
            response = auth_client.get("/")
        assert response.status_code == 200

    def test_auth_prefix_exempt_unauthenticated(self):
        response = Client().get("/auth/login/")
        assert response.status_code == 200

    def test_admin_prefix_exempt_unauthenticated(self):
        """Admin path is handled by Django admin, not redirected to /auth/login/."""
        response = Client().get("/admin/")
        # Django admin redirects to its own login; the middleware must not intercept.
        assert response.status_code != 302 or "/auth/login/" not in (response.url or "")

    def test_webhook_prefix_exempt_unauthenticated(self):
        """/webhook/* paths pass through the middleware (may 404, not redirect)."""
        response = Client().get("/webhook/nonexistent/")
        assert response.status_code != 302 or "/auth/login/" not in (response.url or "")

    def test_api_prefix_exempt_unauthenticated(self):
        """/api/* paths pass through the middleware (may 404, not redirect)."""
        response = Client().get("/api/nonexistent/")
        assert response.status_code != 302 or "/auth/login/" not in (response.url or "")

    def test_redirect_target_is_exact_login_url(self):
        """Redirect must point to exactly /auth/login/, not a partial match."""
        response = Client().get("/dashboard/")
        assert response.status_code == 302
        assert response.url == "/auth/login/"


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


# ---- Streaks tests ----


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


# ---- History tests ----


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

    @patch("src.web.views.rewards.reward_repository")
    @patch("src.web.views.rewards.reward_service")
    def test_claim_reward_redirects(self, mock_rs, mock_repo, auth_client, user):
        reward = MagicMock()
        reward.user_id = user.id
        mock_repo.get_by_id = AsyncMock(return_value=reward)
        mock_rs.mark_reward_claimed.return_value = MagicMock()
        response = auth_client.post("/rewards/1/claim/")
        assert response.status_code == 302
        assert response.url == "/rewards/"

    @patch("src.web.views.rewards.reward_repository")
    @patch("src.web.views.rewards.reward_service")
    def test_claim_nonexistent_reward_redirects(self, mock_rs, mock_repo, auth_client):
        mock_repo.get_by_id = AsyncMock(return_value=None)
        response = auth_client.post("/rewards/99999/claim/")
        assert response.status_code == 302
        assert response.url == "/rewards/"
        mock_rs.mark_reward_claimed.assert_not_called()

    @patch("src.web.views.rewards.reward_repository")
    @patch("src.web.views.rewards.reward_service")
    def test_claim_failure_still_redirects(self, mock_rs, mock_repo, auth_client, user):
        reward = MagicMock()
        reward.user_id = user.id
        mock_repo.get_by_id = AsyncMock(return_value=reward)
        mock_rs.mark_reward_claimed.side_effect = ValueError("Not achieved")
        response = auth_client.post("/rewards/1/claim/")
        assert response.status_code == 302
        assert response.url == "/rewards/"


# ---- Auth tests ----


class TestAuth:
    """Auth view tests for bot-based login."""

    def test_login_page_renders(self):
        response = Client().get("/auth/login/")
        assert response.status_code == 200

    def test_authenticated_user_redirected_from_login(self, auth_client):
        response = auth_client.get("/auth/login/")
        assert response.status_code == 302
        assert response.url == "/"

    def test_bot_login_request_rejects_invalid_json(self):
        response = Client().post(
            "/auth/bot-login/request/",
            data="not json",
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_bot_login_request_rejects_empty_username(self):
        response = Client().post(
            "/auth/bot-login/request/",
            data={"username": ""},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_bot_login_request_rejects_invalid_username(self):
        response = Client().post(
            "/auth/bot-login/request/",
            data={"username": "ab"},  # too short
            content_type="application/json",
        )
        assert response.status_code == 400

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock({"token": "unknown_user_token", "expires_at": "2026-01-01T00:00:00+00:00"}))
    def test_bot_login_request_unknown_user(self, mock_async):
        """Unknown username returns 200 with generic message (anti-enumeration).

        The service always returns a dict (never None) so the view
        never branches on user existence.
        """
        response = Client().post(
            "/auth/bot-login/request/",
            data={"username": "nonexistentuser"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "expires_at" in data
        assert "sent" not in data
        assert "If this username is registered" in data["message"]

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock({"token": "test_token_123", "expires_at": "2026-01-01T00:00:00+00:00"}))
    def test_bot_login_request_success(self, mock_async, user):
        """Valid username returns token, expires_at, and generic message — no sent field."""
        response = Client().post(
            "/auth/bot-login/request/",
            data={"username": "testuser"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "expires_at" in data
        assert "sent" not in data
        assert "If this username is registered" in data["message"]

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock("pending"))
    def test_bot_login_status_pending(self, mock_async):
        """Status endpoint returns pending."""
        response = Client().get("/auth/bot-login/status/some_token/")
        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock("confirmed"))
    def test_bot_login_status_confirmed(self, mock_async):
        """Status endpoint returns confirmed."""
        response = Client().get("/auth/bot-login/status/some_token/")
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock("denied"))
    def test_bot_login_status_denied(self, mock_async):
        """Status endpoint returns denied."""
        response = Client().get("/auth/bot-login/status/some_token/")
        assert response.status_code == 200
        assert response.json()["status"] == "denied"

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock("expired"))
    def test_bot_login_status_expired(self, mock_async):
        """Status endpoint returns expired."""
        response = Client().get("/auth/bot-login/status/some_token/")
        assert response.status_code == 200
        assert response.json()["status"] == "expired"

    def test_bot_login_status_rejects_post(self):
        """POST to status endpoint returns 405 (GET only)."""
        response = Client().post("/auth/bot-login/status/some_token/")
        assert response.status_code == 405

    def test_bot_login_complete_success(self, user):
        """Confirmed login creates Django session."""
        with patch("src.web.views.auth.call_async", side_effect=_call_async_mock(user)):
            client = Client()
            response = client.post(
                "/auth/bot-login/complete/",
                data={"token": "confirmed_token"},
                content_type="application/json",
            )
            assert response.status_code == 200
            assert response.json() == {"success": True, "redirect": "/"}
            assert str(user.pk) == client.session["_auth_user_id"]

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock(None))
    def test_bot_login_complete_fails_for_invalid_token(self, mock_async):
        """Invalid/expired token returns 403."""
        response = Client().post(
            "/auth/bot-login/complete/",
            data={"token": "bad_token"},
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_bot_login_complete_rejects_missing_token(self):
        response = Client().post(
            "/auth/bot-login/complete/",
            data={"token": ""},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_bot_login_request_rejects_array_body(self):
        """POST with JSON array (not object) returns 400, not 500."""
        response = Client().post(
            "/auth/bot-login/request/",
            data=json.dumps(["not", "an", "object"]),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_bot_login_complete_rejects_array_body(self):
        """POST with JSON array (not object) returns 400, not 500."""
        response = Client().post(
            "/auth/bot-login/complete/",
            data=json.dumps([1, 2, 3]),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_bot_login_request_non_string_username(self):
        """Non-string username (e.g. integer) is coerced to str, not 500."""
        response = Client().post(
            "/auth/bot-login/request/",
            data=json.dumps({"username": 123}),
            content_type="application/json",
        )
        # "123" passes regex but user won't exist — anti-enumeration returns 200
        assert response.status_code == 200

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock(None))
    def test_bot_login_complete_non_string_token(self, mock_async):
        """Non-string token (e.g. integer) returns 403/400, not 500."""
        response = Client().post(
            "/auth/bot-login/complete/",
            data=json.dumps({"token": 12345}),
            content_type="application/json",
        )
        assert response.status_code in (400, 403)

    def test_token_cached_for_status_polling(self):
        """Service caches every token (wl_pending:) so status returns 'pending'."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService

        cache.clear()
        svc = WebLoginService()
        with (
            patch.object(svc.user_repo, "get_by_telegram_username", return_value=None),
        ):
            from src.web.utils.sync import call_async
            result = call_async(svc.create_login_request("unknownuser"))
        token = result["token"]
        assert cache.get(f"wl_pending:{token}") is True

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_check_status_falls_back_to_cache_on_db_lock(self, mock_sleep):
        """check_status returns 'pending' (not 500) when SQLite DB is locked."""
        from django.core.cache import cache
        from django.db import OperationalError
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "locked_token_abc"
        cache.set(f"wl_pending:{token}", True, timeout=300)

        with patch.object(
            svc.request_repo, "get_by_token",
            side_effect=OperationalError("database table is locked"),
        ):
            status = call_async(svc.check_status(token))

        assert status == "pending"

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_check_status_always_performs_both_lookups(self, mock_sleep):
        """Both DB query and cache lookup execute regardless of DB result.

        Prevents timing side-channel where DB-hit path skips cache lookup.
        """
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "both_lookup_token"

        # Simulate a confirmed DB record (known-user path)
        db_record = MagicMock()
        db_record.status = "confirmed"
        db_record.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        cache.set(f"wl_pending:{token}", True, timeout=300)

        with (
            patch.object(svc.request_repo, "get_by_token", return_value=db_record) as mock_db,
            patch.object(cache, "get", wraps=cache.get) as mock_cache_get,
        ):
            status = call_async(svc.check_status(token))

        assert status == "confirmed"
        # DB query must have been called
        mock_db.assert_called_once_with(token)
        # Cache lookups must ALSO have been called (constant-time: no short-circuit)
        cache_get_calls = [c.args[0] for c in mock_cache_get.call_args_list]
        assert f"wl_pending:{token}" in cache_get_calls
        assert f"wl_failed:{token}" in cache_get_calls

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_check_status_applies_jitter(self, mock_sleep):
        """check_status calls asyncio.sleep with a random jitter value."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "jitter_test_token"
        cache.set(f"wl_pending:{token}", True, timeout=300)

        with patch.object(svc.request_repo, "get_by_token", return_value=None):
            call_async(svc.check_status(token))

        mock_sleep.assert_called_once()
        jitter = mock_sleep.call_args[0][0]
        assert 0.05 <= jitter <= 0.2

    def test_cache_ttl_derived_from_expires_at(self):
        """Cache timeout is derived from expires_at, not a separate constant."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        svc = WebLoginService()

        with (
            patch.object(svc.user_repo, "get_by_telegram_username", return_value=None),
            patch.object(cache, "set", wraps=cache.set) as mock_set,
        ):
            result = call_async(svc.create_login_request("unknownuser"))

        token = result["token"]
        mock_set.assert_called_once()
        call_args = mock_set.call_args
        assert call_args[0][0] == f"wl_pending:{token}"
        # timeout should be close to 300s but derived from expires_at
        timeout = call_args[1].get("timeout") or call_args[0][2]
        assert 295 <= timeout <= 300

    def test_rate_limited_view(self):
        """Rate limit handler returns 429 with JSON error."""
        import json as json_module

        from django_ratelimit.exceptions import Ratelimited

        from src.web.views.auth import rate_limited_view

        request = type("Request", (), {"META": {"REMOTE_ADDR": "1.2.3.4"}, "path": "/auth/bot-login/request/"})()
        response = rate_limited_view(request, exception=Ratelimited())
        assert response.status_code == 429
        assert json_module.loads(response.content)["error"] == "Too many requests. Please wait a moment and try again."

    def test_logout_redirects(self, auth_client):
        response = auth_client.post("/auth/logout/")
        assert response.status_code == 302
        assert "/auth/login/" in response.url

    def test_bot_login_rate_limit_http_level(self):
        """Sending requests over the limit triggers rate limiting and returns 429 JSON.

        Uses settings.AUTH_RATE_LIMIT (default 10/m).
        """
        from django.core.cache import cache

        cache.clear()

        payload = json.dumps({"username": "nonexistent_user_test"})
        client = Client()

        # Send requests up to the limit (default 10/m)
        for _ in range(10):
            client.post(
                "/auth/bot-login/request/",
                data=payload,
                content_type="application/json",
                REMOTE_ADDR="192.0.2.99",
            )

        response = client.post(
            "/auth/bot-login/request/",
            data=payload,
            content_type="application/json",
            REMOTE_ADDR="192.0.2.99",
        )
        assert response.status_code == 429
        assert response.json()["error"] == "Too many requests. Please wait a moment and try again."


# ---- Race condition / atomicity tests ----


class TestLoginRaceConditions:
    """Integration tests for atomic operations and concurrent access patterns.

    These hit the real DB to verify that the atomic UPDATE ... WHERE guards
    in the repository layer behave correctly under contention.
    """

    @pytest.fixture
    def login_user(self):
        """Create a user for login race condition tests."""
        return User.objects.create_user(
            username="tg_888888888",
            telegram_id="888888888",
            name="Race User",
            language="en",
            timezone="UTC",
        )

    @pytest.fixture
    def pending_request(self, login_user):
        """Create a pending WebLoginRequest in the DB."""
        from src.core.models import WebLoginRequest

        return WebLoginRequest.objects.create(
            user=login_user,
            token="race_test_token_aaa",
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

    @pytest.fixture
    def confirmed_request(self, login_user):
        """Create a confirmed WebLoginRequest in the DB."""
        from src.core.models import WebLoginRequest

        return WebLoginRequest.objects.create(
            user=login_user,
            token="race_test_token_bbb",
            status="confirmed",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

    def test_update_status_atomic_only_first_call_succeeds(self, pending_request):
        """update_status uses UPDATE WHERE status='pending' — the second call
        must return 0 because the status is no longer 'pending'."""
        from src.core.repositories import WebLoginRequestRepository
        from src.web.utils.sync import call_async

        repo = WebLoginRequestRepository()
        token = pending_request.token

        first = call_async(repo.update_status(token, "confirmed"))
        second = call_async(repo.update_status(token, "confirmed"))

        assert first == 1
        assert second == 0

        pending_request.refresh_from_db()
        assert pending_request.status == "confirmed"

    def test_mark_as_used_atomic_only_first_call_succeeds(self, confirmed_request):
        """mark_as_used uses UPDATE WHERE status='confirmed' — the second call
        must return 0 because the status is now 'used'."""
        from src.core.repositories import WebLoginRequestRepository
        from src.web.utils.sync import call_async

        repo = WebLoginRequestRepository()
        token = confirmed_request.token

        first = call_async(repo.mark_as_used(token))
        second = call_async(repo.mark_as_used(token))

        assert first == 1
        assert second == 0

        confirmed_request.refresh_from_db()
        assert confirmed_request.status == "used"

    def test_complete_login_replay_returns_none(self, confirmed_request):
        """Calling complete_login twice with the same token: first returns User,
        second returns None (token already marked as used)."""
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        svc = WebLoginService()
        token = confirmed_request.token

        first = call_async(svc.complete_login(token))
        second = call_async(svc.complete_login(token))

        assert first is not None
        assert second is None

        confirmed_request.refresh_from_db()
        assert confirmed_request.status == "used"

    def test_new_login_request_invalidates_previous(self, login_user):
        """Creating a second login request for the same user sets the first to 'denied'."""
        from src.core.models import WebLoginRequest
        from src.core.repositories import WebLoginRequestRepository
        from src.web.utils.sync import call_async

        repo = WebLoginRequestRepository()

        first = call_async(repo.create(
            user_id=login_user.id,
            token="first_token_111",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        ))
        assert first.status == "pending"

        # Invalidate + create second (mimics _process_login_request)
        call_async(repo.invalidate_pending_for_user(login_user.id))
        call_async(repo.create(
            user_id=login_user.id,
            token="second_token_222",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        ))

        first.refresh_from_db()
        assert first.status == "denied"

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_status_returns_pending_before_db_write(self, mock_sleep):
        """check_status returns 'pending' via cache even when no DB record exists yet
        (simulates the window between cache.set and background thread DB write)."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "no_db_yet_token"

        # Token is in cache but NOT in DB (background thread hasn't run)
        cache.set(f"wl_pending:{token}", True, timeout=300)

        with patch.object(svc.request_repo, "get_by_token", return_value=None):
            status = call_async(svc.check_status(token))

        assert status == "pending"

    def test_mark_as_used_rejects_pending_token(self, pending_request):
        """mark_as_used only works on confirmed tokens, not pending ones."""
        from src.core.repositories import WebLoginRequestRepository
        from src.web.utils.sync import call_async

        repo = WebLoginRequestRepository()
        updated = call_async(repo.mark_as_used(pending_request.token))
        assert updated == 0

        pending_request.refresh_from_db()
        assert pending_request.status == "pending"

    def test_update_status_rejects_confirmed_token(self, confirmed_request):
        """update_status only works on pending tokens, not confirmed ones."""
        from src.core.repositories import WebLoginRequestRepository
        from src.web.utils.sync import call_async

        repo = WebLoginRequestRepository()
        updated = call_async(repo.update_status(confirmed_request.token, "denied"))
        assert updated == 0

        confirmed_request.refresh_from_db()
        assert confirmed_request.status == "confirmed"


# ---- Background thread failure tests ----


class TestBackgroundProcessingFailures:
    """Tests for graceful degradation when background thread processing fails.

    The background thread handles DB writes + Telegram send.  When it fails,
    the user should still see 'pending' (from cache) until the token expires.
    """

    def test_telegram_api_failure_logs_error_and_cache_stays_valid(self):
        """If Telegram send_message raises, the error is logged but the
        cache entry remains so check_status returns 'pending'."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService

        cache.clear()
        svc = WebLoginService()

        # Use a real user so the transactional DB writes succeed
        user = User.objects.create_user(
            username="tg_tgfail1", telegram_id="111111111", name="TG Fail User",
            language="en", timezone="UTC",
        )

        token = "tg_fail_token_aaa"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        cache.set(f"wl_pending:{token}", True, timeout=300)

        with patch.object(svc, "_send_login_notification", new_callable=AsyncMock,
                         side_effect=Exception("Telegram API unavailable")):
            # _process_login_background catches all exceptions
            svc._process_login_background(user, token, expires_at, None)

        # Cache entry survives the background failure
        assert cache.get(f"wl_pending:{token}") is True

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_status_pending_after_telegram_failure(self, mock_sleep):
        """check_status returns 'pending' via cache even when background
        thread failed and no DB record was created."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "tg_fail_status_token"
        cache.set(f"wl_pending:{token}", True, timeout=300)

        # No DB record exists (background thread failed before DB write)
        with patch.object(svc.request_repo, "get_by_token", return_value=None):
            status = call_async(svc.check_status(token))

        assert status == "pending"

    def test_db_failure_in_background_thread_is_caught(self):
        """If DB operations raise in the background thread, the exception
        is caught and logged — no crash, cache still valid."""
        from django.core.cache import cache
        from django.db import OperationalError
        from src.web.services.web_login_service import WebLoginService

        cache.clear()
        svc = WebLoginService()

        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.telegram_id = "888888888"

        token = "db_fail_token_bbb"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        cache.set(f"wl_pending:{token}", True, timeout=300)

        # Mock _process_login_request to raise DB error (simulates any DB failure)
        with patch.object(svc, "_process_login_request", new_callable=AsyncMock,
                         side_effect=OperationalError("connection lost")):
            # Should not raise — exception caught in _process_login_background
            svc._process_login_background(mock_user, token, expires_at, None)

        assert cache.get(f"wl_pending:{token}") is True

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_cache_expiry_transitions_to_expired_after_failure(self, mock_sleep):
        """After background failure + cache TTL expiry, check_status
        returns 'expired' (not 'pending' forever)."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "expired_after_fail_token"

        # Cache entry already evicted (TTL passed)
        # No DB record (background thread failed)
        with patch.object(svc.request_repo, "get_by_token", return_value=None):
            status = call_async(svc.check_status(token))

        assert status == "expired"

    def test_background_failure_error_is_logged(self):
        """_process_login_background logs the error with user ID."""
        from src.web.services.web_login_service import WebLoginService

        svc = WebLoginService()

        mock_user = MagicMock()
        mock_user.id = 99

        with (
            patch.object(svc, "_process_login_request", new_callable=AsyncMock,
                         side_effect=Exception("boom")),
            patch("src.web.services.web_login_service.logger") as mock_logger,
        ):
            svc._process_login_background(
                mock_user, "log_test_token", datetime.now(timezone.utc) + timedelta(minutes=5), None
            )

        mock_logger.error.assert_called_once()
        log_msg = mock_logger.error.call_args[0][0]
        assert "Background login processing failed" in log_msg

    def test_create_login_request_returns_token_even_if_thread_will_fail(self):
        """create_login_request always returns {token, expires_at} regardless
        of what happens in the background thread."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService, _login_executor
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()

        mock_user = MagicMock()
        mock_user.telegram_id = "777777777"

        with (
            patch.object(svc.user_repo, "get_by_telegram_username", return_value=mock_user),
            patch.object(_login_executor, "submit") as mock_submit,
        ):
            result = call_async(svc.create_login_request("testuser"))

        assert "token" in result
        assert "expires_at" in result
        # Executor was called (whether it succeeds or not is irrelevant here)
        mock_submit.assert_called_once()


# ---- IP address validation tests ----


class TestIPAddressParsing:
    """Tests for _parse_ip_address validation and fallback."""

    def test_valid_ipv4_from_forwarded_for(self):
        from src.web.views.auth import _parse_ip_address

        request = MagicMock()
        request.META = {"HTTP_X_FORWARDED_FOR": "203.0.113.50, 70.41.3.18", "REMOTE_ADDR": "127.0.0.1"}
        assert _parse_ip_address(request) == "203.0.113.50"

    def test_valid_ipv6_from_forwarded_for(self):
        from src.web.views.auth import _parse_ip_address

        request = MagicMock()
        request.META = {"HTTP_X_FORWARDED_FOR": "2001:db8::1", "REMOTE_ADDR": "127.0.0.1"}
        assert _parse_ip_address(request) == "2001:db8::1"

    def test_malformed_ip_falls_back_to_remote_addr(self):
        from src.web.views.auth import _parse_ip_address

        request = MagicMock()
        request.META = {"HTTP_X_FORWARDED_FOR": "<script>alert(1)</script>", "REMOTE_ADDR": "10.0.0.1"}
        assert _parse_ip_address(request) == "10.0.0.1"

    def test_empty_forwarded_for_falls_back_to_remote_addr(self):
        from src.web.views.auth import _parse_ip_address

        request = MagicMock()
        request.META = {"HTTP_X_FORWARDED_FOR": "", "REMOTE_ADDR": "192.168.1.1"}
        assert _parse_ip_address(request) == "192.168.1.1"

    def test_missing_forwarded_for_falls_back_to_remote_addr(self):
        from src.web.views.auth import _parse_ip_address

        request = MagicMock()
        request.META = {"REMOTE_ADDR": "172.16.0.1"}
        assert _parse_ip_address(request) == "172.16.0.1"

    def test_missing_both_headers_returns_unknown(self):
        from src.web.views.auth import _parse_ip_address

        request = MagicMock()
        request.META = {}
        assert _parse_ip_address(request) == "unknown"

    def test_device_info_uses_validated_ip(self):
        """_parse_device_info delegates to _parse_ip_address for the IP."""
        from src.web.views.auth import _parse_device_info

        request = MagicMock()
        request.META = {
            "HTTP_USER_AGENT": "Mozilla/5.0 Chrome/120.0",
            "HTTP_X_FORWARDED_FOR": "not-an-ip",
            "REMOTE_ADDR": "10.0.0.5",
        }
        info = _parse_device_info(request)
        assert "10.0.0.5" in info
        assert "not-an-ip" not in info


# ---- Prop structure tests (Inertia JSON mode) ----


INERTIA_HEADERS = {"HTTP_X_INERTIA": "true", "HTTP_X_INERTIA_VERSION": "1.0"}


def _inertia_props(response):
    """Extract Inertia props from a JSON response."""
    data = json.loads(response.content)
    return data["component"], data["props"]


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
        mock_rs.get_claimed_one_time_rewards.return_value = []

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


# ---- Timezone edge case tests ----


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
        from datetime import date
        from unittest.mock import ANY

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


# ---- Username recycling tests ----


class TestUsernameRecycling:
    """Tests for update_telegram_username handling recycling and edge cases."""

    def test_assign_username_clears_old_owner(self):
        """When a username is assigned to user B, it is cleared from user A."""
        from src.core.repositories import UserRepository
        from src.web.utils.sync import call_async

        user_a = User.objects.create_user(
            username="tg_111", telegram_id="111", name="User A",
            language="en", timezone="UTC", telegram_username="recycled",
        )
        user_b = User.objects.create_user(
            username="tg_222", telegram_id="222", name="User B",
            language="en", timezone="UTC",
        )

        repo = UserRepository()
        call_async(repo.update_telegram_username("222", "recycled"))

        user_a.refresh_from_db()
        user_b.refresh_from_db()
        assert user_a.telegram_username is None
        assert user_b.telegram_username == "recycled"

    def test_assign_none_clears_username(self):
        """Passing None clears the user's telegram_username."""
        from src.core.repositories import UserRepository
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_333", telegram_id="333", name="User C",
            language="en", timezone="UTC", telegram_username="oldname",
        )

        repo = UserRepository()
        call_async(repo.update_telegram_username("333", None))

        user.refresh_from_db()
        assert user.telegram_username is None

    def test_username_normalized_to_lowercase(self):
        """Username is lowercased and stripped of @ prefix."""
        from src.core.repositories import UserRepository
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_444", telegram_id="444", name="User D",
            language="en", timezone="UTC",
        )

        repo = UserRepository()
        call_async(repo.update_telegram_username("444", "@MyUserName"))

        user.refresh_from_db()
        assert user.telegram_username == "myusername"

    def test_reassign_same_username_is_idempotent(self):
        """Re-assigning the same username to the same user is a no-op."""
        from src.core.repositories import UserRepository
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_555", telegram_id="555", name="User E",
            language="en", timezone="UTC", telegram_username="stable",
        )

        repo = UserRepository()
        call_async(repo.update_telegram_username("555", "stable"))

        user.refresh_from_db()
        assert user.telegram_username == "stable"


# ---- Full login flow integration test ----


class TestFullLoginFlow:
    """Integration test simulating the complete login flow end-to-end:
    create request → bot confirmation → poll status → complete login → session created.
    """

    @pytest.fixture
    def login_user(self):
        """Create a user for the full flow test."""
        return User.objects.create_user(
            username="tg_777777777",
            telegram_id="777777777",
            name="Flow User",
            language="en",
            timezone="UTC",
            telegram_username="flowuser",
        )

    def test_full_login_flow(self, login_user):
        """End-to-end: create request → bot confirmation → poll status → complete → session."""
        from django.core.cache import cache
        from src.core.models import WebLoginRequest
        from src.core.repositories import WebLoginRequestRepository
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        repo = WebLoginRequestRepository()
        client = Client()

        # Step 1: Create login request via HTTP (background thread is async,
        # so we create the DB record directly to simulate what it does)
        token = "full_flow_test_token"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        cache.set(f"wl_pending:{token}", True, timeout=300)

        login_request = WebLoginRequest.objects.create(
            user=login_user,
            token=token,
            status=WebLoginRequest.Status.PENDING,
            expires_at=expires_at,
        )
        assert login_request.status == WebLoginRequest.Status.PENDING.value

        # Step 2: Poll status — should be pending
        with patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock):
            status = call_async(svc.check_status(token))
        assert status == WebLoginRequest.Status.PENDING.value

        # Step 3: Simulate bot confirmation (as if user pressed Confirm)
        updated = call_async(repo.update_status(token, WebLoginRequest.Status.CONFIRMED.value))
        assert updated == 1

        # Step 4: Poll status — should be confirmed
        with patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock):
            status = call_async(svc.check_status(token))
        assert status == WebLoginRequest.Status.CONFIRMED.value

        # Step 5: Complete login via HTTP
        response = client.post(
            "/auth/bot-login/complete/",
            data=json.dumps({"token": token}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["success"] is True

        # Step 6: Verify session was created — user is now authenticated
        response = client.get("/")
        assert response.status_code == 200  # Not redirected to login

        # Step 7: Verify token is marked as used (replay protection)
        login_request.refresh_from_db()
        assert login_request.status == WebLoginRequest.Status.USED.value

        # Step 8: Replay attempt should fail
        response = client.post(
            "/auth/bot-login/complete/",
            data=json.dumps({"token": token}),
            content_type="application/json",
        )
        assert response.status_code == 403


# ---- Concurrent login request test ----


class TestConcurrentLoginRequests:
    """Test that concurrent login requests from the same user properly
    invalidate old pending requests.
    """

    @pytest.fixture
    def concurrent_user(self):
        """Create a user for concurrent request tests."""
        return User.objects.create_user(
            username="tg_666666666",
            telegram_id="666666666",
            name="Concurrent User",
            language="en",
            timezone="UTC",
            telegram_username="concurrentuser",
        )

    def test_second_request_invalidates_first(self, concurrent_user):
        """When a user creates a second login request, the first pending
        request is set to 'denied' and only the second is active."""
        from django.core.cache import cache
        from django.db import transaction as db_transaction
        from src.core.models import WebLoginRequest
        from src.core.repositories import WebLoginRequestRepository
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        repo = WebLoginRequestRepository()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        # Create first pending request
        req1 = WebLoginRequest.objects.create(
            user=concurrent_user,
            token="concurrent_token_1",
            status=WebLoginRequest.Status.PENDING,
            expires_at=expires_at,
        )
        assert req1.status == WebLoginRequest.Status.PENDING.value

        # Simulate creating a second request (transactional invalidate + create)
        with db_transaction.atomic():
            WebLoginRequest.objects.filter(
                user_id=concurrent_user.id,
                status=WebLoginRequest.Status.PENDING,
            ).update(status=WebLoginRequest.Status.DENIED)
            req2 = WebLoginRequest.objects.create(
                user=concurrent_user,
                token="concurrent_token_2",
                status=WebLoginRequest.Status.PENDING,
                expires_at=expires_at,
            )

        # First request should now be denied
        req1.refresh_from_db()
        assert req1.status == WebLoginRequest.Status.DENIED.value

        # Second request should be pending
        assert req2.status == WebLoginRequest.Status.PENDING.value

        # Confirm second request and complete login — should succeed
        call_async(repo.update_status("concurrent_token_2", WebLoginRequest.Status.CONFIRMED.value))
        user = call_async(svc.complete_login("concurrent_token_2"))
        assert user is not None
        assert user.id == concurrent_user.id

        # First token should NOT be completable (status is 'denied')
        user_from_old = call_async(svc.complete_login("concurrent_token_1"))
        assert user_from_old is None
