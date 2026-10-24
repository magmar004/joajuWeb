import re
import unicodedata

from django.db import migrations, models


TIPOS_INTERES = (
    ('ambiental', 'Ambiental', 1),
    ('educativa', 'Educativa', 2),
    ('comunitaria', 'Comunitaria', 3),
    ('salud', 'Salud', 4),
    ('cultural', 'Cultural', 5),
    ('otra', 'Otra', 6),
)

ALIAS_A_CODIGO = {
    'ambiental': 'ambiental',
    'medio ambiente': 'ambiental',
    'medioambiental': 'ambiental',
    'educativa': 'educativa',
    'educativo': 'educativa',
    'educacion': 'educativa',
    'comunitaria': 'comunitaria',
    'comunitario': 'comunitaria',
    'comunidad': 'comunitaria',
    'salud': 'salud',
    'salud y deporte': 'salud',
    'deporte': 'salud',
    'cultural': 'cultural',
    'cultura': 'cultural',
    'otra': 'otra',
    'otros': 'otra',
    'otras': 'otra',
}


def _normalizar(valor):
    valor = unicodedata.normalize('NFKD', valor.casefold())
    return ''.join(caracter for caracter in valor if not unicodedata.combining(caracter)).strip()


def crear_catalogo_intereses(apps, schema_editor):
    TipoInteres = apps.get_model('usuarios', 'TipoInteresActividad')
    TipoInteres.objects.using(schema_editor.connection.alias).bulk_create([
        TipoInteres(codigo=codigo, nombre=nombre, orden=orden)
        for codigo, nombre, orden in TIPOS_INTERES
    ])


def migrar_intereses_existentes(apps, schema_editor):
    TipoInteres = apps.get_model('usuarios', 'TipoInteresActividad')
    Usuario = apps.get_model('usuarios', 'Usuario')
    alias_a_codigo = {_normalizar(alias): codigo for alias, codigo in ALIAS_A_CODIGO.items()}
    tipos = {
        codigo: TipoInteres.objects.using(schema_editor.connection.alias).get(codigo=codigo)
        for codigo, _, _ in TIPOS_INTERES
    }

    usuarios = Usuario.objects.using(schema_editor.connection.alias).exclude(intereses__isnull=True).exclude(intereses='')
    for usuario in usuarios.iterator():
        codigos = set()
        for termino in re.split(r'[,;\n|]+', usuario.intereses):
            codigo = alias_a_codigo.get(_normalizar(termino))
            if codigo:
                codigos.add(codigo)
        if codigos:
            usuario.intereses_actividad.add(*(tipos[codigo] for codigo in codigos))


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0014_actividad_ciudad_actividad_departamento'),
    ]

    operations = [
        migrations.CreateModel(
            name='TipoInteresActividad',
            fields=[
                ('codigo', models.CharField(max_length=20, primary_key=True, serialize=False)),
                ('nombre', models.CharField(max_length=40)),
                ('orden', models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'tipo de interés',
                'verbose_name_plural': 'tipos de interés',
                'ordering': ('orden', 'nombre'),
            },
        ),
        migrations.AddField(
            model_name='usuario',
            name='intereses_actividad',
            field=models.ManyToManyField(
                blank=True,
                related_name='usuarios',
                to='usuarios.tipointeresactividad',
                verbose_name='Intereses en actividades',
            ),
        ),
        migrations.RunPython(crear_catalogo_intereses, migrations.RunPython.noop),
        migrations.RunPython(migrar_intereses_existentes, migrations.RunPython.noop),
    ]
