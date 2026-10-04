# Edición, cancelación y aviso a voluntarios inscriptos.
from datetime import date, timedelta

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from joajuweb.backend.models import Actividad, EstadoActividad, Inscripcion, Rol, Usuario


@override_settings(MAILERS={
    'default': {'BACKEND': 'django.core.mail.backends.locmem.EmailBackend'},
})
class GestionActividadTestCase(TestCase):
    def setUp(self):
        rol_coord, _ = Rol.objects.get_or_create(nombre='Coordinador')
        rol_vol, _ = Rol.objects.get_or_create(nombre='Voluntario')

        self.coordinador = Usuario.objects.create_user(
            username='coord',
            email='coord@ejemplo.com',
            password='ClaveSegura123!',
        )
        self.coordinador.roles.add(rol_coord)

        self.voluntario = Usuario.objects.create_user(
            username='vol',
            email='vol@ejemplo.com',
            password='ClaveSegura123!',
        )
        self.voluntario.roles.add(rol_vol)

        self.borrador = Actividad.objects.create(
            nombre='Taller en borrador',
            descripcion='Todavía no se publica.',
            fecha=date.today() + timedelta(days=10),
            cupo=12,
            estado=EstadoActividad.BORRADOR,
            creado_por=self.coordinador,
        )
        self.publicada = Actividad.objects.create(
            nombre='Jornada publicada',
            descripcion='Actividad abierta.',
            fecha=date.today() + timedelta(days=8),
            cupo=20,
            estado=EstadoActividad.PUBLICADA,
            creado_por=self.coordinador,
        )

    def test_gestionar_muestra_borrador_y_publicada(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        response = self.client.get(reverse('coordinador:gestionar'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Taller en borrador')
        self.assertContains(response, 'Jornada publicada')
        self.assertContains(response, 'Borrador')
        self.assertContains(response, 'Publicada')

    def test_voluntario_no_gestiona(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.get(reverse('coordinador:gestionar'))
        self.assertEqual(response.url, reverse('voluntario:home'))

    def test_editar_fecha_y_cupo(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        nueva_fecha = date.today() + timedelta(days=15)
        response = self.client.post(
            reverse('coordinador:editar', args=[self.publicada.pk]),
            {
                'nombre': self.publicada.nombre,
                'descripcion': self.publicada.descripcion,
                'fecha': nueva_fecha.isoformat(),
                'cupo': 8,
                'tipo': self.publicada.tipo,
                'area': self.publicada.area,
                'ubicacion': 'Costanera de Asunción',
                'accion': 'guardar',
            },
        )
        self.assertRedirects(response, reverse('coordinador:gestionar'))
        self.publicada.refresh_from_db()
        self.assertEqual(self.publicada.fecha, nueva_fecha)
        self.assertEqual(self.publicada.cupo, 8)

    def test_no_reduce_cupo_por_debajo_de_inscriptos(self):
        otro = Usuario.objects.create_user(
            username='vol2',
            email='vol2@ejemplo.com',
            password='ClaveSegura123!',
        )
        otro.roles.add(Rol.objects.get(nombre='Voluntario'))
        Inscripcion.objects.create(actividad=self.publicada, voluntario=self.voluntario)
        Inscripcion.objects.create(actividad=self.publicada, voluntario=otro)
        self.client.login(username='coord', password='ClaveSegura123!')
        response = self.client.post(
            reverse('coordinador:editar', args=[self.publicada.pk]),
            {
                'nombre': self.publicada.nombre,
                'descripcion': self.publicada.descripcion,
                'fecha': self.publicada.fecha.isoformat(),
                'cupo': 1,
                'tipo': self.publicada.tipo,
                'area': self.publicada.area,
                'ubicacion': 'Costanera de Asunción',
                'accion': 'guardar',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Atención')
        self.assertContains(response, '2 voluntarios inscriptos')
        self.publicada.refresh_from_db()
        self.assertEqual(self.publicada.cupo, 20)

    def test_cancelar_oculta_la_actividad_al_voluntario(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        self.client.post(reverse('coordinador:cancelar', args=[self.publicada.pk]))
        self.publicada.refresh_from_db()
        self.assertEqual(self.publicada.estado, EstadoActividad.CANCELADA)

        self.client.logout()
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.get(reverse('voluntario:listado'))
        self.assertContains(response, 'Todavía no hay actividades publicadas')
        self.assertNotContains(response, 'Actividad abierta.')

    def test_cambio_avisa_a_inscriptos(self):
        Inscripcion.objects.create(actividad=self.publicada, voluntario=self.voluntario)
        self.client.login(username='coord', password='ClaveSegura123!')
        self.client.post(
            reverse('coordinador:editar', args=[self.publicada.pk]),
            {
                'nombre': self.publicada.nombre,
                'descripcion': self.publicada.descripcion,
                'fecha': (date.today() + timedelta(days=20)).isoformat(),
                'cupo': self.publicada.cupo,
                'tipo': self.publicada.tipo,
                'area': self.publicada.area,
                'ubicacion': 'Costanera de Asunción',
                'accion': 'guardar',
            },
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('vol@ejemplo.com', mail.outbox[0].to)
        self.assertIn('actualizó', mail.outbox[0].subject)

    def test_cancelar_avisa_a_inscriptos(self):
        Inscripcion.objects.create(actividad=self.publicada, voluntario=self.voluntario)
        self.client.login(username='coord', password='ClaveSegura123!')
        self.client.post(reverse('coordinador:cancelar', args=[self.publicada.pk]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('canceló', mail.outbox[0].subject)

    def test_editar_borrador_no_envia_correo(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        self.client.post(
            reverse('coordinador:editar', args=[self.borrador.pk]),
            {
                'nombre': 'Taller actualizado',
                'descripcion': self.borrador.descripcion,
                'fecha': self.borrador.fecha.isoformat(),
                'cupo': 5,
                'tipo': self.borrador.tipo,
                'area': self.borrador.area,
                'ubicacion': 'Centro comunitario',
                'accion': 'guardar',
            },
        )
        self.assertEqual(len(mail.outbox), 0)
        self.borrador.refresh_from_db()
        self.assertEqual(self.borrador.nombre, 'Taller actualizado')
        self.assertEqual(self.borrador.estado, EstadoActividad.BORRADOR)
