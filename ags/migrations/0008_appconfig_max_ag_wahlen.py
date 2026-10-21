import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ags', '0007_termin_erinnerung'),
    ]

    operations = [
        # Bestehende Konfiguration behält das bisherige Limit 5; neue Halbjahre starten mit 4.
        migrations.AddField(
            model_name='appconfig',
            name='max_ag_wahlen',
            field=models.PositiveSmallIntegerField(
                default=5, help_text='Wird beim Halbjahreswechsel auf den neuen Standard gesetzt.',
                validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)],
                verbose_name='Max. AG-Wahlen pro Kind'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='appconfig',
            name='max_ag_wahlen',
            field=models.PositiveSmallIntegerField(
                default=4, help_text='Wird beim Halbjahreswechsel auf den neuen Standard gesetzt.',
                validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)],
                verbose_name='Max. AG-Wahlen pro Kind'),
        ),
    ]
