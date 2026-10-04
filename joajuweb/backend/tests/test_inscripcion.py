# El voluntario se inscribe en una publicada y puede cancelar su inscripción.
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from joajuweb.backend.models import Actividad, EstadoActividad, Inscripcion, Rol, Usuario


class InscripcionActividadTestCase(TestCase):
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

        self.otro = Usuario.objects.create_user(
            username='vol2',
            email='vol2@ejemplo.com',
            password='ClaveSegura123!',
        )
        self.otro.roles.add(rol_vol)

        self.publicada = Actividad.objects.create(
            nombre='Jornada de limpieza',
            descripcion='Limpieza de la costanera.',
            fecha=date.today() + timedelta(days=7),
            cupo=2,
            estado=EstadoActividad.PUBLICADA,
            creado_por=self.coordinador,
        )
        self.borrador = Actividad.objects.create(
            nombre='Taller oculto',
            descripcion='Todavía no se publica.',
            fecha=date.today() + timedelta(days=10),
            cupo=10,
            estado=EstadoActividad.BORRADOR,
            creado_por=self.coordinador,
        )

    def test_listado_muestra_sumarme(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.get(reverse('voluntario:listado'))
        self.assertContains(response, 'Jornada de limpieza')
        self.assertContains(response, 'Sumarme')

    def test_detalle_pide_confirmacion(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.get(reverse('voluntario:detalle', args=[self.publicada.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirmar inscripción')

    def test_voluntario_confirma_inscripcion(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.post(
            reverse('voluntario:inscribirse', args=[self.publicada.pk]),
        )
        self.assertRedirects(response, reverse('voluntario:listado'))
        self.assertTrue(
            Inscripcion.objects.filter(actividad=self.publicada, voluntario=self.voluntario).exists()
        )
        listado = self.client.get(reverse('voluntario:listado'))
        self.assertContains(listado, 'Inscripto')
        self.assertContains(listado, 'Cancelar inscripción')

    def test_no_se_inscribe_dos_veces(self):
        Inscripcion.objects.create(actividad=self.publicada, voluntario=self.voluntario)
        self.client.login(username='vol', password='ClaveSegura123!')
        self.client.post(reverse('voluntario:inscribirse', args=[self.publicada.pk]))
        self.assertEqual(
            Inscripcion.objects.filter(actividad=self.publicada, voluntario=self.voluntario).count(),
            1,
        )

    def test_no_inscribe_si_no_hay_cupo(self):
        Inscripcion.objects.create(actividad=self.publicada, voluntario=self.otro)
        otro_mas = Usuario.objects.create_user(
            username='vol3',
            email='vol3@ejemplo.com',
            password='ClaveSegura123!',
        )
        otro_mas.roles.add(Rol.objects.get(nombre='Voluntario'))
        Inscripcion.objects.create(actividad=self.publicada, voluntario=otro_mas)

        self.client.login(username='vol', password='ClaveSegura123!')
        self.client.post(reverse('voluntario:inscribirse', args=[self.publicada.pk]))
        self.assertFalse(
            Inscripcion.objects.filter(actividad=self.publicada, voluntario=self.voluntario).exists()
        )
        self.assertEqual(self.publicada.cantidad_inscriptos(), self.publicada.cupo)
        self.assertTrue(self.publicada.esta_completa())
        listado = self.client.get(reverse('voluntario:listado'))
        self.assertContains(listado, 'Sin cupo')
        self.assertContains(listado, 'Completa')
        detalle = self.client.get(reverse('voluntario:detalle', args=[self.publicada.pk]))
        self.assertContains(detalle, 'está completa')
        self.assertNotContains(detalle, 'Confirmar inscripción')

    def test_no_inscribe_en_borrador(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.get(reverse('voluntario:detalle', args=[self.borrador.pk]))
        self.assertEqual(response.status_code, 404)
        self.client.post(reverse('voluntario:inscribirse', args=[self.borrador.pk]))
        self.assertFalse(Inscripcion.objects.filter(actividad=self.borrador).exists())

    def test_voluntario_cancela_inscripcion(self):
        Inscripcion.objects.create(actividad=self.publicada, voluntario=self.voluntario)
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.post(
            reverse('voluntario:baja', args=[self.publicada.pk]),
        )
        self.assertRedirects(response, reverse('voluntario:listado'))
        self.assertFalse(
            Inscripcion.objects.filter(actividad=self.publicada, voluntario=self.voluntario).exists()
        )

    def test_al_cancelar_inscripcion_se_libera_cupo(self):
        self.publicada.cupo = 1
        self.publicada.save(update_fields=['cupo'])
        Inscripcion.objects.create(actividad=self.publicada, voluntario=self.otro)
        self.assertTrue(self.publicada.esta_completa())

        self.client.login(username='vol2', password='ClaveSegura123!')
        self.client.post(reverse('voluntario:baja', args=[self.publicada.pk]))
        self.assertFalse(self.publicada.esta_completa())

        self.client.logout()
        self.client.login(username='vol', password='ClaveSegura123!')
        self.client.post(reverse('voluntario:inscribirse', args=[self.publicada.pk]))
        self.assertTrue(
            Inscripcion.objects.filter(actividad=self.publicada, voluntario=self.voluntario).exists()
        )

    def test_coordinador_ve_actividad_completa(self):
        self.publicada.cupo = 1
        self.publicada.save(update_fields=['cupo'])
        Inscripcion.objects.create(actividad=self.publicada, voluntario=self.voluntario)
        self.client.login(username='coord', password='ClaveSegura123!')
        response = self.client.get(reverse('coordinador:gestionar'))
        self.assertContains(response, 'Completa')
        self.assertContains(response, '0 disponibles')

    def test_coordinador_no_se_inscribe(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        response = self.client.post(
            reverse('voluntario:inscribirse', args=[self.publicada.pk]),
        )
        self.assertRedirects(response, reverse('voluntario:listado'))
        self.assertFalse(Inscripcion.objects.exists())
