"""Tests for the streak-only reward chance formula (feature 0048).

p(s) = BASE + BONUS * (1 - exp(-(s - 1) / TAU)), capped at CAP (percent).
"""

import inspect
import math
import random

import pytest

from src.services.reward_service import reward_service


def _expected(s: int) -> float:
    s = max(1, s)
    return min(20.0 + 30.0 * (1 - math.exp(-(s - 1) / 5.5)), 50.0)


@pytest.mark.parametrize(
    "streak,exact,rounded",
    [
        (1, 20.00, 20),
        (2, 24.99, 25),
        (3, 29.15, 29),
        (4, 32.61, 33),
        (7, 39.92, 40),
        (10, 44.16, None),
        (14, 47.18, 47),
        (23, 49.45, 49),
        (24, 49.54, 50),
        (30, 49.85, 50),
        (365, 50.00, 50),
    ],
)
def test_formula_checkpoints(streak, exact, rounded):
    p = reward_service.calculate_reward_chance(streak)
    assert p == pytest.approx(_expected(streak), abs=1e-9)
    assert p == pytest.approx(exact, abs=0.01)
    if rounded is not None:
        assert round(p) == rounded


@pytest.mark.parametrize("streak", [0, -1, -100])
def test_non_positive_streak_clamps_to_base(streak):
    assert reward_service.calculate_reward_chance(streak) == pytest.approx(20.0)


def test_monotonic_and_capped():
    values = [reward_service.calculate_reward_chance(s) for s in range(1, 400)]
    assert all(b >= a for a, b in zip(values, values[1:]))
    assert max(values) <= 50.0


def test_takes_only_streak():
    params = list(inspect.signature(reward_service.calculate_reward_chance).parameters)
    assert params == ["streak_count"]


def test_old_formula_removed():
    assert not hasattr(reward_service, "calculate_effective_no_reward_probability")


def test_seeded_win_rate_at_streak_one():
    """20,000 Bernoulli rolls at s=1 land within 20% ± 1.5pp."""
    state = random.getstate()
    try:
        random.seed(48)
        p = reward_service.calculate_reward_chance(1)
        wins = sum(1 for _ in range(20_000) if random.random() * 100 < p)
    finally:
        random.setstate(state)
    assert abs(wins / 20_000 * 100 - 20.0) <= 1.5
