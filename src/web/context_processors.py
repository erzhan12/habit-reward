"""Template context processors for the web layer."""


def csp_nonce(request):
    """Make the CSP nonce available as ``{{ csp_nonce }}`` in templates.

    When a Content-Security-Policy middleware (e.g. django-csp) is active,
    it attaches a per-request nonce to ``request.csp_nonce``.  This context
    processor exposes that value so templates can allowlist inline scripts
    and styles without resorting to ``'unsafe-inline'``.

    If no CSP middleware is installed, returns an empty string (no-op).

    Usage in a Django template::

        <style nonce="{{ csp_nonce }}">
            body { background: #fff; }
        </style>

        <script nonce="{{ csp_nonce }}">
            console.log("allowed by CSP");
        </script>
    """
    return {"csp_nonce": getattr(request, "csp_nonce", "")}
