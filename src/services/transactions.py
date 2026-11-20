"""Single-transaction execution with bounded retry (feature 0048 §4).

Every freeze-touching write path (completion, backdate recalculation, undo, the
freeze job, admin actions) runs as ONE synchronous function inside one
``transaction.atomic()``, with no ``await`` between BEGIN and COMMIT. Overlapping
coroutines on a shared thread-sensitive connection would otherwise nest as
savepoints of each other.

On lock contention (SQLite "database is locked", PostgreSQL serialization or
deadlock errors) the whole function is re-run: nothing was committed, and random
draws are made again inside the new attempt.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import TypeVar

from asgiref.sync import sync_to_async
from django.db import OperationalError, transaction

logger = logging.getLogger(__name__)

T = TypeVar("T")

RETRY_DELAYS_SECONDS = (0.05, 0.15, 0.4)

_LOCK_ERROR_MARKERS = (
    "database is locked",        # SQLite, file database
    "database table is locked",  # SQLite, shared-cache (in-memory test) database
    "could not serialize",       # PostgreSQL serialization failure
    "deadlock detected",         # PostgreSQL
)


class ServiceBusyError(RuntimeError):
    """The database stayed busy through every retry; the caller should ask the user to retry.

    Deliberately not a ``ValueError``: callers map ``ValueError`` to validation
    messages (e.g. "already completed"), while this maps to HTTP 503 / "busy".
    """


def is_lock_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in _LOCK_ERROR_MARKERS)


def _atomic_call(fn: Callable[..., T], *args, **kwargs) -> T:
    with transaction.atomic():
        return fn(*args, **kwargs)


async def run_in_transaction(fn: Callable[..., T], *args, **kwargs) -> T:
    """Run ``fn`` in one transaction on the thread-sensitive DB thread, retrying on lock errors."""
    attempts = len(RETRY_DELAYS_SECONDS) + 1
    for attempt in range(attempts):
        try:
            return await sync_to_async(_atomic_call, thread_sensitive=True)(fn, *args, **kwargs)
        except OperationalError as exc:
            if not is_lock_error(exc):
                raise
            if attempt == attempts - 1:
                logger.warning("%s: database busy after %s attempts", getattr(fn, "__name__", fn), attempts)
                raise ServiceBusyError("Database is busy, please try again") from exc
            await asyncio.sleep(RETRY_DELAYS_SECONDS[attempt])
    raise AssertionError("unreachable")  # pragma: no cover


def run_in_transaction_sync(fn: Callable[..., T], *args, **kwargs) -> T:
    """Sync variant for callers already on a sync thread (admin actions, management code)."""
    attempts = len(RETRY_DELAYS_SECONDS) + 1
    for attempt in range(attempts):
        try:
            return _atomic_call(fn, *args, **kwargs)
        except OperationalError as exc:
            if not is_lock_error(exc):
                raise
            if attempt == attempts - 1:
                logger.warning("%s: database busy after %s attempts", getattr(fn, "__name__", fn), attempts)
                raise ServiceBusyError("Database is busy, please try again") from exc
            time.sleep(RETRY_DELAYS_SECONDS[attempt])
    raise AssertionError("unreachable")  # pragma: no cover
