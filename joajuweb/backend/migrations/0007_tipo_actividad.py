from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0006_asistencia'),
    ]

    operations = [
        migrations.AddField(
            model_name='actividad',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('ambiental', 'Ambiental'),
                    ('educativa', 'Educativa'),
                    ('comunitaria', 'Comunitaria'),
                    ('salud', 'Salud'),
                    ('cultural', 'Cultural'),
                    ('otra', 'Otra'),
                ],
                default='comunitaria',
                max_length=20,
                verbose_name='Tipo',
            ),
        ),
    ]
