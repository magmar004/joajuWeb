from .auth import CustomLoginForm, CustomSetPasswordForm, PerfilForm, RegistroForm

try:
    from .actividades import ActividadForm, JornadasFormSet
except ImportError:
    ActividadForm = None
    JornadasFormSet = None

_all_ = [
    'RegistroForm',
    'CustomLoginForm',
    'CustomSetPasswordForm',
    'PerfilForm',
    'ActividadForm',
    'JornadasFormSet',
]
