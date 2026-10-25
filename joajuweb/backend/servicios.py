# Reglas de negocio de actividades: crear, editar, cancelar e inscribir.
from collections import OrderedDict
import secrets

from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone

from joajuweb.backend.models import (
    Actividad,
    AreaActividad,
    EstadoActividad,
    EstadoAsistencia,
    Inscripcion,
    AsistenciaJornada,
    TipoActividad,
    Usuario,
)
from joajuweb.backend.notificaciones import (
    avisar_actividad_publicada,
    avisar_cancelacion,
    avisar_modificacion,
)


class AsistenciaError(Exception):
    pass


class InscripcionError(Exception):
    pass


class PerfilError(Exception):
    pass


class ActividadError(Exception):
    pass


def _autorizar_coordinador(actividad, usuario):
    if not usuario.is_authenticated or not usuario.es_coordinador() or actividad.creado_por_id != usuario.pk:
        raise PermissionDenied


def _horarios_guardados(actividad):
    return list(actividad.jornadas.values_list('pk', 'fecha', 'hora_inicio', 'hora_fin'))


def _horarios_formulario(jornadas):
    return sorted([
        (form.instance.pk, form.cleaned_data['fecha'], form.cleaned_data.get('hora_inicio'), form.cleaned_data.get('hora_fin'))
        for form in jornadas.forms
        if form.cleaned_data and not form.cleaned_data.get('DELETE')
    ], key=lambda item: item[1])


def _guardar_jornadas(actividad, jornadas):
    jornadas.instance = actividad
    jornadas.save()


def _crear_con_codigo(actividad):
    # El índice único es la garantía final; cada intento tiene su propio savepoint.
    from joajuweb.backend.models.actividades import generar_codigo_asistencia
    for _ in range(5):
        actividad.codigo_asistencia = generar_codigo_asistencia()
        try:
            with transaction.atomic():
                actividad.save()
            return
        except IntegrityError:
            if not Actividad.objects.filter(codigo_asistencia=actividad.codigo_asistencia).exists():
                raise
    raise ActividadError('No se pudo generar el código. Intentá nuevamente.')

CAMPOS_AVISO = ('nombre', 'descripcion', 'tipo', 'departamento', 'ciudad', 'ubicacion', 'fecha', 'cupo')


def guardar_borrador(form, coordinador, jornadas):
    return _persistir(form, coordinador, EstadoActividad.BORRADOR, jornadas)


def publicar(form, coordinador, jornadas):
    actividad = _persistir(form, coordinador, EstadoActividad.PUBLICADA, jornadas)
    transaction.on_commit(lambda: avisar_actividad_publicada(actividad), robust=True)
    return actividad


@transaction.atomic
def _persistir(form, coordinador, estado, jornadas):
    if not coordinador.is_authenticated or not coordinador.es_coordinador():
        raise PermissionDenied
    actividad = form.save(commit=False)
    actividad.creado_por = coordinador
    actividad.estado = estado
    _crear_con_codigo(actividad)
    _guardar_jornadas(actividad, jornadas)
    return actividad


@transaction.atomic
def modificar_actividad(form, coordinador, jornadas, publicar_ahora=False):
    # is_valid() ya escribió los datos nuevos en instance; leemos el original de la BD.
    original = Actividad.objects.select_for_update().get(pk=form.instance.pk)
    _autorizar_coordinador(original, coordinador)
    if not original.se_puede_editar():
        raise ActividadError('Una actividad cancelada o finalizada no se puede modificar.')
    if form.cleaned_data['cupo'] < original.cantidad_inscriptos():
        raise ActividadError('El cupo ya no alcanza para los inscriptos actuales. Revisá el formulario.')
    horarios_cambiaron = _horarios_guardados(original) != _horarios_formulario(jornadas)
    if (horarios_cambiaron or original.fecha != form.cleaned_data['fecha']) and AsistenciaJornada.objects.filter(jornada__actividad=original).exists():
        raise ActividadError('No se puede reprogramar una actividad que ya tiene asistencia registrada.')
    estaba_publicada = original.esta_publicada()
    cambios = _cambios_relevantes(original, form.cleaned_data)
    if horarios_cambiaron:
        cambios.append('Jornadas u horarios de Asunción actualizados. Consultá el detalle de la actividad.')

    actividad = form.save(commit=False)
    se_publica_ahora = publicar_ahora and actividad.esta_borrador()
    if se_publica_ahora:
        actividad.estado = EstadoActividad.PUBLICADA
    actividad.save()
    _guardar_jornadas(actividad, jornadas)

    avisos = 0
    if estaba_publicada and cambios:
        avisos = avisar_modificacion(actividad, cambios)
    if se_publica_ahora:
        transaction.on_commit(lambda: avisar_actividad_publicada(actividad), robust=True)
    return actividad, avisos


