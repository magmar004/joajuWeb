from .auth import CustomLoginForm, CustomSetPasswordForm, PerfilForm, RegistroForm

try:
    from .actividades import ActividadForm
except ImportError:
    ActividadForm = None

_all_ = [
    'RegistroForm',
    'CustomLoginForm',
    'CustomSetPasswordForm',
    'PerfilForm',
    'ActividadForm',
]