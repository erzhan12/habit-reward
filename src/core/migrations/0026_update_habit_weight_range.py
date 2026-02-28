"""Change Habit.weight from 1-100 (default 10) to 0-30 (default 0).

Part of the reward probability redesign: habit weight now directly reduces
the no-reward probability instead of acting as a multiplicative factor.
"""

from django.db import migrations, models
import django.core.validators


def reset_habit_weights(apps, schema_editor):
    """Set all existing habits' weight to 0 (new default)."""
    Habit = apps.get_model('core', 'Habit')
    Habit.objects.all().update(weight=0)


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
