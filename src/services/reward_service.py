"""Reward selection and management service with weighted random selection."""

import logging
import math
import random
from datetime import date
from typing import Awaitable
from types import SimpleNamespace, MethodType

from django.db.models import F

from src.core.repositories import reward_repository, reward_progress_repository, habit_log_repository
from src.core.models import Reward, RewardProgress
from src.models.reward_progress import RewardProgress as RewardProgressModel
from django.conf import settings
from src.utils.async_compat import run_sync_or_async, maybe_await

# Import enums from Django models
RewardStatus = RewardProgress.RewardStatus

# Configure logging
logger = logging.getLogger(__name__)


class RewardService:
    """Service for reward selection and cumulative reward progress tracking."""

    def __init__(self):
        """Initialize RewardService with repositories."""
        self.reward_repo = reward_repository
        self.progress_repo = reward_progress_repository
        self.habit_log_repo = habit_log_repository

    @staticmethod
    def calculate_reward_chance(streak_count: int) -> float:
        """Return the reward chance (percent) for a completion on streak day ``streak_count``.

        Formula (feature 0048): ``p(s) = BASE + BONUS * (1 - exp(-(s - 1) / TAU))``,
        capped at ``CAP``. Depends only on the streak; habit weight and the user's
        ``no_reward_probability`` no longer affect it. ``s <= 0`` is treated as 1.

        Callers roll with ``select_reward(effective_no_reward_probability=100 - p)``.
        """
        s = max(1, int(streak_count))
        p = settings.REWARD_CHANCE_BASE + settings.REWARD_CHANCE_STREAK_BONUS * (
            1 - math.exp(-(s - 1) / settings.REWARD_CHANCE_STREAK_TAU)
        )
        return min(p, settings.REWARD_CHANCE_CAP)

    def select_reward(
        self,
        effective_no_reward_probability: float,
        user_id: str | None = None,
        exclude_reward_ids: list[str] | None = None,
        target_date: 'date | None' = None,
    ) -> Reward | None | Awaitable[Reward | None]:
        """Perform weighted random reward selection with pre-computed no-reward probability.

        Args:
            effective_no_reward_probability: Pre-computed no-reward %, i.e.
                ``100 - calculate_reward_chance(streak)``.
            user_id: Required user ID for filtering rewards.
            exclude_reward_ids: Reward IDs to exclude from selection.
            target_date: Date for daily-limit checks.

        Returns:
            Reward | None: Selected reward, or None for "no reward" outcome
        """

        if not (0 <= effective_no_reward_probability <= 100):
            raise ValueError(
                f"effective_no_reward_probability must be 0-100, got {effective_no_reward_probability}"
            )

        async def _impl() -> Reward | None:
            logger.info(
                "Selecting reward with effective_no_reward=%.1f%%, user_id=%s",
                effective_no_reward_probability,
                user_id,
            )
            if exclude_reward_ids:
                logger.info(
                    "Excluding %s rewards from selection",
                    len(exclude_reward_ids),
                )

            # user_id is required now since rewards are user-specific
            if not user_id:
                logger.error("user_id is required for select_reward")
                return None

            rewards = await maybe_await(self.reward_repo.get_all_active(user_id))

            if not rewards:
                logger.warning("No active rewards found for user %s, returning None (no reward)", user_id)
                return None

            logger.debug("Found %s active rewards", len(rewards))

            if exclude_reward_ids:
                original_count = len(rewards)
                rewards = [r for r in rewards if r.id not in exclude_reward_ids]
                logger.info(
                    "After exclusion: %s rewards remaining (filtered out %s)",
                    len(rewards),
                    original_count - len(rewards),
                )

            if not rewards:
                logger.warning("All rewards excluded, returning None (no reward)")
                return None

            # Apply user-specific filters (completed rewards, daily limits)
            logger.info("Applying user-specific filters for user=%s", user_id)
            progress_list = await maybe_await(self.progress_repo.get_all_by_user(user_id))
            progress_by_reward_id = {p.reward_id: p for p in progress_list}
            logger.debug("Found %s progress records for user", len(progress_list))

            today_counts: dict = {}
            for reward in rewards:
                if self._is_completed(reward, progress_by_reward_id.get(reward.id)):
                    continue
                if reward.max_daily_claims is not None and reward.max_daily_claims > 0:
                    today_counts[reward.id] = await maybe_await(
                        self.get_todays_pieces_by_reward(user_id, reward.id, target_date=target_date)
                    )

            rewards = self._eligible_rewards(rewards, progress_by_reward_id, today_counts)
            if not rewards:
                return None
            return self._draw(rewards, effective_no_reward_probability)

        return run_sync_or_async(_impl())

    # --- Pure selection helpers shared by select_reward and select_reward_sync ---

    @staticmethod
    def _is_completed(reward, progress) -> bool:
        return bool(progress and progress.pieces_earned >= reward.pieces_required)

    def _eligible_rewards(self, rewards: list, progress_by_reward_id: dict, today_counts: dict) -> list:
        """Drop completed rewards and rewards at their daily limit (``today_counts``)."""
        eligible, excluded_completed, excluded_daily_limit = [], [], []
        for reward in rewards:
            progress = progress_by_reward_id.get(reward.id)
            if self._is_completed(reward, progress):
                excluded_completed.append(reward.name)
                logger.debug(
                    "Excluding %s - already completed (%s/%s pieces)",
                    reward.name, progress.pieces_earned, reward.pieces_required,
                )
                continue
            if reward.max_daily_claims is not None and reward.max_daily_claims > 0:
                today_count = today_counts.get(reward.id, 0)
                if today_count >= reward.max_daily_claims:
                    excluded_daily_limit.append(f"{reward.name} ({today_count}/{reward.max_daily_claims})")
                    logger.debug(
                        "Excluding %s - daily limit reached (%s/%s pieces today)",
                        reward.name, today_count, reward.max_daily_claims,
                    )
                    continue
            eligible.append(reward)

        if excluded_completed:
            logger.info("Excluded %s completed rewards: %s", len(excluded_completed), ", ".join(excluded_completed))
        if excluded_daily_limit:
            logger.info(
                "Excluded %s rewards due to daily limit: %s",
                len(excluded_daily_limit), ", ".join(excluded_daily_limit),
            )
        if not eligible:
            logger.warning(
                "No eligible rewards remain after filtering (completed: %s, daily limit: %s)",
                len(excluded_completed), len(excluded_daily_limit),
            )
        return eligible

    def _draw(self, rewards: list, effective_no_reward_probability: float):
        """Weighted draw among ``rewards`` plus an implicit "no reward" option.

        If S = sum(reward weights) and p = effective no-reward %, the "no reward"
        weight is N = S * p / (100 - p), so P(no reward) = N / (S + N) = p.
        """
        reward_weights = [reward.weight for reward in rewards]
        sum_reward_weights = sum(reward_weights)
        logger.info("Reward weights: %s (sum=%.2f)", [(r.name, r.weight) for r in rewards], sum_reward_weights)

        if sum_reward_weights <= 0:
            logger.warning("Total reward selection weight is %s, returning None (no reward)", sum_reward_weights)
            return None

        p = effective_no_reward_probability
        if p <= 0:
            population, weights = rewards, reward_weights
            logger.info("p<=0: No 'None' in population (always reward)")
        elif p >= 100:
            logger.info("p>=100: effective_no_reward=%.1f%% -> always no reward", p)
            return None
        else:
            no_reward_weight = sum_reward_weights * (p / (100.0 - p))
            population = rewards + [None]
            weights = reward_weights + [no_reward_weight]
            logger.info(
                "Formula: N = S * p / (100 - p) = %.2f * %.1f / %.1f = %.2f",
                sum_reward_weights, p, 100.0 - p, no_reward_weight,
            )

        selected = random.choices(population, weights=weights, k=1)[0]
        if selected is None:
            logger.info("Selected: None (no reward)")
        else:
            logger.info("Selected reward: %s", selected.name)
        return selected

    def select_reward_sync(
        self, effective_no_reward_probability: float, user_id: int | str, target_date: date
    ) -> Reward | None:
        """Sync twin of ``select_reward`` for the single-transaction completion (0048 §4).

        Same filters and draw; reads through the repositories' sync methods so it can
        run inside ``transaction.atomic()`` with no ``await``.
        """
        if not (0 <= effective_no_reward_probability <= 100):
            raise ValueError(
                f"effective_no_reward_probability must be 0-100, got {effective_no_reward_probability}"
            )
        rewards = self.reward_repo.get_all_active_sync(user_id)
        if not rewards:
            logger.warning("No active rewards found for user %s, returning None (no reward)", user_id)
            return None
        progress_by_reward_id = {p.reward_id: p for p in self.progress_repo.get_all_by_user_sync(user_id)}
        todays_logs = self.habit_log_repo.get_todays_logs_by_user_sync(user_id, target_date)
        today_counts: dict = {}
        for reward in rewards:
            if reward.max_daily_claims is not None and reward.max_daily_claims > 0:
                today_counts[reward.id] = sum(
                    1 for log in todays_logs if log.got_reward and log.reward_id == reward.id
                )
        rewards = self._eligible_rewards(rewards, progress_by_reward_id, today_counts)
        if not rewards:
            return None
        return self._draw(rewards, effective_no_reward_probability)

    def update_reward_progress_sync(self, user_id, reward_id) -> RewardProgress:
        """Sync twin of ``update_reward_progress`` (same rules: achieved stays, claimed resets)."""
        if self.reward_repo.get_by_id_sync(reward_id) is None:
            logger.error("Reward %s doesn't exist", reward_id)
            raise ValueError("Reward doesn't exist")
        progress = self.progress_repo.get_or_create_sync(user_id, reward_id)
        status = progress.get_status()
        if status == RewardStatus.ACHIEVED:
            logger.info("Reward %s already achieved for user %s, skipping increment", reward_id, user_id)
            return progress
        updates: dict[str, object] = {"pieces_earned": progress.pieces_earned + 1}
        if status == RewardStatus.CLAIMED:
            updates["claimed"] = False
        return self.progress_repo.update_sync(progress.id, updates)

    def get_todays_awarded_rewards(self, user_id: str, target_date: 'date | None' = None) -> list[str] | Awaitable[list[str]]:
        """Get list of reward IDs that were already awarded today."""

        async def _impl() -> list[str]:
            logger.info("Fetching today's awarded rewards for user=%s", user_id)

            todays_logs = await maybe_await(
                self.habit_log_repo.get_todays_logs_by_user(user_id, target_date=target_date)
            )

            awarded_reward_ids = [
                log.reward_id
                for log in todays_logs
                if log.got_reward and log.reward_id
            ]

            logger.info(
                "Found %s rewards awarded today for user=%s",
                len(awarded_reward_ids),
                user_id,
            )
            logger.debug("Today's awarded reward IDs: %s", awarded_reward_ids)
            return awarded_reward_ids

        return run_sync_or_async(_impl())

    def get_todays_pieces_by_reward(
        self,
        user_id: str,
        reward_id: str,
        target_date: 'date | None' = None,
    ) -> int | Awaitable[int]:
        """
        Count how many pieces of a specific reward were awarded today.

        This counts ALL pieces awarded today from habit logs, regardless of
        whether they have been claimed or not. This prevents users from
        bypassing daily limits by claiming between completions.

        Args:
            user_id: User ID
            reward_id: Reward ID

        Returns:
            Number of pieces awarded today for this reward (claimed or unclaimed)
        """

        async def _impl() -> int:
            logger.debug(
                "Counting today's pieces (all) for user=%s, reward=%s",
                user_id,
                reward_id,
            )

            # Get today's logs for this user
            todays_logs = await maybe_await(
                self.habit_log_repo.get_todays_logs_by_user(user_id, target_date=target_date)
            )

            # Count logs where this specific reward was awarded
            # This includes both claimed and unclaimed pieces to prevent bypass
            count = sum(
                1 for log in todays_logs
                if log.got_reward and log.reward_id == reward_id
            )

            logger.debug(
                "Found %s pieces awarded today for user=%s, reward=%s (including claimed)",
                count,
                user_id,
                reward_id,
            )
            return count

        return run_sync_or_async(_impl())

    def update_reward_progress(
        self,
        user_id: str,
        reward_id: str
    ) -> RewardProgress | Awaitable[RewardProgress]:
        """Update progress for any reward (unified system)."""

        async def _impl() -> RewardProgress:
            logger.info(
                "Updating reward progress for user=%s, reward=%s",
                user_id,
                reward_id,
            )
            progress = await maybe_await(
                self.progress_repo.get_by_user_and_reward(user_id, reward_id)
            )
            reward = await maybe_await(self.reward_repo.get_by_id(reward_id))

            if not reward:
                logger.error("Reward %s doesn't exist", reward_id)
                raise ValueError("Reward doesn't exist")

            if progress is None:
                progress = await maybe_await(
                    self.progress_repo.create(
                        SimpleNamespace(
                            user_id=user_id,
                            reward_id=reward_id,
                            pieces_earned=0,
                            claimed=False,
                        )
                    )
                )

            progress = self._coerce_progress(progress)
            current_status = progress.get_status()

            if current_status == RewardStatus.ACHIEVED:
                logger.info(
                    "Reward %s already achieved for user %s, skipping increment",
                    reward_id,
                    user_id,
                )
                return progress

            updates: dict[str, object] = {}
            if current_status == RewardStatus.CLAIMED:
                logger.info(
                    "Reward %s was claimed for user %s, resetting claimed flag",
                    reward_id,
                    user_id,
                )
                updates["claimed"] = False

            new_pieces = progress.pieces_earned + 1
            updates["pieces_earned"] = new_pieces

            updated_progress = await maybe_await(
                self.progress_repo.update(progress.id, updates)
            )

            return self._coerce_progress(updated_progress)

        return run_sync_or_async(_impl())

    def mark_reward_claimed(
        self,
        user_id: str,
        reward_id: str
    ) -> RewardProgress | Awaitable[RewardProgress]:
        """Mark a reward as claimed by user and reset the counter.

        For non-recurring rewards (is_recurring=False), also deactivates the reward
        after claiming.
        """

        async def _impl() -> RewardProgress:
            progress = await maybe_await(
                self.progress_repo.get_by_user_and_reward(user_id, reward_id)
            )

            if not progress:
                raise ValueError("Reward progress not found")

            current_status = progress.get_status()

            if current_status != RewardStatus.ACHIEVED:
                raise ValueError("Reward must be in 'Achieved' status to be claimed")

            # Get reward to check is_recurring
            reward = await maybe_await(self.reward_repo.get_by_id(reward_id))
            if not reward:
                raise ValueError("Reward not found")

            # Update progress (reset pieces and mark claimed)
            # Recurring rewards: claimed=False so they immediately return to
            # PENDING status and remain visible for the next earning cycle.
            # One-time rewards: claimed=True (then auto-deactivated below).
            updated_progress = await maybe_await(
                self.progress_repo.update(
                    progress.id,
                    {
                        "claimed": not reward.is_recurring,
                        "pieces_earned": 0,  # Reset counter for fresh start
                        "times_claimed": F("times_claimed") + 1,
                    },
                )
            )

            # Auto-deactivate non-recurring rewards
            if not reward.is_recurring:
                await maybe_await(
                    self.reward_repo.update(reward_id, {"active": False})
                )
                logger.info(
                    "Auto-deactivated non-recurring reward %s for user %s",
                    reward_id,
                    user_id,
                )

            logger.info(
                "Marked reward %s as claimed for user %s and reset pieces_earned to 0",
                reward_id,
                user_id,
            )

            return self._coerce_progress(updated_progress)

        return run_sync_or_async(_impl())


    def get_active_rewards(self, user_id: int | str) -> list[Reward] | Awaitable[list[Reward]]:
        """Get all active rewards for a specific user."""

        async def _impl() -> list[Reward]:
            return await maybe_await(self.reward_repo.get_all_active(user_id))

        return run_sync_or_async(_impl())

    def create_reward(
        self,
        *,
        user_id: int | str,
        name: str,
        weight: float,
        pieces_required: int,
        piece_value: float | None = None,
        is_recurring: bool = True
    ) -> Reward | Awaitable[Reward]:
        """Create a new reward after performing validation checks."""

        async def _impl() -> Reward:
            logger.info(
                "Creating reward for user=%s name=%s weight=%s pieces_required=%s piece_value=%s is_recurring=%s",
                user_id,
                name,
                weight,
                pieces_required,
                piece_value,
                is_recurring,
            )

            existing = await maybe_await(self.reward_repo.get_by_name(user_id, name))
            if existing:
                logger.warning(
                    "Reward creation blocked: duplicate name '%s' for user %s",
                    name,
                    user_id,
                )
                raise ValueError("Reward name already exists")

            data: dict[str, object] = {
                "user_id": user_id,
                "name": name,
                "weight": weight,
                "pieces_required": pieces_required,
                "is_recurring": is_recurring,
            }

            if piece_value is not None:
                data["piece_value"] = piece_value

            reward = await maybe_await(self.reward_repo.create(data))
            logger.info(
                "Reward '%s' created with id=%s for user %s",
                reward.name,
                getattr(reward, "id", None),
                user_id,
            )
            return reward

        return run_sync_or_async(_impl())

    def get_user_reward_progress(
        self,
        user_id: str
    ) -> list[RewardProgress] | Awaitable[list[RewardProgress]]:
        """Get all reward progress for a user.

        Returns all active rewards sorted by:
        1. Zero-piece rewards first — ``pieces_earned == 0`` or
           ``pieces_required`` unknown (includes synthetic entries for active
           rewards without a progress row, and recurring CLAIMED rewards which
           are treated as a fresh cycle).
        2. PENDING rewards with partial progress, sorted by completion ratio
           (``pieces_earned / pieces_required``) descending — closest-to-ready
           first, so the on-page progress bars decrease monotonically.
        3. ACHIEVED (ready-to-claim) rewards last, sorted by ``pieces_earned``
           ascending. They sit just above the separate claimed-rewards section
           rendered by the web UI. An ACHIEVED reward with ``pieces_earned == 0``
           (e.g. an instant 0/0 reward) belongs to bucket 1 instead — the
           zero-piece check takes precedence over status.

        One-time CLAIMED rewards are excluded; they surface via
        ``get_claimed_rewards`` and are rendered separately in the web UI.
        """

        async def _impl() -> list[RewardProgress]:
            results = await maybe_await(self.progress_repo.get_all_by_user(user_id))
            coerced = [self._coerce_progress(r) for r in results]

            progress_reward_ids = set()

            zero_piece: list[RewardProgress] = []
            pending: list[RewardProgress] = []
            ready_to_claim: list[RewardProgress] = []
            for p in coerced:
                progress_reward_ids.add(
                    int(p.reward_id) if isinstance(p.reward_id, str) else p.reward_id
                )
                status = p.get_status()
                if status == RewardStatus.CLAIMED:
                    reward_obj = getattr(p, "reward", None)
                    if reward_obj and getattr(reward_obj, "is_recurring", False):
                        zero_piece.append(p)
                    continue

                pieces_req = self._resolve_pieces_required(p)
                if p.pieces_earned == 0 or pieces_req is None:
                    zero_piece.append(p)
                elif status == RewardStatus.ACHIEVED:
                    ready_to_claim.append(p)
                else:
                    pending.append(p)

            active_rewards = await maybe_await(
                self.reward_repo.get_all_active(user_id)
            )
            for reward in active_rewards:
                if reward.id not in progress_reward_ids:
                    synthetic = RewardProgressModel(
                        id=None,
                        user_id=user_id,
                        reward_id=reward.id,
                        pieces_earned=0,
                        pieces_required=reward.pieces_required,
                        claimed=False,
                        times_claimed=0,
                        reward=reward,
                    )
                    zero_piece.append(synthetic)

            # Pending: closest-to-ready first (descending by completion ratio)
            # so the visual progress bars decrease monotonically down the list.
            def _pending_sort_key(rp):
                req = self._resolve_pieces_required(rp)
                return -(rp.pieces_earned / req) if req else 0.0
            pending.sort(key=_pending_sort_key)
            ready_to_claim.sort(key=lambda rp: rp.pieces_earned)

            return zero_piece + pending + ready_to_claim

        return run_sync_or_async(_impl())

    def get_actionable_rewards(
        self,
        user_id: str
    ) -> list[RewardProgress] | Awaitable[list[RewardProgress]]:
        """Get all achieved (actionable) rewards for a user."""

        async def _impl() -> list[RewardProgress]:
            results = await maybe_await(
                self.progress_repo.get_achieved_by_user(user_id)
            )
            return [self._coerce_progress(r) for r in results]

        return run_sync_or_async(_impl())

    def get_claimed_rewards(
        self,
        user_id: str
    ) -> list[RewardProgress] | Awaitable[list[RewardProgress]]:
        """Get all rewards ever claimed by a user (times_claimed > 0).

        Results are sorted alphabetically by reward name (handled by repository query).
        """

        async def _impl() -> list[RewardProgress]:
            results = await maybe_await(
                self.progress_repo.get_ever_claimed_by_user(user_id)
            )
            return [self._coerce_progress(r) for r in results]

        return run_sync_or_async(_impl())

    def toggle_reward_active(
        self,
        user_id: str,
        reward_id: str,
        active: bool
    ) -> Reward | Awaitable[Reward]:
        """Toggle reward active status.

        Args:
            user_id: User ID (for ownership validation)
            reward_id: Reward ID
            active: New active status (True=activate, False=deactivate)

        Returns:
            Updated Reward instance

        Raises:
            ValueError: If reward not found or user doesn't own it
        """

        async def _impl() -> Reward:
            # Validate reward exists
            reward = await maybe_await(self.reward_repo.get_by_id(reward_id))
            if not reward:
                logger.error("Reward %s not found", reward_id)
                raise ValueError("Reward not found")

            # Validate ownership
            user_id_int = int(user_id) if isinstance(user_id, str) else user_id
            reward_user_id = int(reward.user_id) if isinstance(reward.user_id, str) else reward.user_id
            if reward_user_id != user_id_int:
                logger.error(
                    "User %s attempted to toggle reward %s owned by user %s",
                    user_id,
                    reward_id,
                    reward.user_id
                )
                raise ValueError("You don't have permission to modify this reward")

            # Update active status
            updated_reward = await maybe_await(
                self.reward_repo.update(reward_id, {"active": active})
            )

            logger.info(
                "User %s toggled reward %s active status to %s",
                user_id,
                reward_id,
                active
            )

            return updated_reward

        return run_sync_or_async(_impl())


    @staticmethod
    def _resolve_pieces_required(progress: RewardProgress) -> int | None:
        """Resolve pieces_required across model variants.

        Django RewardProgress exposes the value only via `_get_pieces_required_safe()`
        (the field lives on the related Reward, cached by the repository).
        Pydantic RewardProgress has it as a direct field. Returns None when
        neither path yields a value — caller should treat as "unknown".
        """
        if hasattr(progress, "_get_pieces_required_safe"):
            try:
                value = progress._get_pieces_required_safe()
                if value is not None:
                    return value
            except (ValueError, AttributeError):
                pass
        return getattr(progress, "pieces_required", None)

    @staticmethod
    def _coerce_progress(progress: RewardProgress) -> RewardProgress:
        """Ensure progress object exposes `get_status` and typed fields."""

        if hasattr(progress, "get_status"):
            return progress

        if hasattr(progress, "status"):
            progress.get_status = MethodType(
                lambda self: getattr(self, "status"),
                progress,
            )
            return progress

        required_attrs = ("user_id", "reward_id")
        if not all(hasattr(progress, attr) for attr in required_attrs):
            return progress

        return RewardProgressModel.model_validate(
            progress,
            from_attributes=True,
        )


# Global service instance
reward_service = RewardService()
