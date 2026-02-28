"""Tests for timing jitter in the login status endpoint.

Verifies that check_status applies non-trivial timing jitter to
prevent timing side-channel attacks. See SECURITY.md for the full
threat model.

CI flakiness note
~~~~~~~~~~~~~~~~~
These tests mock ``asyncio.sleep`` and assert on the *values* passed to it
(range and statistical variation), so they do **not** depend on real wall-clock
timing and should be stable across fast and slow CI runners.

The one potential source of flakiness is ``test_jitter_has_nontrivial_variation``,
which asserts ``stdev > 0.01`` over 10 CSPRNG samples.  The probability of 10
uniform [0.05, 0.2] samples having stdev <= 0.01 is astronomically low
(~1 in 10^12), but if this ever flakes on CI, increase the sample count or
widen the threshold.  Setting ``CI=true`` in the environment will NOT skip
these tests — they are deterministic enough to run everywhere.
"""

import statistics
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.core.models import User
from src.web.services.web_login_service import WL_PENDING_KEY

# To enable automatic retries on CI, install pytest-rerunfailures and uncomment:
#   pytestmark = [pytest.mark.django_db, pytest.mark.flaky(reruns=2)]
# To skip timing tests entirely on slow CI runners:
#   pytestmark = [pytest.mark.django_db, pytest.mark.skipif(
#       os.environ.get("CI") == "true", reason="Timing tests skipped on CI")]
pytestmark = pytest.mark.django_db


class TestTimingJitter:
    """Verify that check_status adds measurable timing variation."""

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_jitter_values_within_expected_range(self, mock_sleep):
        """10 sequential check_status calls produce jitter values in [0.05, 0.2]."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "jitter_range_test_token"
        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)

        jitter_values = []
        for _ in range(10):
            mock_sleep.reset_mock()
            with patch.object(svc.request_repo, "get_status_fields", return_value=None):
                call_async(svc.check_status(token))

            mock_sleep.assert_called_once()
            jitter = mock_sleep.call_args[0][0]
            jitter_values.append(jitter)

        # All jitter values must be within the configured range
        for j in jitter_values:
            assert 0.05 <= j <= 0.2, f"Jitter {j} outside [0.05, 0.2] range"

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_jitter_has_nontrivial_variation(self, mock_sleep):
        """Jitter values across 10 calls show measurable variation (> 0.01s stdev).

        A constant delay would indicate the CSPRNG is broken or the jitter
        code path is bypassed.
        """
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "jitter_variation_test_token"
        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)

        jitter_values = []
        for _ in range(10):
            mock_sleep.reset_mock()
            with patch.object(svc.request_repo, "get_status_fields", return_value=None):
                call_async(svc.check_status(token))

            jitter = mock_sleep.call_args[0][0]
            jitter_values.append(jitter)

        stdev = statistics.stdev(jitter_values)
        assert stdev > 0.01, (
            f"Jitter stdev too low ({stdev:.4f}s) — "
            f"values may be constant: {jitter_values}"
        )

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_jitter_applied_to_pending_status(self, mock_sleep):
        """Pending status triggers jitter (timing-sensitive code path)."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "jitter_pending_tok"
        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)

        with patch.object(svc.request_repo, "get_status_fields", return_value=None):
            status = call_async(svc.check_status(token))

        assert status == "pending"
        mock_sleep.assert_called_once()

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_jitter_applied_to_expired_status(self, mock_sleep):
        """Expired status (no cache, no DB) triggers jitter."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()

        with patch.object(svc.request_repo, "get_status_fields", return_value=None):
            status = call_async(svc.check_status("nonexistent_tok"))

        assert status == "expired"
        mock_sleep.assert_called_once()

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_jitter_applied_for_confirmed_status(self, mock_sleep):
        """Confirmed status also receives jitter to prevent timing analysis.

        All status paths receive jitter — cache hits (confirmed/denied/used)
        are measurably faster than DB lookups, so without universal jitter
        an attacker could use statistical timing analysis to distinguish
        code paths.
        """
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_jitter_confirmed",
            telegram_id="990000001",
            name="Jitter Confirmed",
            language="en",
            timezone="UTC",
        )

        token = "jitter_confirmed_tok"
        WebLoginRequest.objects.create(
            user=user,
            token=token,
            status=WebLoginRequest.Status.CONFIRMED,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        svc = WebLoginService()
        status = call_async(svc.check_status(token))

        assert status == "confirmed"
        mock_sleep.assert_called_once()
