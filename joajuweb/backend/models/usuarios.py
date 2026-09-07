# Cuentas y roles
from django.contrib.auth.models import AbstractUser
from django.db import models


class Rol(models.Model):
    # Rol de la plataforma (Voluntario, Coordinador)
    id_rol = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre del Rol")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    # Usuario propio; el rol se asigna en la relación N:M con Rol
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    foto = models.ImageField(
        upload_to='perfiles/',
        blank=True,
        null=True,
        verbose_name="Foto",
    )
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    roles = models.ManyToManyField(Rol, related_name="usuarios", blank=True, verbose_name="Roles")

    def __str__(self):
        return f"{self.username} ({self.email})"

    def es_coordinador(self):
        return self.roles.filter(nombre__iexact="Coordinador").exists()

    def rol_principal(self):
        return self.roles.first()
