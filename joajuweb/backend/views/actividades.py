# Publicar, listar, gestionar, editar, cancelar e inscribirse en actividades.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from joajuweb.backend.forms import ActividadForm, JornadasFormSet
from joajuweb.backend.models import (
    Actividad,
    AreaActividad,
    EstadoActividad,
    EstadoAsistencia,
    TipoActividad,
)
from joajuweb.backend.servicios import (
    AsistenciaError,
    ActividadError,
    InscripcionError,
    agrupar_actividades,
    cancelar_actividad,
    finalizar_actividad,
    cancelar_inscripcion,
    filtrar_actividades_publicadas,
    guardar_borrador,
    inscribir_voluntario,
    modificar_actividad,
    publicar,
    registrar_asistencia,
    confirmar_asistencia,
    inscripciones_de_jornada,
    version_asistencia,
)


def _es_coordinador(user):
    return user.is_authenticated and user.es_coordinador()


def _actividad_del_coordinador(request, pk):
    return get_object_or_404(Actividad, pk=pk, creado_por=request.user)


@login_required
def publicar_view(request):
    if not _es_coordinador(request.user):
        return redirect('voluntario:home')

    if request.method == 'POST':
        form = ActividadForm(request.POST)
        jornadas = JornadasFormSet(request.POST, instance=form.instance, prefix='jornadas')
        valido = form.is_valid()
        jornadas_validas = jornadas.is_valid()
        if valido and jornadas_validas:
            if request.POST.get('accion') == 'publicar':
                actividad = publicar(form, request.user, jornadas)
                messages.success(
                    request,
                    f'La actividad "{actividad.nombre}" fue publicada. Ya es visible para los voluntarios.',
                )
                return redirect('voluntario:listado')
            actividad = guardar_borrador(form, request.user, jornadas)
            messages.success(
                request,
                f'La actividad "{actividad.nombre}" se guardó como borrador. Los voluntarios no la ven todavía.',
            )
            return redirect('coordinador:gestionar')
    else:
        form = ActividadForm()
        jornadas = JornadasFormSet(instance=form.instance, prefix='jornadas')

    return render(request, 'coordinador/publicar.html', {'form': form, 'jornadas': jornadas})


def _ids_inscriptos(user):
    if not user.is_authenticated:
        return set()
    return set(user.inscripciones.values_list('actividad_id', flat=True))


@login_required
def listado_view(request):
    tipo = request.GET.get('tipo', '').strip()
    area = request.GET.get('area', '').strip()
    ubicacion = request.GET.get('ubicacion', '').strip()
    agrupar = request.GET.get('agrupar', 'tipo').strip()
    if agrupar not in ('tipo', 'area', 'ubicacion'):
        agrupar = 'tipo'

    actividades = list(filtrar_actividades_publicadas(
        tipo=tipo or None,
        area=area or None,
        ubicacion=ubicacion or None,
    ))
    return render(request, 'voluntario/listado.html', {
        'grupos': agrupar_actividades(actividades, agrupar=agrupar),
        'ids_inscriptos': _ids_inscriptos(request.user),
        'tipos': TipoActividad,
        'areas': AreaActividad,
        'agrupar_opciones': (
            ('tipo', 'Tipo'),
            ('area', 'Área'),
            ('ubicacion', 'Ubicación'),
        ),
        'hay_filtros': bool(tipo or area or ubicacion),
        'filtros': {
            'tipo': tipo,
            'area': area,
            'ubicacion': ubicacion,
            'agrupar': agrupar,
        },
    })


@login_required
def detalle_view(request, pk):
    actividad = get_object_or_404(Actividad.objects.filter(
        estado__in=[EstadoActividad.PUBLICADA, EstadoActividad.FINALIZADA],
    ), pk=pk)
    return render(request, 'voluntario/detalle.html', {
        'actividad': actividad,
        'esta_inscripto': actividad.esta_inscripto(request.user),
        'es_voluntario': not _es_coordinador(request.user),
        'jornadas': actividad.jornadas.all(),
        'inscripcion': request.user.inscripciones.filter(actividad=actividad).prefetch_related('asistencias__jornada').first(),
    })


