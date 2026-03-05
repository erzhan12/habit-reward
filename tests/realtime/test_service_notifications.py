"""Tests that habit service triggers WebSocket notifications."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.services.habit_service import HabitService


def _setup_mocks(service):
    """Set up common mocks for habit service tests."""
    # Prevent _refresh_dependencies from resetting our mocks
    service._refresh_dependencies = lambda: None

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.telegram_id = "123"
    mock_user.timezone = "UTC"
    mock_user.is_active = True
    mock_user.no_reward_probability = 50.0

    mock_habit = MagicMock()
    mock_habit.id = 10
    mock_habit.name = "Exercise"
    mock_habit.weight = 5
    mock_habit.user_id = 1
    mock_habit.active = True
    mock_habit.created_at = MagicMock()
    mock_habit.created_at.date.return_value = __import__("datetime").date(2024, 1, 1)

    service.user_repo = MagicMock()
    service.user_repo.get_by_telegram_id = MagicMock(return_value=mock_user)
    service.habit_repo = MagicMock()
    service.habit_repo.get_by_name = MagicMock(return_value=mock_habit)
    service.habit_repo.get_by_id = MagicMock(return_value=mock_habit)
    service.habit_log_repo = MagicMock()
    service.habit_log_repo.get_log_for_habit_on_date = MagicMock(return_value=None)
    service.habit_log_repo.get_last_log_for_habit = MagicMock(return_value=None)
    service.habit_log_repo.create = MagicMock(return_value=MagicMock(id=100))
    service.streak_service = MagicMock()
    service.streak_service.calculate_streak = MagicMock(return_value=3)
    service.streak_service.cache_key = MagicMock(return_value="streaks:1")
    service.reward_service = MagicMock()
    service.reward_service.calculate_effective_no_reward_probability = MagicMock(return_value=40.0)
    service.reward_service.select_reward = MagicMock(return_value=None)
    service.reward_progress_repo = MagicMock()
    service.audit_log_service = MagicMock()
    service.audit_log_service.log_habit_completion = MagicMock(return_value=None)
    service.audit_log_service.log_habit_revert = MagicMock(return_value=None)

    return mock_user, mock_habit


def _mock_loop():
    """Create a mock event loop with create_task."""
    mock_loop = MagicMock()
    mock_loop.create_task = MagicMock()
    return mock_loop


@pytest.mark.asyncio
async def test_completion_triggers_notification():
    service = HabitService()
    mock_user, mock_habit = _setup_mocks(service)
    loop = _mock_loop()

    with patch("src.services.habit_service.connection_manager") as mock_cm:
        mock_cm.notify_user = AsyncMock()

        with (
            patch("src.services.habit_service.cache") as mock_cache,
            patch("src.services.habit_service.streak_service"),
            patch("src.services.habit_service.asyncio") as mock_asyncio,
        ):
            mock_asyncio.get_running_loop.return_value = loop
            mock_cache.adelete = AsyncMock()
            result = await service.process_habit_completion(
                user_telegram_id="123",
                habit_name="Exercise",
                user_timezone="UTC",
            )

        loop.create_task.assert_called_once()
        assert result.habit_confirmed is True


@pytest.mark.asyncio
async def test_notification_failure_doesnt_break_completion():
    service = HabitService()
    _setup_mocks(service)

    with patch("src.services.habit_service.connection_manager") as mock_cm:
        mock_cm.notify_user = AsyncMock(side_effect=RuntimeError("WS down"))

        with (
            patch("src.services.habit_service.cache") as mock_cache,
            patch("src.services.habit_service.streak_service"),
        ):
            mock_cache.adelete = AsyncMock()
            # Should NOT raise despite notification failure
            result = await service.process_habit_completion(
                user_telegram_id="123",
                habit_name="Exercise",
                user_timezone="UTC",
            )

        assert result.habit_confirmed is True


@pytest.mark.asyncio
async def test_revert_triggers_notification():
    service = HabitService()
    mock_user, mock_habit = _setup_mocks(service)
    loop = _mock_loop()

    # Set up a log to revert
    mock_log = MagicMock()
    mock_log.id = 100
    mock_log.got_reward = False
    mock_log.reward_id = None
    mock_log.reward = None
    service.habit_log_repo.get_last_log_for_habit = MagicMock(return_value=mock_log)
    service.habit_log_repo.delete = MagicMock(return_value=1)

    with patch("src.services.habit_service.connection_manager") as mock_cm:
        mock_cm.notify_user = AsyncMock()

        with (
            patch("src.services.habit_service.cache") as mock_cache,
            patch("src.services.habit_service.streak_service"),
            patch("src.services.habit_service.asyncio") as mock_asyncio,
        ):
            mock_asyncio.get_running_loop.return_value = loop
            mock_cache.adelete = AsyncMock()
            result = await service.revert_habit_completion(
                user_telegram_id="123",
                habit_id=10,
            )

        loop.create_task.assert_called_once()
        assert result.success is True


@pytest.mark.asyncio
async def test_revert_by_log_id_triggers_notification():
    service = HabitService()
    mock_user, mock_habit = _setup_mocks(service)
    loop = _mock_loop()

    mock_log = MagicMock()
    mock_log.id = 100
    mock_log.user_id = 1
    mock_log.habit_id = 10
    mock_log.got_reward = False
    mock_log.reward_id = None
    mock_log.reward = None
    service.habit_log_repo.get_by_id = MagicMock(return_value=mock_log)
    service.habit_log_repo.delete = MagicMock(return_value=1)

    with patch("src.services.habit_service.connection_manager") as mock_cm:
        mock_cm.notify_user = AsyncMock()

        with (
            patch("src.services.habit_service.cache") as mock_cache,
            patch("src.services.habit_service.streak_service"),
            patch("src.services.habit_service.asyncio") as mock_asyncio,
        ):
            mock_asyncio.get_running_loop.return_value = loop
            mock_cache.adelete = AsyncMock()
            result = await service.revert_habit_completion_by_log_id(
                user_id=1,
                log_id=100,
            )

        loop.create_task.assert_called_once()
        assert result.success is True
