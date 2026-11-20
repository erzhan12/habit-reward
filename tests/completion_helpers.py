"""Helpers for orchestration tests that stub the completion transaction (feature 0048).

``process_habit_completion`` runs its DB work as one sync function through
``run_in_transaction``. Orchestration tests (validation, timezone defaults,
notifications, audit snapshot) replace that call with a canned result; completion
semantics are covered DB-backed in tests/test_habit_freeze_flow.py.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from src.services.habit_service import CompletionCommit


def fake_commit(streak=1, effective=80.0, reward=None, progress=None, outcome=None,
                covered_date=None, freeze_won=False, freeze_count=0):
    return CompletionCommit(
        habit_log=MagicMock(id=100),
        streak_count=streak,
        reward_chance=100.0 - effective,
        effective_no_reward=effective,
        selected_reward=reward,
        reward_progress=progress,
        outcome=outcome,
        covered_date=covered_date,
        freeze_won=freeze_won,
        freeze_count=freeze_count,
    )


def patch_commit(**kwargs):
    """Patch the transaction runner used by habit_service with a canned CompletionCommit."""
    return patch(
        "src.services.habit_service.run_in_transaction",
        new=AsyncMock(return_value=fake_commit(**kwargs)),
    )
