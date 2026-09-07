from .auth import (
    CustomLoginView,
    coordinador_home_view,
    coordinador_modulo_view,
    home_view,
    no_disponible_view,
    registro_view,
    voluntario_home_view,
)

try:
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
except ImportError:
    asistencia_view = None
    baja_inscripcion_view = None
    cancelar_view = None
    detalle_view = None
    editar_view = None
    gestionar_view = None
    inscribirse_view = None
    listado_view = None
    publicar_view = None

try:
    from .historial import historial_ajeno_view, historial_propio_view, participacion_view
except ImportError:
    historial_ajeno_view = None
    historial_propio_view = None
    participacion_view = None

try:
    from .perfil import perfil_view
except ImportError:
    perfil_view = None

try:
    from .reportes import reportes_view
except ImportError:
    reportes_view = None

_all_ = [
    'registro_view',
    'CustomLoginView',
    'home_view',
    'voluntario_home_view',
    'coordinador_home_view',
    'coordinador_modulo_view',
    'no_disponible_view',
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