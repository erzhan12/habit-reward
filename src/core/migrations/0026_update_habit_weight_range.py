"""Change Habit.weight from 1-100 (default 10) to 0-30 (default 0).

Part of the reward probability redesign: habit weight now directly reduces
the no-reward probability instead of acting as a multiplicative factor.

WARNING: This migration maps existing habit weights from the old 1-100 scale
to the new 0-30 scale using proportional mapping: new = round(old * 30 / 100).
Values that were already 0 remain 0. Users should review their habit weights
after this migration to ensure the mapped values match their intent.
"""

from django.db import migrations, models
import django.core.validators


def reset_habit_weights(apps, schema_editor):
    """Map existing habit weights from old 1-100 scale to new 0-30 scale.

    Uses proportional mapping: new_weight = round(old_weight * 30 / 100).
    Examples: 10 -> 3, 50 -> 15, 100 -> 30, 1 -> 0.
    """
    from django.db.models import F
    from django.db.models.functions import Round

    Habit = apps.get_model('core', 'Habit')
    Habit.objects.all().update(weight=Round(F('weight') * 30.0 / 100.0))


def restore_habit_weights(apps, schema_editor):
    """Restore weights to old default (10) for rollback."""
    Habit = apps.get_model('core', 'Habit')
    Habit.objects.filter(weight=0).update(weight=10)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_create_login_token_ip_binding'),
    ]

    operations = [
        # First reset data so existing values (1-100) don't violate new Max(30)
        migrations.RunPython(reset_habit_weights, restore_habit_weights),
        # Then alter the field constraints
        migrations.AlterField(
            model_name='habit',
            name='weight',
            field=models.IntegerField(
                default=0,
                help_text='Habit weight for reward probability bonus (0-30, each point = -1% no-reward)',
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(30),
                ],
            ),
        ),
    ]
