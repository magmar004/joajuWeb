# Formulario de carga de actividad. El estado lo define el servicio, no este form.
from django import forms

from joajuweb.backend.models import Actividad, CIUDADES_CENTRAL, JornadaActividad

TAMANO_MAX_IMAGEN_ACTIVIDAD = 5 * 1024 * 1024
FORMATOS_IMAGEN_ACTIVIDAD = {'JPEG', 'PNG', 'WEBP'}


class ActividadForm(forms.ModelForm):
    class Meta:
        model = Actividad
        fields = ('nombre', 'descripcion', 'tipo', 'departamento', 'ciudad', 'ubicacion', 'fecha', 'cupo', 'imagen')
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control custom-input',
                'placeholder': 'Ej. Jornada de reforestación',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control custom-input',
                'rows': 4,
                'placeholder': 'Contá en qué consiste la actividad y qué se espera de los voluntarios',
            }),
            'tipo': forms.Select(attrs={'class': 'form-select custom-input'}),
            'departamento': forms.Select(attrs={'class': 'form-select custom-input'}),
            'ciudad': forms.TextInput(attrs={
                'class': 'form-control custom-input',
                'placeholder': 'Escribí el nombre de la ciudad',
                'autocomplete': 'address-level2',
            }),
            'ubicacion': forms.TextInput(attrs={
                'class': 'form-control custom-input',
                'placeholder': 'Ej. Costanera de Asunción',
            }),
            'fecha': forms.DateInput(
                attrs={'class': 'form-control custom-input', 'type': 'date'},
                format='%Y-%m-%d',
            ),
            'imagen': forms.ClearableFileInput(attrs={
                'class': 'form-control custom-input',
                'accept': '.jpg,.jpeg,.png,.webp',
            }),
            'cupo': forms.NumberInput(attrs={
                'class': 'form-control custom-input',
                'min': 1,
                'placeholder': 'Cantidad máxima de voluntarios',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ciudad_actual = self.instance.ciudad or ''
        ciudades_normalizadas = {ciudad.casefold() for ciudad in CIUDADES_CENTRAL}
        self.ciudad_central_actual = ciudad_actual
        self.ciudad_central_legacy = bool(
            self.instance.pk
            and self.instance.departamento == 'central'
            and ciudad_actual
            and ciudad_actual.casefold() not in ciudades_normalizadas
        )
        self.fields['departamento'].choices = [
            ('', 'Seleccioná un departamento'),
            *[
                (valor, etiqueta)
                for valor, etiqueta in self.fields['departamento'].choices
                if valor
            ],
        ]
        for field in self.fields.values():
            field.required = True
        self.fields['imagen'].required = False
        self.fields['fecha'].input_formats = ['%Y-%m-%d']

    def clean(self):
        datos = super().clean()
        departamento = datos.get('departamento')
        ciudad = (datos.get('ciudad') or '').strip()
        if departamento == 'asuncion':
            datos['ciudad'] = 'Asunción'
        elif departamento == 'central' and ciudad:
            ciudades_por_nombre = {nombre.casefold(): nombre for nombre in CIUDADES_CENTRAL}
            ciudad_canonica = ciudades_por_nombre.get(ciudad.casefold())
            ciudad_anterior = (self.instance.ciudad or '').strip()
            if ciudad_canonica:
                datos['ciudad'] = ciudad_canonica
            elif not (
                self.instance.pk
                and self.instance.departamento == 'central'
                and ciudad.casefold() == ciudad_anterior.casefold()
            ):
                self.add_error('ciudad', 'Para el departamento Central, elegí una ciudad de la lista.')
        return datos

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if not imagen:
            return imagen
        if imagen.size > TAMANO_MAX_IMAGEN_ACTIVIDAD:
            raise forms.ValidationError('La fotografía no puede superar los 5 MB.')
        formato = getattr(getattr(imagen, 'image', None), 'format', None)
        if formato and formato.upper() not in FORMATOS_IMAGEN_ACTIVIDAD:
            raise forms.ValidationError('Usá una imagen en formato JPG, PNG o WEBP.')
        return imagen

    def clean_nombre(self):
        nombre = (self.cleaned_data.get('nombre') or '').strip()
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio.")
        return nombre

    def clean_descripcion(self):
        descripcion = (self.cleaned_data.get('descripcion') or '').strip()
        if not descripcion:
            raise forms.ValidationError("La descripción es obligatoria.")
        return descripcion

    def clean_ubicacion(self):
        ubicacion = (self.cleaned_data.get('ubicacion') or '').strip()
        if not ubicacion:
            raise forms.ValidationError("La ubicación es obligatoria.")
        return ubicacion

    def clean_cupo(self):
        cupo = self.cleaned_data.get('cupo')
        if cupo is None:
            raise forms.ValidationError("El cupo es obligatorio.")
        if cupo < 1:
            raise forms.ValidationError("El cupo debe ser de al menos 1 voluntario.")
        if self.instance.pk:
            inscriptos = self.instance.cantidad_inscriptos()
            if cupo < inscriptos:
                raise forms.ValidationError(
                    f"Ya hay {inscriptos} voluntarios inscriptos. El cupo no puede ser menor."
                )
        return cupo


class JornadaForm(forms.ModelForm):
    class Meta:
        model = JornadaActividad
        fields = ('fecha', 'hora_inicio', 'hora_fin')
        widgets = {
            'fecha': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control custom-input'}),
            'hora_inicio': forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control custom-input'}),
            'hora_fin': forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control custom-input'}),
        }

    def clean(self):
        datos = super().clean()
        # Una jornada histórica sin horario puede conservarse sin cambios.
        historica = self.instance.pk and self.instance.hora_inicio is None and self.instance.hora_fin is None
        if not historica or datos.get('hora_inicio') or datos.get('hora_fin'):
            for campo in ('hora_inicio', 'hora_fin'):
                if not datos.get(campo):
                    self.add_error(campo, 'Completá el horario de Asunción.')
        return datos


class BaseJornadasFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        fechas = [form.cleaned_data['fecha'] for form in self.forms if form.cleaned_data and not form.cleaned_data.get('DELETE')]
        if len(fechas) != len(set(fechas)):
            raise forms.ValidationError('Solo puede haber una jornada por fecha de Asunción.')
        if fechas and self.instance.fecha and min(fechas) != self.instance.fecha:
            raise forms.ValidationError('La fecha de la actividad debe coincidir con su primera jornada.')


JornadasFormSet = forms.inlineformset_factory(
    Actividad, JornadaActividad, form=JornadaForm, formset=BaseJornadasFormSet,
    extra=0, min_num=1, validate_min=True, can_delete=True,
    max_num=366, validate_max=True,
)
