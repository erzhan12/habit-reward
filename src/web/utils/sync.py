"""Sync bridge for calling async repository methods from Django views.

Django 5.x runserver uses ASGI by default, which means an event loop is
running on a background thread.  The shared ``run_sync_or_async`` helper
detects that loop and returns the coroutine (expecting the caller to await
it), but Django sync views cannot await.

This module uses ``asgiref.sync.async_to_sync`` which is purpose-built for
this exact scenario — calling async code from synchronous Django views
running under an ASGI server.
"""

from __future__ import annotations

from typing import Awaitable, TypeVar

from asgiref.sync import async_to_sync

T = TypeVar("T")


def call_async(coro: Awaitable[T]) -> T:
    """Execute an async coroutine synchronously using asgiref.

    Works correctly under both WSGI and ASGI Django servers.
    """

    async def _wrapper() -> T:
        return await coro

    return async_to_sync(_wrapper)()
