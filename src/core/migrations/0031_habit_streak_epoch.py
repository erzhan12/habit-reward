"""Feature 0048 launch reset: add Habit.streak_epoch and set it to each user's local today.

Hand-written so it does not pick up the unrelated pending ``user.theme`` choices drift.
Writes only ``habits.streak_epoch``; no ``HabitLog`` row is touched, so historical
``streak_count`` values (and longest-streak stats) are preserved.
"""

from datetime import timezone as dt_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import migrations, models
from django.utils import timezone


def _local_date(now, tz_name):
    try:
        return now.astimezone(ZoneInfo(tz_name or "UTC")).date()
    except (KeyError, ValueError, ZoneInfoNotFoundError):
        return now.astimezone(dt_timezone.utc).date()


def set_streak_epoch(apps, schema_editor):
    Habit = apps.get_model("core", "Habit")
    now = timezone.now()
    by_date = {}
    for habit_id, tz_name in Habit.objects.values_list("id", "user__timezone"):
        by_date.setdefault(_local_date(now, tz_name), []).append(habit_id)
    for epoch, ids in by_date.items():
        Habit.objects.filter(id__in=ids).update(streak_epoch=epoch)


def clear_streak_epoch(apps, schema_editor):
    Habit = apps.get_model("core", "Habit")
    Habit.objects.update(streak_epoch=None)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0030_update_theme_choices"),
    ]

    operations = [
        migrations.AddField(
            model_name="habit",
            name="streak_epoch",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="User-local date from which completions count toward the streak "
                "(feature 0048 launch reset). Earlier logs are ignored as predecessors; a log "
                "on this date counts as streak day 1. Null: all history counts.",
            ),
        ),
        migrations.RunPython(set_streak_epoch, clear_streak_epoch),
    ]
