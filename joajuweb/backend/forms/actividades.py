# Formulario de carga de actividad. El estado lo define el servicio, no este form.
from django import forms

from joajuweb.backend.models import Actividad


class ActividadForm(forms.ModelForm):
    class Meta:
        model = Actividad
        fields = ('nombre', 'descripcion', 'tipo', 'area', 'ubicacion', 'fecha', 'cupo')
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
            'area': forms.Select(attrs={'class': 'form-select custom-input'}),
            'ubicacion': forms.TextInput(attrs={
                'class': 'form-control custom-input',
                'placeholder': 'Ej. Costanera de Asunción',
            }),
            'fecha': forms.DateInput(
                attrs={'class': 'form-control custom-input', 'type': 'date'},
                format='%Y-%m-%d',
            ),
            'cupo': forms.NumberInput(attrs={
                'class': 'form-control custom-input',
                'min': 1,
                'placeholder': 'Cantidad máxima de voluntarios',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True
        self.fields['fecha'].input_formats = ['%Y-%m-%d']

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
