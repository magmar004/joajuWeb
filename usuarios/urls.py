from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import registro_view, CustomLoginView, home_view

urlpatterns = [
    path('', home_view, name='home'),
    path('registro/', registro_view, name='registro'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]