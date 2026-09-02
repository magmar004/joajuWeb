"""
Enrutamiento de URLs para el módulo de gestión de usuarios y autenticación.
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import registro_view, CustomLoginView, home_view
from .forms import CustomSetPasswordForm

urlpatterns = [
    # Vista Principal / Dashboard
    path('', home_view, name='home'),

    # Autenticación Básica
    path('registro/', registro_view, name='registro'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Flujo de Recuperación de Contraseña (basado en Tokens de un solo uso)
    path('reset_password/', 
         auth_views.PasswordResetView.as_view(
             template_name='usuarios/password_reset_form.html',
             email_template_name='usuarios/password_reset_email.html',
             subject_template_name='usuarios/password_reset_subject.txt'
         ), 
         name='password_reset'),

    path('reset_password_sent/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='usuarios/password_reset_done.html'
         ), 
         name='password_reset_done'),

    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='usuarios/password_reset_confirm.html',
             form_class=CustomSetPasswordForm
         ), 
         name='password_reset_confirm'),

    path('reset_password_complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='usuarios/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]