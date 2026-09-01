from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario, Rol

class RegistroForm(UserCreationForm):
    nombre = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}))
    apellido = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'}))
    telefono = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'}))
    rol = forms.ModelChoiceField(queryset=Rol.objects.all(), required=True, empty_label="Selecciona tu rol", widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = Usuario
        fields = ['username', 'nombre', 'apellido', 'email', 'telefono', 'rol']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Nombre de usuario'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Contraseña'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirmar contraseña'})