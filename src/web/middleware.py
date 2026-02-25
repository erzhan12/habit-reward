"""Web interface middleware."""

from django.conf import settings
from django.contrib.messages import get_messages
from django.shortcuts import redirect

from inertia import share


class WebAuthMiddleware:
    """Redirect unauthenticated users to login for web routes.

    Exempt paths: /auth/*, /admin/*, /webhook/*, /static/*
    """

    EXEMPT_PREFIXES = ("/auth/", "/admin/", "/webhook/", "/static/", "/api/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Skip exempt paths
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return self.get_response(request)

        # Redirect unauthenticated users to login
        if not request.user.is_authenticated:
            return redirect("/auth/login/")

        return self.get_response(request)


class InertiaFlashMiddleware:
    """Share Django messages as Inertia flash props.

    Reads messages from the session (set by previous request) and shares
    them as ``flash`` prop so Layout.vue can display toast notifications.
    Must run before InertiaMiddleware in the MIDDLEWARE list.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        flash = [
            {"type": m.tags.split()[-1] if m.tags else "info", "text": str(m)}
            for m in get_messages(request)
        ]
        share(request, flash=flash)
        return self.get_response(request)


class ContentSecurityPolicyMiddleware:
    """Set Content-Security-Policy and other security headers on all responses.

    In production (DEBUG=False), applies a strict CSP and security headers.
    In development, skips these headers to allow Vite HMR.

    CSP tradeoff: style-src includes 'unsafe-inline' because Tailwind/Vue
    and component-scoped styles often rely on inline styles. Alternatives
    (nonces or hashes) would require build/template changes; documented here
    for future hardening.

    script-src includes 'unsafe-eval' because the Telegram Login Widget
    (telegram-widget.js) uses eval() internally for __parseFunction.
    """

    CSP_POLICY = "; ".join([
        "default-src 'self'",
        "script-src 'self' 'unsafe-eval' https://telegram.org",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "frame-src https://oauth.telegram.org",
        "connect-src 'self'",
    ])

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not settings.DEBUG:
            response["Content-Security-Policy"] = self.CSP_POLICY
            response["X-Content-Type-Options"] = "nosniff"
            response["X-Frame-Options"] = "DENY"
            response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
