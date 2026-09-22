# Consulta y edición del perfil propio.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from joajuweb.backend.forms import PerfilForm
from joajuweb.backend.servicios import PerfilError, actualizar_perfil


@login_required
def perfil_view(request):
    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES, instance=request.user)
        try:
            actualizar_perfil(form)
        except PerfilError:
            messages.warning(request, 'Revisá los campos marcados.')
        else:
            messages.success(request, 'Tus datos de perfil se actualizaron.')
            return redirect('perfil')
    else:
        form = PerfilForm(instance=request.user)

    return render(request, 'perfil.html', {'form': form})
