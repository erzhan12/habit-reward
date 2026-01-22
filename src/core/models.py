"""Django ORM models for habit reward system."""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    """User account and profile extending Django's AbstractUser.

    Inherits from AbstractUser to enable Django authentication features
    while maintaining Telegram bot compatibility.

    Inherited fields from AbstractUser:
    - username: CharField (unique, required) - Auto-generated as f"tg_{telegram_id}"
    - email: EmailField (optional)
    - password: CharField (hashed password, unusable for Telegram-only users)
    - first_name, last_name: CharField (optional)
    - is_staff: BooleanField (Django admin access)
    - is_superuser: BooleanField (Django superuser permissions)
    - is_active: BooleanField (replaces custom 'active' field)
    - date_joined: DateTimeField (replaces 'created_at')
    """

    # Custom Telegram-specific fields
    telegram_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique Telegram user ID"
    )
    name = models.CharField(
        max_length=255,
        help_text="User display name (separate from first_name/last_name)"
    )
    language = models.CharField(
        max_length=2,
        default='en',
        choices=[
            ('en', 'English'),
            ('ru', 'Russian'),
            ('kk', 'Kazakh'),
        ],
        help_text="User's preferred language (ISO 639-1 code)"
    )
    no_reward_probability = models.FloatField(
        default=50.0,
        validators=[MinValueValidator(0.01), MaxValueValidator(99.99)],
        help_text="Probability of getting no reward during habit completion (0.01-99.99%)"
    )
    updated_at = models.DateTimeField(auto_now=True)

    # Django's is_active field (from AbstractUser) replaces custom 'active' field
    # Default is True in AbstractUser, we'll override in Meta

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['telegram_id']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.name} ({self.telegram_id})"

    def save(self, *args, **kwargs):
        """Override save to auto-generate username from telegram_id if not set."""
        if not self.username and self.telegram_id:
            self.username = f"tg_{self.telegram_id}"

        # Set unusable password for Telegram-only users if no password set
        if not self.password:
            self.set_unusable_password()

        super().save(*args, **kwargs)


