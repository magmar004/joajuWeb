# Login, registro, panel y stubs de módulos del coordinador
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from joajuweb.backend.forms import CustomLoginForm, RegistroForm

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


@login_required
def home_view(request):
    return redirect(destino_segun_rol(request.user))


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