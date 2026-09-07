from .usuarios import Rol, Usuario

try:
    from .actividades import (
        Actividad,
        AreaActividad,
        EstadoActividad,
        EstadoAsistencia,
        EstadoParticipacion,
        Inscripcion,
        TipoActividad,
    )
except ImportError:
    Actividad = None
    AreaActividad = None
    EstadoActividad = None
    EstadoAsistencia = None
    EstadoParticipacion = None
    Inscripcion = None
    TipoActividad = None

_all_ = [
    'Rol',
    'Usuario',
    'Actividad',
    'AreaActividad',
    'EstadoActividad',
    'EstadoAsistencia',
    'EstadoParticipacion',
    'Inscripcion',
    'TipoActividad',
]