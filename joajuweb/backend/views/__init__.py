from .actividades import (
    asistencia_view,
    baja_inscripcion_view,
    cancelar_view,
    detalle_view,
    editar_view,
    gestionar_view,
    inscribirse_view,
    listado_view,
    publicar_view,
)
from .auth import (
    CustomLoginView,
    coordinador_home_view,
    coordinador_modulo_view,
    home_view,
    registro_view,
    voluntario_home_view,
)
from .historial import historial_ajeno_view, historial_propio_view, participacion_view
from .perfil import perfil_view
from .reportes import reportes_view

__all__ = [
    'registro_view',
    'CustomLoginView',
    'home_view',
    'voluntario_home_view',
    'coordinador_home_view',
    'coordinador_modulo_view',
    'publicar_view',
    'listado_view',
    'detalle_view',
    'inscribirse_view',
    'baja_inscripcion_view',
    'gestionar_view',
    'editar_view',
    'cancelar_view',
    'asistencia_view',
    'historial_propio_view',
    'historial_ajeno_view',
    'participacion_view',
    'reportes_view',
    'perfil_view',
]
