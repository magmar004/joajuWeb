"""
Módulo de modelos para la gestión de usuarios y roles del sistema JoajuWeb.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser


class Rol(models.Model):
    """
    Modelo que representa los roles dentro de la plataforma (ej. Voluntario, Coordinador).
    """
    id_rol = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre del Rol")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado que extiende la clase AbstractUser de Django.
    """
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    roles = models.ManyToManyField(Rol, related_name="usuarios", blank=True, verbose_name="Roles")

    def __str__(self):
        return f"{self.username} ({self.email})"