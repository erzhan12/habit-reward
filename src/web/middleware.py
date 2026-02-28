"""Web interface middleware."""

import secrets

from django.conf import settings
from django.contrib.messages import get_messages
from django.shortcuts import redirect

from inertia import share

import src.web.checks  # noqa: F401 — register system checks


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

    A per-request nonce replaces the old ``'unsafe-inline'`` for style-src.
    The nonce is stored on ``request.csp_nonce`` and made available in
    templates via the ``csp_nonce`` context processor.

    Note: Vue 3 runtime style injection (scoped component styles) may still
    require ``'unsafe-inline'`` as a fallback until Vue adds native nonce
    support for injected ``<style>`` tags.  The nonce covers any inline
    styles in Django templates and manually authored ``<style>`` blocks.
    """

    # Template with {nonce} placeholder, filled per-request.
    _CSP_TEMPLATE = "; ".join([
        "default-src 'self'",
        "script-src 'self'",
        # 'unsafe-inline' is needed for Vue 3 scoped styles which inject
        # <style> tags at runtime without nonce support.  The nonce still
        # covers Django template styles and manually authored blocks.
        # TODO(#24): Remove 'unsafe-inline' once Vue build pipeline supports
        # nonce injection for scoped styles (e.g. via
        # vite-plugin-css-injected-by-js or SFC compiler nonce option).
        # See: https://github.com/erzhan12/habit-reward/issues/24
        "style-src 'self' 'nonce-{nonce}' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "connect-src 'self'",
    ])

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate a per-request nonce for CSP.
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)
        if not settings.DEBUG:
            response["Content-Security-Policy"] = self._CSP_TEMPLATE.format(
                nonce=request.csp_nonce
            )
            response["X-Content-Type-Options"] = "nosniff"
            response["X-Frame-Options"] = "DENY"
            response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
