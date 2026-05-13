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
        if request.user.is_authenticated:
            share(request, userTheme=request.user.theme)
        return self.get_response(request)


class ContentSecurityPolicyMiddleware:
    """Set Content-Security-Policy and other security headers on all responses.

    In production (DEBUG=False), applies a strict CSP and security headers.
    In development, skips these headers to allow Vite HMR.

    A per-request nonce, stored on ``request.csp_nonce`` and exposed to
    templates via the ``csp_nonce`` context processor, locks down
    ``<style>`` blocks and ``<link rel="stylesheet">`` references.

    Partial resolution of issue #24: ``style-src`` is split into
    ``style-src-elem`` (strict — no ``'unsafe-inline'``) and
    ``style-src-attr`` (still ``'unsafe-inline'`` for Vue ``:style``
    bindings).  A legacy ``style-src`` directive is kept as a fallback
    for older browsers that do not understand the split directives —
    those browsers ignore the unknown ``-elem``/``-attr`` directives
    and fall back to ``style-src``, which retains ``'unsafe-inline'``
    for backward compatibility.  Modern browsers (Chrome 75+, Firefox
    109+, Safari 15.4+) honor the strict split and ignore the legacy
    directive.  See https://github.com/erzhan12/habit-reward/issues/24.
    """

    # Template with {nonce} placeholder, filled per-request.
    _CSP_TEMPLATE = "; ".join([
        "default-src 'self'",
        "script-src 'self'",
        # Strict <style> / <link rel=stylesheet> policy: nonce + allowlist,
        # no 'unsafe-inline'.  Honored by modern CSP3 browsers.
        "style-src-elem 'self' 'nonce-{nonce}' https://fonts.googleapis.com",
        # Permissive inline style="..." attribute policy for Vue :style
        # bindings.  TODO(#24): eliminate :style bindings so we can drop
        # 'unsafe-inline' here too.
        "style-src-attr 'unsafe-inline'",
        # Legacy fallback for browsers that do not honor style-src-elem /
        # style-src-attr (pre-CSP3).  Those browsers fall through to this
        # directive, which keeps 'unsafe-inline' so the app still renders.
        # TODO(#24): drop once old-browser traffic is negligible.
        "style-src 'self' 'nonce-{nonce}' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
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