@login_required
def inscribirse_view(request, pk):
    if _es_coordinador(request.user):
        messages.warning(request, 'Los coordinadores no se inscriben como voluntarios.')
        return redirect('voluntario:listado')
    if request.method != 'POST':
        return redirect('voluntario:detalle', pk=pk)

    actividad = get_object_or_404(Actividad, pk=pk)
    try:
        inscribir_voluntario(actividad, request.user)
    except InscripcionError as error:
        messages.warning(request, str(error))
        if actividad.esta_publicada():
            return redirect('voluntario:detalle', pk=pk)
        return redirect('voluntario:listado')

    messages.success(request, f'Te inscribiste en "{actividad.nombre}".')
    return redirect('voluntario:listado')


@login_required
def baja_inscripcion_view(request, pk):
    if request.method != 'POST':
        return redirect('voluntario:listado')

    actividad = get_object_or_404(Actividad, pk=pk)
    try:
        cancelar_inscripcion(actividad, request.user)
    except InscripcionError as error:
        messages.warning(request, str(error))
    else:
        messages.success(request, f'Cancelaste tu inscripción en "{actividad.nombre}".')
    return redirect('voluntario:listado')


@login_required
def gestionar_view(request):
    if not _es_coordinador(request.user):
        return redirect('voluntario:home')
    propias = Actividad.objects.filter(creado_por=request.user).prefetch_related('jornadas')
    publicadas = list(propias.filter(estado=EstadoActividad.PUBLICADA))
    return render(request, 'coordinador/gestionar.html', {
        'borradores': propias.filter(estado=EstadoActividad.BORRADOR),
        'publicadas': [item for item in publicadas if not item.ya_finalizo()],
        'pendientes_cierre': [item for item in publicadas if item.ya_finalizo()],
        'finalizadas': propias.filter(estado=EstadoActividad.FINALIZADA),
        'canceladas': propias.filter(estado=EstadoActividad.CANCELADA),
    })


@login_required
def inscritos_view(request, pk):
    if not _es_coordinador(request.user):
        return redirect('voluntario:home')
    actividad = _actividad_del_coordinador(request, pk)
    # La inscripción es a toda la actividad, independientemente del horario diario.
    inscripciones = actividad.inscripciones.select_related('voluntario').order_by(
        'voluntario__first_name', 'voluntario__last_name', 'voluntario__username',
    )
    return render(request, 'coordinador/inscritos.html', {
        'actividad': actividad, 'inscripciones': inscripciones,
    })


@login_required
def editar_view(request, pk):
    if not _es_coordinador(request.user):
        return redirect('voluntario:home')

    actividad = _actividad_del_coordinador(request, pk)
    if not actividad.se_puede_editar():
        messages.warning(request, 'Una actividad cancelada o finalizada no se puede modificar.')
        return redirect('coordinador:gestionar')

    if request.method == 'POST':
        form = ActividadForm(request.POST, instance=actividad)
        jornadas = JornadasFormSet(request.POST, instance=actividad, prefix='jornadas')
        valido = form.is_valid()
        jornadas_validas = jornadas.is_valid()
        if valido and jornadas_validas:
            publicar_ahora = request.POST.get('accion') == 'publicar'
            try:
                actividad, avisos = modificar_actividad(form, request.user, jornadas, publicar_ahora=publicar_ahora)
            except ActividadError as error:
                form.add_error(None, str(error))
            else:
                extra = f' Se avisó a {avisos} voluntario(s) inscripto(s).' if avisos else ''
                messages.success(request, f'Se guardaron los cambios de "{actividad.nombre}".{extra}')
                return redirect('coordinador:gestionar')
    else:
        form = ActividadForm(instance=actividad)
        jornadas = JornadasFormSet(instance=actividad, prefix='jornadas')

    return render(request, 'coordinador/editar.html', {
        'form': form,
        'actividad': actividad,
        'jornadas': jornadas,
    })


