# Formularios de registro, login, perfil y restablecimiento de contraseña.
import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm, UserCreationForm
from django.core.validators import FileExtensionValidator

from joajuweb.backend.models import Rol, Usuario

TAMANO_MAX_FOTO = 2 * 1024 * 1024
TELEFONO_VALIDO = re.compile(r'^[0-9+\-\s()]{6,20}$')


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'rol':
                field.widget.attrs.update({'class': 'form-select custom-input'})
            else:
                field.widget.attrs.update({'class': 'form-control custom-input'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.telefono = self.cleaned_data['telefono']
        if commit:
            user.save()
            user.roles.add(self.cleaned_data['rol'])
        return user


class CustomLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control custom-input'})


class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].label = "Nueva contraseña"
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control custom-input',
            'placeholder': '••••••••',
        })
        self.fields['new_password2'].label = "Confirmar nueva contraseña"
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control custom-input',
            'placeholder': '••••••••',
        })


class PerfilForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre", max_length=150, required=True)
    last_name = forms.CharField(label="Apellido", max_length=150, required=True)
    email = forms.EmailField(label="Correo electrónico", required=True)
    telefono = forms.CharField(label="Teléfono", max_length=20, required=False)
    foto = forms.ImageField(
        label="Foto de perfil",
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
        widget=forms.FileInput(attrs={'class': 'form-control custom-input', 'accept': 'image/*'}),
    )
    quitar_foto = forms.BooleanField(label="Quitar foto actual", required=False)

    class Meta:
        model = Usuario
        fields = ('first_name', 'last_name', 'email', 'telefono', 'foto')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nombre, field in self.fields.items():
            if nombre == 'foto':
                continue
            if nombre == 'quitar_foto':
                field.widget.attrs.update({'class': 'form-check-input'})
                continue
            field.widget.attrs.update({'class': 'form-control custom-input'})

    def clean_first_name(self):
        nombre = (self.cleaned_data.get('first_name') or '').strip()
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio.")
        return nombre

    def clean_last_name(self):
        apellido = (self.cleaned_data.get('last_name') or '').strip()
        if not apellido:
            raise forms.ValidationError("El apellido es obligatorio.")
        return apellido

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise forms.ValidationError("El correo electrónico es obligatorio.")
        existe = Usuario.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if existe.exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    def clean_telefono(self):
        telefono = (self.cleaned_data.get('telefono') or '').strip()
        if not telefono:
            return ''
        if not TELEFONO_VALIDO.match(telefono):
            raise forms.ValidationError("Ingresá un teléfono válido (solo números, espacios o +).")
        return telefono

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if foto and getattr(foto, 'size', 0) > TAMANO_MAX_FOTO:
            raise forms.ValidationError("La foto no puede superar los 2 MB.")
        return foto

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get('quitar_foto') and usuario.foto:
            usuario.foto.delete(save=False)
            usuario.foto = None
        if commit:
            usuario.save()
        return usuario
