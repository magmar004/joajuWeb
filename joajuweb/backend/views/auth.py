# Login, registro, panel y stubs de módulos del coordinador
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from joajuweb.backend.forms import CustomLoginForm, RegistroForm
from joajuweb.backend.models import DepartamentoActividad, TipoActividad
from joajuweb.backend.servicios import filtrar_actividades_publicadas

try:
    from joajuweb.backend.servicios import resumen_inicio_voluntario
except ImportError:
    resumen_inicio_voluntario = None

MODULOS_COORDINADOR = {
    'publicar_actividades': {
        'titulo': 'Publicar actividades de voluntariado',
        'icono': 'bi-plus-circle-fill',
        'descripcion': 'Desde aquí podrás crear y publicar nuevas actividades de voluntariado.',
    },
    'gestionar_actividades': {
        'titulo': 'Gestionar actividades de voluntariado',
        'icono': 'bi-calendar2-check-fill',
        'descripcion': 'Desde aquí podrás editar y dar seguimiento a las actividades ya publicadas.',
    },
    'reportes': {
        'titulo': 'Reportes',
        'icono': 'bi-bar-chart-fill',
        'descripcion': 'Desde aquí podrás consultar totales y el detalle de actividades, voluntarios e inscripciones.',
    },
    'registro_participacion': {
        'titulo': 'Registro de participación',
        'icono': 'bi-people-fill',
        'descripcion': 'Desde aquí podrás dar seguimiento a la participación de los voluntarios.',
    },
}


def destino_segun_rol(user):
    if user.es_coordinador():
        return 'coordinador:home'
    return 'voluntario:home'


def registro_view(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(destino_segun_rol(user))
    else:
        form = RegistroForm()
    return render(request, 'auth/registro.html', {'form': form})


class CustomLoginView(LoginView):
    template_name = 'auth/login.html'
    authentication_form = CustomLoginForm

    def get_success_url(self):
        url = self.get_redirect_url()
        if url:
            return url
        return reverse(destino_segun_rol(self.request.user))


def _render_inicio_publico(request):
    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    departamento = request.GET.get('departamento', '').strip()
    ciudad = request.GET.get('ciudad', '').strip()
    if tipo not in TipoActividad.values:
        tipo = ''
    if departamento not in DepartamentoActividad.values:
        departamento = ''
    actividades = filtrar_actividades_publicadas(
        tipo=tipo or None,
        departamento=departamento or None,
        ciudad=ciudad or None,
        q=q,
    ).prefetch_related('jornadas')
    opciones_departamento = dict(DepartamentoActividad.choices)
    valores_activos = []
    if q:
        valores_activos.append(('q', 'Búsqueda', q))
    if tipo:
        valores_activos.append(('tipo', 'Tipo', TipoActividad(tipo).label))
    if departamento:
        valores_activos.append(('departamento', 'Departamento', opciones_departamento[departamento]))
    if ciudad:
        valores_activos.append(('ciudad', 'Ciudad', ciudad))
    filtros_activos = []
    for clave, etiqueta, valor in valores_activos:
        parametros = request.GET.copy()
        parametros.pop(clave, None)
        destino = reverse('inicio_publico')
        if parametros:
            destino = f'{destino}?{parametros.urlencode()}'
        filtros_activos.append({'etiqueta': etiqueta, 'valor': valor, 'url': destino})
    iconos_tematica = {
        'ambiental': 'bi-tree',
        'educativa': 'bi-mortarboard',
        'comunitaria': 'bi-people-fill',
        'salud': 'bi-heart-pulse',
        'cultural': 'bi-palette-fill',
        'otra': 'bi-stars',
    }
    tematicas = []
    for valor, etiqueta in TipoActividad.choices:
        parametros = request.GET.copy()
        if parametros.get('tipo') == valor:
            parametros.pop('tipo', None)
        else:
            parametros['tipo'] = valor
        destino = reverse('inicio_publico')
        if parametros:
            destino = f'{destino}?{parametros.urlencode()}'
        tematicas.append({
            'valor': valor,
            'etiqueta': etiqueta,
            'icono': iconos_tematica.get(valor, 'bi-stars'),
            'url': f'{destino}#eventos',
            'activa': tipo == valor,
        })
    parametros_todas = request.GET.copy()
    parametros_todas.pop('tipo', None)
    destino_todas = reverse('inicio_publico')
    if parametros_todas:
        destino_todas = f'{destino_todas}?{parametros_todas.urlencode()}'
    return render(request, 'publico/inicio.html', {
        'actividades': actividades,
        'q': q,
        'tipo': tipo,
        'tipos': TipoActividad,
        'departamento': departamento,
        'departamentos': DepartamentoActividad,
        'ciudad': ciudad,
        'hay_filtros': bool(q or tipo or departamento or ciudad),
        'filtros_activos': filtros_activos,
        'tematicas': tematicas,
        'url_todas_tematica': f'{destino_todas}#eventos',
    })


def home_view(request):
    if request.user.is_authenticated:
        return redirect(destino_segun_rol(request.user))
    return _render_inicio_publico(request)


def inicio_publico_view(request):
    return _render_inicio_publico(request)


def ayuda_view(request):
    return render(request, 'publico/ayuda.html')


@login_required
def voluntario_home_view(request):
    if request.user.es_coordinador():
        return redirect('coordinador:home')
    contexto = resumen_inicio_voluntario(request.user) if resumen_inicio_voluntario else {}
    return render(request, 'voluntario/home.html', contexto)


@login_required
def coordinador_home_view(request):
    if not request.user.es_coordinador():
        return redirect('voluntario:home')
    return render(request, 'coordinador/home.html')


@login_required
def coordinador_modulo_view(request, modulo):
    if not request.user.es_coordinador():
        return redirect('voluntario:home')
    if modulo == 'publicar_actividades':
        return redirect('coordinador:publicar')
    if modulo == 'gestionar_actividades':
        return redirect('coordinador:gestionar')
    if modulo == 'registro_participacion':
        return redirect('coordinador:participacion')
    if modulo in ('reportes_basicos', 'registro_actividades'):
        return redirect('coordinador:reportes')
    contexto = MODULOS_COORDINADOR.get(modulo)
    if not contexto:
        raise Http404
    return render(request, 'coordinador/modulo.html', {'modulo': contexto})


@login_required
def no_disponible_view(request, **kwargs):
    return render(request, 'auth/no_disponible.html')
