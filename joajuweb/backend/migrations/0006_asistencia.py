from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0005_cancelacion_e_inscripcion'),
    ]

    operations = [
        migrations.AddField(
            model_name='inscripcion',
            name='asistencia',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente'),
                    ('presente', 'Presente'),
                    ('ausente', 'Ausente'),
                ],
                default='pendiente',
                max_length=20,
                verbose_name='Asistencia',
            ),
        ),
    ]
