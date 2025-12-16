"""Django admin configuration for habit reward models."""

import logging
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import transaction
from src.core.models import User, Habit, Reward, RewardProgress, HabitLog, BotAuditLog

logger = logging.getLogger(__name__)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model extending Django's UserAdmin.

    Extends Django's built-in UserAdmin to include Telegram-specific fields
    while maintaining all standard Django authentication features.
    """

    # List display with both Django auth and custom fields
    list_display = ['username', 'telegram_id', 'name', 'is_active', 'language', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'language', 'date_joined']
    search_fields = ['username', 'telegram_id', 'name', 'email']
    readonly_fields = ['date_joined', 'updated_at', 'last_login']
    ordering = ['-date_joined']

    # Customize fieldsets to include Telegram fields
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Telegram Information', {
            'fields': ('telegram_id', 'name', 'language')
        }),
        ('Personal info', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined', 'updated_at'),
        }),
    )

    # Add fieldsets for creating new users
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'telegram_id', 'name', 'language', 'password1', 'password2'),
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
    )


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    """Admin interface for Habit model."""

    list_display = ['name', 'user', 'weight', 'category', 'active', 'created_at']
    list_filter = ['active', 'category', 'created_at', 'user']
    search_fields = ['name', 'category', 'user__name', 'user__telegram_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['user', 'name']
    autocomplete_fields = ['user']

    fieldsets = (
        ('Habit Information', {
            'fields': ('user', 'name', 'weight', 'category', 'active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    """Admin interface for Reward model."""

    list_display = ['name', 'user', 'type', 'weight', 'pieces_required', 'piece_value', 'max_daily_claims', 'is_recurring', 'active', 'created_at']
    list_filter = ['type', 'active', 'is_recurring', 'created_at', 'user']
    search_fields = ['name', 'user__name', 'user__telegram_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['user', 'name']
    autocomplete_fields = ['user']

    fieldsets = (
        ('Reward Information', {
            'fields': ('user', 'name', 'type', 'weight', 'pieces_required', 'piece_value', 'is_recurring', 'active'),
            'description': 'is_recurring: If True, reward can be claimed multiple times. If False, reward auto-deactivates after first claim.'
        }),
        ('Daily Frequency Control', {
            'fields': ('max_daily_claims',),
            'description': 'Maximum times this reward can be claimed per day. Leave empty or set to 0 for unlimited daily claims.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RewardProgress)
class RewardProgressAdmin(admin.ModelAdmin):
    """Admin interface for RewardProgress model."""

    list_display = ['user', 'reward', 'pieces_earned', 'get_pieces_required', 'get_status', 'claimed', 'updated_at']
    list_filter = ['claimed', 'updated_at']
    search_fields = ['user__name', 'user__telegram_id', 'reward__name']
    readonly_fields = ['get_status', 'get_pieces_required', 'get_progress_percent', 'created_at', 'updated_at']
    ordering = ['-updated_at']
    autocomplete_fields = ['user', 'reward']

    fieldsets = (
        ('Progress Information', {
            'fields': ('user', 'reward', 'pieces_earned', 'claimed')
        }),
        ('Computed Fields', {
            'fields': ('get_status', 'get_pieces_required', 'get_progress_percent'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_status(self, obj):
        """Display status from computed method."""
        return obj.get_status().label
    get_status.short_description = 'Status'

    def get_pieces_required(self, obj):
        """Display pieces_required from computed method."""
        return obj.get_pieces_required()
    get_pieces_required.short_description = 'Pieces Required'

    def get_progress_percent(self, obj):
        """Display progress percentage."""
        return f"{obj.get_progress_percent():.1f}%"
    get_progress_percent.short_description = 'Progress'


@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    """Admin interface for HabitLog model."""

    list_display = ['user', 'habit', 'last_completed_date', 'timestamp', 'streak_count', 'got_reward', 'reward']
    list_filter = ['got_reward', 'last_completed_date', 'timestamp']
    search_fields = ['user__name', 'user__telegram_id', 'habit__name']
    readonly_fields = ['timestamp', 'created_at']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    autocomplete_fields = ['user', 'habit', 'reward']
    actions = ['revert_selected_logs']

    fieldsets = (
        ('Log Information', {
            'fields': ('user', 'habit', 'reward', 'timestamp', 'last_completed_date')
        }),
        ('Metrics', {
            'fields': ('got_reward', 'streak_count', 'habit_weight', 'total_weight_applied')
        }),
    )

    def created_at(self, obj):
        """Alias for timestamp (for consistency)."""
        return obj.timestamp
    created_at.short_description = 'Created At'

    @admin.action(description='Revert selected habit logs (and reward progress)')
    def revert_selected_logs(self, request, queryset):
        """Custom admin action to properly revert habit logs.

        This action calls habit_service.revert_habit_completion() for each selected log,
        which ensures proper rollback of reward progress and maintains data integrity.
        """
        # Optimize queries by prefetching related objects
        queryset = queryset.select_related('user', 'habit', 'reward')

        success_count = 0
        failed_count = 0
        error_messages = []

        for log in queryset:
            try:
                # Validate that log has required relationships
                if not log.user:
                    failed_count += 1
                    error_msg = f"Log #{log.id}: Missing user"
                    error_messages.append(error_msg)
                    logger.warning(f"⚠️ {error_msg}")
                    continue

                if not log.habit:
                    failed_count += 1
                    error_msg = f"Log #{log.id}: Missing habit"
                    error_messages.append(error_msg)
                    logger.warning(f"⚠️ {error_msg}")
                    continue

                # Revert the log using synchronous Django ORM
                # This bypasses the async service layer to avoid event loop conflicts
                user = log.user
                habit = log.habit
                reward = log.reward

                logger.info(
                    f"🔄 Admin reverting log #{log.id} for user {user.telegram_id}, habit {habit.id}"
                )

                # Use atomic transaction to ensure consistency
                with transaction.atomic():
                    # Store info before deletion
                    log_id = log.id
                    habit_name = habit.name
                    got_reward = log.got_reward

                    # Delete the habit log
                    log.delete()

                    # Prepare snapshot for audit log
                    snapshot = {
                        'habit_name': habit_name,
                        'log_id': log_id,
                    }

                    # If log had a reward, decrement reward progress
                    if got_reward and reward:
                        try:
                            progress = RewardProgress.objects.select_related('reward').get(
                                user=user,
                                reward=reward
                            )

                            # Decrement pieces_earned
                            if progress.pieces_earned > 0:
                                progress.pieces_earned -= 1

                                # If was claimed, mark as unclaimed
                                if progress.claimed:
                                    progress.claimed = False

                                progress.save()
                                logger.info(
                                    f"📉 Decremented reward progress for '{reward.name}': "
                                    f"{progress.pieces_earned + 1} → {progress.pieces_earned}"
                                )

                                # Add reward info to snapshot
                                snapshot.update({
                                    'reward_name': reward.name,
                                    'pieces_earned': progress.pieces_earned,
                                    'pieces_required': reward.pieces_required,
                                    'claimed': progress.claimed,
                                })
                        except RewardProgress.DoesNotExist:
                            logger.warning(
                                f"⚠️ Reward progress not found for log #{log_id}, skipping decrement"
                            )

                    # Create audit log entry for habit revert
                    BotAuditLog.objects.create(
                        user=user,
                        event_type=BotAuditLog.EventType.HABIT_REVERTED,
                        habit=habit,
                        reward=reward if got_reward else None,
                        snapshot=snapshot
                    )

                success_count += 1
                logger.info(
                    f"✅ Successfully reverted log #{log_id} for habit '{habit_name}'"
                )

            except ValueError as e:
                failed_count += 1
                error_msg = f"Log #{log.id}: {str(e)}"
                error_messages.append(error_msg)
                logger.error(f"❌ {error_msg}")

            except Exception as e:
                failed_count += 1
                error_msg = f"Log #{log.id}: Unexpected error - {str(e)}"
                error_messages.append(error_msg)
                logger.error(f"❌ {error_msg}", exc_info=True)

        # Display results to admin user
        if failed_count == 0:
            # Full success
            self.message_user(
                request,
                f"Successfully reverted {success_count} habit log(s).",
                messages.SUCCESS
            )
        elif success_count == 0:
            # Total failure
            error_summary = "\n".join(error_messages[:5])  # Show first 5 errors
            if len(error_messages) > 5:
                error_summary += f"\n... and {len(error_messages) - 5} more errors"

            self.message_user(
                request,
                f"Failed to revert all {failed_count} log(s).\n\nErrors:\n{error_summary}",
                messages.ERROR
            )
        else:
            # Partial success
            error_summary = "\n".join(error_messages[:3])  # Show first 3 errors
            if len(error_messages) > 3:
                error_summary += f"\n... and {len(error_messages) - 3} more errors"

            self.message_user(
                request,
                f"Reverted {success_count} log(s). Failed: {failed_count}.\n\nErrors:\n{error_summary}",
                messages.WARNING
            )


@admin.register(BotAuditLog)
class BotAuditLogAdmin(admin.ModelAdmin):
    """Admin interface for BotAuditLog model (read-only)."""

    list_display = ['timestamp', 'user', 'event_type', 'command', 'habit', 'reward']
    list_filter = ['event_type', 'timestamp']
    search_fields = ['user__telegram_id', 'user__name', 'command', 'error_message']
    readonly_fields = ['timestamp', 'user', 'event_type', 'command', 'callback_data',
                       'habit', 'reward', 'habit_log', 'snapshot', 'error_message']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    autocomplete_fields = []  # All fields are read-only

    fieldsets = (
        ('Event Information', {
            'fields': ('timestamp', 'user', 'event_type')
        }),
        ('Event Details', {
            'fields': ('command', 'callback_data', 'habit', 'reward', 'habit_log')
        }),
        ('Snapshot & Error', {
            'fields': ('snapshot', 'error_message'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        """Disable add permission - logs are created automatically."""
        return False

    def has_change_permission(self, request, obj=None):
        """Allow viewing but not editing."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup purposes."""
        return request.user.is_superuser
