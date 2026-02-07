"""Tests for timezone utilities."""

from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch
from zoneinfo import ZoneInfo

import pytest

from src.bot.timezone_utils import get_user_today, get_user_timezone, validate_timezone


class TestGetUserToday:
    """Tests for get_user_today()."""

    def test_utc_matches_utc_date(self):
        """get_user_today('UTC') should match datetime.now(UTC).date()."""
        result = get_user_today('UTC')
        expected = datetime.now(ZoneInfo('UTC')).date()
        assert result == expected

    def test_different_date_after_midnight_local(self):
        """When local time is past midnight but UTC hasn't crossed yet,
        local date should be ahead of UTC date."""
        # Mock: UTC time is 21:00 on Feb 6 → Almaty (UTC+5) is 02:00 on Feb 7
        fake_utc_time = datetime(2025, 2, 6, 21, 0, 0, tzinfo=ZoneInfo('UTC'))

        with patch('src.bot.timezone_utils.datetime') as mock_dt:
            # Make datetime.now() return our fake time for any timezone
            def now_side_effect(tz=None):
                if tz:
                    return fake_utc_time.astimezone(tz)
                return fake_utc_time
            mock_dt.now.side_effect = now_side_effect

            almaty_date = get_user_today('Asia/Almaty')
            utc_date = get_user_today('UTC')

        assert almaty_date == date(2025, 2, 7)
        assert utc_date == date(2025, 2, 6)
        assert almaty_date > utc_date

    def test_negative_offset_behind_utc(self):
        """UTC-5 timezone should be behind UTC date when UTC is past midnight."""
        # Mock: UTC time is 02:00 on Feb 7 → New York (UTC-5) is 21:00 on Feb 6
        fake_utc_time = datetime(2025, 2, 7, 2, 0, 0, tzinfo=ZoneInfo('UTC'))

        with patch('src.bot.timezone_utils.datetime') as mock_dt:
            def now_side_effect(tz=None):
                if tz:
                    return fake_utc_time.astimezone(tz)
                return fake_utc_time
            mock_dt.now.side_effect = now_side_effect

            ny_date = get_user_today('America/New_York')
            utc_date = get_user_today('UTC')

        assert ny_date == date(2025, 2, 6)
        assert utc_date == date(2025, 2, 7)
        assert ny_date < utc_date

    def test_invalid_timezone_falls_back_to_utc(self):
        """Invalid timezone should fall back to UTC without raising."""
        result = get_user_today('Invalid/Timezone')
        expected = datetime.now(ZoneInfo('UTC')).date()
        assert result == expected

    def test_empty_string_falls_back_to_utc(self):
        """Empty timezone string should fall back to UTC."""
        result = get_user_today('')
        expected = datetime.now(ZoneInfo('UTC')).date()
        assert result == expected


class TestGetUserTimezone:
    """Tests for get_user_timezone()."""

    @pytest.mark.asyncio
    async def test_returns_user_timezone(self):
        """Should return user's stored timezone."""
        mock_user = Mock()
        mock_user.timezone = 'Asia/Almaty'

        mock_repo = Mock()
        mock_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)

        with patch(
            'src.core.repositories.user_repository', mock_repo
        ):
            result = await get_user_timezone('12345')

        assert result == 'Asia/Almaty'

    @pytest.mark.asyncio
    async def test_returns_utc_when_no_timezone_set(self):
        """Should return UTC when user has no timezone."""
        mock_user = Mock()
        mock_user.timezone = None

        mock_repo = Mock()
        mock_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)

        with patch(
            'src.core.repositories.user_repository', mock_repo
        ):
            result = await get_user_timezone('12345')

        assert result == 'UTC'

    @pytest.mark.asyncio
    async def test_returns_utc_when_user_not_found(self):
        """Should return UTC when user doesn't exist."""
        mock_repo = Mock()
        mock_repo.get_by_telegram_id = AsyncMock(return_value=None)

        with patch(
            'src.core.repositories.user_repository', mock_repo
        ):
            result = await get_user_timezone('99999')

        assert result == 'UTC'

    @pytest.mark.asyncio
    async def test_returns_utc_when_timezone_is_empty_string(self):
        """Should return UTC when user timezone is empty string."""
        mock_user = Mock()
        mock_user.timezone = ''

        mock_repo = Mock()
        mock_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)

        with patch(
            'src.core.repositories.user_repository', mock_repo
        ):
            result = await get_user_timezone('12345')

        assert result == 'UTC'


class TestValidateTimezone:
    """Tests for validate_timezone()."""

    def test_valid_timezone(self):
        assert validate_timezone('Asia/Almaty') is True

    def test_valid_utc(self):
        assert validate_timezone('UTC') is True

    def test_invalid_timezone(self):
        assert validate_timezone('Invalid/Timezone') is False

    def test_empty_string(self):
        assert validate_timezone('') is False

    def test_none_like_string(self):
        assert validate_timezone('None') is False
