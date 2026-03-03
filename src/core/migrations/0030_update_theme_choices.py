"""Data migration: map old theme IDs to new theme IDs, then alter field choices."""

from django.db import migrations, models


# Old theme ID → new theme ID mapping
FORWARD_MAP = {
    'dark_emerald': 'clean_modern',
    'light_clean': 'clean_modern',
    'neon_cyberpunk': 'gamified_arcade',
    'warm_earth': 'clean_modern',
    'ocean_gradient': 'gamified_arcade',
    'ios_glass': 'clean_modern',
    'minimal_ink': 'clean_modern',
}

# Best-effort reverse mapping for rollback
REVERSE_MAP = {
    'clean_modern': 'dark_emerald',
    'gamified_arcade': 'neon_cyberpunk',
    'cozy_warm': 'warm_earth',
    'minimalist_zen': 'minimal_ink',
    'ios_native': 'ios_glass',
    'dark_focus': 'dark_emerald',
    'retro_terminal': 'neon_cyberpunk',
    'nature_forest': 'warm_earth',
}

NEW_CHOICES = [
    ('clean_modern', 'Clean Modern'),
    ('gamified_arcade', 'Gamified Arcade'),
    ('cozy_warm', 'Cozy Warm'),
    ('minimalist_zen', 'Minimalist Zen'),
    ('ios_native', 'iOS Native'),
    ('dark_focus', 'Dark Focus'),
    ('retro_terminal', 'Retro Terminal'),
    ('nature_forest', 'Nature Forest'),
]


def migrate_themes_forward(apps, schema_editor):
    User = apps.get_model('core', 'User')
    for old_id, new_id in FORWARD_MAP.items():
        User.objects.filter(theme=old_id).update(theme=new_id)


def migrate_themes_reverse(apps, schema_editor):
    User = apps.get_model('core', 'User')
    for new_id, old_id in REVERSE_MAP.items():
        User.objects.filter(theme=new_id).update(theme=old_id)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_add_theme_to_user'),
    ]

    operations = [
        # Step 1: Data migration — remap old theme IDs to new ones
        migrations.RunPython(
            migrate_themes_forward,
            migrate_themes_reverse,
        ),
        # Step 2: Alter the field with new choices and default
        migrations.AlterField(
            model_name='user',
            name='theme',
            field=models.CharField(
                choices=NEW_CHOICES,
                default='clean_modern',
                help_text="User's selected UI theme",
                max_length=20,
            ),
        ),
    ]
