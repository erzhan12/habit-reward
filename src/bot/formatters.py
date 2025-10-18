"""Message formatting functions for Telegram bot responses."""

from src.models.habit_completion_result import HabitCompletionResult
from src.models.reward_progress import RewardProgress
from src.models.reward import Reward, RewardType
from src.models.habit_log import HabitLog
from src.config import settings


def format_habit_completion_message(result: HabitCompletionResult) -> str:
    """
    Format habit completion result into a user-friendly message.

    Args:
        result: HabitCompletionResult object

    Returns:
        Formatted message string
    """
    message_parts = []

    # Habit confirmation
    message_parts.append(f"✅ *Habit completed:* {result.habit_name}")

    # Streak status
    fire_emoji = "🔥" * min(result.streak_count, 5)
    message_parts.append(f"{fire_emoji} *Streak:* {result.streak_count} days")

    # Reward result
    if result.got_reward and result.reward:
        if result.reward.type == RewardType.CUMULATIVE:
            message_parts.append(f"\n🎁 *Reward:* {result.reward.name}")
            if result.cumulative_progress:
                progress_bar = create_progress_bar(
                    result.cumulative_progress.pieces_earned,
                    result.cumulative_progress.pieces_required
                )
                message_parts.append(
                    f"📊 Progress: {progress_bar} "
                    f"{result.cumulative_progress.pieces_earned}/{result.cumulative_progress.pieces_required}"
                )
                if result.cumulative_progress.actionable_now:
                    message_parts.append("⏳ *Reward achieved!* You can claim it now!")
        else:
            message_parts.append(f"\n🎁 *Reward:* {result.reward.name}")
    else:
        message_parts.append("\n❌ No reward this time - keep going!")

    # Motivational quote (if present)
    if result.motivational_quote:
        message_parts.append(f"\n💭 _{result.motivational_quote}_")

    return "\n".join(message_parts)


def format_reward_progress_message(progress: RewardProgress, reward: Reward) -> str:
    """
    Format reward progress into a message.

    Args:
        progress: RewardProgress object
        reward: Reward object

    Returns:
        Formatted message string
    """
    progress_bar = create_progress_bar(
        progress.pieces_earned,
        progress.pieces_required or 1
    )

    message = (
        f"{progress.status_emoji} *{reward.name}*\n"
        f"📊 {progress_bar} {progress.pieces_earned}/{progress.pieces_required}\n"
        f"Status: {progress.status.value}"
    )

    if progress.actionable_now:
        message += "\n⏳ *Ready to claim!*"

    return message


def format_streaks_message(streaks: dict[str, tuple[str, int]]) -> str:
    """
    Format streaks dictionary into a message.

    Args:
        streaks: Dictionary mapping habit_id to (habit_name, streak_count)

    Returns:
        Formatted message string
    """
    if not streaks:
        return "No habits logged yet. Start building your streaks!"

    message_parts = ["🔥 *Your Current Streaks:*\n"]

    # Sort by streak count (descending)
    sorted_streaks = sorted(
        streaks.items(),
        key=lambda x: x[1][1],
        reverse=True
    )

    for habit_id, (habit_name, streak_count) in sorted_streaks:
        fire_emoji = "🔥" * min(streak_count, 5)
        message_parts.append(f"{fire_emoji} *{habit_name}:* {streak_count} days")

    return "\n".join(message_parts)


def format_rewards_list_message(rewards: list[Reward]) -> str:
    """
    Format list of rewards into a message.

    Args:
        rewards: List of Reward objects

    Returns:
        Formatted message string
    """
    if not rewards:
        return "No rewards configured yet."

    message_parts = ["🎁 *Available Rewards:*\n"]

    for reward in rewards:
        type_emoji = {
            RewardType.VIRTUAL: "💎",
            RewardType.REAL: "🎁",
            RewardType.NONE: "❌",
            RewardType.CUMULATIVE: "📦"
        }.get(reward.type, "❓")

        reward_info = f"{type_emoji} *{reward.name}*"

        if reward.is_cumulative and reward.pieces_required:
            reward_info += f" ({reward.pieces_required} pieces)"

        message_parts.append(reward_info)

    return "\n".join(message_parts)


def format_habit_logs_message(logs: list[HabitLog], habits: dict[str, str]) -> str:
    """
    Format habit logs into a message.

    Args:
        logs: List of HabitLog objects
        habits: Dictionary mapping habit_id to habit_name

    Returns:
        Formatted message string
    """
    if not logs:
        return "No habit logs found."

    message_parts = ["📋 *Recent Habit Completions:*\n"]

    for log in logs[:settings.recent_logs_limit]:  # Show only last N
        habit_name = habits.get(log.habit_id, "Unknown habit")
        date_str = log.last_completed_date.strftime("%b %d")
        reward_emoji = "🎁" if log.got_reward else "❌"
        streak_emoji = "🔥" * min(log.streak_count, 3)

        message_parts.append(
            f"{date_str} - {habit_name} {streak_emoji} {reward_emoji}"
        )

    return "\n".join(message_parts)


def create_progress_bar(current: int, total: int, length: int | None = None) -> str:
    """
    Create a visual progress bar.

    Args:
        current: Current progress value
        total: Total/target value
        length: Length of progress bar in characters (defaults to config value)

    Returns:
        Progress bar string (e.g., "████░░░░░░")
    """
    if length is None:
        length = settings.progress_bar_length
        
    if total == 0:
        return "░" * length

    filled = int((current / total) * length)
    filled = min(filled, length)  # Cap at length

    return "█" * filled + "░" * (length - filled)
