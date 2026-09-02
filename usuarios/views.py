"""
Módulo de vistas / controladores para los flujos de login, registro y panel de inicio.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from .forms import RegistroForm, CustomLoginForm


def registro_view(request):
    """
    Procesa la solicitud de registro. Si el formulario es válido, persiste el usuario
     e inicia sesión de forma automática antes de redirigir al Dashboard (home).
    """
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegistroForm()
    return render(request, 'usuarios/registro.html', {'form': form})


class CustomLoginView(LoginView):
    """
    Vista basada en clases (CBV) para el inicio de sesión, asociando
    el formulario personalizado CustomLoginForm y la plantilla correspondiente.
    """
    template_name = 'usuarios/login.html'
    authentication_form = CustomLoginForm


def home_view(request):
    """
    Renderiza la pantalla principal (Dashboard) para los usuarios autenticados.
    """
    return render(request, 'usuarios/home.html')