from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario, Rol

class RegistroForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", max_length=150, required=True)
    last_name = forms.CharField(label="Apellido", max_length=150, required=True)
    email = forms.EmailField(label="Correo Electrónico", required=True)
    telefono = forms.CharField(label="Teléfono", max_length=20, required=False)
    rol = forms.ModelChoiceField(
        queryset=Rol.objects.all(),
        label="Registrarse como",
        empty_label="Selecciona un rol"
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'telefono')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.telefono = self.cleaned_data['telefono']
        if commit:
            user.save()
            rol_seleccionado = self.cleaned_data['rol']
            user.roles.add(rol_seleccionado)
        return user 