@login_required
def cancelar_view(request, pk):
    if not _es_coordinador(request.user):
        return redirect('voluntario:home')
    if request.method != 'POST':
        return redirect('coordinador:gestionar')

    actividad = _actividad_del_coordinador(request, pk)
    if not actividad.se_puede_cancelar():
        messages.warning(request, 'Solo se pueden cancelar actividades publicadas.')
        return redirect('coordinador:gestionar')

    actividad, avisos = cancelar_actividad(actividad, request.user)
    extra = f' Se avisó a {avisos} voluntario(s) inscripto(s).' if avisos else ''
    messages.success(request, f'La actividad "{actividad.nombre}" fue cancelada.{extra}')
    return redirect('coordinador:gestionar')


@login_required
@require_POST
def finalizar_view(request, pk):
    if not _es_coordinador(request.user):
        return redirect('voluntario:home')
    actividad = _actividad_del_coordinador(request, pk)
    try:
        finalizar_actividad(actividad, request.user)
    except ActividadError as error:
        messages.warning(request, str(error))
    else:
        messages.success(request, f'La actividad "{actividad.nombre}" fue dada por terminada. Podés seguir completando y corrigiendo la asistencia.')
    return redirect('coordinador:gestionar')


@login_required
@never_cache
@transaction.atomic
def asistencia_view(request, pk):
    if not _es_coordinador(request.user):
        return redirect('voluntario:home')

    actividad = get_object_or_404(Actividad.objects.select_for_update(), pk=pk, creado_por=request.user)
    jornadas = list(actividad.jornadas.all())
    seleccion = request.POST.get('jornada') if request.method == 'POST' else request.GET.get('jornada')
    jornada = next((item for item in jornadas if str(item.pk) == seleccion), None)
    if seleccion and jornada is None:
        from django.http import Http404
        raise Http404
    if jornada is None and jornadas:
        jornada = next((item for item in reversed(jornadas) if item.finalizo()), jornadas[0])
    inscripciones = list(inscripciones_de_jornada(jornada)) if jornada else []
    editable = bool(jornada and jornada.finalizo() and actividad.permite_asistencia_manual() and inscripciones)
    marcas = {}
    if request.method == 'POST' and jornada:
        marcas = {item.pk: request.POST.get(f'asistencia_{item.pk}') for item in inscripciones}
        try:
            registrar_asistencia(actividad, jornada.pk, marcas, request.user, request.POST.get('version', ''))
        except AsistenciaError as error:
            messages.warning(request, str(error))
        else:
            messages.success(request, f'Se registró la asistencia de "{actividad.nombre}".')
            return redirect(f'{request.path}?jornada={jornada.pk}')
    registros = {item.inscripcion_id: item for item in jornada.asistencias.all()} if jornada else {}
    filas = []
    for inscripcion in inscripciones:
        registro = registros.get(inscripcion.pk)
        actual = registro.estado if registro else EstadoAsistencia.PENDIENTE
        filas.append({
            'inscripcion': inscripcion, 'estado_actual': actual,
            'estado': marcas.get(inscripcion.pk, actual),
            'origen': registro.get_origen_display() if registro else '',
        })
    return render(request, 'coordinador/asistencia.html', {
        'actividad': actividad,
        'jornadas': jornadas, 'jornada': jornada, 'filas': filas, 'editable': editable,
        'version': version_asistencia(jornada) if jornada else '',
        'total_inscritos': actividad.cantidad_inscriptos(),
        'inscritos_excluidos': actividad.cantidad_inscriptos() - len(inscripciones),
    })


@login_required
@require_POST
def confirmar_asistencia_view(request, pk):
    actividad = get_object_or_404(Actividad, pk=pk)
    try:
        registro = confirmar_asistencia(actividad.pk, request.user, request.POST.get('codigo'))
    except AsistenciaError as error:
        messages.warning(request, str(error))
    else:
        messages.success(request, f'Confirmaste tu asistencia del {registro.jornada.fecha:%d/%m/%Y}.')
    if actividad.esta_publicada():
        return redirect('voluntario:detalle', pk=pk)
    return redirect('voluntario:listado')
