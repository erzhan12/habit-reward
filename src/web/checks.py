"""Django system checks for the web layer."""

import logging

from django.conf import settings
from django.core.checks import Error, Warning, register

logger = logging.getLogger(__name__)


@register()
def check_xff_trust_configuration(app_configs, **kwargs):
    """Warn if TRUST_X_FORWARDED_FOR=True but no reverse proxy indicators.

    When TRUST_X_FORWARDED_FOR is enabled, Django will trust the
    X-Forwarded-For header for client IP detection.  This is only safe
    behind a reverse proxy that overwrites the header.

    We check for ``SECURE_PROXY_SSL_HEADER`` as a proxy indicator — if it's
    not set, the app is likely exposed directly to the internet.
    """
    errors = []
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        has_proxy_header = bool(getattr(settings, "SECURE_PROXY_SSL_HEADER", None))
        if not has_proxy_header:
            msg = (
                "TRUST_X_FORWARDED_FOR=True but SECURE_PROXY_SSL_HEADER is not "
                "set. This suggests Django may not be behind a reverse proxy. "
                "X-Forwarded-For can be spoofed by clients when exposed directly "
                "to the internet. Set SECURE_PROXY_SSL_HEADER or disable "
                "TRUST_X_FORWARDED_FOR."
            )
            logger.warning("SECURITY: %s", msg)
            errors.append(Error(msg, id="web.E001"))
        if not settings.DEBUG:
            msg = (
                "TRUST_X_FORWARDED_FOR=True in a production environment "
                "(DEBUG=False). Ensure Django is behind a trusted reverse proxy "
                "(nginx, Caddy, etc.) that overwrites the X-Forwarded-For "
                "header. Without this, clients can spoof their IP address."
            )
            logger.warning("SECURITY: %s", msg)
            errors.append(Error(msg, id="web.E002"))
    return errors


@register()
def check_login_expiry_consistency(app_configs, **kwargs):
    """Warn when backend WEB_LOGIN_EXPIRY_MINUTES doesn't match frontend LOGIN_EXPIRY_MS.

    The frontend LOGIN_EXPIRY_MS is hardcoded at 300_000 ms (5 minutes).
    If the backend setting diverges, login requests will behave
    inconsistently — e.g. the frontend may stop polling before the
    backend token actually expires, or vice versa.
    """
    errors = []
    backend_minutes = getattr(settings, "WEB_LOGIN_EXPIRY_MINUTES", 5)
    frontend_ms = 300_000  # LOGIN_EXPIRY_MS in frontend/src/pages/Login.vue
    backend_ms = backend_minutes * 60 * 1000
    if backend_ms != frontend_ms:
        msg = (
            f"WEB_LOGIN_EXPIRY_MINUTES={backend_minutes} ({backend_ms}ms) does not "
            f"match frontend LOGIN_EXPIRY_MS={frontend_ms}ms. Update one to match "
            "the other to avoid inconsistent login expiry behaviour."
        )
        logger.warning("CONFIG: %s", msg)
        errors.append(Warning(msg, id="web.W001"))
    return errors


@register()
def check_sqlite_thread_pool_conflict(app_configs, **kwargs):
    """Error when SQLite is used with multiple background login threads.

    SQLite uses file-level locking — only one writer at a time.  When
    ``WEB_LOGIN_THREAD_POOL_SIZE > 1``, multiple background threads
    attempt concurrent DB writes, causing "database is locked" errors
    and silent deadlocks under load.
    """
    errors = []
    engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
    pool_size = getattr(settings, "WEB_LOGIN_THREAD_POOL_SIZE", 1)
    if "sqlite" in engine and pool_size > 1:
        msg = (
            f"SQLite backend ({engine}) is configured with "
            f"WEB_LOGIN_THREAD_POOL_SIZE={pool_size}. SQLite uses file-level "
            "locking and cannot handle concurrent writes from multiple "
            "background threads. Set WEB_LOGIN_THREAD_POOL_SIZE=1 or switch "
            "to PostgreSQL for concurrent login processing."
        )
        logger.warning("CONFIG: %s", msg)
        errors.append(Error(msg, id="web.E003"))
    return errors
