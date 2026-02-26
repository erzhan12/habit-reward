"""Django system checks for the web layer."""

import logging

from django.conf import settings
from django.core.checks import Warning, register

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
            errors.append(Warning(msg, id="web.W001"))
        if not settings.DEBUG:
            msg = (
                "TRUST_X_FORWARDED_FOR=True in a production environment "
                "(DEBUG=False). Ensure Django is behind a trusted reverse proxy "
                "(nginx, Caddy, etc.) that overwrites the X-Forwarded-For "
                "header. Without this, clients can spoof their IP address."
            )
            logger.warning("SECURITY: %s", msg)
            errors.append(Warning(msg, id="web.W002"))
    return errors
