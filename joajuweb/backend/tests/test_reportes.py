# El coordinador consulta totales y detalle, filtrables por fecha y tipo.
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from joajuweb.backend.models import (
    Actividad,
    EstadoActividad,
    EstadoAsistencia,
    Inscripcion,
    Rol,
    TipoActividad,
    Usuario,
)


class ReportesCoordinadorTestCase(TestCase):
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

        self.ambiental = Actividad.objects.create(
            nombre='Jornada de limpieza',
            descripcion='Costanera.',
            fecha=date.today() - timedelta(days=3),
            cupo=10,
            tipo=TipoActividad.AMBIENTAL,
            estado=EstadoActividad.PUBLICADA,
            creado_por=self.coordinador,
        )
        self.educativa = Actividad.objects.create(
            nombre='Taller de lectura',
            descripcion='Escuela.',
            fecha=date.today() + timedelta(days=10),
            cupo=8,
            tipo=TipoActividad.EDUCATIVA,
            estado=EstadoActividad.PUBLICADA,
            creado_por=self.coordinador,
        )
        Actividad.objects.create(
            nombre='Huerta de otro',
            descripcion='No debe verse.',
            fecha=date.today(),
            cupo=5,
            tipo=TipoActividad.AMBIENTAL,
            estado=EstadoActividad.PUBLICADA,
            creado_por=self.otro_coord,
        )
        inscripcion = Inscripcion.objects.create(
            actividad=self.ambiental, voluntario=self.voluntario,
        )
        inscripcion.asistencia = EstadoAsistencia.PRESENTE
        inscripcion.save(update_fields=['asistencia'])
        Inscripcion.objects.create(actividad=self.educativa, voluntario=self.voluntario)

    def test_reporte_muestra_totales_y_detalle(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        response = self.client.get(reverse('coordinador:reportes'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jornada de limpieza')
        self.assertContains(response, 'Taller de lectura')
        self.assertContains(response, 'Luis Pérez')
        self.assertContains(response, '2')
        self.assertNotContains(response, 'Huerta de otro')
        self.assertEqual(response.context['totales']['actividades'], 2)
        self.assertEqual(response.context['totales']['voluntarios'], 1)
        self.assertEqual(response.context['totales']['inscripciones'], 2)
        self.assertEqual(response.context['totales']['presentes'], 1)

    def test_filtro_por_tipo(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        response = self.client.get(reverse('coordinador:reportes'), {'tipo': 'ambiental'})
        self.assertContains(response, 'Jornada de limpieza')
        self.assertNotContains(response, 'Taller de lectura')
        self.assertEqual(response.context['totales']['actividades'], 1)

    def test_filtro_por_fecha(self):
        self.client.login(username='coord', password='ClaveSegura123!')
        response = self.client.get(reverse('coordinador:reportes'), {
            'fecha_desde': (date.today() + timedelta(days=1)).isoformat(),
        })
        self.assertNotContains(response, 'Jornada de limpieza')
        self.assertContains(response, 'Taller de lectura')
        self.assertEqual(response.context['totales']['actividades'], 1)

    def test_voluntario_no_ve_reportes(self):
        self.client.login(username='vol', password='ClaveSegura123!')
        response = self.client.get(reverse('coordinador:reportes'))
        self.assertRedirects(response, reverse('voluntario:home'))