@transaction.atomic
def cancelar_actividad(actividad, coordinador):
    actividad = Actividad.objects.select_for_update().get(pk=actividad.pk)
    _autorizar_coordinador(actividad, coordinador)
    if not actividad.se_puede_cancelar():
        return actividad, 0
    avisos = avisar_cancelacion(actividad)
    actividad.estado = EstadoActividad.CANCELADA
    actividad.save(update_fields=['estado'])
    return actividad, avisos


@transaction.atomic
def finalizar_actividad(actividad, coordinador):
    actividad = Actividad.objects.select_for_update().get(pk=actividad.pk)
    _autorizar_coordinador(actividad, coordinador)
    if actividad.esta_finalizada():
        return actividad
    if not actividad.esta_publicada():
        raise ActividadError('Solo se pueden dar por terminadas actividades publicadas.')
    if not actividad.se_puede_finalizar():
        raise ActividadError('Todavía quedan jornadas vigentes o futuras. Podés dar por terminada la actividad después del cierre de la última jornada.')
    actividad.estado = EstadoActividad.FINALIZADA
    actividad.finalizada_en = timezone.now()
    actividad.save(update_fields=['estado', 'finalizada_en'])
    return actividad


def inscribir_voluntario(actividad, voluntario):
    if voluntario.es_coordinador():
        raise InscripcionError('Los coordinadores no se inscriben como voluntarios.')
    if not actividad.esta_publicada():
        raise InscripcionError('Solo podés inscribirte en actividades publicadas.')
    try:
        with transaction.atomic():
            actividad_bloqueada = Actividad.objects.select_for_update().get(pk=actividad.pk)
            if not actividad_bloqueada.esta_publicada():
                raise InscripcionError('Solo podés inscribirte en actividades publicadas.')
            if not actividad_bloqueada.inscripciones_abiertas():
                raise InscripcionError('Las inscripciones están cerradas: no quedan jornadas vigentes o futuras.')
            if Inscripcion.objects.filter(actividad=actividad_bloqueada, voluntario=voluntario).exists():
                raise InscripcionError('Ya estás inscripto en esta actividad.')
            _validar_cupo_disponible(actividad_bloqueada)
            return Inscripcion.objects.create(
                actividad=actividad_bloqueada,
                voluntario=voluntario,
            )
    except IntegrityError:
        raise InscripcionError('Ya estás inscripto en esta actividad.')


