"""Feature 0048 PR B: one HabitLog per (habit, last_completed_date).

Required by the completion transaction (a concurrent double submit must fail on
insert). Pre-flight before deploying, read-only:

    HabitLog.objects.values('habit_id', 'last_completed_date') \
        .annotate(c=Count('id')).filter(c__gt=1)

If it returns rows, do not delete anything: stop and decide (plan Open Question 7).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_habit_freeze'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='habitlog',
            constraint=models.UniqueConstraint(
                fields=('habit', 'last_completed_date'), name='uniq_habitlog_habit_day'
            ),
        ),
    ]
