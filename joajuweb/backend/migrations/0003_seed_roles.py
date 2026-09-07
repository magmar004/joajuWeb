from django.db import migrations


ROLES_INICIALES = [
    ("Voluntario", "Usuario voluntario de la plataforma"),
    ("Coordinador", "Coordinador de actividades"),
]


def seed_roles(apps, schema_editor):
    Rol = apps.get_model("usuarios", "Rol")
    for nombre, descripcion in ROLES_INICIALES:
        Rol.objects.get_or_create(nombre=nombre, defaults={"descripcion": descripcion})


def unseed_roles(apps, schema_editor):
    Rol = apps.get_model("usuarios", "Rol")
    Rol.objects.filter(nombre__in=[nombre for nombre, _ in ROLES_INICIALES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0002_remove_usuario_estado_remove_usuario_foto_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_roles, unseed_roles),
    ]
