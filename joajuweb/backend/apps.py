from django.apps import AppConfig


class BackendConfig(AppConfig):
    # label=usuarios mantiene AUTH_USER_MODEL y las migraciones ya aplicadas.
    name = 'joajuweb.backend'
    label = 'usuarios'
    default_auto_field = 'django.db.models.BigAutoField'
