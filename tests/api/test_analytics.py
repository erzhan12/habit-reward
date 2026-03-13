"""Tests for analytics API endpoints."""

from datetime import date
from unittest.mock import patch, AsyncMock, MagicMock

from src.models.analytics import (
    DailyCompletion,
    HabitCompletionRate,
    HabitRanking,
    HabitTrendData,
    WeeklySummary,
)


class TestCompletionRates:
    """Test GET /v1/analytics/completion-rates."""

    @patch("src.api.v1.routers.analytics.analytics_service")
    def test_default_period(self, mock_svc, client, mock_user):
        mock_svc.get_habit_completion_rates = AsyncMock(
            return_value=[
                HabitCompletionRate(
                    habit_id=1, habit_name="Exercise",
                    completion_rate=0.8, completed_days=8, available_days=10,
                )
            ]
        )
        response = client.get("/v1/analytics/completion-rates")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["habit_name"] == "Exercise"
        assert data[0]["completion_rate"] == 0.8

    @patch("src.api.v1.routers.analytics.analytics_service")
    def test_period_7d(self, mock_svc, client, mock_user):
        mock_svc.get_habit_completion_rates = AsyncMock(return_value=[])
        response = client.get("/v1/analytics/completion-rates?period=7d")
        assert response.status_code == 200
        assert response.json() == []

    @patch("src.api.v1.routers.analytics.analytics_service")
    def test_custom_date_range(self, mock_svc, client, mock_user):
        mock_svc.get_habit_completion_rates = AsyncMock(return_value=[])
        response = client.get(
            "/v1/analytics/completion-rates?start_date=2026-03-01&end_date=2026-03-10"
        )
        assert response.status_code == 200
        mock_svc.get_habit_completion_rates.assert_called_once_with(
            mock_user.id, date(2026, 3, 1), date(2026, 3, 10)
        )

    @patch("src.api.v1.routers.analytics.analytics_service")
    def test_invalid_date_range(self, mock_svc, client, mock_user):
        response = client.get(
            "/v1/analytics/completion-rates?start_date=2026-03-10&end_date=2026-03-01"
        )
        assert response.status_code == 400
        assert "start_date" in response.json()["detail"]

    @patch("src.api.v1.routers.analytics.analytics_service")
    def test_range_too_large(self, mock_svc, client, mock_user):
        # 2025-01-01 to 2026-03-01 = 425 inclusive days > 365
        response = client.get(
            "/v1/analytics/completion-rates?start_date=2025-01-01&end_date=2026-03-01"
        )
        assert response.status_code == 400
        assert "365" in response.json()["detail"]

    @patch("src.api.v1.routers.analytics.analytics_service")
    def test_range_exactly_365_allowed(self, mock_svc, client, mock_user):
        """Exactly 365 inclusive days should be accepted."""
        mock_svc.get_habit_completion_rates = AsyncMock(return_value=[])
        # 2025-03-14 to 2026-03-13 = 365 inclusive days
        response = client.get(
            "/v1/analytics/completion-rates?start_date=2025-03-14&end_date=2026-03-13"
        )
        assert response.status_code == 200

    @patch("src.api.v1.routers.analytics.analytics_service")
    def test_range_366_rejected(self, mock_svc, client, mock_user):
        """366 inclusive days should be rejected."""
        # 2025-03-13 to 2026-03-13 = 366 inclusive days
        response = client.get(
            "/v1/analytics/completion-rates?start_date=2025-03-13&end_date=2026-03-13"
        )
        assert response.status_code == 400

    @patch("src.api.v1.routers.analytics.analytics_service")
    def test_partial_range_only_start_date(self, mock_svc, client, mock_user):
        """Sending only start_date without end_date should return 400."""
        response = client.get(
            "/v1/analytics/completion-rates?start_date=2026-03-01"
        )
        assert response.status_code == 400
        assert "Both" in response.json()["detail"]

    @patch("src.api.v1.routers.analytics.analytics_service")
    def test_partial_range_only_end_date(self, mock_svc, client, mock_user):
        """Sending only end_date without start_date should return 400."""
        response = client.get(
            "/v1/analytics/completion-rates?end_date=2026-03-10"
        )
        assert response.status_code == 400
        assert "Both" in response.json()["detail"]

    def test_unauthenticated(self, client_no_auth):
        response = client_no_auth.get("/v1/analytics/completion-rates")
        assert response.status_code == 401


