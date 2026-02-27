"""Django system checks for the web layer."""

import logging

from django.conf import settings
from django.core.checks import Error, Warning, register

logger = logging.getLogger(__name__)


@register()
def check_xff_trust_configuration(app_configs, **kwargs):
    """Error if TRUST_X_FORWARDED_FOR=True but no reverse proxy indicators.

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
            if settings.DEBUG:
                msg = (
                    "TRUST_X_FORWARDED_FOR enabled in development mode — "
                    "ensure you configure a reverse proxy before deploying "
                    "to production."
                )
                logger.warning("SECURITY: %s", msg)
                errors.append(Warning(msg, id="web.W003"))
            else:
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
    """Warn or error when SQLite is used with multiple background login threads.

    SQLite uses file-level locking — only one writer at a time.  With
    2-10 threads you may see occasional "database is locked" errors
    under load (Warning).  Above 10 threads, deadlocks become likely
    and PostgreSQL should be used instead (Error).
    """
    errors = []
    engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
    pool_size = getattr(settings, "WEB_LOGIN_THREAD_POOL_SIZE", 1)
    if "sqlite" in engine and pool_size > 10:
        msg = (
            f"SQLite backend ({engine}) is configured with "
            f"WEB_LOGIN_THREAD_POOL_SIZE={pool_size}. SQLite cannot reliably "
            "handle >10 concurrent write threads. Switch to PostgreSQL or "
            "reduce WEB_LOGIN_THREAD_POOL_SIZE to 10 or fewer."
        )
        logger.warning("CONFIG: %s", msg)
        errors.append(Error(msg, id="web.E003"))
    elif "sqlite" in engine and pool_size > 1:
        msg = (
            f"SQLite backend ({engine}) is configured with "
            f"WEB_LOGIN_THREAD_POOL_SIZE={pool_size}. SQLite uses file-level "
            "locking and may produce 'database is locked' errors under "
            "concurrent load. Consider switching to PostgreSQL for "
            "production use, or set WEB_LOGIN_THREAD_POOL_SIZE=1."
        )
        logger.warning("CONFIG: %s", msg)
        errors.append(Warning(msg, id="web.W002"))
    return errors


@register()
def check_thread_pool_vs_db_connections(app_configs, **kwargs):
    """Warn when thread pool size risks exceeding database max_connections.

    Each background login thread may hold a persistent DB connection
    (CONN_MAX_AGE > 0).  With Django's main thread, management commands,
    and potential multiple workers, the total connection demand can exceed
    the database's max_connections limit.  We use a 2x safety margin.

    For PostgreSQL, we attempt to read the actual max_connections setting.
    For other backends, we use a conservative default of 100.
    """
    errors = []
    pool_size = getattr(settings, "WEB_LOGIN_THREAD_POOL_SIZE", 10)
    engine = settings.DATABASES.get("default", {}).get("ENGINE", "")

    # Skip for SQLite — it doesn't have a connection limit.
    if "sqlite" in engine:
        return errors

    max_connections = None
    if "postgresql" in engine or "postgis" in engine:
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SHOW max_connections")
                max_connections = int(cursor.fetchone()[0])
        except Exception:
            pass

    if max_connections is None:
        # Conservative default for unknown backends.
        max_connections = 100

    required = pool_size * 2  # safety margin for main thread + workers
    if required > max_connections:
        msg = (
            f"WEB_LOGIN_THREAD_POOL_SIZE={pool_size} (×2 safety margin = "
            f"{required} connections) may exceed the database "
            f"max_connections={max_connections}. Reduce the thread pool size "
            "or increase max_connections to avoid connection exhaustion."
        )
        logger.warning("CONFIG: %s", msg)
        errors.append(Warning(msg, id="web.W006"))
    return errors


@register()
def check_sqlite_conn_max_age(app_configs, **kwargs):
    """Warn when CONN_MAX_AGE is set on SQLite (no pooling effect)."""
    errors = []
    db_config = settings.DATABASES.get("default", {})
    engine = db_config.get("ENGINE", "")
    conn_max_age = int(db_config.get("CONN_MAX_AGE", 0) or 0)
    if "sqlite" in engine and conn_max_age > 0:
        msg = (
            f"CONN_MAX_AGE={conn_max_age} is set for SQLite backend ({engine}), "
            "but SQLite does not benefit from persistent connection pooling. "
            "Use CONN_MAX_AGE=0 for SQLite, or switch to PostgreSQL/MySQL to "
            "benefit from connection reuse."
        )
        logger.warning("CONFIG: %s", msg)
        errors.append(Warning(msg, id="web.W007"))
    return errors


@register()
def check_sqlite_username_constraint(app_configs, **kwargs):
    """Error when SQLite is used with the User.telegram_username regex constraint.

    The CheckConstraint on User.telegram_username uses ``__regex`` which maps
    to PostgreSQL's ``~`` operator.  SQLite supports regex via a Python
    callback but the engine differs from PostgreSQL's — locale handling,
    character class semantics, and edge cases may diverge.  This could
    allow invalid usernames to pass the CHECK constraint on SQLite while
    being correctly rejected on PostgreSQL.

    Production deployments MUST use PostgreSQL for reliable constraint
    enforcement.  SQLite is acceptable only for local development/testing.
    """
    errors = []
    engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
    if "sqlite" in engine:
        msg = (
            "CRITICAL: SQLite backend detected. User.telegram_username CHECK "
            "constraint uses PostgreSQL regex syntax (__regex) which behaves "
            "differently on SQLite. DO NOT USE SQLite IN PRODUCTION. "
            "For local development, you can disable this check by setting "
            "SILENCED_SYSTEM_CHECKS=['web.E004'] in settings, but you MUST "
            "migrate to PostgreSQL before deploying."
        )
        errors.append(Error(msg, id="web.E004"))
    return errors
