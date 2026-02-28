"""Django management command to clean up expired web login requests.

Usage:
    python manage.py cleanup_expired_logins

Schedule hourly via cron:
    0 * * * * cd /path/to/project && python manage.py cleanup_expired_logins
"""

import logging

from django.core.management.base import BaseCommand

from src.core.repositories import web_login_request_repository
from src.web.utils.sync import call_async

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Delete expired WebLoginRequest and LoginTokenIpBinding records."""

    help = "Delete web login requests and IP bindings that have passed their expiry time"

    def handle(self, *args, **options):
        """Execute the cleanup."""
        self.stdout.write(
            self.style.NOTICE("Cleaning up expired web login requests...")
        )

        try:
            deleted_count = call_async(
                web_login_request_repository.delete_expired()
            )
            ip_deleted_count = web_login_request_repository.delete_expired_ip_bindings()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {deleted_count} expired login request(s)"
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {ip_deleted_count} expired IP binding(s)"
                )
            )

            logger.info(
                "cleanup_expired_logins completed: deleted %d request(s), %d IP binding(s)",
                deleted_count,
                ip_deleted_count,
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during cleanup: {e}")
            )
            logger.error("cleanup_expired_logins failed: %s", e, exc_info=True)
            raise
