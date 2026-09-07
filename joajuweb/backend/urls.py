from django.contrib.auth import views as auth_views
from django.urls import include, path

from joajuweb.backend.forms import CustomSetPasswordForm
from joajuweb.backend.views import (
    CustomLoginView,
    asistencia_view,
    baja_inscripcion_view,
    cancelar_view,
    coordinador_home_view,
    coordinador_modulo_view,
    detalle_view,
    editar_view,
    gestionar_view,
    historial_ajeno_view,
    historial_propio_view,
    home_view,
    inscribirse_view,
    listado_view,
    no_disponible_view,
    participacion_view,
    publicar_view,
    reportes_view,
    perfil_view,
    registro_view,
    voluntario_home_view,
)


def _vista(vista):
    return vista or no_disponible_view


urlpatterns = [
    path('', home_view, name='home'),
    path('registro/', registro_view, name='registro'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('reset_password/',
         auth_views.PasswordResetView.as_view(
             template_name='auth/password_reset_form.html',
             email_template_name='auth/password_reset_email.html',
             subject_template_name='auth/password_reset_subject.txt',
         ),
         name='password_reset'),
    path('reset_password_sent/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='auth/password_reset_done.html',
         ),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='auth/password_reset_confirm.html',
             form_class=CustomSetPasswordForm,
         ),
         name='password_reset_confirm'),
    path('reset_password_complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='auth/password_reset_complete.html',
         ),
         name='password_reset_complete'),
    path('perfil/', _vista(perfil_view), name='perfil'),
    path('voluntario/', include((
        [
            path('', voluntario_home_view, name='home'),
            path('historial/', _vista(historial_propio_view), name='historial'),
            path('actividades/', _vista(listado_view), name='listado'),
            path('actividades/<int:pk>/', _vista(detalle_view), name='detalle'),
            path('actividades/<int:pk>/inscribirse/', _vista(inscribirse_view), name='inscribirse'),
            path('actividades/<int:pk>/baja/', _vista(baja_inscripcion_view), name='baja'),
        ],
        'voluntario',
    ))),
    path('coordinador/', include((
        [
            path('', coordinador_home_view, name='home'),
            path('reportes/', _vista(reportes_view), name='reportes'),
            path('participacion/', _vista(participacion_view), name='participacion'),
            path('voluntarios/<int:pk>/historial/', _vista(historial_ajeno_view), name='historial_voluntario'),
            path('actividades/', _vista(gestionar_view), name='gestionar'),
            path('actividades/publicar/', _vista(publicar_view), name='publicar'),
            path('actividades/<int:pk>/editar/', _vista(editar_view), name='editar'),
            path('actividades/<int:pk>/asistencia/', _vista(asistencia_view), name='asistencia'),
            path('actividades/<int:pk>/cancelar/', _vista(cancelar_view), name='cancelar'),
            path('<slug:modulo>/', coordinador_modulo_view, name='modulo'),
        ],
        'coordinador',
    ))),
]