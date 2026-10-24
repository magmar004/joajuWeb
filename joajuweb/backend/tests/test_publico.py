from datetime import date, datetime, time, timedelta, timezone as tz
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from joajuweb.backend.models import Actividad, JornadaActividad, Rol, Usuario


AHORA = datetime(2026, 10, 21, 15, tzinfo=tz.utc)


class PaginasPublicasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        rol = Rol.objects.get(nombre='Coordinador')
        cls.coordinador = Usuario.objects.create_user('coord-publico')
        cls.coordinador.roles.add(rol)
        cls.voluntario = Usuario.objects.create_user('vol-publico')

        cls.actividad = Actividad.objects.create(
            nombre='Jornada de limpieza',
            descripcion='Cuidemos juntos los espacios de la comunidad.',
            fecha=date(2026, 10, 22),
            cupo=10,
            ubicacion='Plaza central',
            estado='publicada',
            creado_por=cls.coordinador,
        )
        JornadaActividad.objects.create(
            actividad=cls.actividad,
            fecha=date(2026, 10, 22),
            hora_inicio=time(9),
            hora_fin=time(12),
        )
        cls.borrador = Actividad.objects.create(
            nombre='Actividad privada',
            descripcion='No debe aparecer en el sitio público.',
            fecha=date(2026, 10, 23),
            cupo=5,
            estado='borrador',
            creado_por=cls.coordinador,
        )

    def setUp(self):
        self.reloj = patch('django.utils.timezone.now', return_value=AHORA)
        self.reloj.start()
        self.addCleanup(self.reloj.stop)

    def test_inicio_publico_muestra_actividades_vigentes_y_busca_por_nombre(self):
        response = self.client.get(reverse('home'), {'q': 'limpieza'})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'publico/inicio.html')
        self.assertContains(response, 'Jornada de limpieza')
        self.assertNotContains(response, 'Actividad privada')
        self.assertContains(response, 'Plaza central')

        response = self.client.get(reverse('home'), {'q': 'espacios'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Jornada de limpieza')

    def test_detalle_publico_muestra_actividad_publicada_y_oculta_borradores(self):
        response = self.client.get(reverse('actividad_publica_detalle', args=[self.actividad.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'publico/detalle_actividad.html')
        self.assertContains(response, 'Cuidemos juntos los espacios')
        self.assertContains(response, reverse('login'))
        self.assertEqual(
            self.client.get(reverse('actividad_publica_detalle', args=[self.borrador.pk])).status_code,
            404,
        )

    def test_inicio_redirige_a_panel_segun_rol_para_usuarios_autenticados(self):
        self.client.force_login(self.coordinador)
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, reverse('coordinador:home'))
        publico = self.client.get(reverse('inicio_publico'))
        self.assertEqual(publico.status_code, 200)
        self.assertContains(publico, f'href="{reverse("coordinador:home")}"')
        self.assertEqual(int(self.client.session['_auth_user_id']), self.coordinador.pk)

        self.client.force_login(self.voluntario)
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, reverse('voluntario:home'))
        publico = self.client.get(reverse('inicio_publico'))
        self.assertEqual(publico.status_code, 200)
        self.assertContains(publico, f'href="{reverse("voluntario:home")}"')

        panel = self.client.get(reverse('voluntario:home'))
        self.assertContains(panel, f'href="{reverse("inicio_publico")}">Inicio</a>')

        self.client.force_login(self.coordinador)
        panel = self.client.get(reverse('coordinador:home'))
        self.assertContains(panel, f'href="{reverse("inicio_publico")}">Inicio</a>')

    def test_visitante_no_puede_inscribirse_sin_autenticarse(self):
        response = self.client.post(reverse('voluntario:inscribirse', args=[self.actividad.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
        self.assertFalse(self.actividad.inscripciones.exists())
