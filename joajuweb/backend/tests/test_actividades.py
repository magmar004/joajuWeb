# Un borrador no es visible para el voluntario, una publicada sí
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from joajuweb.backend.models import Actividad, EstadoActividad, Inscripcion, Rol, Usuario


class PublicacionActividadTestCase(TestCase):
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

        self.datos_validos = {
            'nombre': 'Jornada de limpieza',
            'descripcion': 'Limpieza de la costanera junto a vecinos.',
            'fecha': (date.today() + timedelta(days=7)).isoformat(),
            'cupo': 20,
            'tipo': 'ambiental',
            'area': 'asuncion',
            'ubicacion': 'Costanera de Asunción',
        }

    def test_campos_obligatorios(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        response = self.client.post(reverse('coordinador:publicar'), {
            'nombre': '',
            'descripcion': '',
            'fecha': '',
            'cupo': '',
            'accion': 'publicar',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Actividad.objects.exists())
        self.assertContains(response, 'Atención')

    def test_coordinador_guarda_borrador(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        response = self.client.post(
            reverse('coordinador:publicar'),
            {**self.datos_validos, 'accion': 'guardar'},
        )
        self.assertEqual(response.status_code, 302)
        actividad = Actividad.objects.get()
        self.assertEqual(actividad.estado, EstadoActividad.BORRADOR)
        self.assertEqual(actividad.creado_por, self.coordinador)

    def test_coordinador_publica_actividad(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        response = self.client.post(
            reverse('coordinador:publicar'),
            {**self.datos_validos, 'accion': 'publicar'},
        )
        self.assertRedirects(response, reverse('voluntario:listado'))
        self.assertEqual(Actividad.objects.get().estado, EstadoActividad.PUBLICADA)

    def test_voluntario_no_puede_publicar(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.post(
            reverse('coordinador:publicar'),
            {**self.datos_validos, 'accion': 'publicar'},
        )
        self.assertEqual(response.url, reverse('voluntario:home'))
        self.assertFalse(Actividad.objects.exists())

    def test_voluntario_ve_solo_publicadas(self):
        Actividad.objects.create(
            nombre='Borrador oculto',
            descripcion='No debería verse.',
            fecha=date.today() + timedelta(days=3),
            cupo=10,
            estado=EstadoActividad.BORRADOR,
            creado_por=self.coordinador,
        )
        Actividad.objects.create(
            nombre='Actividad visible',
            descripcion='Los voluntarios deben verla.',
            fecha=date.today() + timedelta(days=5),
            cupo=15,
            estado=EstadoActividad.PUBLICADA,
            creado_por=self.coordinador,
        )
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.get(reverse('voluntario:listado'))
        self.assertContains(response, 'Actividad visible')
        self.assertNotContains(response, 'Borrador oculto')

    def test_home_voluntario_muestra_publicadas(self):
        Actividad.objects.create(
            nombre='Huerta comunitaria',
            descripcion='Armado de huerta.',
            fecha=date.today() + timedelta(days=2),
            cupo=8,
            estado=EstadoActividad.PUBLICADA,
            creado_por=self.coordinador,
        )
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.get(reverse('home'), follow=True)
        self.assertContains(response, 'Huerta comunitaria')
        self.assertContains(response, 'Abiertas para sumarte')
        self.assertContains(response, 'Tu próxima actividad')

    def test_home_voluntario_muestra_proxima_y_pocas_abiertas(self):
        proxima = Actividad.objects.create(
            nombre='Mi jornada',
            descripcion='Ya estoy inscripto.',
            fecha=date.today() + timedelta(days=1),
            cupo=8,
            estado=EstadoActividad.PUBLICADA,
            creado_por=self.coordinador,
        )
        Inscripcion.objects.create(actividad=proxima, voluntario=self.voluntario)
        extras = []
        for i in range(5):
            extras.append(Actividad.objects.create(
                nombre=f'Abierta {i + 1}',
                descripcion='Oportunidad abierta.',
                fecha=date.today() + timedelta(days=2 + i),
                cupo=8,
                estado=EstadoActividad.PUBLICADA,
                creado_por=self.coordinador,
            ))
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.get(reverse('voluntario:home'))
        self.assertContains(response, 'Mi jornada')
        self.assertContains(response, 'Tu próxima')
        self.assertContains(response, 'Abierta 1')
        self.assertContains(response, 'Abierta 3')
        self.assertNotContains(response, 'Abierta 4')
        self.assertNotContains(response, 'Abierta 5')

    def test_listado_filtra_por_tipo_area_y_ubicacion(self):
        Actividad.objects.create(
            nombre='Limpieza costanera',
            descripcion='Actividad ambiental.',
            fecha=date.today() + timedelta(days=3),
            cupo=10,
            tipo='ambiental',
            area='asuncion',
            ubicacion='Costanera de Asunción',
            estado=EstadoActividad.PUBLICADA,
            creado_por=self.coordinador,
        )
        Actividad.objects.create(
            nombre='Taller en Lambaré',
            descripcion='Actividad educativa.',
            fecha=date.today() + timedelta(days=4),
            cupo=10,
            tipo='educativa',
            area='central',
            ubicacion='Plaza de Lambaré',
            estado=EstadoActividad.PUBLICADA,
            creado_por=self.coordinador,
        )
        self.client.login(username='vol', password='ClaveSegura123!')

        por_tipo = self.client.get(reverse('voluntario:listado'), {'tipo': 'ambiental'})
        self.assertContains(por_tipo, 'Limpieza costanera')
        self.assertNotContains(por_tipo, 'Taller en Lambaré')

        por_area = self.client.get(reverse('voluntario:listado'), {'area': 'central'})
        self.assertContains(por_area, 'Taller en Lambaré')
        self.assertNotContains(por_area, 'Limpieza costanera')

        por_lugar = self.client.get(reverse('voluntario:listado'), {'ubicacion': 'Costanera'})
        self.assertContains(por_lugar, 'Limpieza costanera')
        self.assertNotContains(por_lugar, 'Taller en Lambaré')

        agrupado = self.client.get(reverse('voluntario:listado'), {'agrupar': 'area'})
        self.assertContains(agrupado, 'Asunción')
        self.assertContains(agrupado, 'Central')
