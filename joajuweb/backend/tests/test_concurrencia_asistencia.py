from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta, timezone
from threading import Barrier
from unittest.mock import patch

from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from joajuweb.backend.models import Actividad, AsistenciaJornada, Inscripcion, JornadaActividad, Rol, Usuario
from joajuweb.backend.servicios import AsistenciaError, confirmar_asistencia


@skipUnlessDBFeature('has_select_for_update')
class ConcurrenciaAsistenciaTests(TransactionTestCase):
    def test_dos_confirmaciones_simultaneas_no_duplican(self):
        ahora = datetime(2026, 10, 21, 15, tzinfo=timezone.utc)  # 12:00 de Asunción.
        rol, _ = Rol.objects.get_or_create(nombre='Coordinador')
        coordinador = Usuario.objects.create_user('coordinador-concurrencia')
        coordinador.roles.add(rol)
        voluntario = Usuario.objects.create_user('voluntario-concurrencia')
        actividad = Actividad.objects.create(nombre='Concurrencia', descripcion='Prueba', fecha=ahora.date(), cupo=5, estado='publicada', creado_por=coordinador)
        JornadaActividad.objects.create(actividad=actividad, fecha=ahora.date(), hora_inicio=time(10), hora_fin=time(13))
        inscripcion = Inscripcion.objects.create(actividad=actividad, voluntario=voluntario)
        Inscripcion.objects.filter(pk=inscripcion.pk).update(fecha_inscripcion=ahora - timedelta(days=1))
        barrera = Barrier(2)

        def confirmar():
            close_old_connections()
            try:
                usuario = Usuario.objects.get(pk=voluntario.pk)
                barrera.wait(timeout=10)
                confirmar_asistencia(actividad.pk, usuario, actividad.codigo_asistencia)
                return 'registrado'
            except AsistenciaError:
                return 'duplicado rechazado'
            finally:
                close_old_connections()

        with patch('django.utils.timezone.now', return_value=ahora), ThreadPoolExecutor(max_workers=2) as executor:
            futuros = [executor.submit(confirmar) for _ in range(2)]
            resultados = [futuro.result(timeout=15) for futuro in futuros]
        self.assertCountEqual(resultados, ['registrado', 'duplicado rechazado'])
        self.assertEqual(AsistenciaJornada.objects.count(), 1)
