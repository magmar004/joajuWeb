# El usuario consulta y actualiza su perfil.
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from joajuweb.backend.models import Rol, Usuario


def _imagen_png(nombre='foto.png'):
    buffer = BytesIO()
    Image.new('RGB', (8, 8), color='purple').save(buffer, format='PNG')
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PerfilUsuarioTestCase(TestCase):
    def setUp(self):
        rol_vol, _ = Rol.objects.get_or_create(nombre='Voluntario')
        rol_coord, _ = Rol.objects.get_or_create(nombre='Coordinador')
        self.voluntario = Usuario.objects.create_user(
            username='vol',
            email='vol@ejemplo.com',
            password='ClaveSegura123!',
            first_name='Luis',
            last_name='Pérez',
            telefono='0981123456',
        )
        self.voluntario.roles.add(rol_vol)
        self.coordinador = Usuario.objects.create_user(
            username='coord',
            email='coord@ejemplo.com',
            password='ClaveSegura123!',
            first_name='Ana',
            last_name='López',
        )
        self.coordinador.roles.add(rol_coord)

    def test_perfil_requiere_login(self):
        response = self.client.get(reverse('perfil'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_voluntario_ve_su_perfil(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.get(reverse('perfil'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mi perfil')
        self.assertContains(response, 'Luis')
        self.assertContains(response, 'vol@ejemplo.com')

    def test_coordinador_ve_su_perfil(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        response = self.client.get(reverse('perfil'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana')

    def test_actualiza_nombre_y_contacto(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.post(reverse('perfil'), {
            'first_name': 'Luis Miguel',
            'last_name': 'Pérez',
            'email': 'nuevo@ejemplo.com',
            'telefono': '0991111222',
        })
        self.assertRedirects(response, reverse('perfil'))
        self.voluntario.refresh_from_db()
        self.assertEqual(self.voluntario.first_name, 'Luis Miguel')
        self.assertEqual(self.voluntario.email, 'nuevo@ejemplo.com')
        self.assertEqual(self.voluntario.telefono, '0991111222')

    def test_rechaza_nombre_vacio(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.post(reverse('perfil'), {
            'first_name': '   ',
            'last_name': 'Pérez',
            'email': 'vol@ejemplo.com',
            'telefono': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Atención')
        self.voluntario.refresh_from_db()
        self.assertEqual(self.voluntario.first_name, 'Luis')

    def test_rechaza_email_ajeno(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.post(reverse('perfil'), {
            'first_name': 'Luis',
            'last_name': 'Pérez',
            'email': 'coord@ejemplo.com',
            'telefono': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ya está registrado')
        self.voluntario.refresh_from_db()
        self.assertEqual(self.voluntario.email, 'vol@ejemplo.com')

    def test_rechaza_telefono_invalido(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.post(reverse('perfil'), {
            'first_name': 'Luis',
            'last_name': 'Pérez',
            'email': 'vol@ejemplo.com',
            'telefono': 'abc',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'teléfono válido')

    def test_guarda_foto(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.post(reverse('perfil'), {
            'first_name': 'Luis',
            'last_name': 'Pérez',
            'email': 'vol@ejemplo.com',
            'telefono': '0981123456',
            'foto': _imagen_png(),
        })
        self.assertRedirects(response, reverse('perfil'))
        self.voluntario.refresh_from_db()
        self.assertTrue(self.voluntario.foto)
