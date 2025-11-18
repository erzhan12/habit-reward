"""Django admin configuration for habit reward models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from src.core.models import User, Habit, Reward, RewardProgress, HabitLog, BotAuditLog


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

    list_display = ['name', 'weight', 'category', 'active', 'created_at']
    list_filter = ['active', 'category', 'created_at']
    search_fields = ['name', 'category']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']

    fieldsets = (
        ('Habit Information', {
            'fields': ('name', 'weight', 'category', 'active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    """Admin interface for Reward model."""

    list_display = ['name', 'type', 'weight', 'pieces_required', 'piece_value', 'max_daily_claims', 'active', 'created_at']
    list_filter = ['type', 'active', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']

    fieldsets = (
        ('Reward Information', {
            'fields': ('name', 'type', 'weight', 'pieces_required', 'piece_value', 'active')
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
