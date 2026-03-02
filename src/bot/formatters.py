"""Message formatting functions for Telegram bot responses."""

import logging

from src.models.habit_completion_result import HabitCompletionResult
from src.models.reward_progress import RewardProgress, RewardStatus
from src.models.reward import Reward
from src.models.habit_log import HabitLog
from src.config import settings
from src.bot.messages import msg

logger = logging.getLogger(__name__)


def format_habit_completion_message(result: HabitCompletionResult, language: str = 'en') -> str:
    """
    Format habit completion result into a user-friendly message.

    Args:
        result: HabitCompletionResult object
        language: Language code for translations

    Returns:
        Formatted message string
    """
    message_parts = []

    # Habit confirmation
    message_parts.append(msg('SUCCESS_HABIT_COMPLETED', language, habit_name=result.habit_name))

    # Streak status
    fire_emoji = "🔥" * min(result.streak_count, 5)
    message_parts.append(f"{fire_emoji} " + msg('FORMAT_STREAK', language, streak_count=result.streak_count))

    # Reward result - all rewards now show progress
    # got_reward=True means they won a reward (reward is not None)
    if result.got_reward and result.reward:
        message_parts.append("\n" + msg('FORMAT_REWARD', language, reward_name=result.reward.name))
        if result.cumulative_progress:
            progress_bar = create_progress_bar(
                result.cumulative_progress.pieces_earned,
                result.cumulative_progress.get_pieces_required()
            )
            message_parts.append(
                msg('FORMAT_PROGRESS', language,
                    progress_bar=progress_bar,
                    pieces_earned=result.cumulative_progress.pieces_earned,
                    pieces_required=result.cumulative_progress.get_pieces_required() or 1)
            )
            if result.cumulative_progress.get_status() == RewardStatus.ACHIEVED:
                message_parts.append(msg('INFO_REWARD_ACTIONABLE', language))
    else:
        message_parts.append("\n" + msg('INFO_NO_REWARD', language))

    # Motivational quote (if present)
    if result.motivational_quote:
        message_parts.append(f"\n💭 <i>{result.motivational_quote}</i>")

    return "\n".join(message_parts)


def format_reward_progress_message(progress: RewardProgress, reward: Reward, language: str = 'en') -> str:
    """
    Format reward progress into a message.

    Args:
        progress: RewardProgress object
        reward: Reward object
        language: Language code for translations

    Returns:
        Formatted message string
    """
    progress_bar = create_progress_bar(
        progress.pieces_earned,
        progress.get_pieces_required() or 1
    )

    message = (
        f"{progress.get_status_emoji()} <b>{reward.name}</b>\n"
        f"📊 {progress_bar} {progress.pieces_earned}/{progress.get_pieces_required() or 1}"
    )

    return message


def format_streaks_message(streaks: dict[str, tuple[str, int]], language: str = 'en') -> str:
    """
    Format streaks dictionary into a message.

    Args:
        streaks: Dictionary mapping habit_id to (habit_name, streak_count)
        language: Language code for translations

    Returns:
        Formatted message string
    """
    if not streaks:
        return msg('FORMAT_NO_STREAKS', language)

    message_parts = [msg('HEADER_STREAKS', language)]

    # Sort by streak count (descending)
    sorted_streaks = sorted(
        streaks.items(),
        key=lambda x: x[1][1],
        reverse=True
    )

    for habit_id, (habit_name, streak_count) in sorted_streaks:
        fire_emoji = "🔥" * min(streak_count, 5)
        message_parts.append(f"{fire_emoji} <b>{habit_name}:</b> {streak_count} days")

    return "\n".join(message_parts)


def format_rewards_list_message(rewards: list[Reward], language: str = 'en') -> str:
    """
    Format list of rewards into a message.

    Args:
        rewards: List of Reward objects
        language: Language code for translations

    Returns:
        Formatted message string
    """
    if not rewards:
        return msg('FORMAT_NO_REWARDS_YET', language)

    message_parts = [msg('HEADER_REWARDS_LIST', language)]

    for reward in rewards:
        reward_info = f"🎁 <b>{reward.name}</b>"

        # Build details list (pieces and weight)
        details = []
        if reward.pieces_required > 1:
            details.append(f"{reward.pieces_required} {msg('LABEL_PIECES', language)}")
        details.append(f"w: {int(reward.weight)}")

        if details:
            reward_info += f" ({', '.join(details)})"

        message_parts.append(reward_info)

    return "\n".join(message_parts)


def format_habit_logs_message(logs: list[HabitLog], habits: dict[str, str], language: str = 'en') -> str:
    """
    Format habit logs into a message.

    Args:
        logs: List of HabitLog objects
        habits: Dictionary mapping habit_id to habit_name
        language: Language code for translations

    Returns:
        Formatted message string
    """
    if not logs:
        return msg('FORMAT_NO_LOGS', language)

    message_parts = [msg('HEADER_HABIT_LOGS', language)]

    for log in logs[:settings.recent_logs_limit]:  # Show only last N
        habit_name = habits.get(log.habit_id, "Unknown habit")
        date_str = log.last_completed_date.strftime("%b %d")
        # Visual indicator for reward status in habit history
        # 🎁 = got_reward=True (reward received)
        # ❌ = got_reward=False (no reward)
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


def format_claim_success_with_progress(
    reward_name: str,
    progress_list: list[RewardProgress],
    rewards_dict: dict[str, Reward],
    language: str = 'en'
) -> str:
    """
    Format success message after claiming reward, including updated reward progress summary.

    Args:
        reward_name: Name of the reward that was just claimed
        progress_list: List of all RewardProgress objects for the user
        rewards_dict: Dictionary mapping reward_id to Reward object
        language: Language code for translations

    Returns:
        Formatted message string with success header and updated progress
    """
    message_parts = []

    # Success header
    message_parts.append(msg('SUCCESS_REWARD_CLAIMED_HEADER', language, reward_name=reward_name))
    message_parts.append("\n" + "─" * 30)

    # Updated progress header
    message_parts.append(msg('HEADER_UPDATED_REWARD_PROGRESS', language))

    # Format each progress entry
    for progress in progress_list:
        reward = rewards_dict.get(progress.reward_id)
        if reward:
            progress_msg = format_reward_progress_message(progress, reward, language)
            message_parts.append("\n" + progress_msg)

    return "\n".join(message_parts)


def format_claimed_rewards_message(
    progress_list: list[RewardProgress],
    rewards_dict: dict[str | int, Reward],
    language: str = 'en'
) -> str:
    """
    Format claimed one-time rewards into a message.

    Args:
        progress_list: List of claimed RewardProgress objects
        rewards_dict: Dictionary mapping reward_id to Reward object
        language: Language code for translations

    Returns:
        Formatted message string with header and reward list
    """
    message_parts = [msg('HEADER_CLAIMED_REWARDS', language)]

    for progress in progress_list:
        reward = rewards_dict.get(progress.reward_id)
        if reward:
            pieces = progress.get_pieces_required()
            if pieces is None:
                logger.warning(f"Missing pieces_required for progress {progress.id}")
                pieces = 1
            line = f"🏆 <b>{reward.name}</b> — {pieces} {msg('LABEL_PIECES', language)}"
            times_claimed = getattr(progress, 'times_claimed', 0)
            if times_claimed > 0:
                line += f" | {msg('LABEL_TIMES_CLAIMED', language, count=times_claimed)}"
            message_parts.append(line)

    return "\n".join(message_parts)
