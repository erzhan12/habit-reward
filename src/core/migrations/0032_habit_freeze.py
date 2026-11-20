"""Feature 0048 PR B: streak freeze schema (Habit.freeze_count, HabitFreezeEvent).

Schema only; existing habits start with freeze_count = 0. The pending, unrelated
user.theme choices drift is deliberately excluded. The HabitLog uniqueness
constraint lives in 0033 so its pre-flight can be run on its own.
"""

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_habit_streak_epoch'),
    ]

    operations = [
        migrations.CreateModel(
            name='HabitFreezeEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('earned', 'Earned'), ('spent', 'Spent')], max_length=10)),
                ('earned_on', models.DateField(blank=True, help_text='EARNED: user-local date of the winning completion; null otherwise', null=True)),
                ('covered_date', models.DateField(blank=True, help_text='SPENT: user-local date of the missed day the freeze covered', null=True)),
                ('state', models.CharField(blank=True, choices=[('held', 'Held'), ('spent', 'Spent'), ('forfeited', 'Forfeited')], help_text='EARNED only: held (in inventory), spent, or forfeited (returned while another freeze was held)', max_length=10, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'habit_freeze_events',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddField(
            model_name='habit',
            name='freeze_count',
            field=models.PositiveSmallIntegerField(default=0, help_text='Unused streak freezes held by this habit (0 or 1). Changed only through FreezeService / admin actions, never by a form save (feature 0048).'),
        ),
        migrations.AlterField(
            model_name='habit',
            name='weight',
            field=models.IntegerField(default=0, help_text='Habit weight (0-30). Counts toward daily points only; does not affect the reward chance since feature 0048', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(30)]),
        ),
        migrations.AlterField(
            model_name='habitlog',
            name='total_weight_applied',
            field=models.FloatField(help_text='Effective no-reward probability % applied during reward selection (100 - reward chance since feature 0048; pre-0026 records contain legacy multiplier values)'),
        ),
        migrations.AlterField(
            model_name='user',
            name='no_reward_probability',
            field=models.FloatField(default=50.0, help_text='Legacy setting, unused since feature 0048: the reward chance depends only on the streak', validators=[django.core.validators.MinValueValidator(0.01), django.core.validators.MaxValueValidator(99.99)]),
        ),
        migrations.AddConstraint(
            model_name='habit',
            constraint=models.CheckConstraint(condition=models.Q(('freeze_count__gte', 0), ('freeze_count__lte', 1)), name='habit_freeze_count_range'),
        ),
        migrations.AddField(
            model_name='habitfreezeevent',
            name='earned_event',
            field=models.ForeignKey(blank=True, help_text='SPENT only: the EARNED event whose freeze this spend consumed (null for an untracked freeze)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='spends', to='core.habitfreezeevent'),
        ),
        migrations.AddField(
            model_name='habitfreezeevent',
            name='habit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='freeze_events', to='core.habit'),
        ),
        migrations.AddField(
            model_name='habitfreezeevent',
            name='habit_log',
            field=models.ForeignKey(blank=True, help_text='EARNED: the completion that won the freeze (null for non-completion grants or after that completion was undone). SPENT: always null', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='freeze_events', to='core.habitlog'),
        ),
        migrations.AddField(
            model_name='habitfreezeevent',
            name='user',
            field=models.ForeignKey(help_text='Owner, for per-user queries', on_delete=django.db.models.deletion.CASCADE, related_name='freeze_events', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddIndex(
            model_name='habitfreezeevent',
            index=models.Index(fields=['habit', 'event_type', 'state'], name='habit_freez_habit_i_68834d_idx'),
        ),
        migrations.AddConstraint(
            model_name='habitfreezeevent',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('covered_date__isnull', False), ('earned_on__isnull', True), ('event_type', 'spent'), ('state__isnull', True)), models.Q(('covered_date__isnull', True), ('earned_event__isnull', True), ('event_type', 'earned'), ('state__isnull', False)), _connector='OR'), name='freeze_event_shape'),
        ),
        migrations.AddConstraint(
            model_name='habitfreezeevent',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('event_type', 'spent'), _negated=True), ('habit_log__isnull', True), _connector='OR'), name='freeze_spent_has_no_log'),
        ),
        migrations.AddConstraint(
            model_name='habitfreezeevent',
            constraint=models.UniqueConstraint(condition=models.Q(('event_type', 'spent')), fields=('habit', 'covered_date'), name='uniq_freeze_spent_habit_day'),
        ),
        migrations.AddConstraint(
            model_name='habitfreezeevent',
            constraint=models.UniqueConstraint(condition=models.Q(('habit_log__isnull', False)), fields=('habit_log', 'event_type'), name='uniq_freeze_event_log_type'),
        ),
        migrations.AddConstraint(
            model_name='habitfreezeevent',
            constraint=models.UniqueConstraint(condition=models.Q(('event_type', 'earned'), ('state', 'held')), fields=('habit',), name='uniq_freeze_held_per_habit'),
        ),
    ]
