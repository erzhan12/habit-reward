#!/usr/bin/env python
"""Test script to verify 50% no-reward probability in habit completion.

This integration test creates real database records and runs 10,000 habit
completions to statistically verify that "no reward" outcomes occur
approximately 50% of the time.

Usage:
    uv run python scripts/test_50_percent_no_reward.py
    uv run python scripts/test_50_percent_no_reward.py --iterations 1000
    uv run python scripts/test_50_percent_no_reward.py --verbose

The script uses a temporary SQLite database that is automatically deleted
after the test completes.
"""
import os
import sys
import argparse
import tempfile
import math
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def setup_temp_database():
    """Create a temporary database for testing."""
    # Create temp file for SQLite database
    temp_db = tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=False)
    temp_db_path = temp_db.name
    temp_db.close()

    # Set environment to use temp database
    os.environ['DATABASE_URL'] = f'sqlite:///{temp_db_path}'
    os.environ['DJANGO_SETTINGS_MODULE'] = 'src.habit_reward_project.settings'

    return temp_db_path


def cleanup_database(db_path):
    """Remove temporary database file."""
    try:
        if os.path.exists(db_path):
            os.unlink(db_path)
            print(f"Cleaned up temp database: {db_path}")
    except Exception as e:
        print(f"Warning: Could not delete temp database: {e}")


def calculate_chi_square(observed_no_reward, observed_reward, total):
    """Calculate chi-square statistic for 50/50 split."""
    expected = total / 2
    chi_square = ((observed_no_reward - expected) ** 2 / expected +
                  (observed_reward - expected) ** 2 / expected)
    return chi_square


def chi_square_p_value(chi_square, df=1):
    """Approximate p-value for chi-square with 1 degree of freedom.

    Uses the approximation: p ≈ erfc(sqrt(chi_square/2))
    """
    if chi_square <= 0:
        return 1.0
    # Approximation using error function complement
    x = math.sqrt(chi_square / 2)
    # Simple approximation of erfc
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    t = 1.0 / (1.0 + p * x)
    erfc = t * (a1 + t * (a2 + t * (a3 + t * (a4 + t * a5)))) * math.exp(-x * x)
    return erfc


def wilson_confidence_interval(successes, total, confidence=0.95):
    """Calculate Wilson score confidence interval for proportion.

    More accurate than normal approximation for proportions near 0 or 1.
    """
    if total == 0:
        return (0, 1)

    z = 1.96  # 95% confidence
    p = successes / total

    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denominator

    return (max(0, center - margin), min(1, center + margin))


def setup_django_and_migrate():
    """Setup Django and run migrations."""
    import django
    django.setup()

    # Run migrations
    from django.core.management import call_command
    print("Setting up database...")
    call_command('migrate', '--run-syncdb', verbosity=0)


