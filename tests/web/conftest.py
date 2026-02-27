"""Shared fixtures and helpers for web test modules."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from django.test import Client

from src.core.models import User


def _call_async_mock(return_value):
    """Side effect for call_async mock that properly closes unawaited coroutines."""
    def _impl(coro):
        if hasattr(coro, 'close'):
            coro.close()
        return return_value
    return _impl


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username="tg_999999999",
        telegram_id="999999999",
        name="Test User",
        language="en",
        timezone="UTC",
    )


@pytest.fixture
def auth_client(user):
    """Create an authenticated Django test client."""
    client = Client()
    client.force_login(user)
    return client


def _mock_habit(id=1, name="Running", weight=10):
    """Create a mock habit object."""
    h = MagicMock()
    h.id = id
    h.name = name
    h.weight = weight
    h.active = True
    return h


def _mock_habit_log(habit_id=1):
    """Create a mock habit log."""
    log = MagicMock()
    log.habit_id = habit_id
    return log


def _mock_progress(reward_id=1, name="Coffee", pieces_earned=2,
                   pieces_required=3, status_name="PENDING", is_recurring=True):
    """Create a mock reward progress."""
    reward = MagicMock()
    reward.id = reward_id
    reward.name = name
    reward.is_recurring = is_recurring

    progress = MagicMock()
    progress.reward = reward
    progress.pieces_earned = pieces_earned
    progress.get_pieces_required.return_value = pieces_required

    status = MagicMock()
    status.name = status_name
    status.value = f"emoji {status_name}"
    progress.get_status.return_value = status

    return progress


INERTIA_HEADERS = {"HTTP_X_INERTIA": "true", "HTTP_X_INERTIA_VERSION": "1.0"}


def _inertia_props(response):
    """Extract Inertia props from a JSON response."""
    data = json.loads(response.content)
    return data["component"], data["props"]
