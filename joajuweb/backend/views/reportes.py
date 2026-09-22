# Reportes de impacto: totales y detalle filtrables por fecha y tipo.
from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from joajuweb.backend.models import TipoActividad
from joajuweb.backend.servicios import generar_reporte


def _fecha(valor):
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        return None


@login_required
def reportes_view(request):
    if not request.user.es_coordinador():
        return redirect('voluntario:home')

    fecha_desde = _fecha(request.GET.get('fecha_desde'))
    fecha_hasta = _fecha(request.GET.get('fecha_hasta'))
    tipo = request.GET.get('tipo') or ''
    if tipo not in TipoActividad.values:
        tipo = ''

    reporte = generar_reporte(
        request.user,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        tipo=tipo or None,
    )
    return render(request, 'coordinador/reportes.html', {
        'totales': reporte['totales'],
        'actividades': reporte['actividades'],
        'voluntarios': reporte['voluntarios'],
        'inscripciones': reporte['inscripciones'],
        'tipos': TipoActividad,
        'filtros': {
            'fecha_desde': fecha_desde.isoformat() if fecha_desde else '',
            'fecha_hasta': fecha_hasta.isoformat() if fecha_hasta else '',
            'tipo': tipo,
        },
    })
