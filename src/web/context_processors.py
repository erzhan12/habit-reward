"""Template context processors for the web layer."""


def csp_nonce(request):
    """Make the CSP nonce available as ``{{ csp_nonce }}`` in templates.

    Reads the per-request nonce attached by
    :class:`src.web.middleware.ContentSecurityPolicyMiddleware` so
    templates can allowlist inline scripts and styles without resorting
    to ``'unsafe-inline'``.

    If the middleware did not run (e.g. tests bypassing the stack),
    returns an empty string (no-op).

    Usage in a Django template::

        <style nonce="{{ csp_nonce }}">
            body { background: #fff; }
        </style>

        <script nonce="{{ csp_nonce }}">
            console.log("allowed by CSP");
        </script>
    """
    return {"csp_nonce": getattr(request, "csp_nonce", "")}
