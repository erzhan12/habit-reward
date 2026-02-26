"""Template context processors for the web layer."""


def csp_nonce(request):
    """Make the CSP nonce available as {{ csp_nonce }} in templates."""
    return {"csp_nonce": getattr(request, "csp_nonce", "")}
