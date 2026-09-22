# Reglas de negocio de actividades: crear, editar, cancelar e inscribir.
from collections import OrderedDict
from datetime import date

from django.db import IntegrityError, transaction
from django.db.models import Count, Q

from joajuweb.backend.models import (
    Actividad,
    AreaActividad,
    EstadoActividad,
    EstadoAsistencia,
    Inscripcion,
    TipoActividad,
    Usuario,
)
from joajuweb.backend.notificaciones import avisar_cancelacion, avisar_modificacion


class AsistenciaError(Exception):
    pass


class InscripcionError(Exception):
    pass


class PerfilError(Exception):
    pass

CAMPOS_AVISO = ('nombre', 'descripcion', 'tipo', 'area', 'ubicacion', 'fecha', 'cupo')


def guardar_borrador(form, coordinador):
    return _persistir(form, coordinador, EstadoActividad.BORRADOR)


def publicar(form, coordinador):
    return _persistir(form, coordinador, EstadoActividad.PUBLICADA)


def _persistir(form, coordinador, estado):
    actividad = form.save(commit=False)
    actividad.creado_por = coordinador
    actividad.estado = estado
    actividad.save()
    return actividad


def modificar_actividad(form, publicar_ahora=False):
    # is_valid() ya escribió los datos nuevos en instance; leemos el original de la BD.
    original = Actividad.objects.get(pk=form.instance.pk)
    estaba_publicada = original.esta_publicada()
    cambios = _cambios_relevantes(original, form.cleaned_data)

    actividad = form.save(commit=False)
    if publicar_ahora and actividad.esta_borrador():
        actividad.estado = EstadoActividad.PUBLICADA
    actividad.save()

    avisos = 0
    if estaba_publicada and cambios:
        avisos = avisar_modificacion(actividad, cambios)
    return actividad, avisos


def cancelar_actividad(actividad):
    if not actividad.se_puede_cancelar():
        return actividad, 0
    avisos = avisar_cancelacion(actividad)
    actividad.estado = EstadoActividad.CANCELADA
    actividad.save(update_fields=['estado'])
    return actividad, avisos


def inscribir_voluntario(actividad, voluntario):
    if voluntario.es_coordinador():
        raise InscripcionError('Los coordinadores no se inscriben como voluntarios.')
    if not actividad.esta_publicada():
        raise InscripcionError('Solo podés inscribirte en actividades publicadas.')
    try:
        with transaction.atomic():
            actividad_bloqueada = Actividad.objects.select_for_update().get(pk=actividad.pk)
            if Inscripcion.objects.filter(actividad=actividad_bloqueada, voluntario=voluntario).exists():
                raise InscripcionError('Ya estás inscripto en esta actividad.')
            _validar_cupo_disponible(actividad_bloqueada)
            return Inscripcion.objects.create(
                actividad=actividad_bloqueada,
                voluntario=voluntario,
            )
    except IntegrityError:
        raise InscripcionError('Ya estás inscripto en esta actividad.')


def historial_voluntario(voluntario):
    return (
        Inscripcion.objects.filter(voluntario=voluntario)
        .select_related('actividad', 'actividad__creado_por')
        .order_by('-actividad__fecha', '-fecha_inscripcion')
    )


def puede_ver_historial(viewer, voluntario):
    if not viewer.is_authenticated:
        return False
    if viewer.pk == voluntario.pk:
        return True
    if not viewer.es_coordinador():
        return False
    return Inscripcion.objects.filter(
        voluntario=voluntario,
        actividad__creado_por=viewer,
    ).exists()


def voluntarios_de_coordinador(coordinador):
    return (
        Usuario.objects.filter(
            inscripciones__actividad__creado_por=coordinador,
        )
        .distinct()
        .order_by('first_name', 'last_name', 'username')
    )


def cancelar_inscripcion(actividad, voluntario):
    borradas, _ = Inscripcion.objects.filter(
        actividad=actividad,
        voluntario=voluntario,
    ).delete()
    if not borradas:
        raise InscripcionError('No estás inscripto en esta actividad.')


def registrar_asistencia(actividad, marcas):
    if not actividad.se_puede_registrar_asistencia():
        raise AsistenciaError(
            'La asistencia se registra cuando la actividad ya finalizó y tiene inscriptos.'
        )
    validos = {EstadoAsistencia.PRESENTE, EstadoAsistencia.AUSENTE}
    inscripciones = list(actividad.inscripciones.all())
    for inscripcion in inscripciones:
        valor = marcas.get(inscripcion.pk)
        if valor not in validos:
            raise AsistenciaError('Marcá presente o ausente en todos los voluntarios.')
    for inscripcion in inscripciones:
        inscripcion.asistencia = marcas[inscripcion.pk]
        inscripcion.save(update_fields=['asistencia'])
    return len(inscripciones)


