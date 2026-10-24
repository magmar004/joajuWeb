from io import BytesIO
from datetime import date, time
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from joajuweb.backend.forms.actividades import ActividadForm
from joajuweb.backend.models import Actividad, JornadaActividad, Rol, Usuario


class ActividadImagenFormTests(SimpleTestCase):
    def imagen_subida(self, formato):
        buffer = BytesIO()
        Image.new('RGB', (2, 2), color='purple').save(buffer, format=formato)
        extension = {'JPEG': 'jpg', 'PNG': 'png', 'GIF': 'gif'}[formato]
        return SimpleUploadedFile(
            f'actividad.{extension}', buffer.getvalue(), content_type=f'image/{extension}',
        )

    def formulario(self, imagen):
        datos = {
            'nombre': 'Actividad de prueba',
            'descripcion': 'Descripción de prueba',
            'tipo': 'comunitaria',
            'departamento': 'central',
            'ciudad': 'San Lorenzo',
            'ubicacion': 'Centro',
            'fecha': '2026-10-25',
            'cupo': '12',
        }
        return ActividadForm(datos, {'imagen': imagen})

    def test_acepta_imagen_png_valida(self):
        form = self.formulario(self.imagen_subida('PNG'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_rechaza_formatos_no_permitidos(self):
        form = self.formulario(self.imagen_subida('GIF'))
        self.assertFalse(form.is_valid())
        self.assertIn('imagen', form.errors)
        self.assertIn('JPG, PNG o WEBP', str(form.errors['imagen']))

    def test_rechaza_archivo_mayor_a_cinco_megabytes(self):
        imagen = self.imagen_subida('PNG')
        imagen.file.seek(0, 2)
        imagen.file.write(b'0' * (5 * 1024 * 1024))
        imagen.size = imagen.file.tell()
        imagen.file.seek(0)

        form = self.formulario(imagen)
        self.assertFalse(form.is_valid())
        self.assertIn('5 MB', str(form.errors['imagen']))


class ActividadImagenUploadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        coordinador_role = Rol.objects.get(nombre='Coordinador')
        cls.coordinador = Usuario.objects.create_user('coord-fotos')
        cls.coordinador.roles.add(coordinador_role)

    def setUp(self):
        self.media_temp = TemporaryDirectory()
        self.addCleanup(self.media_temp.cleanup)
        media_override = override_settings(MEDIA_ROOT=self.media_temp.name)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.client.force_login(self.coordinador)

    def imagen_subida(self):
        buffer = BytesIO()
        Image.new('RGB', (2, 2), color='orange').save(buffer, format='PNG')
        return SimpleUploadedFile('actividad.png', buffer.getvalue(), content_type='image/png')

    def datos_base(self, actividad=None):
        fecha = date(2026, 11, 1)
        datos = {
            'nombre': actividad.nombre if actividad else 'Actividad con fotografía',
            'descripcion': 'Descripción para probar la carga.',
            'tipo': 'comunitaria',
            'departamento': 'central',
            'ciudad': 'San Lorenzo',
            'ubicacion': 'Centro',
            'fecha': fecha.isoformat(),
            'cupo': '8',
            'jornadas-TOTAL_FORMS': '1',
            'jornadas-INITIAL_FORMS': '0',
            'jornadas-MIN_NUM_FORMS': '1',
            'jornadas-MAX_NUM_FORMS': '366',
            'jornadas-0-fecha': fecha.isoformat(),
            'jornadas-0-hora_inicio': '09:00',
            'jornadas-0-hora_fin': '12:00',
        }
        if actividad:
            jornada = actividad.jornadas.get()
            datos['jornadas-INITIAL_FORMS'] = '1'
            datos['jornadas-0-id'] = str(jornada.pk)
        return datos

    def test_coordinador_crea_actividad_con_imagen(self):
        datos = self.datos_base()
        datos['imagen'] = self.imagen_subida()
        response = self.client.post(reverse('coordinador:publicar'), datos)

        self.assertEqual(response.status_code, 302)
        actividad = Actividad.objects.get(nombre='Actividad con fotografía')
        self.assertTrue(actividad.imagen.name.startswith('actividades/'))
        self.assertTrue(actividad.imagen.storage.exists(actividad.imagen.name))

    def test_coordinador_reemplaza_imagen_al_editar_actividad(self):
        actividad = Actividad.objects.create(
            nombre='Actividad editable',
            descripcion='Descripción original',
            fecha=date(2026, 11, 1),
            cupo=8,
            creado_por=self.coordinador,
        )
        JornadaActividad.objects.create(
            actividad=actividad,
            fecha=actividad.fecha,
            hora_inicio=time(9),
            hora_fin=time(12),
        )
        datos = self.datos_base(actividad)
        datos['imagen'] = self.imagen_subida()
        response = self.client.post(reverse('coordinador:editar', args=[actividad.pk]), datos)

        self.assertEqual(response.status_code, 302)
        actividad.refresh_from_db()
        self.assertTrue(actividad.imagen.name.startswith('actividades/'))
        self.assertTrue(actividad.imagen.storage.exists(actividad.imagen.name))
