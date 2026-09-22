# Historial de participación del voluntario y consulta del coordinador.
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from joajuweb.backend.models import Usuario
from joajuweb.backend.servicios import (
    historial_voluntario,
    puede_ver_historial,
    voluntarios_de_coordinador,
)


def _es_coordinador(user):
    return user.is_authenticated and user.es_coordinador()


@login_required
def historial_propio_view(request):
    if _es_coordinador(request.user):
        return redirect('coordinador:participacion')
    return render(request, 'voluntario/historial.html', {
        'voluntario': request.user,
        'inscripciones': historial_voluntario(request.user),
        'es_propio': True,
    })


@login_required
def participacion_view(request):
    if not _es_coordinador(request.user):
        return redirect('voluntario:home')
    return render(request, 'coordinador/participacion.html', {
        'voluntarios': voluntarios_de_coordinador(request.user),
    })


@login_required
def historial_ajeno_view(request, pk):
    voluntario = get_object_or_404(Usuario, pk=pk)
    if not puede_ver_historial(request.user, voluntario):
        if _es_coordinador(request.user):
            return redirect('coordinador:participacion')
        return redirect('voluntario:home')
    return render(request, 'voluntario/historial.html', {
        'voluntario': voluntario,
        'inscripciones': historial_voluntario(voluntario),
        'es_propio': request.user.pk == voluntario.pk,
    })
