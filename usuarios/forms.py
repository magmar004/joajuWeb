"""
Formularios de autenticación y registro de usuarios estilizados para Bootstrap 5.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, SetPasswordForm
from .models import Usuario, Rol


class RegistroForm(UserCreationForm):
    """
    Formulario personalizado para la creación de nuevas cuentas de usuario.
    Incluye asignación de rol, campos de perfil y validación estricta de correo único.
    """
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

    def __init__(self, *args, **kwargs):
        """Aplica clases de estilo Bootstrap 5 a todos los widgets del formulario."""
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'rol':
                field.widget.attrs.update({'class': 'form-select custom-input'})
            else:
                field.widget.attrs.update({'class': 'form-control custom-input'})

    def clean_email(self):
        """Valida que el correo electrónico ingresado no se encuentre registrado previamente en la BD."""
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    def save(self, commit=True):
        """Guarda la instancia del usuario y vincula el rol seleccionado en la relación N:M."""
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


class CustomLoginForm(AuthenticationForm):
    """
    Formulario de autenticación que aplica estilos Bootstrap a los campos de login.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control custom-input'})


class CustomSetPasswordForm(SetPasswordForm):
    """
    Formulario para el cambio/restablecimiento de contraseña con campos traducidos al español y clases CSS.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].label = "Nueva contraseña"
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control custom-input',
            'placeholder': '••••••••'
        })
        self.fields['new_password2'].label = "Confirmar nueva contraseña"
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control custom-input',
            'placeholder': '••••••••'
        })