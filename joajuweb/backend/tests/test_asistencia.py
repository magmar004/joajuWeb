# El coordinador registra presente/ausente al finalizar la actividad.
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from joajuweb.backend.models import (
    Actividad,
    EstadoActividad,
    EstadoAsistencia,
    EstadoParticipacion,
    Inscripcion,
    Rol,
    Usuario,
)


class AsistenciaActividadTestCase(TestCase):
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
            first_name='Ana',
            last_name='Gómez',
        )
        self.otro_vol.roles.add(rol_vol)

        self.finalizada = Actividad.objects.create(
            nombre='Huerta comunitaria',
            descripcion='Cosecha de invierno.',
            fecha=date.today() - timedelta(days=1),
            cupo=10,
            estado=EstadoActividad.PUBLICADA,
            creado_por=self.coordinador,
        )
        self.proxima = Actividad.objects.create(
            nombre='Jornada futura',
            descripcion='Todavía no ocurrió.',
            fecha=date.today() + timedelta(days=4),
            cupo=8,
            estado=EstadoActividad.PUBLICADA,
            creado_por=self.coordinador,
        )
        self.insc_luis = Inscripcion.objects.create(
            actividad=self.finalizada, voluntario=self.voluntario,
        )
        self.insc_ana = Inscripcion.objects.create(
            actividad=self.finalizada, voluntario=self.otro_vol,
        )
        Inscripcion.objects.create(actividad=self.proxima, voluntario=self.voluntario)

    def test_coordinador_registra_presente_y_ausente(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        response = self.client.post(
            reverse('coordinador:asistencia', args=[self.finalizada.pk]),
            {
                f'asistencia_{self.insc_luis.pk}': EstadoAsistencia.PRESENTE,
                f'asistencia_{self.insc_ana.pk}': EstadoAsistencia.AUSENTE,
            },
        )
        self.assertRedirects(response, reverse('coordinador:gestionar'))
        self.insc_luis.refresh_from_db()
        self.insc_ana.refresh_from_db()
        self.assertEqual(self.insc_luis.asistencia, EstadoAsistencia.PRESENTE)
        self.assertEqual(self.insc_ana.asistencia, EstadoAsistencia.AUSENTE)
        self.assertEqual(self.insc_luis.estado_participacion(), EstadoParticipacion.PARTICIPO)
        self.assertEqual(self.insc_ana.estado_participacion(), EstadoParticipacion.AUSENTE)

        historial = self.client.get(
            reverse('coordinador:historial_voluntario', args=[self.voluntario.pk]),
        )
        self.assertContains(historial, 'Presente')

    def test_no_registra_si_falta_una_marca(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        self.client.post(
            reverse('coordinador:asistencia', args=[self.finalizada.pk]),
            {f'asistencia_{self.insc_luis.pk}': EstadoAsistencia.PRESENTE},
        )
        self.insc_luis.refresh_from_db()
        self.assertEqual(self.insc_luis.asistencia, EstadoAsistencia.PENDIENTE)

    def test_no_registra_antes_de_finalizar(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        response = self.client.get(reverse('coordinador:asistencia', args=[self.proxima.pk]))
        self.assertRedirects(response, reverse('coordinador:gestionar'))
        gestionar = self.client.get(reverse('coordinador:gestionar'))
        self.assertContains(gestionar, 'Asistencia')
        self.assertNotContains(
            gestionar,
            reverse('coordinador:asistencia', args=[self.proxima.pk]),
        )

    def test_voluntario_no_registra_asistencia(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.post(
            reverse('coordinador:asistencia', args=[self.finalizada.pk]),
            {
                f'asistencia_{self.insc_luis.pk}': EstadoAsistencia.PRESENTE,
                f'asistencia_{self.insc_ana.pk}': EstadoAsistencia.AUSENTE,
            },
        )
        self.assertRedirects(response, reverse('voluntario:home'))
        self.insc_luis.refresh_from_db()
        self.assertEqual(self.insc_luis.asistencia, EstadoAsistencia.PENDIENTE)

    def test_otro_coordinador_no_registra(self):
        self.client.login(username='coord2', password='ClaveSegura123!')
        response = self.client.get(reverse('coordinador:asistencia', args=[self.finalizada.pk]))
        self.assertEqual(response.status_code, 404)
