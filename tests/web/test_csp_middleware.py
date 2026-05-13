"""Tests for ContentSecurityPolicyMiddleware (issue #24).

Verifies the split-directive CSP policy: strict ``style-src-elem`` for
``<style>`` blocks (no ``'unsafe-inline'``), permissive
``style-src-attr`` for Vue ``:style`` bindings, and a legacy
``style-src`` fallback for browsers that do not support the split
directives.
"""

import re

import pytest
from django.http import HttpResponse
from django.test import Client, RequestFactory, override_settings

from src.web.middleware import ContentSecurityPolicyMiddleware


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _parse_csp(header_value: str) -> dict[str, list[str]]:
    """Parse a Content-Security-Policy header into ``{directive: [tokens]}``.

    Split the header on ``;``, strip whitespace, then split each directive
    on its first run of whitespace.  Directive names are returned as-is.

    All directive lookups MUST use this parsed dict, never substring matches
    on the raw header — ``style-src`` is a prefix of ``style-src-elem`` and
    ``style-src-attr``, so ``'style-src' in header`` produces false positives.
    """
    parsed: dict[str, list[str]] = {}
    for directive in header_value.split(";"):
        directive = directive.strip()
        if not directive:
            continue
        parts = directive.split(None, 1)
        name = parts[0]
        tokens = parts[1].split() if len(parts) > 1 else []
        parsed[name] = tokens
    return parsed


def _ok_response(request):
    """Stub get_response returning a 200 OK."""
    return HttpResponse("ok")


def _run_middleware(request):
    """Invoke ContentSecurityPolicyMiddleware against ``request`` directly."""
    middleware = ContentSecurityPolicyMiddleware(_ok_response)
    return middleware(request)


# Production-mode settings override: DEBUG=False AND
# DJANGO_VITE['default']['dev_mode']=False.  See
# src/habit_reward_project/settings.py:316-322 — DJANGO_VITE['default']
# ['dev_mode'] is initialized from DEBUG at import time, so overriding
# only DEBUG leaves Vite in dev mode and integration tests that render
# base.html will not exercise the production asset path.
_PRODUCTION_SETTINGS = dict(
    DEBUG=False,
    DJANGO_VITE={
        "default": {
            "dev_mode": False,
            "dev_server_host": "localhost",
            "dev_server_port": 5173,
        }
    },
)


