"""Web interface middleware."""

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
