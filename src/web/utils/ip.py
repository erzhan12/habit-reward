"""IP address parsing and validation utilities."""

import ipaddress
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def parse_ip_address(request) -> str:
    """Extract and validate the client IP from the request.

    When ``settings.TRUST_X_FORWARDED_FOR`` is True, takes the leftmost IP
    from the X-Forwarded-For header (the original client IP when behind a
    trusted reverse proxy) and validates it with ``ipaddress.ip_address()``.
    Falls back to REMOTE_ADDR if the header is missing, malformed, or if
    the setting is disabled (default).

    Args:
        request: Django HttpRequest (or any object with a ``.META`` dict).

    Returns:
        Validated IP address string, or ``"unknown"`` if nothing is available.

    IMPORTANT: Only enable TRUST_X_FORWARDED_FOR when Django is behind a
    reverse proxy (e.g. nginx or Caddy) that overwrites X-Forwarded-For
    with the real client IP.
    """
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            # Take the leftmost IP (original client) regardless of chain
            # length. Multi-proxy chains (CDN → LB → app) are legitimate.
            # Log at DEBUG for visibility without rejecting valid requests.
            parts = [p.strip() for p in forwarded.split(",")]
            if len(parts) > 2:
                logger.debug(
                    "X-Forwarded-For contains %d IPs (multi-proxy chain): %s",
                    len(parts),
                    forwarded[:100],
                )
            candidate = parts[0]
            try:
                ipaddress.ip_address(candidate)
                return candidate
            except ValueError:
                pass
    return request.META.get("REMOTE_ADDR", "unknown")