def generar_reporte(coordinador, fecha_desde=None, fecha_hasta=None, tipo=None):
    actividades = Actividad.objects.filter(creado_por=coordinador)
    if fecha_desde:
        actividades = actividades.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        actividades = actividades.filter(fecha__lte=fecha_hasta)
    if tipo:
        actividades = actividades.filter(tipo=tipo)

    actividades = list(
        actividades.annotate(
            n_inscriptos=Count('inscripciones', distinct=True),
            n_presentes=Count(
                'inscripciones',
                filter=Q(inscripciones__asistencia=EstadoAsistencia.PRESENTE),
                distinct=True,
            ),
            n_ausentes=Count(
                'inscripciones',
                filter=Q(inscripciones__asistencia=EstadoAsistencia.AUSENTE),
                distinct=True,
            ),
        ).order_by('-fecha', 'nombre')
    )
    ids_actividades = [actividad.pk for actividad in actividades]
    inscripciones = list(
        Inscripcion.objects.filter(actividad_id__in=ids_actividades)
        .select_related('voluntario', 'actividad')
        .order_by('-actividad__fecha', 'voluntario__username')
    )
    voluntarios = list(
        Usuario.objects.filter(inscripciones__actividad_id__in=ids_actividades)
        .distinct()
        .annotate(
            n_inscripciones=Count(
                'inscripciones',
                filter=Q(inscripciones__actividad_id__in=ids_actividades),
            ),
            n_presentes=Count(
                'inscripciones',
                filter=Q(
                    inscripciones__actividad_id__in=ids_actividades,
                    inscripciones__asistencia=EstadoAsistencia.PRESENTE,
                ),
            ),
        )
        .order_by('first_name', 'last_name', 'username')
    )

    return {
        'totales': {
            'actividades': len(actividades),
            'publicadas': sum(1 for item in actividades if item.esta_publicada()),
            'canceladas': sum(1 for item in actividades if item.esta_cancelada()),
            'voluntarios': len(voluntarios),
            'inscripciones': len(inscripciones),
            'presentes': sum(
                1 for item in inscripciones if item.asistencia == EstadoAsistencia.PRESENTE
            ),
            'ausentes': sum(
                1 for item in inscripciones if item.asistencia == EstadoAsistencia.AUSENTE
            ),
        },
        'actividades': actividades,
        'voluntarios': voluntarios,
        'inscripciones': inscripciones,
    }


def _validar_cupo_disponible(actividad):
    if actividad.esta_completa():
        raise InscripcionError('La actividad está completa. No quedan cupos disponibles.')


def filtrar_actividades_publicadas(tipo=None, area=None, ubicacion=None):
    actividades = Actividad.publicadas()
    if tipo:
        actividades = actividades.filter(tipo=tipo)
    if area:
        actividades = actividades.filter(area=area)
    if ubicacion:
        actividades = actividades.filter(ubicacion__icontains=ubicacion)
    return actividades


def agrupar_actividades(actividades, agrupar='tipo'):
    if agrupar == 'area':
        return _agrupar_por_choices(actividades, 'area', AreaActividad.choices)
    if agrupar == 'ubicacion':
        grupos = OrderedDict()
        for actividad in actividades:
            titulo = actividad.ubicacion.strip() or 'Sin ubicación'
            grupos.setdefault(titulo, []).append(actividad)
        return [{'titulo': titulo, 'actividades': items} for titulo, items in grupos.items()]
    return _agrupar_por_choices(actividades, 'tipo', TipoActividad.choices)


def _agrupar_por_choices(actividades, campo, choices):
    por_clave = {}
    for actividad in actividades:
        por_clave.setdefault(getattr(actividad, campo), []).append(actividad)
    grupos = []
    for valor, etiqueta in choices:
        items = por_clave.get(valor)
        if items:
            grupos.append({'titulo': etiqueta, 'actividades': items})
    return grupos


def resumen_inicio_voluntario(voluntario, limite_abiertas=3):
    hoy = date.today()
    ids_inscriptos = set(voluntario.inscripciones.values_list('actividad_id', flat=True))
    proximas = list(Actividad.publicadas().filter(fecha__gte=hoy))
    proxima = next((actividad for actividad in proximas if actividad.id in ids_inscriptos), None)
    abiertas = [
        actividad for actividad in proximas
        if proxima is None or actividad.id != proxima.id
    ][:limite_abiertas]
    return {
        'proxima': proxima,
        'proxima_lista': [proxima] if proxima else [],
        'abiertas': abiertas,
        'ids_inscriptos': ids_inscriptos,
    }


def actualizar_perfil(form):
    if not form.is_valid():
        raise PerfilError('Revisá los campos marcados.')
    return form.save()


def _cambios_relevantes(actividad, datos):
    etiquetas = {
        'nombre': 'Nombre',
        'descripcion': 'Descripción',
        'fecha': 'Fecha',
        'tipo': 'Tipo',
        'area': 'Área',
        'ubicacion': 'Ubicación',
        'cupo': 'Cupo',
    }
    cambios = []
    for campo in CAMPOS_AVISO:
        anterior = getattr(actividad, campo)
        nuevo = datos.get(campo)
        if anterior != nuevo:
            cambios.append(f'{etiquetas[campo]}: {anterior} → {nuevo}')
    return cambios
