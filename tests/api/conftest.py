"""Shared fixtures for API tests."""

import pytest
from datetime import date
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from src.api.main import create_app
from src.api.dependencies.auth import get_current_active_user, get_current_user_flexible
from src.core.models import User, Habit, Reward, HabitLog, RewardProgress, AuthCode, APIKey


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = MagicMock(spec=User)
    user.id = 1
    user.telegram_id = "123456789"
    user.name = "Test User"
    user.language = "en"
    user.is_active = True
    user.username = "tg_123456789"
    return user


@pytest.fixture
def mock_inactive_user():
    """Create a mock inactive user for testing."""
    user = MagicMock(spec=User)
    user.id = 2
    user.telegram_id = "987654321"
    user.name = "Inactive User"
    user.language = "en"
    user.is_active = False
    user.username = "tg_987654321"
    return user


@pytest.fixture
def mock_habit(mock_user):
    """Create a mock habit for testing."""
    habit = MagicMock(spec=Habit)
    habit.id = 1
    habit.user_id = mock_user.id
    habit.name = "Morning Exercise"
    habit.weight = 10
    habit.category = "health"
    habit.allowed_skip_days = 0
    habit.exempt_weekdays = []
    habit.active = True
    return habit


@pytest.fixture
def mock_inactive_habit(mock_user):
    """Create a mock inactive habit for testing."""
    habit = MagicMock(spec=Habit)
    habit.id = 2
    habit.user_id = mock_user.id
    habit.name = "Inactive Habit"
    habit.weight = 5
    habit.category = "other"
    habit.allowed_skip_days = 0
    habit.exempt_weekdays = []
    habit.active = False
    return habit


@pytest.fixture
def mock_reward(mock_user):
    """Create a mock reward for testing."""
    reward = MagicMock(spec=Reward)
    reward.id = 1
    reward.user_id = mock_user.id
    reward.name = "Coffee"
    reward.weight = 10.0
    reward.pieces_required = 10
    reward.piece_value = None
    reward.max_daily_claims = None
    reward.active = True
    return reward


@pytest.fixture
def mock_reward_progress(mock_user, mock_reward):
    """Create a mock reward progress for testing."""
    progress = MagicMock(spec=RewardProgress)
    progress.id = 1
    progress.user_id = mock_user.id
    progress.reward_id = mock_reward.id
    progress.pieces_earned = 5
    progress.claimed = False
    progress.reward = mock_reward
    progress._cached_pieces_required = mock_reward.pieces_required

    # Mock methods
    def get_status():
        status = MagicMock()
        status.value = "pending"
        return status

    progress.get_status = get_status
    progress.get_pieces_required = lambda: mock_reward.pieces_required
    progress.get_progress_percent = lambda: 50.0
    progress.progress_percent = 50.0

    return progress


@pytest.fixture
def mock_habit_log(mock_user, mock_habit, mock_reward):
    """Create a mock habit log for testing."""
    from datetime import datetime

    log = MagicMock(spec=HabitLog)
    log.id = 1
    log.user_id = mock_user.id
    log.habit_id = mock_habit.id
    log.habit = mock_habit
    log.reward_id = mock_reward.id
    log.reward = mock_reward
    log.got_reward = True
    log.streak_count = 5
    log.habit_weight = 10
    log.total_weight_applied = 1.5
    log.last_completed_date = date.today()
    # Make timestamp a datetime object so .isoformat() works
    log.timestamp = datetime(2025, 12, 10, 12, 0, 0)
    return log


@pytest.fixture
def mock_auth_code(mock_user):
    """Create a mock auth code for testing."""
    from datetime import datetime, timezone, timedelta

    code = MagicMock(spec=AuthCode)
    code.id = 1
    code.user_id = mock_user.id
    code.user = mock_user
    code.code = "123456"
    code.created_at = datetime.now(timezone.utc)
    code.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    code.used = False
    code.device_info = "Test Device"
    code.failed_attempts = 0
    code.locked_until = None
    return code


@pytest.fixture
def mock_api_key(mock_user):
    """Create a mock API key for testing."""
    from datetime import datetime, timezone

    key = MagicMock(spec=APIKey)
    key.id = 1
    key.user_id = mock_user.id
    key.user = mock_user
    key.key_hash = "hashed_key_value"
    key.name = "Test App"
    key.created_at = datetime.now(timezone.utc)
    key.last_used_at = None
    key.is_active = True
    key.expires_at = None
    return key


@pytest.fixture
def client(mock_user):
    """Create a test client with authentication override."""
    app = create_app()
    # Override both authentication dependencies
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[get_current_user_flexible] = lambda: mock_user

    with TestClient(app) as test_client:
        yield test_client

    # Clear overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth():
    """Create a test client without authentication override."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
