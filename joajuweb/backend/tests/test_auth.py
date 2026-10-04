# Pruebas de registro, login y panel según rol
from django.test import TestCase
from django.urls import reverse

from joajuweb.backend.models import Rol, Usuario


class AuthTestCase(TestCase):
    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(
            nombre='Voluntario',
            defaults={'descripcion': 'Rol de prueba'},
        )
        self.user_data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@ejemplo.com',
            'telefono': '0981123456',
            'rol': self.rol.pk,
            'password1': 'ClaveSegura123!',
            'password2': 'ClaveSegura123!',
        }

    def test_registro_usuario(self):
        response = self.client.post(reverse('registro'), self.user_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Usuario.objects.filter(username='testuser').exists())

    def test_login_usuario(self):
        Usuario.objects.create_user(username='testuser', email='test@ejemplo.com', password='ClaveSegura123!')
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'ClaveSegura123!'})
        self.assertEqual(response.status_code, 302)

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'ClaveIncorrecta'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Usuario o contraseña incorrectos')


class CoordinadorDashboardTestCase(TestCase):
    def setUp(self):
        rol_coord, _ = Rol.objects.get_or_create(nombre='Coordinador')
        rol_vol, _ = Rol.objects.get_or_create(nombre='Voluntario')

        self.coordinador = Usuario.objects.create_user(
            username='coord',
            email='coord@ejemplo.com',
            password='ClaveSegura123!',
            first_name='Ana',
            last_name='López',
        )
        self.coordinador.roles.add(rol_coord)

        self.voluntario = Usuario.objects.create_user(
            username='vol',
            email='vol@ejemplo.com',
            password='ClaveSegura123!',
        )
        self.voluntario.roles.add(rol_vol)

    def test_home_requiere_autenticacion(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_dashboard_coordinador_muestra_botones(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        response = self.client.get(reverse('home'), follow=True)
        self.assertContains(response, 'Panel del Coordinador')
        self.assertContains(response, 'Publicar actividades de voluntariado')
        self.assertEqual(response.request['PATH_INFO'], reverse('coordinador:home'))

    def test_dashboard_voluntario_no_muestra_botones_coordinador(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.get(reverse('home'), follow=True)
        self.assertContains(response, '¡Bienvenido a Joaju!')
        self.assertNotContains(response, 'Panel del Coordinador')
        self.assertNotContains(response, 'Publicar actividades de voluntariado')
        self.assertEqual(response.request['PATH_INFO'], reverse('voluntario:home'))

    def test_modulo_coordinador_rechaza_voluntario(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.get(reverse('coordinador:modulo', args=['gestionar_actividades']))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('voluntario:home'))
