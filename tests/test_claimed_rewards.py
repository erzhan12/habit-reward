"""Unit tests for the Claimed Rewards feature (Feature 0035)."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.services.reward_service import RewardService
from src.models.reward_progress import RewardProgress
from src.models.reward import Reward
from src.bot.formatters import format_claimed_rewards_message
from src.bot.keyboards import build_rewards_menu_keyboard


def _make_progress(
    *,
    pieces_earned: int = 0,
    pieces_required: int = 5,
    claimed: bool = False,
    reward_id: int = 1,
    user_id: int = 42,
) -> RewardProgress:
    """Build a Pydantic RewardProgress for testing."""
    return RewardProgress(
        id=reward_id,
        user_id=user_id,
        reward_id=reward_id,
        pieces_earned=pieces_earned,
        pieces_required=pieces_required,
        claimed=claimed,
    )


def _make_reward(
    *,
    reward_id: int = 1,
    name: str = "Test Reward",
    is_recurring: bool = False,
    pieces_required: int = 5,
) -> Reward:
    """Build a Pydantic Reward for testing."""
    return Reward(
        id=reward_id,
        name=name,
        weight=10.0,
        pieces_required=pieces_required,
        is_recurring=is_recurring,
    )


class TestGetClaimedOneTimeRewards:
    """Tests for RewardService.get_claimed_one_time_rewards()."""

    @pytest.fixture
    def service(self):
        svc = RewardService()
        svc.progress_repo = AsyncMock()
        return svc

    @pytest.mark.asyncio
    async def test_empty_when_no_claimed(self, service):
        """Returns empty list when user has no claimed one-time rewards."""
        service.progress_repo.get_claimed_non_recurring_by_user.return_value = []

        result = await service.get_claimed_one_time_rewards("42")

        assert result == []
        service.progress_repo.get_claimed_non_recurring_by_user.assert_called_once_with("42")

    @pytest.mark.asyncio
    async def test_returns_claimed_non_recurring(self, service):
        """Returns claimed non-recurring rewards."""
        service.progress_repo.get_claimed_non_recurring_by_user.return_value = [
            _make_progress(pieces_earned=0, pieces_required=5, claimed=True, reward_id=1),
            _make_progress(pieces_earned=0, pieces_required=3, claimed=True, reward_id=2),
        ]

        result = await service.get_claimed_one_time_rewards("42")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_coerces_results(self, service):
        """Results are coerced through _coerce_progress."""
        service.progress_repo.get_claimed_non_recurring_by_user.return_value = [
            _make_progress(pieces_earned=0, pieces_required=5, claimed=True, reward_id=1),
        ]

        result = await service.get_claimed_one_time_rewards("42")

        assert len(result) == 1
        # Coerced result should have get_status() returning CLAIMED
        assert result[0].get_status().value == "✅ Claimed"


class TestFormatClaimedRewardsMessage:
    """Tests for format_claimed_rewards_message()."""

    def test_formats_single_reward(self):
        """Formats a single claimed reward correctly."""
        progress = _make_progress(
            pieces_earned=0, pieces_required=5, claimed=True, reward_id=1
        )
        reward = _make_reward(reward_id=1, name="Coffee", pieces_required=5)
        rewards_dict = {1: reward}

        result = format_claimed_rewards_message([progress], rewards_dict, 'en')

        assert "🏆" in result
        assert "<b>Coffee</b>" in result
        assert "5 pieces" in result

    def test_formats_multiple_rewards(self):
        """Formats multiple claimed rewards."""
        progress1 = _make_progress(reward_id=1, claimed=True, pieces_required=5)
        progress2 = _make_progress(reward_id=2, claimed=True, pieces_required=10)
        reward1 = _make_reward(reward_id=1, name="Coffee", pieces_required=5)
        reward2 = _make_reward(reward_id=2, name="Movie", pieces_required=10)
        rewards_dict = {1: reward1, 2: reward2}

        result = format_claimed_rewards_message(
            [progress1, progress2], rewards_dict, 'en'
        )

        assert "<b>Coffee</b>" in result
        assert "<b>Movie</b>" in result
        assert "5 pieces" in result
        assert "10 pieces" in result

    def test_includes_header(self):
        """Message includes the claimed rewards header."""
        progress = _make_progress(reward_id=1, claimed=True, pieces_required=3)
        reward = _make_reward(reward_id=1, name="Treat", pieces_required=3)
        rewards_dict = {1: reward}

        result = format_claimed_rewards_message([progress], rewards_dict, 'en')

        assert "<b>Claimed Rewards:</b>" in result

    def test_empty_list(self):
        """Empty progress list produces header only."""
        result = format_claimed_rewards_message([], {}, 'en')

        assert "<b>Claimed Rewards:</b>" in result


class TestRewardsMenuKeyboard:
    """Tests for build_rewards_menu_keyboard()."""

    def test_claimed_rewards_button_present(self):
        """Rewards menu keyboard includes Claimed Rewards button."""
        keyboard = build_rewards_menu_keyboard('en')

        # Flatten all buttons
        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        callback_datas = [btn.callback_data for btn in all_buttons]

        assert "menu_rewards_claimed" in callback_datas

    def test_claimed_rewards_button_after_claim(self):
        """Claimed Rewards button comes after Claim Reward button."""
        keyboard = build_rewards_menu_keyboard('en')

        # Flatten all buttons
        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        callback_datas = [btn.callback_data for btn in all_buttons]

        claim_idx = callback_datas.index("menu_rewards_claim")
        claimed_idx = callback_datas.index("menu_rewards_claimed")

        assert claimed_idx > claim_idx

    def test_claimed_rewards_button_before_back(self):
        """Claimed Rewards button comes before Back button."""
        keyboard = build_rewards_menu_keyboard('en')

        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        callback_datas = [btn.callback_data for btn in all_buttons]

        claimed_idx = callback_datas.index("menu_rewards_claimed")
        back_idx = callback_datas.index("menu_back_start")

        assert claimed_idx < back_idx


class TestClaimedRewardsHandler:
    """Tests for claimed_rewards_command handler."""

    @pytest.fixture
    def mock_update(self):
        """Create mock Telegram update."""
        from telegram import User as TelegramUser
        telegram_user = TelegramUser(id=999999999, first_name="Test", is_bot=False)
        message = Mock()
        message.reply_text = AsyncMock()

        update = Mock()
        update.effective_user = telegram_user
        update.message = message
        return update

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.user_data = {}
        return context

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.reward_service')
    @patch('src.bot.handlers.reward_handlers.user_repository')
    @patch('src.bot.handlers.reward_handlers.get_message_language_async', new_callable=AsyncMock, return_value='en')
    async def test_user_not_found(self, mock_lang, mock_user_repo, mock_reward_svc, mock_update, mock_context):
        """Shows ERROR_USER_NOT_FOUND when user doesn't exist."""
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=None)

        from src.bot.handlers.reward_handlers import claimed_rewards_command
        await claimed_rewards_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "not found" in call_args[0][0].lower() or "User not found" in call_args[0][0]

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.reward_service')
    @patch('src.bot.handlers.reward_handlers.user_repository')
    @patch('src.bot.handlers.reward_handlers.get_message_language_async', new_callable=AsyncMock, return_value='en')
    async def test_empty_claimed_rewards(self, mock_lang, mock_user_repo, mock_reward_svc, mock_update, mock_context):
        """Shows INFO_NO_CLAIMED_REWARDS when no claimed one-time rewards exist."""
        mock_user = Mock()
        mock_user.id = 42
        mock_user.is_active = True
        mock_user.language = 'en'
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
        mock_reward_svc.get_claimed_one_time_rewards = AsyncMock(return_value=[])

        from src.bot.handlers.reward_handlers import claimed_rewards_command
        await claimed_rewards_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "No claimed rewards" in call_args[0][0] or "claimed rewards" in call_args[0][0].lower()
