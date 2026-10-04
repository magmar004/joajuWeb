# El voluntario ve su trayectoria; solo él y su coordinador acceden.
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from joajuweb.backend.models import (
    Actividad,
    EstadoActividad,
    EstadoParticipacion,
    Inscripcion,
    Rol,
    Usuario,
)


class HistorialParticipacionTestCase(TestCase):
    def setUp(self):
        rol_coord, _ = Rol.objects.get_or_create(nombre='Coordinador')
        rol_vol, _ = Rol.objects.get_or_create(nombre='Voluntario')

        self.coordinador = Usuario.objects.create_user(
            username='coord',
            email='coord@ejemplo.com',
            password='ClaveSegura123!',
        )
        self.coordinador.roles.add(rol_coord)

        self.otro_coord = Usuario.objects.create_user(
            username='coord2',
            email='coord2@ejemplo.com',
            password='ClaveSegura123!',
        )
        self.otro_coord.roles.add(rol_coord)

        self.voluntario = Usuario.objects.create_user(
            username='vol',
            email='vol@ejemplo.com',
            password='ClaveSegura123!',
            first_name='Luis',
            last_name='Pérez',
        )
        self.voluntario.roles.add(rol_vol)

        self.otro_vol = Usuario.objects.create_user(
            username='vol2',
            email='vol2@ejemplo.com',
            password='ClaveSegura123!',
        )
        self.otro_vol.roles.add(rol_vol)

        self.pasada = Actividad.objects.create(
            nombre='Huerta comunitaria',
            descripcion='Cosecha de invierno.',
            fecha=date.today() - timedelta(days=5),
            cupo=10,
            estado=EstadoActividad.PUBLICADA,
            creado_por=self.coordinador,
        )
        self.proxima = Actividad.objects.create(
            nombre='Jornada de limpieza',
            descripcion='Limpieza de la costanera.',
            fecha=date.today() + timedelta(days=7),
            cupo=12,
            estado=EstadoActividad.PUBLICADA,
            creado_por=self.coordinador,
        )
        self.cancelada = Actividad.objects.create(
            nombre='Taller cancelado',
            descripcion='Se suspendió.',
            fecha=date.today() - timedelta(days=2),
            cupo=8,
            estado=EstadoActividad.CANCELADA,
            creado_por=self.coordinador,
        )
        Inscripcion.objects.create(actividad=self.pasada, voluntario=self.voluntario)
        Inscripcion.objects.create(actividad=self.proxima, voluntario=self.voluntario)
        Inscripcion.objects.create(actividad=self.cancelada, voluntario=self.voluntario)

    def test_voluntario_ve_estados_de_participacion(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.get(reverse('voluntario:historial'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Huerta comunitaria')
        self.assertContains(response, 'Pendiente')
        self.assertContains(response, 'Jornada de limpieza')
        self.assertContains(response, 'Inscripto')
        self.assertContains(response, 'Taller cancelado')
        self.assertContains(response, 'Cancelada')

    def test_inscripcion_pasada_sin_asistencia_es_pendiente(self):
        inscripcion = Inscripcion.objects.get(actividad=self.pasada, voluntario=self.voluntario)
        self.assertEqual(inscripcion.estado_participacion(), EstadoParticipacion.PENDIENTE)

    def test_otro_voluntario_no_ve_el_historial(self):
        self.client.login(username='vol2', password='ClaveSegura123!')
        response = self.client.get(
            reverse('coordinador:historial_voluntario', args=[self.voluntario.pk]),
        )
        self.assertRedirects(response, reverse('voluntario:home'))

    def test_coordinador_propio_ve_el_historial(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        response = self.client.get(
            reverse('coordinador:historial_voluntario', args=[self.voluntario.pk]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Luis Pérez')
        self.assertContains(response, 'Huerta comunitaria')

    def test_otro_coordinador_no_ve_el_historial(self):
        self.client.login(username='coord2', password='ClaveSegura123!')
        response = self.client.get(
            reverse('coordinador:historial_voluntario', args=[self.voluntario.pk]),
        )
        self.assertRedirects(response, reverse('coordinador:participacion'))

    def test_coordinador_lista_solo_sus_voluntarios(self):
        self.client.login(username='coord', password='ClaveSegura123!') 
        response = self.client.get(reverse('coordinador:participacion'))
        self.assertContains(response, 'Luis Pérez')
        self.assertContains(response, 'vol@ejemplo.com')

        self.client.logout()
        self.client.login(username='coord2', password='ClaveSegura123!')
        vacio = self.client.get(reverse('coordinador:participacion'))
        self.assertContains(vacio, 'Todavía no hay voluntarios inscriptos')

    def test_voluntario_no_entra_a_participacion(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.get(reverse('coordinador:participacion'))
        self.assertRedirects(response, reverse('voluntario:home'))
