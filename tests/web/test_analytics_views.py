"""Tests for analytics page view."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from src.models.analytics import (
    DailyCompletion,
    HabitCompletionRate,
    HabitRanking,
    HabitTrendData,
    WeeklySummary,
)
from tests.web.conftest import INERTIA_HEADERS, _inertia_props


def _mock_rates():
    return [
        HabitCompletionRate(
            habit_id=1, habit_name="Running", completion_rate=0.8,
            completed_days=24, available_days=30,
        ),
        HabitCompletionRate(
            habit_id=2, habit_name="Reading", completion_rate=0.6,
            completed_days=18, available_days=30,
        ),
    ]


def _mock_rankings():
    return [
        HabitRanking(
            rank=1, habit_id=1, habit_name="Running", completion_rate=0.8,
            total_completions=24, current_streak=5, longest_streak_in_range=10,
        ),
        HabitRanking(
            rank=2, habit_id=2, habit_name="Reading", completion_rate=0.6,
            total_completions=18, current_streak=3, longest_streak_in_range=7,
        ),
    ]


def _mock_trends():
    return HabitTrendData(
        daily=[DailyCompletion(date=date(2026, 3, 1), completions=2)],
        weekly=[WeeklySummary(week_start=date(2026, 2, 23), completions=10, available_days=14, rate=0.71)],
    )


def _patch_analytics():
    return patch("src.web.views.analytics.analytics_service")


@pytest.mark.django_db
class TestAnalyticsPage:

    def _setup_mocks(self, mock_svc, rates=None, rankings=None, trends=None):
        mock_svc.get_habit_completion_rates = AsyncMock(return_value=_mock_rates() if rates is None else rates)
        mock_svc.get_habit_rankings = AsyncMock(return_value=_mock_rankings() if rankings is None else rankings)
        mock_svc.get_habit_trends = AsyncMock(return_value=_mock_trends() if trends is None else trends)

    def test_analytics_page_default_period(self, auth_client):
        with _patch_analytics() as mock_svc:
            self._setup_mocks(mock_svc)
            response = auth_client.get("/analytics/", **INERTIA_HEADERS)
            assert response.status_code == 200
            component, props = _inertia_props(response)
            assert component == "Analytics"
            assert props["currentPeriod"] == "30d"
            assert "rates" in props
            assert "rankings" in props
            assert "trends" in props
            assert "summary" in props

    def test_analytics_page_7d_period(self, auth_client):
        with _patch_analytics() as mock_svc:
            self._setup_mocks(mock_svc)
            response = auth_client.get("/analytics/?period=7d", **INERTIA_HEADERS)
            assert response.status_code == 200
            _, props = _inertia_props(response)
            assert props["currentPeriod"] == "7d"

    def test_analytics_page_90d_period(self, auth_client):
        with _patch_analytics() as mock_svc:
            self._setup_mocks(mock_svc)
            response = auth_client.get("/analytics/?period=90d", **INERTIA_HEADERS)
            assert response.status_code == 200
            _, props = _inertia_props(response)
            assert props["currentPeriod"] == "90d"

    def test_analytics_page_invalid_period_defaults_30d(self, auth_client):
        with _patch_analytics() as mock_svc:
            self._setup_mocks(mock_svc)
            response = auth_client.get("/analytics/?period=invalid", **INERTIA_HEADERS)
            assert response.status_code == 200
            _, props = _inertia_props(response)
            assert props["currentPeriod"] == "30d"

    def test_analytics_page_no_habits(self, auth_client):
        with _patch_analytics() as mock_svc:
            self._setup_mocks(
                mock_svc,
                rates=[],
                rankings=[],
                trends=HabitTrendData(daily=[], weekly=[]),
            )
            response = auth_client.get("/analytics/", **INERTIA_HEADERS)
            assert response.status_code == 200
            _, props = _inertia_props(response)
            assert props["rates"] == []
            assert props["rankings"] == []
            assert props["summary"]["avgCompletionRate"] == 0
            assert props["summary"]["totalCompletions"] == 0
            assert props["summary"]["bestHabit"] is None

    def test_analytics_page_requires_auth(self, client):
        response = client.get("/analytics/")
        assert response.status_code == 302

    def test_summary_computation(self, auth_client):
        with _patch_analytics() as mock_svc:
            self._setup_mocks(mock_svc)
            response = auth_client.get("/analytics/", **INERTIA_HEADERS)
            _, props = _inertia_props(response)
            summary = props["summary"]
            # avg of 0.8 and 0.6 = 0.7
            assert abs(summary["avgCompletionRate"] - 0.7) < 0.01
            assert summary["totalCompletions"] == 42  # 24 + 18
            assert summary["totalAvailableDays"] == 60  # 30 + 30
            assert summary["bestHabit"]["name"] == "Running"
            assert summary["bestHabit"]["rate"] == 0.8
