"""Django management command to clean up old audit logs.

Usage:
    python manage.py cleanup_audit_logs [--days DAYS]

Example:
    python manage.py cleanup_audit_logs --days 90

This command is intended to be run daily via cron:
    0 2 * * * cd /path/to/project && python manage.py cleanup_audit_logs
"""

import logging
from django.core.management.base import BaseCommand
from src.services.audit_log_service import audit_log_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Clean up old audit log entries."""

    help = 'Delete audit log entries older than retention period (default: 90 days)'

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days to retain audit logs (default: 90)',
        )

    def handle(self, *args, **options):
        """Execute the cleanup command."""
        days = options['days']

        self.stdout.write(
            self.style.NOTICE(
                f'Starting cleanup of audit logs older than {days} days...'
            )
        )

        # Call the service method (synchronously - Django management commands are sync)
        try:
            deleted_count = audit_log_service.cleanup_old_logs(days=days)

            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Successfully deleted {deleted_count} old audit log entries'
                )
            )

            logger.info(
                f"Cleanup command completed: deleted {deleted_count} audit logs "
                f"older than {days} days"
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'❌ Error during cleanup: {str(e)}'
                )
            )
            logger.error(f"Cleanup command failed: {str(e)}", exc_info=True)
            raise
