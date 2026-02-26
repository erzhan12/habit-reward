"""Tests for web interface views."""

import json
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

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock(None))
    def test_bot_login_request_unknown_user(self, mock_async):
        """Unknown username returns 200 with generic message (anti-enumeration)."""
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

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock(None))
    def test_fake_token_cached_for_status_polling(self, mock_async):
        """Fake token from unknown user is cached so status returns 'pending'."""
        from django.core.cache import cache

        cache.clear()
        response = Client().post(
            "/auth/bot-login/request/",
            data={"username": "unknownuser"},
            content_type="application/json",
        )
        assert response.status_code == 200
        fake_token = response.json()["token"]
        assert cache.get(f"wl_fake:{fake_token}") is True

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