def historial_voluntario(voluntario, q=''):
    inscripciones = (
        Inscripcion.objects.filter(voluntario=voluntario)
        .select_related('actividad', 'actividad__creado_por')
        .prefetch_related('asistencias__jornada', 'actividad__jornadas')
        .order_by('-actividad__fecha', '-fecha_inscripcion')
    )
    return aplicar_busqueda(
        inscripciones,
        q,
        ('actividad__nombre', 'actividad__ubicacion', 'actividad__descripcion'),
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


def voluntarios_de_coordinador(coordinador, q=''):
    voluntarios = (
        Usuario.objects.filter(
            inscripciones__actividad__creado_por=coordinador,
        )
        .distinct()
        .order_by('first_name', 'last_name', 'username')
    )
    return aplicar_busqueda(
        voluntarios,
        q,
        ('first_name', 'last_name', 'username', 'email'),
    )


@transaction.atomic
def cancelar_inscripcion(actividad, voluntario):
    actividad = Actividad.objects.select_for_update().get(pk=actividad.pk)
    if actividad.ya_finalizo():
        raise InscripcionError('La actividad ya terminó. La inscripción se conserva en tu historial.')
    inscripcion = Inscripcion.objects.filter(
        actividad=actividad,
        voluntario=voluntario,
    ).first()
    if not inscripcion:
        raise InscripcionError('No estás inscripto en esta actividad.')
    if inscripcion.asistencias.exists():
        raise InscripcionError('No podés cancelar una inscripción que ya tiene asistencia registrada.')
    inscripcion.delete()


def inscripciones_de_jornada(jornada):
    # Las jornadas históricas pueden contener registros previos a la propia inscripción.
    return jornada.actividad.inscripciones.filter(
        Q(fecha_inscripcion__lt=jornada.cierre()) | Q(asistencias__jornada=jornada)
    ).distinct().select_related('voluntario').order_by('voluntario__first_name', 'voluntario__last_name', 'voluntario__username')


def _estado_formulario(jornada):
    versiones = dict(jornada.asistencias.values_list('inscripcion_id', 'version'))
    return {
        'jornada': jornada.pk,
        'horario': [str(jornada.fecha), str(jornada.hora_inicio), str(jornada.hora_fin)],
        'zona_horaria': timezone.get_default_timezone_name(),
        'versiones': {str(item.pk): versiones.get(item.pk, 0) for item in inscripciones_de_jornada(jornada)},
    }


def version_asistencia(jornada):
    return signing.dumps(_estado_formulario(jornada), salt='asistencia-jornada')


@transaction.atomic
def registrar_asistencia(actividad, jornada_id, marcas, coordinador, version):
    actividad = Actividad.objects.select_for_update().get(pk=actividad.pk)
    _autorizar_coordinador(actividad, coordinador)
    jornada = actividad.jornadas.filter(pk=jornada_id).first()
    if not actividad.permite_asistencia_manual() or jornada is None or not jornada.finalizo():
        raise AsistenciaError('El registro manual solo está disponible al terminar la jornada de una actividad publicada o finalizada.')
    try:
        anterior = signing.loads(version, salt='asistencia-jornada')
    except (signing.BadSignature, TypeError):
        raise AsistenciaError('El formulario no es válido. Revisá los estados y volvé a guardar.')
    if anterior != _estado_formulario(jornada):
        raise AsistenciaError('Cambiaron las inscripciones, el horario o la asistencia desde que abriste el formulario. Revisá los estados actuales antes de guardar nuevamente.')
    inscripciones = list(inscripciones_de_jornada(jornada))
    if not inscripciones:
        raise AsistenciaError('No hay inscriptos elegibles en esta jornada.')
    if set(marcas) != {item.pk for item in inscripciones} or any(valor not in {EstadoAsistencia.PRESENTE, EstadoAsistencia.AUSENTE} for valor in marcas.values()):
        raise AsistenciaError('Marcá presente o ausente en todos los voluntarios de la jornada.')
    for inscripcion in inscripciones:
        registro, creado = AsistenciaJornada.objects.get_or_create(
            inscripcion=inscripcion, jornada=jornada,
            defaults={'estado': marcas[inscripcion.pk], 'origen': AsistenciaJornada.Origen.MANUAL, 'actualizado_en': timezone.now(), 'registrado_por': coordinador},
        )
        if not creado and registro.estado != marcas[inscripcion.pk]:
            registro.estado = marcas[inscripcion.pk]
            registro.origen = AsistenciaJornada.Origen.MANUAL
            registro.actualizado_en = timezone.now()
            registro.registrado_por = coordinador
            registro.version += 1
            registro.save()
    return len(inscripciones)


@transaction.atomic
def confirmar_asistencia(actividad_id, voluntario, codigo):
    if not voluntario.is_authenticated or voluntario.es_coordinador():
        raise PermissionDenied
    actividad = Actividad.objects.select_for_update().get(pk=actividad_id)
    if not actividad.esta_publicada():
        raise AsistenciaError('La actividad no está disponible para confirmar asistencia.')
    codigo = (codigo or '').strip().upper()
    if not codigo.isascii() or not secrets.compare_digest(codigo, actividad.codigo_asistencia):
        raise AsistenciaError('El código es incorrecto o corresponde a otra actividad.')
    inscripcion = actividad.inscripciones.filter(voluntario=voluntario).first()
    if inscripcion is None:
        raise AsistenciaError('No estás inscripto en esta actividad.')
    ahora = timezone.now()
    jornada = next((item for item in actividad.jornadas.all() if item.inicio() is not None and item.inicio() <= ahora < item.cierre()), None)
    if jornada is None:
        raise AsistenciaError('Estás fuera del horario permitido para confirmar asistencia (hora de Asunción).')
    if inscripcion.fecha_inscripcion > ahora:
        raise AsistenciaError('Tu inscripción no es válida para esta jornada.')
    registro = jornada.asistencias.filter(inscripcion=inscripcion).first()
    if registro:
        if registro.estado == EstadoAsistencia.AUSENTE:
            raise AsistenciaError('Ya figurás como ausente. Solicitá al coordinador que revise el registro.')
        raise AsistenciaError('Tu asistencia ya fue registrada para esta jornada.')
    return AsistenciaJornada.objects.create(
        jornada=jornada, inscripcion=inscripcion, estado=EstadoAsistencia.PRESENTE,
        origen=AsistenciaJornada.Origen.CODIGO, actualizado_en=ahora, registrado_por=voluntario,
    )


def generar_reporte(coordinador, fecha_desde=None, fecha_hasta=None, tipo=None):
    actividades = Actividad.objects.filter(creado_por=coordinador)
    filtro_jornadas = Q()
    filtro_fechas = Q()
    if fecha_desde:
        filtro_fechas &= Q(jornadas__fecha__gte=fecha_desde)
        filtro_jornadas &= Q(inscripciones__asistencias__jornada__fecha__gte=fecha_desde)
    if fecha_hasta:
        filtro_fechas &= Q(jornadas__fecha__lte=fecha_hasta)
        filtro_jornadas &= Q(inscripciones__asistencias__jornada__fecha__lte=fecha_hasta)
    if tipo:
        actividades = actividades.filter(tipo=tipo)
    actividades = actividades.filter(filtro_fechas)

    actividades = list(
        actividades.annotate(
            n_inscriptos=Count('inscripciones', distinct=True),
            n_presentes=Count(
                'inscripciones__asistencias',
                filter=Q(inscripciones__asistencias__estado=EstadoAsistencia.PRESENTE) & filtro_jornadas,
                distinct=True,
            ),
            n_ausentes=Count(
                'inscripciones__asistencias',
                filter=Q(inscripciones__asistencias__estado=EstadoAsistencia.AUSENTE) & filtro_jornadas,
                distinct=True,
            ),
        ).order_by('-fecha', 'nombre')
    )
    ids_actividades = [actividad.pk for actividad in actividades]
    inscripciones = list(
        Inscripcion.objects.filter(actividad_id__in=ids_actividades)
        .select_related('voluntario', 'actividad')
        .prefetch_related('asistencias__jornada')
        .order_by('-actividad__fecha', 'voluntario__username')
    )
    voluntarios = list(
        Usuario.objects.filter(inscripciones__actividad_id__in=ids_actividades)
        .distinct()
        .annotate(
            n_inscripciones=Count(
                'inscripciones',
                filter=Q(inscripciones__actividad_id__in=ids_actividades),
                distinct=True,
            ),
            n_presentes=Count(
                'inscripciones__asistencias',
                filter=Q(
                    inscripciones__actividad_id__in=ids_actividades,
                    inscripciones__asistencias__estado=EstadoAsistencia.PRESENTE,
                ) & filtro_jornadas,
                distinct=True,
            ),
        )
        .order_by('first_name', 'last_name', 'username')
    )

    for inscripcion in inscripciones:
        inscripcion.registros_reporte = [
            item for item in inscripcion.asistencias.all()
            if (not fecha_desde or item.jornada.fecha >= fecha_desde)
            and (not fecha_hasta or item.jornada.fecha <= fecha_hasta)
        ]

    return {
        'totales': {
            'actividades': len(actividades),
            'publicadas': sum(1 for item in actividades if item.esta_publicada()),
            'canceladas': sum(1 for item in actividades if item.esta_cancelada()),
            'voluntarios': len(voluntarios),
            'inscripciones': len(inscripciones),
            'presentes': sum(item.n_presentes for item in actividades),
            'ausentes': sum(item.n_ausentes for item in actividades),
        },
        'actividades': actividades,
        'voluntarios': voluntarios,
        'inscripciones': inscripciones,
    }


def _validar_cupo_disponible(actividad):
    if actividad.esta_completa():
        raise InscripcionError('La actividad está completa. No quedan cupos disponibles.')


def filtrar_actividades_publicadas(tipo=None, area=None, ubicacion=None, q='', departamento=None, ciudad=None):
    actividades = Actividad.vigentes()
    if tipo:
        actividades = actividades.filter(tipo=tipo)
    if area:
        actividades = actividades.filter(area=area)
    if departamento:
        actividades = actividades.filter(departamento=departamento)
    if ciudad:
        actividades = actividades.filter(ciudad__icontains=ciudad)
    if ubicacion:
        actividades = actividades.filter(ubicacion__icontains=ubicacion)
    return aplicar_busqueda(actividades, q, ('nombre', 'descripcion', 'ubicacion', 'ciudad', 'departamento'))


def aplicar_busqueda(queryset, texto, campos):
    for termino in (texto or '').split():
        filtro = Q()
        for campo in campos:
            filtro |= Q(**{f'{campo}__icontains': termino})
        queryset = queryset.filter(filtro)
    return queryset


def coincide_busqueda(texto, *partes):
    terminos = [parte.casefold() for parte in (texto or '').split() if parte]
    if not terminos:
        return True
    contenido = ' '.join(str(parte or '') for parte in partes).casefold()
    return all(termino in contenido for termino in terminos)


def agrupar_actividades(actividades, agrupar='tipo'):
    if agrupar == 'area':
        grupos = OrderedDict()
        for actividad in actividades:
            titulo = actividad.get_localidad() or actividad.get_area_display()
            grupos.setdefault(titulo, []).append(actividad)
        return [{'titulo': titulo, 'actividades': items} for titulo, items in grupos.items()]
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


def resumen_inicio_voluntario(voluntario, limite_abiertas=3, limite_recomendadas=3):
    ids_inscriptos = set(voluntario.inscripciones.values_list('actividad_id', flat=True))
    proximas = list(Actividad.vigentes())
    proxima = next((actividad for actividad in proximas if actividad.id in ids_inscriptos), None)
    abiertas = [
        actividad for actividad in proximas
        if proxima is None or actividad.id != proxima.id
    ][:limite_abiertas]
    tipos_interes = list(voluntario.intereses_actividad.values_list('codigo', flat=True))
    recomendadas = []
    if tipos_interes:
        recomendadas = list(
            Actividad.vigentes()
            .filter(tipo__in=tipos_interes)
            .exclude(pk__in=ids_inscriptos)
            .prefetch_related('jornadas')[:limite_recomendadas]
        )
    return {
        'proxima': proxima,
        'proxima_lista': [proxima] if proxima else [],
        'abiertas': abiertas,
        'recomendadas': recomendadas,
        'tiene_intereses': bool(tipos_interes),
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
        'departamento': 'Departamento',
        'ciudad': 'Ciudad',
        'departamento': 'Departamento',
        'ciudad': 'Ciudad',
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
