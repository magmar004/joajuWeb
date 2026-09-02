from django.db import models
from django.contrib.auth.models import AbstractUser

class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.nombre

class Usuario(AbstractUser):
    telefono = models.CharField(max_length=20, blank=True, null=True)
    foto = models.ImageField(upload_to='perfiles/', blank=True, null=True)
    fecha_registro = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=20, default='ACTIVO')
    roles = models.ManyToManyField(Rol, related_name='usuarios')

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"