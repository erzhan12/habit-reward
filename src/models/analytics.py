"""Pydantic response models for habit performance analytics."""

from datetime import date

from pydantic import BaseModel, Field


class HabitCompletionRate(BaseModel):
    """Completion rate for a single habit over a date range."""

    habit_id: int
    habit_name: str
    completion_rate: float = Field(ge=0.0, le=1.0, description="0.0–1.0")
    completed_days: int
    available_days: int


class HabitRanking(BaseModel):
    """Habit ranked by completion rate, enriched with streak data."""

    rank: int
    habit_id: int
    habit_name: str
    completion_rate: float = Field(ge=0.0, le=1.0)
    total_completions: int
    current_streak: int
    longest_streak_in_range: int


class DailyCompletion(BaseModel):
    """Completion count for a single date."""

    date: date
    completions: int


class WeeklySummary(BaseModel):
    """Aggregated completion data for an ISO week."""

    week_start: date
    completions: int
    available_days: int
    rate: float = Field(ge=0.0, le=1.0)


class HabitTrendData(BaseModel):
    """Daily and weekly trend data for habit completions."""

    daily: list[DailyCompletion]
    weekly: list[WeeklySummary]