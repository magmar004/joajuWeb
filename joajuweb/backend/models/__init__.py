from .usuarios import Rol, TipoInteresActividad, Usuario

try:
    from .actividades import (
        Actividad,
        AreaActividad,
        CIUDADES_CENTRAL,
        DepartamentoActividad,
        EstadoActividad,
        EstadoAsistencia,
        EstadoParticipacion,
        Inscripcion,
        JornadaActividad,
        AsistenciaJornada,
        TipoActividad,
    )
except ImportError:
    Actividad = None
    AreaActividad = None
    CIUDADES_CENTRAL = ()
    DepartamentoActividad = None
    EstadoActividad = None
    EstadoAsistencia = None
    EstadoParticipacion = None
    Inscripcion = None
    JornadaActividad = None
    AsistenciaJornada = None
    TipoActividad = None

_all_ = [
    'Rol',
    'TipoInteresActividad',
    'Usuario',
    'Actividad',
    'AreaActividad',
    'CIUDADES_CENTRAL',
    'DepartamentoActividad',
    'EstadoActividad',
    'EstadoAsistencia',
    'EstadoParticipacion',
    'Inscripcion',
    'JornadaActividad',
    'AsistenciaJornada',
    'TipoActividad',
]