class TestRankings:
    """Test GET /v1/analytics/rankings."""

    @patch("src.api.v1.routers.analytics.analytics_service")
    def test_returns_ranked_list(self, mock_svc, client, mock_user):
        mock_svc.get_habit_rankings = AsyncMock(
            return_value=[
                HabitRanking(
                    rank=1, habit_id=1, habit_name="Best",
                    completion_rate=0.9, total_completions=27,
                    current_streak=10, longest_streak_in_range=15,
                ),
                HabitRanking(
                    rank=2, habit_id=2, habit_name="Worst",
                    completion_rate=0.3, total_completions=9,
                    current_streak=0, longest_streak_in_range=5,
                ),
            ]
        )
        response = client.get("/v1/analytics/rankings")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["rank"] == 1
        assert data[0]["current_streak"] == 10
        assert data[1]["rank"] == 2

    @patch("src.api.v1.routers.analytics.analytics_service")
    def test_no_habits(self, mock_svc, client, mock_user):
        mock_svc.get_habit_rankings = AsyncMock(return_value=[])
        response = client.get("/v1/analytics/rankings")
        assert response.status_code == 200
        assert response.json() == []

    def test_unauthenticated(self, client_no_auth):
        response = client_no_auth.get("/v1/analytics/rankings")
        assert response.status_code == 401


class TestTrends:
    """Test GET /v1/analytics/trends."""

    @patch("src.api.v1.routers.analytics.analytics_service")
    def test_returns_daily_and_weekly(self, mock_svc, client, mock_user):
        mock_svc.get_habit_trends = AsyncMock(
            return_value=HabitTrendData(
                daily=[
                    DailyCompletion(date=date(2026, 3, 1), completions=2),
                    DailyCompletion(date=date(2026, 3, 2), completions=1),
                ],
                weekly=[
                    WeeklySummary(
                        week_start=date(2026, 2, 23),
                        completions=3, available_days=7, rate=0.4286,
                    ),
                ],
            )
        )
        response = client.get("/v1/analytics/trends")
        assert response.status_code == 200
        data = response.json()
        assert len(data["daily"]) == 2
        assert len(data["weekly"]) == 1
        assert data["weekly"][0]["week_start"] == "2026-02-23"

    @patch("src.api.v1.routers.analytics.analytics_service")
    @patch("src.api.v1.routers.analytics.habit_repository")
    def test_filter_by_habit_id(self, mock_repo, mock_svc, client, mock_user):
        # Mock habit owned by mock_user
        mock_habit = MagicMock()
        mock_habit.id = 5
        mock_habit.user_id = mock_user.id
        mock_repo.get_by_id = AsyncMock(return_value=mock_habit)
        mock_svc.get_habit_trends = AsyncMock(
            return_value=HabitTrendData(daily=[], weekly=[])
        )
        response = client.get("/v1/analytics/trends?habit_id=5")
        assert response.status_code == 200
        assert mock_svc.get_habit_trends.call_args.kwargs["habit_id"] == 5

    @patch("src.api.v1.routers.analytics.analytics_service")
    @patch("src.api.v1.routers.analytics.habit_repository")
    def test_habit_not_found_returns_404(self, mock_repo, mock_svc, client, mock_user):
        mock_repo.get_by_id = AsyncMock(return_value=None)
        response = client.get("/v1/analytics/trends?habit_id=999")
        assert response.status_code == 404

    @patch("src.api.v1.routers.analytics.analytics_service")
    @patch("src.api.v1.routers.analytics.habit_repository")
    def test_foreign_habit_returns_403(self, mock_repo, mock_svc, client, mock_user):
        mock_habit = MagicMock()
        mock_habit.id = 5
        mock_habit.user_id = 999  # different user
        mock_repo.get_by_id = AsyncMock(return_value=mock_habit)
        response = client.get("/v1/analytics/trends?habit_id=5")
        assert response.status_code == 403

    @patch("src.api.v1.routers.analytics.analytics_service")
    def test_custom_range(self, mock_svc, client, mock_user):
        mock_svc.get_habit_trends = AsyncMock(
            return_value=HabitTrendData(daily=[], weekly=[])
        )
        response = client.get(
            "/v1/analytics/trends?start_date=2026-01-01&end_date=2026-03-01"
        )
        assert response.status_code == 200

    def test_unauthenticated(self, client_no_auth):
        response = client_no_auth.get("/v1/analytics/trends")
        assert response.status_code == 401
