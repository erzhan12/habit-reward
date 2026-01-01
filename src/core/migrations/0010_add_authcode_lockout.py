# Generated manually for Feature 0026 security fixes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_add_authcode_apikey_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='authcode',
            name='failed_attempts',
            field=models.IntegerField(default=0, help_text='Number of failed verification attempts'),
        ),
        migrations.AddField(
            model_name='authcode',
            name='locked_until',
            field=models.DateTimeField(blank=True, help_text='Time until which this code is locked due to too many failures', null=True),
        ),
    ]

