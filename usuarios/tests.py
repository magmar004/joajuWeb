"""
Pruebas unitarias automatizadas para los flujos de registro, inicio de sesión y seguridad.
"""
from django.test import TestCase
from django.urls import reverse
from .models import Usuario, Rol


class AuthTestCase(TestCase):
    """
    Suite de pruebas para verificar el comportamiento de los endpoints de autenticación.
    """
    def setUp(self):
        """Configuración del entorno de prueba previa a cada ejecución de test."""
        self.rol = Rol.objects.create(nombre='Voluntario', descripcion='Rol de prueba')
        self.user_data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@ejemplo.com',
            'telefono': '0981123456',
            'rol': self.rol.pk,
            'password1': 'ClaveSegura123!',
            'password2': 'ClaveSegura123!'
        }

    def test_registro_usuario(self):
        """Verifica el envío exitoso del formulario de registro y la redirección correspondiente."""
        response = self.client.post(reverse('registro'), self.user_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Usuario.objects.filter(username='testuser').exists())

    def test_login_usuario(self):
        """Prueba la autenticación correcta con credenciales válidas."""
        Usuario.objects.create_user(username='testuser', email='test@ejemplo.com', password='ClaveSegura123!')
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'ClaveSegura123!'})
        self.assertEqual(response.status_code, 302)

    def test_login_invalid_credentials(self):
        """Comprueba que el sistema rechace el acceso ante contraseñas incorrectas."""
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'ClaveIncorrecta'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Usuario o contraseña incorrectos')