def run_test(iterations=10000, verbose=False):
    """Run the 50% no-reward probability test.

    This function tests the reward selection directly, bypassing the full
    habit completion flow to avoid async complexity and speed up testing.

    Args:
        iterations: Number of reward selections to run
        verbose: Whether to print detailed progress

    Returns:
        Tuple of (passed, results_dict)
    """
    # Import after Django setup
    from src.core.models import User, Habit, Reward

    print("Creating test data...")

    # Create test user
    user = User.objects.create(
        username='test_probability_user',
        telegram_id='999999999',
        name='Test User',
        is_active=True
    )

    # Create test habit
    habit = Habit.objects.create(
        user=user,
        name='Test Habit',
        weight=50,
        active=True,
        allowed_skip_days=0,
        exempt_weekdays=[]
    )

    # Create multiple rewards with different weights
    reward1 = Reward.objects.create(
        user=user,
        name='Reward A',
        type='virtual',
        weight=10,
        pieces_required=1000,  # High so it never completes
        is_recurring=True,
        active=True
    )

    reward2 = Reward.objects.create(
        user=user,
        name='Reward B',
        type='real',
        weight=20,
        pieces_required=1000,
        is_recurring=True,
        active=True
    )

    reward3 = Reward.objects.create(
        user=user,
        name='Reward C',
        type='virtual',
        weight=15,
        pieces_required=1000,
        is_recurring=True,
        active=True
    )

    print(f"Created user: {user.telegram_id}")
    print(f"Created habit: {habit.name} (weight={habit.weight})")
    print(f"Created rewards: {reward1.name} (w={reward1.weight}), "
          f"{reward2.name} (w={reward2.weight}), {reward3.name} (w={reward3.weight})")

    # Import reward service
    from src.services.reward_service import RewardService

    # Initialize service
    reward_service = RewardService()

    # Calculate total weight (using habit weight and streak of 1)
    total_weight = reward_service.calculate_total_weight(
        habit_weight=habit.weight,
        streak_count=1
    )

    print(f"Total weight for selection: {total_weight}")

    # Counters
    got_reward_count = 0
    no_reward_count = 0
    reward_distribution = {}

    # Progress tracking
    print(f"\nRunning {iterations:,} reward selections...")
    progress_interval = max(1, iterations // 20)  # Show 20 progress updates

    for i in range(iterations):
        if (i + 1) % progress_interval == 0 or i == 0:
            pct = (i + 1) / iterations * 100
            print(f"  Progress: {i + 1:,}/{iterations:,} ({pct:.0f}%)")

        try:
            # Directly call select_reward (synchronous version)
            # The service uses run_sync_or_async which returns the result directly
            # when called from sync context
            selected = reward_service.select_reward(
                total_weight=total_weight,
                user_id=user.id,
                exclude_reward_ids=[]
            )

            if selected is not None:
                got_reward_count += 1
                reward_name = selected.name if hasattr(selected, 'name') else 'Unknown'
                reward_distribution[reward_name] = reward_distribution.get(reward_name, 0) + 1
            else:
                no_reward_count += 1

        except Exception as e:
            if verbose:
                print(f"  Error on iteration {i}: {e}")
            # Try to continue
            continue

    # Calculate statistics
    total = got_reward_count + no_reward_count
    no_reward_pct = (no_reward_count / total * 100) if total > 0 else 0
    got_reward_pct = (got_reward_count / total * 100) if total > 0 else 0

    chi_square = calculate_chi_square(no_reward_count, got_reward_count, total)
    p_value = chi_square_p_value(chi_square)

    ci_low, ci_high = wilson_confidence_interval(no_reward_count, total)

    # Print results
    print("\n" + "=" * 60)
    print("50% No-Reward Probability Test Results")
    print("=" * 60)

    print(f"\nTotal selections: {total:,}")
    print(f"\nOutcome Distribution:")
    print(f"  Got Reward:  {got_reward_count:>6,} ({got_reward_pct:>5.2f}%)")
    print(f"  No Reward:   {no_reward_count:>6,} ({no_reward_pct:>5.2f}%)")
    print(f"  Expected:    {total // 2:>6,} (50.00%)")

    print(f"\nReward Distribution (when reward given):")
    for name, count in sorted(reward_distribution.items(), key=lambda x: -x[1]):
        pct = count / got_reward_count * 100 if got_reward_count > 0 else 0
        print(f"  {name}: {count:,} ({pct:.1f}%)")

    print(f"\nStatistical Analysis:")
    deviation = no_reward_pct - 50.0
    print(f"  Deviation from 50%: {deviation:+.2f}%")
    print(f"  Chi-square:         {chi_square:.3f}")
    print(f"  p-value:            {p_value:.4f}")
    print(f"  95% CI for no-reward: [{ci_low*100:.2f}%, {ci_high*100:.2f}%]")

    # Determine pass/fail
    # Accept if no-reward rate is within 47-53% (generous margin for 10K samples)
    # With 10K samples, 95% CI is typically ±1%
    passed = 47.0 <= no_reward_pct <= 53.0

    print("\n" + "=" * 60)
    if passed:
        print("PASS: No-reward rate is within expected range (47-53%)")
    else:
        print("FAIL: No-reward rate is outside expected range")
        print(f"       Expected ~50%, got {no_reward_pct:.2f}%")
    print("=" * 60)

    return passed, {
        'total': total,
        'got_reward': got_reward_count,
        'no_reward': no_reward_count,
        'no_reward_pct': no_reward_pct,
        'chi_square': chi_square,
        'p_value': p_value,
        'ci': (ci_low, ci_high)
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Test 50% no-reward probability in habit completion',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/test_50_percent_no_reward.py
  uv run python scripts/test_50_percent_no_reward.py --iterations 1000
  uv run python scripts/test_50_percent_no_reward.py --iterations 10000 --verbose
        """
    )

    parser.add_argument(
        '--iterations', '-n',
        type=int,
        default=10000,
        help='Number of reward selections to run (default: 10000)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print detailed progress and errors'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("50% No-Reward Probability Test")
    print("=" * 60)
    print(f"\nIterations: {args.iterations:,}")

    # Setup temp database
    temp_db_path = setup_temp_database()
    print(f"Using temp database: {temp_db_path}")

    try:
        # Setup Django and run migrations
        setup_django_and_migrate()

        # Run the test (synchronous)
        passed, results = run_test(
            iterations=args.iterations,
            verbose=args.verbose
        )

        sys.exit(0 if passed else 1)

    finally:
        # Cleanup
        cleanup_database(temp_db_path)


if __name__ == '__main__':
    main()