class Habit(models.Model):
    """Habit definition."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='habits',
        help_text="User who owns this habit"
    )
    name = models.CharField(
        max_length=255,
        help_text="Habit name"
    )
    weight = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Habit base weight for reward calculations (1-100)"
    )
    category = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Habit category (e.g., health, productivity)"
    )
    allowed_skip_days = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of consecutive days user can skip without breaking streak (0 for strict)"
    )
    exempt_weekdays = models.JSONField(
        default=list,
        blank=True,
        help_text="List of weekday numbers (1=Mon, 7=Sun) that don't count against streak"
    )
    active = models.BooleanField(
        default=True,
        help_text="Whether habit is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'habits'
        unique_together = [('user', 'name')]
        indexes = [
            models.Index(fields=['user', 'active', 'name']),
            models.Index(fields=['category']),
        ]
        ordering = ['name']

    def __str__(self):
        if self.user:
            return f"{self.user.name} - {self.name}"
        return self.name


class Reward(models.Model):
    """Reward definition."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rewards',
        help_text="User who owns this reward"
    )
    name = models.CharField(
        max_length=255,
        help_text="Reward name"
    )
    weight = models.FloatField(
        default=1.0,
        help_text="Reward weight for selection probability"
    )
    pieces_required = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Number of pieces needed (1 for instant rewards)"
    )
    piece_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Value of each piece earned"
    )
    max_daily_claims = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum times this reward can be claimed per day (NULL or 0 = unlimited)"
    )
    is_recurring = models.BooleanField(
        default=True,
        help_text="If True, reward can be claimed multiple times. If False, reward auto-deactivates after first claim."
    )
    active = models.BooleanField(default=True, help_text="Whether reward is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rewards'
        unique_together = [('user', 'name')]
        indexes = [
            models.Index(fields=['user', 'active']),
        ]
        ordering = ['name']

    def __str__(self):
        if self.user:
            return f"{self.user.name} - {self.name}"
        return self.name


class RewardProgress(models.Model):
    """User progress toward a reward."""

    class RewardStatus(models.TextChoices):
        """Status of reward progress."""
        PENDING = '🕒 Pending', 'Pending'
        ACHIEVED = '⏳ Achieved', 'Achieved'
        CLAIMED = '✅ Claimed', 'Claimed'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reward_progress',
        help_text="Link to user"
    )
    reward = models.ForeignKey(
        Reward,
        on_delete=models.CASCADE,
        related_name='user_progress',
        help_text="Link to reward"
    )
    pieces_earned = models.IntegerField(
        default=0,
        help_text="Number of pieces earned so far"
    )
    claimed = models.BooleanField(
        default=False,
        help_text="Whether user has claimed this reward"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reward_progress'
        unique_together = [('user', 'reward')]
        indexes = [
            models.Index(fields=['user', 'reward']),
            models.Index(fields=['user']),
        ]
        ordering = ['reward__name']

    def get_status(self):
        """Computed status (replaces Airtable formula).

        IMPORTANT: This method requires the reward relationship to be loaded
        via select_related('reward') to avoid synchronous DB queries in async contexts.
        """
        if self.claimed:
            return self.RewardStatus.CLAIMED

        # Get pieces_required safely to avoid sync DB queries in async contexts
        pieces_required = self._get_pieces_required_safe()

        if self.pieces_earned >= pieces_required:
            return self.RewardStatus.ACHIEVED
        else:
            return self.RewardStatus.PENDING

    def _get_pieces_required_safe(self):
        """Safely get pieces_required without triggering sync DB queries.

        Returns:
            int: pieces_required value

        Raises:
            ValueError: If reward is not loaded and no cached value exists
        """
        # Check if we have a cached value (set by repository methods)
        if hasattr(self, '_cached_pieces_required'):
            return self._cached_pieces_required

        # Check if reward is loaded in Django's cache
        if hasattr(self, '_state') and 'reward' in self._state.fields_cache:
            return self.reward.pieces_required

        # Fallback: try to access reward (will fail in async context)
        # This maintains backward compatibility but with better error message
        try:
            return self.reward.pieces_required
        except Exception as e:
            raise ValueError(
                "RewardProgress.get_status() requires reward to be prefetched with "
                "select_related('reward'), or _cached_pieces_required to be set. "
                f"Original error: {e}"
            ) from e

    def get_pieces_required(self):
        """Get pieces required from linked reward (replaces Airtable lookup).

        IMPORTANT: Only access this after using select_related('reward')
        to avoid synchronous database queries in async code.
        """
        return self.reward.pieces_required

    def get_progress_percent(self):
        """Calculate progress percentage."""
        pieces_required = self.get_pieces_required()
        if not pieces_required or pieces_required == 0:
            return 0.0
        return min((self.pieces_earned / pieces_required) * 100, 100.0)

    def get_status_emoji(self):
        """Get emoji for current status."""
        return self.get_status().value.split()[0]

    def __str__(self):
        return f"{self.user.name} - {self.reward.name} ({self.pieces_earned}/{self.get_pieces_required()})"


class HabitLog(models.Model):
    """Habit completion log entry."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='habit_logs',
        help_text="Link to user"
    )
    habit = models.ForeignKey(
        Habit,
        on_delete=models.CASCADE,
        related_name='logs',
        help_text="Link to habit"
    )
    reward = models.ForeignKey(
        Reward,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='awarded_in_logs',
        help_text="Link to reward (if awarded)"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When habit was completed"
    )
    got_reward = models.BooleanField(
        default=False,
        help_text="Whether a meaningful reward was given"
    )
    streak_count = models.IntegerField(
        default=1,
        help_text="Current streak for this habit"
    )
    habit_weight = models.IntegerField(
        help_text="Habit weight at time of completion (1-100)"
    )
    total_weight_applied = models.FloatField(
        help_text="Total calculated weight (habit × user × streak multiplier)"
    )
    last_completed_date = models.DateField(
        help_text="Date of completion (for streak tracking)"
    )

    class Meta:
        db_table = 'habit_logs'
        indexes = [
            models.Index(fields=['user', 'habit', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['last_completed_date']),
            models.Index(fields=['got_reward']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.name} - {self.habit.name} ({self.timestamp.date()})"


class BotAuditLog(models.Model):
    """Audit log for high-level Telegram bot interactions.

    Captures event snapshots for debugging data corruption issues and user support.
    Logs are retained for 90 days with automatic cleanup.
    """

    class EventType(models.TextChoices):
        """Types of events logged in the audit trail."""
        COMMAND = 'command', 'Command'
        HABIT_COMPLETED = 'habit_completed', 'Habit Completed'
        HABIT_REVERTED = 'habit_reverted', 'Habit Reverted'
        REWARD_SELECTED = 'reward_selected', 'Reward Selected'
        REWARD_CLAIMED = 'reward_claimed', 'Reward Claimed'
        REWARD_REVERTED = 'reward_reverted', 'Reward Reverted'
        BUTTON_CLICK = 'button_click', 'Button Click'
        ERROR = 'error', 'Error'

    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the event occurred"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        db_index=True,
        help_text="User who triggered the event"
    )
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        db_index=True,
        help_text="Type of event"
    )
    command = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Command name (e.g., /habit_done, /streaks)"
    )
    callback_data = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Button callback data from inline keyboards"
    )
    habit = models.ForeignKey(
        Habit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="Related habit (if applicable)"
    )
    reward = models.ForeignKey(
        Reward,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="Related reward (if applicable)"
    )
    habit_log = models.ForeignKey(
        HabitLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="Related habit log entry (if applicable)"
    )
    snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="State snapshot at time of event (JSON)"
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error message and traceback (for ERROR events)"
    )

    class Meta:
        db_table = 'bot_audit_logs'
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['event_type', '-timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.name} - {self.event_type} ({self.timestamp})"


class AuthCode(models.Model):
    """One-time authentication code for secure API login.

    Users request a code via the API, receive it in Telegram,
    then enter it in the web/mobile app to prove Telegram ownership.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='auth_codes',
        help_text="User this code belongs to"
    )
    code = models.CharField(
        max_length=6,
        help_text="6-digit numeric code"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the code was generated"
    )
    expires_at = models.DateTimeField(
        help_text="When the code expires (5 minutes from creation)"
    )
    used = models.BooleanField(
        default=False,
        help_text="Whether the code has been used"
    )
    device_info = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Device/browser info from the requesting app"
    )
    failed_attempts = models.IntegerField(
        default=0,
        help_text="Number of failed verification attempts"
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Time until which this code is locked due to too many failures"
    )

    class Meta:
        db_table = 'auth_codes'
        indexes = [
            models.Index(fields=['user', 'code']),
            models.Index(fields=['expires_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"AuthCode for {self.user.name} (expires: {self.expires_at})"


class APIKey(models.Model):
    """API key for automated integrations.

    Users create keys via Telegram bot for use in fitness apps,
    iOS Shortcuts, scripts, etc. Keys are shown once and stored as hashes.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_keys',
        help_text="User who owns this API key"
    )
    key_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA256 hash of the API key (never store plaintext)"
    )
    name = models.CharField(
        max_length=100,
        help_text="User-friendly name (e.g., 'Fitness App', 'iOS Shortcut')"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the key was created"
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the key was last used"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the key is active (can be revoked)"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiration date"
    )

    class Meta:
        db_table = 'api_keys'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['key_hash']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"APIKey '{self.name}' for {self.user.name}"
