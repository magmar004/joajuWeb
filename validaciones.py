# validaciones.py

from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password


def validar_correo_unico(correo, modelo_usuario):
    """
    JOA-31: Valida que el correo no esté ya registrado.
    """
    if modelo_usuario.objects.filter(correo=correo).exists():
        raise ValidationError("Ya existe una cuenta registrada con este correo electrónico.")
    return correo


def encriptar_password(password_plano):
    """
    JOA-32: Encripta la contraseña antes de guardarla.
    """
    return make_password(password_plano)


def verificar_password(password_plano, password_hash):
    """
    Función complementaria para el login.
    """
    return check_password(password_plano, password_hash)