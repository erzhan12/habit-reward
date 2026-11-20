"""Pure gap engine (feature 0048 §2): evaluate_gap, missed_days, usable rule, find_due_spend."""

from datetime import date, timedelta

import pytest

from src.services.streak_service import (
    GapOutcome,
    evaluate_gap,
    find_due_spend,
    freeze_usable_predicate,
    missed_days,
)

MON = date(2026, 11, 16)  # Monday


def d(n: int) -> date:
    return MON + timedelta(days=n)


# --- missed_days -----------------------------------------------------------------

def test_missed_days_strictly_between():
    assert missed_days(d(0), d(1), []) == []
    assert missed_days(d(0), d(3), []) == [d(1), d(2)]


def test_missed_days_skips_exempt_weekdays():
    # Fri -> next Tue with Sat/Sun exempt: only Monday is missed.
    assert missed_days(d(4), d(8), [6, 7]) == [d(7)]


# --- evaluate_gap matrix ---------------------------------------------------------

def _never(_):
    return False


def _always(_):
    return True


@pytest.mark.parametrize("A", [0, 1, 2])
@pytest.mark.parametrize("extra", [0, 1, 2, 3])  # missed = A - 1 .. A + 2 (clamped at 0)
@pytest.mark.parametrize("freeze", ["spent", "inventory", "none"])
def test_matrix(A, extra, freeze):
    n_missed = max(0, A - 1 + extra)
    prev, cur = d(0), d(n_missed + 1)
    c = d(A + 1)  # missed[A]
    spent = {c} if freeze == "spent" and n_missed >= A + 1 else set()
    usable = _always if freeze == "inventory" else _never

    r = evaluate_gap(prev, cur, A, [], spent, usable)

    if n_missed <= A:
        assert (r.outcome, r.covered_date, r.needs_catchup_spend) == (GapOutcome.CONTINUE, None, False)
    elif freeze == "none":
        assert (r.outcome, r.covered_date, r.needs_catchup_spend) == (GapOutcome.RESET, None, False)
    else:
        expected = GapOutcome.FREEZE_SAVED if n_missed == A + 1 else GapOutcome.FREEZE_BURNED
        assert r.outcome == expected
        assert r.covered_date == c
        assert r.needs_catchup_spend is (freeze == "inventory")


def test_streak_continues_flags():
    assert GapOutcome.CONTINUE.keeps_streak
    assert GapOutcome.FREEZE_SAVED.keeps_streak
    assert not GapOutcome.FREEZE_BURNED.keeps_streak
    assert not GapOutcome.RESET.keeps_streak


def test_spent_event_wins_over_inventory():
    r = evaluate_gap(d(0), d(2), 0, [], {d(1)}, _always)
    assert (r.outcome, r.needs_catchup_spend) == (GapOutcome.FREEZE_SAVED, False)


def test_spent_event_on_other_day_does_not_cover():
    r = evaluate_gap(d(0), d(3), 0, [], {d(2)}, _never)
    assert r.outcome == GapOutcome.RESET


def test_exempt_weekdays_inside_gap_move_guard_day():
    # Fri -> Wed, weekends exempt, A=0: missed Mon, Tue; guard day is Monday.
    r = evaluate_gap(d(4), d(9), 0, [6, 7], set(), _always)
    assert (r.outcome, r.covered_date) == (GapOutcome.FREEZE_BURNED, d(7))
    # Fri -> Tue: only Monday missed -> saved.
    r = evaluate_gap(d(4), d(8), 0, [6, 7], set(), _always)
    assert (r.outcome, r.covered_date) == (GapOutcome.FREEZE_SAVED, d(7))


def test_usable_predicate_receives_guard_day():
    seen = []
    evaluate_gap(d(0), d(4), 1, [], set(), lambda c: seen.append(c) or False)
    assert seen == [d(2)]


# --- usable rule -------------------------------------------------------------------

def test_no_freeze_never_usable():
    assert freeze_usable_predicate(0, None)(d(5)) is False


def test_untracked_freeze_always_usable():
    assert freeze_usable_predicate(1, None)(d(0)) is True


def test_won_freeze_usable_only_for_later_days():
    usable = freeze_usable_predicate(1, d(3))
    assert usable(d(4)) is True
    assert usable(d(3)) is False
    assert usable(d(2)) is False


# --- find_due_spend (trailing gap) ----------------------------------------------------

def test_due_after_first_missed_day_ended():
    # Last log Mon, today Wed: Tuesday ended -> due for Tuesday.
    assert find_due_spend(d(0), d(2), 0, [], set(), _always) == d(1)


def test_not_due_before_day_ends():
    # Last log Mon, today Tue: Tuesday has not ended.
    assert find_due_spend(d(0), d(1), 0, [], set(), _always) is None


def test_not_due_when_already_spent_or_unusable():
    assert find_due_spend(d(0), d(2), 0, [], {d(1)}, _always) is None
    assert find_due_spend(d(0), d(2), 0, [], set(), _never) is None


def test_due_even_when_streak_already_broken():
    # Job was down: Tue, Wed, Thu ended -> still spends for Tue (Duolingo-style).
    assert find_due_spend(d(0), d(4), 0, [], set(), _always) == d(1)


def test_due_respects_allowance_and_exempt_days():
    assert find_due_spend(d(0), d(2), 1, [], set(), _always) is None
    assert find_due_spend(d(0), d(3), 1, [], set(), _always) == d(2)
    # Fri, weekend exempt, today Mon: nothing missed yet.
    assert find_due_spend(d(4), d(7), 0, [6, 7], set(), _always) is None


def test_no_last_log_nothing_due():
    assert find_due_spend(None, d(2), 0, [], set(), _always) is None
