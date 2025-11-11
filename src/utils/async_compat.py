"""Helpers for bridging sync and async call sites."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Awaitable, TypeVar

T = TypeVar("T")


def run_sync_or_async(coro: Awaitable[T]) -> T | Awaitable[T]:
    """Execute *coro* immediately when no event loop is running.

    When invoked inside an async context the original coroutine is returned so
    the caller can ``await`` it normally. This allows a single service method to
    support both synchronous unit tests and asynchronous production handlers.
    """

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return coro


async def maybe_await(value: Any) -> Any:
    """Await *value* when it is awaitable, otherwise return it directly."""

    if inspect.isawaitable(value):
        return await value
    return value