# -----------------------------------------------------------------------------
# Unit tests — drive the middleware directly with RequestFactory
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestContentSecurityPolicyMiddleware:
    """Direct unit tests for the CSP middleware.

    These tests do not render templates, so overriding ``DEBUG`` alone is
    sufficient — they do not exercise ``django_vite``.
    """

    def setup_method(self):
        self.factory = RequestFactory()

    @override_settings(DEBUG=False)
    def test_csp_header_set_in_production(self):
        request = self.factory.get("/")
        response = _run_middleware(request)
        assert "Content-Security-Policy" in response

    @override_settings(DEBUG=True)
    def test_csp_header_absent_in_debug(self):
        request = self.factory.get("/")
        response = _run_middleware(request)
        assert "Content-Security-Policy" not in response

    @override_settings(DEBUG=False)
    def test_csp_includes_style_src_elem_with_nonce(self):
        request = self.factory.get("/")
        response = _run_middleware(request)
        parsed = _parse_csp(response["Content-Security-Policy"])

        assert "style-src-elem" in parsed
        tokens = parsed["style-src-elem"]
        assert "'self'" in tokens
        assert "https://fonts.googleapis.com" in tokens
        # Strict: no 'unsafe-inline' on -elem.
        assert "'unsafe-inline'" not in tokens
        # Nonce token must match the request nonce.
        nonce_tokens = [t for t in tokens if t.startswith("'nonce-")]
        assert len(nonce_tokens) == 1
        # Strip "'nonce-" prefix and trailing "'".
        nonce_value = nonce_tokens[0][len("'nonce-") : -1]
        assert nonce_value == request.csp_nonce

    @override_settings(DEBUG=False)
    def test_csp_includes_style_src_attr_with_unsafe_inline(self):
        request = self.factory.get("/")
        response = _run_middleware(request)
        parsed = _parse_csp(response["Content-Security-Policy"])

        assert "style-src-attr" in parsed
        assert parsed["style-src-attr"] == ["'unsafe-inline'"]

    @override_settings(DEBUG=False)
    def test_csp_legacy_style_src_fallback(self):
        request = self.factory.get("/")
        response = _run_middleware(request)
        parsed = _parse_csp(response["Content-Security-Policy"])

        assert "style-src" in parsed
        tokens = parsed["style-src"]
        assert "'self'" in tokens
        assert "'unsafe-inline'" in tokens
        assert "https://fonts.googleapis.com" in tokens
        nonce_tokens = [t for t in tokens if t.startswith("'nonce-")]
        assert len(nonce_tokens) == 1

    @override_settings(DEBUG=False)
    def test_csp_nonce_is_unique_per_request(self):
        request1 = self.factory.get("/")
        response1 = _run_middleware(request1)
        request2 = self.factory.get("/")
        response2 = _run_middleware(request2)

        parsed1 = _parse_csp(response1["Content-Security-Policy"])
        parsed2 = _parse_csp(response2["Content-Security-Policy"])

        nonce1 = next(t for t in parsed1["style-src-elem"] if t.startswith("'nonce-"))
        nonce2 = next(t for t in parsed2["style-src-elem"] if t.startswith("'nonce-"))
        assert nonce1 != nonce2

    @override_settings(DEBUG=False)
    def test_csp_nonce_attached_to_request(self):
        request = self.factory.get("/")
        _run_middleware(request)
        # secrets.token_urlsafe(16) → 22-char base64-url string.
        assert isinstance(request.csp_nonce, str)
        assert len(request.csp_nonce) >= 16

    @override_settings(DEBUG=False)
    def test_other_security_headers_set(self):
        request = self.factory.get("/")
        response = _run_middleware(request)
        assert response["X-Content-Type-Options"] == "nosniff"
        assert response["X-Frame-Options"] == "DENY"
        assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"

    @override_settings(DEBUG=False)
    def test_unchanged_directives_remain_present(self):
        """Other CSP directives must not regress."""
        request = self.factory.get("/")
        response = _run_middleware(request)
        parsed = _parse_csp(response["Content-Security-Policy"])

        assert parsed["default-src"] == ["'self'"]
        assert parsed["script-src"] == ["'self'"]
        assert parsed["font-src"] == ["'self'", "https://fonts.gstatic.com"]
        assert parsed["img-src"] == ["'self'", "data:", "https:"]
        assert parsed["connect-src"] == ["'self'"]

    @override_settings(DEBUG=False)
    def test_csp_header_format_integrity(self):
        """Header is a single line, directives separated by ``;``."""
        request = self.factory.get("/")
        response = _run_middleware(request)
        header = response["Content-Security-Policy"]
        assert "\n" not in header
        assert "\r" not in header
        # Directive separator is ``;`` — there must be no stray commas
        # outside of source-expression values (none of which use commas).
        assert "," not in header


# -----------------------------------------------------------------------------
# Integration test — exercises the full template rendering pipeline
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestCSPNonceTemplateIntegration:
    """End-to-end check that meta-tag nonce equals CSP-header nonce."""

    @override_settings(**_PRODUCTION_SETTINGS)
    def test_template_meta_nonce_matches_csp_header(self):
        """The ``<meta name="csp-nonce">`` value in the rendered HTML
        must equal the nonce embedded in the ``style-src-elem`` CSP
        directive — confirms middleware and context processor share the
        same per-request nonce.

        Uses ``/auth/login/`` because it renders ``base.html`` without
        requiring authentication or heavy view-layer mocks.
        """
        response = Client().get("/auth/login/")
        assert response.status_code == 200
        assert "Content-Security-Policy" in response

        body = response.content.decode("utf-8")
        match = re.search(
            r'<meta\s+name="csp-nonce"\s+content="([^"]*)"', body
        )
        assert match is not None, "csp-nonce meta tag not found in response"
        meta_nonce = match.group(1)
        assert meta_nonce, "csp-nonce meta tag has empty content"

        parsed = _parse_csp(response["Content-Security-Policy"])
        elem_tokens = parsed["style-src-elem"]
        nonce_token = next(t for t in elem_tokens if t.startswith("'nonce-"))
        # Normalize: strip surrounding quotes and the ``nonce-`` prefix.
        # E.g. "'nonce-abc123'" → "abc123".
        header_nonce = nonce_token.strip("'")[len("nonce-") :]

        assert header_nonce == meta_nonce
