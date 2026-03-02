"""Add times_claimed counter to RewardProgress.

Tracks how many times a user has claimed a particular reward.
Backfills existing claimed=True records with times_claimed=1.
"""

from django.db import migrations, models


def backfill_times_claimed(apps, schema_editor):
    """Set times_claimed=1 for all records where claimed=True."""
    RewardProgress = apps.get_model('core', 'RewardProgress')
    RewardProgress.objects.filter(claimed=True).update(times_claimed=1)


def reverse_backfill(apps, schema_editor):
    """Reset times_claimed back to 0 for rollback."""
    RewardProgress = apps.get_model('core', 'RewardProgress')
    RewardProgress.objects.all().update(times_claimed=0)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_update_habit_weight_range'),
    ]

    operations = [
        migrations.AddField(
            model_name='rewardprogress',
            name='times_claimed',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Number of times this reward has been claimed',
            ),
        ),
        migrations.RunPython(backfill_times_claimed, reverse_backfill),
    ]
