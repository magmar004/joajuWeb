# Formularios de registro, login, perfil y restablecimiento de contraseña.
import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm, UserCreationForm
from django.core.validators import FileExtensionValidator

from joajuweb.backend.models import Rol, TipoInteresActividad, Usuario

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
    intereses_actividad = forms.ModelMultipleChoiceField(
        queryset=TipoInteresActividad.objects.none(),
        label='Temáticas de interés',
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    recibir_avisos_actividades = forms.BooleanField(
        label='Quiero recibir avisos por correo sobre nuevas actividades de mis intereses',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'telefono', 'intereses_actividad', 'recibir_avisos_actividades')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['intereses_actividad'].queryset = TipoInteresActividad.objects.order_by('orden', 'nombre')
        self.voluntario_role_value = str(
            Rol.objects.filter(nombre__iexact='Voluntario').values_list('pk', flat=True).first() or ''
        )
        for field_name, field in self.fields.items():
            if field_name == 'rol':
                field.widget.attrs.update({'class': 'form-select custom-input'})
            elif field_name == 'intereses_actividad':
                continue
            elif field_name == 'recibir_avisos_actividades':
                continue
            else:
                field.widget.attrs.update({'class': 'form-control custom-input'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    def clean(self):
        datos = super().clean()
        rol = datos.get('rol')
        if (
            rol
            and rol.nombre.casefold() == 'voluntario'
            and datos.get('recibir_avisos_actividades')
            and not datos.get('intereses_actividad')
        ):
            self.add_error('intereses_actividad', 'Elegí al menos una temática para recibir avisos.')
        return datos

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.telefono = self.cleaned_data['telefono']
        es_voluntario = self.cleaned_data['rol'].nombre.casefold() == 'voluntario'
        user.recibir_avisos_actividades = (
            es_voluntario and self.cleaned_data.get('recibir_avisos_actividades', False)
        )
        if commit:
            user.save()
            user.roles.add(self.cleaned_data['rol'])
            if es_voluntario:
                user.intereses_actividad.set(self.cleaned_data.get('intereses_actividad', ()))
            else:
                user.intereses_actividad.clear()
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
    
    # Campos agregados para la HU13 - Perfil Ampliado
    biografia = forms.CharField(
        label="Sobre mí / Biografía",
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Contanos un poco sobre vos...'})
    )
    habilidades = forms.CharField(
        label="Habilidades y competencias",
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Ej: Liderazgo, Primeros auxilios, Trabajo en equipo'})
    )
    intereses_actividad = forms.ModelMultipleChoiceField(
        queryset=TipoInteresActividad.objects.none(),
        label="Áreas de interés",
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    recibir_avisos_actividades = forms.BooleanField(
        label='Recibir avisos por correo sobre nuevas actividades de mis intereses',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    foto = forms.ImageField(
        label="Foto de perfil",
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
        widget=forms.FileInput(attrs={'class': 'form-control custom-input', 'accept': 'image/*'}),
    )
    quitar_foto = forms.BooleanField(label="Quitar foto actual", required=False)

    class Meta:
        model = Usuario
        fields = ('first_name', 'last_name', 'email', 'telefono', 'biografia', 'habilidades', 'intereses_actividad', 'recibir_avisos_actividades', 'foto')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['intereses_actividad'].queryset = TipoInteresActividad.objects.order_by('orden', 'nombre')
        for nombre, field in self.fields.items():
            if nombre in ('foto', 'intereses_actividad', 'recibir_avisos_actividades'):
                continue
            if nombre == 'quitar_foto':
                field.widget.attrs.update({'class': 'form-check-input'})
                continue
            field.widget.attrs.update({'class': 'form-control custom-input'})

    def clean(self):
        datos = super().clean()
        if datos.get('recibir_avisos_actividades') and not datos.get('intereses_actividad'):
            self.add_error('intereses_actividad', 'Elegí al menos una temática para recibir avisos.')
        return datos

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
            self.save_m2m()
        return usuario
