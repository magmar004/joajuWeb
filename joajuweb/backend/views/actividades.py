# Publicar, listar, gestionar, editar, cancelar e inscribirse en actividades.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from joajuweb.backend.forms import ActividadForm
from joajuweb.backend.models import (
    Actividad,
    AreaActividad,
    EstadoActividad,
    EstadoAsistencia,
    TipoActividad,
)
from joajuweb.backend.servicios import (
    AsistenciaError,
    InscripcionError,
    agrupar_actividades,
    cancelar_actividad,
    cancelar_inscripcion,
    filtrar_actividades_publicadas,
    guardar_borrador,
    inscribir_voluntario,
    modificar_actividad,
    publicar,
    registrar_asistencia,
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
        if form.is_valid():
            if request.POST.get('accion') == 'publicar':
                actividad = publicar(form, request.user)
                messages.success(
                    request,
                    f'La actividad "{actividad.nombre}" fue publicada. Ya es visible para los voluntarios.',
                )
                return redirect('voluntario:listado')
            actividad = guardar_borrador(form, request.user)
            messages.success(
                request,
                f'La actividad "{actividad.nombre}" se guardó como borrador. Los voluntarios no la ven todavía.',
            )
            return redirect('coordinador:gestionar')
    else:
        form = ActividadForm()

    return render(request, 'coordinador/publicar.html', {'form': form})


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
    actividad = get_object_or_404(Actividad.publicadas(), pk=pk)
    return render(request, 'voluntario/detalle.html', {
        'actividad': actividad,
        'esta_inscripto': actividad.esta_inscripto(request.user),
        'es_voluntario': not _es_coordinador(request.user),
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
    propias = Actividad.objects.filter(creado_por=request.user)
    return render(request, 'coordinador/gestionar.html', {
        'borradores': propias.filter(estado=EstadoActividad.BORRADOR),
        'publicadas': propias.filter(estado=EstadoActividad.PUBLICADA),
        'canceladas': propias.filter(estado=EstadoActividad.CANCELADA),
    })


@login_required
def editar_view(request, pk):
    if not _es_coordinador(request.user):
        return redirect('voluntario:home')

    actividad = _actividad_del_coordinador(request, pk)
    if not actividad.se_puede_editar():
        messages.warning(request, 'Una actividad cancelada no se puede modificar.')
        return redirect('coordinador:gestionar')

    if request.method == 'POST':
        form = ActividadForm(request.POST, instance=actividad)
        if form.is_valid():
            publicar_ahora = request.POST.get('accion') == 'publicar'
            actividad, avisos = modificar_actividad(form, publicar_ahora=publicar_ahora)
            extra = f' Se avisó a {avisos} voluntario(s) inscripto(s).' if avisos else ''
            if publicar_ahora:
                messages.success(request, f'La actividad "{actividad.nombre}" fue publicada.{extra}')
            else:
                messages.success(request, f'Se guardaron los cambios de "{actividad.nombre}".{extra}')
            return redirect('coordinador:gestionar')
    else:
        form = ActividadForm(instance=actividad)

    return render(request, 'coordinador/editar.html', {
        'form': form,
        'actividad': actividad,
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

    actividad, avisos = cancelar_actividad(actividad)
    extra = f' Se avisó a {avisos} voluntario(s) inscripto(s).' if avisos else ''
    messages.success(request, f'La actividad "{actividad.nombre}" fue cancelada.{extra}')
    return redirect('coordinador:gestionar')


@login_required
def asistencia_view(request, pk):
    if not _es_coordinador(request.user):
        return redirect('voluntario:home')

    actividad = _actividad_del_coordinador(request, pk)
    if not actividad.se_puede_registrar_asistencia():
        messages.warning(
            request,
            'La asistencia se registra cuando la actividad ya finalizó y tiene voluntarios inscriptos.',
        )
        return redirect('coordinador:gestionar')

    inscripciones = actividad.inscripciones.select_related('voluntario').order_by(
        'voluntario__first_name', 'voluntario__username',
    )

    if request.method == 'POST':
        marcas = {}
        for inscripcion in inscripciones:
            marcas[inscripcion.pk] = request.POST.get(f'asistencia_{inscripcion.pk}')
        try:
            registrar_asistencia(actividad, marcas)
        except AsistenciaError as error:
            messages.warning(request, str(error))
        else:
            messages.success(request, f'Se registró la asistencia de "{actividad.nombre}".')
            return redirect('coordinador:gestionar')

    return render(request, 'coordinador/asistencia.html', {
        'actividad': actividad,
        'inscripciones': inscripciones,
        'estados_asistencia': EstadoAsistencia,
    })
