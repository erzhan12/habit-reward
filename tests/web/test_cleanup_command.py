"""Tests for the cleanup_expired_logins management command."""

from datetime import datetime, timedelta, timezone

import pytest
from django.core.management import call_command

from src.core.models import User, WebLoginRequest

pytestmark = pytest.mark.django_db


@pytest.fixture
def login_user():
    """Create a test user for login requests."""
    return User.objects.create_user(
        username="tg_111111111",
        telegram_id="111111111",
        name="Cleanup Test User",
        language="en",
        timezone="UTC",
    )


class TestCleanupExpiredLogins:
    """Tests for cleanup_expired_logins management command."""

    def test_deletes_expired_requests(self, login_user):
        """Expired login requests are deleted."""
        now = datetime.now(timezone.utc)
        WebLoginRequest.objects.create(
            user=login_user,
            token="expired_token_aaa",
            status=WebLoginRequest.Status.PENDING,
            expires_at=now - timedelta(minutes=10),
        )
        WebLoginRequest.objects.create(
            user=login_user,
            token="expired_token_bbb",
            status=WebLoginRequest.Status.CONFIRMED,
            expires_at=now - timedelta(hours=1),
        )

        call_command("cleanup_expired_logins")

        assert WebLoginRequest.objects.count() == 0

    def test_preserves_non_expired_requests(self, login_user):
        """Non-expired login requests are preserved."""
        now = datetime.now(timezone.utc)
        WebLoginRequest.objects.create(
            user=login_user,
            token="active_token_aaa",
            status=WebLoginRequest.Status.PENDING,
            expires_at=now + timedelta(minutes=5),
        )

        call_command("cleanup_expired_logins")

        assert WebLoginRequest.objects.count() == 1

    def test_mixed_expired_and_active(self, login_user):
        """Only expired requests are deleted; active ones remain."""
        now = datetime.now(timezone.utc)
        WebLoginRequest.objects.create(
            user=login_user,
            token="expired_token_ccc",
            status=WebLoginRequest.Status.PENDING,
            expires_at=now - timedelta(minutes=10),
        )
        active = WebLoginRequest.objects.create(
            user=login_user,
            token="active_token_bbb",
            status=WebLoginRequest.Status.PENDING,
            expires_at=now + timedelta(minutes=5),
        )

        call_command("cleanup_expired_logins")

        remaining = WebLoginRequest.objects.all()
        assert list(remaining) == [active]

    def test_no_expired_requests(self, login_user):
        """Command succeeds with no expired requests to delete."""
        now = datetime.now(timezone.utc)
        WebLoginRequest.objects.create(
            user=login_user,
            token="active_token_ccc",
            status=WebLoginRequest.Status.PENDING,
            expires_at=now + timedelta(minutes=5),
        )

        call_command("cleanup_expired_logins")

        assert WebLoginRequest.objects.count() == 1

    def test_deletes_expired_denied_requests(self, login_user):
        """Expired denied login requests are also deleted."""
        now = datetime.now(timezone.utc)
        WebLoginRequest.objects.create(
            user=login_user,
            token="expired_denied_aaa",
            status=WebLoginRequest.Status.DENIED,
            expires_at=now - timedelta(minutes=10),
        )

        call_command("cleanup_expired_logins")

        assert WebLoginRequest.objects.count() == 0

    def test_deletes_expired_used_requests(self, login_user):
        """Expired used login requests are also deleted."""
        now = datetime.now(timezone.utc)
        WebLoginRequest.objects.create(
            user=login_user,
            token="expired_used_aaa",
            status=WebLoginRequest.Status.USED,
            expires_at=now - timedelta(minutes=10),
        )

        call_command("cleanup_expired_logins")

        assert WebLoginRequest.objects.count() == 0

    def test_mixed_statuses_only_expired_deleted(self, login_user):
        """Expired records with various statuses are deleted; active ones preserved."""
        now = datetime.now(timezone.utc)
        # Expired records with different statuses
        for i, status in enumerate(["pending", "confirmed", "denied", "used"]):
            WebLoginRequest.objects.create(
                user=login_user,
                token=f"expired_status_{status}_{i}",
                status=status,
                expires_at=now - timedelta(minutes=10),
            )
        # Active record
        active = WebLoginRequest.objects.create(
            user=login_user,
            token="active_pending_ddd",
            status=WebLoginRequest.Status.PENDING,
            expires_at=now + timedelta(minutes=5),
        )

        call_command("cleanup_expired_logins")

        remaining = list(WebLoginRequest.objects.all())
        assert remaining == [active]

    def test_database_error_during_cleanup(self, login_user):
        """Command raises and logs error when database operation fails."""
        from unittest.mock import patch

        with patch(
            "src.core.repositories.web_login_request_repository.delete_expired",
            side_effect=Exception("Database connection lost"),
        ):
            with pytest.raises(Exception, match="Database connection lost"):
                call_command("cleanup_expired_logins")

    def test_empty_table(self):
        """Command succeeds on an empty table."""
        call_command("cleanup_expired_logins")

        assert WebLoginRequest.objects.count() == 0
