"""Configuración aislada para pruebas funcionales sin PostgreSQL local.

Los tests de bloqueo/concurrencia deben ejecutarse también con joajuweb.settings
contra PostgreSQL; SQLite no implementa SELECT FOR UPDATE.
"""
from .settings import *  # noqa: F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
MAILERS = {'default': {'BACKEND': 'django.core.mail.backends.locmem.EmailBackend'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
