from datetime import datetime, time, timedelta, timezone as tz
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from joajuweb.backend.models import Actividad, Inscripcion, JornadaActividad, Rol, Usuario
from joajuweb.backend.servicios import (
    ActividadError, AsistenciaError, InscripcionError, cancelar_actividad,
    cancelar_inscripcion, confirmar_asistencia, filtrar_actividades_publicadas,
    finalizar_actividad, generar_reporte, inscribir_voluntario,
    registrar_asistencia, resumen_inicio_voluntario, version_asistencia,
)


AHORA = datetime(2026, 10, 21, 15, tzinfo=tz.utc)  # 12:00 de Asunción.


class FinalizacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.coordinador = Usuario.objects.create_user('creador-cierre')
        cls.otro = Usuario.objects.create_user('otro-cierre')
        rol = Rol.objects.get(nombre='Coordinador')
        cls.coordinador.roles.add(rol)
        cls.otro.roles.add(rol)
        cls.voluntario = Usuario.objects.create_user('inscripto-cierre')
        cls.nuevo = Usuario.objects.create_user('nuevo-cierre')
        cls.actividad = Actividad.objects.create(
            nombre='Actividad para cerrar', descripcion='Prueba de cierre',
            fecha=AHORA.date(), cupo=10, estado='publicada', creado_por=cls.coordinador,
        )
        cls.jornada = JornadaActividad.objects.create(
            actividad=cls.actividad, fecha=AHORA.date(), hora_inicio=time(8), hora_fin=time(12),
        )
        cls.inscripcion = Inscripcion.objects.create(actividad=cls.actividad, voluntario=cls.voluntario)
        Inscripcion.objects.filter(pk=cls.inscripcion.pk).update(fecha_inscripcion=AHORA - timedelta(days=1))

    def setUp(self):
        reloj = patch('django.utils.timezone.now', return_value=AHORA)
        reloj.start()
        self.addCleanup(reloj.stop)

    def finalizar(self):
        return finalizar_actividad(self.actividad, self.coordinador)

    def futuro(self):
        return JornadaActividad.objects.create(
            actividad=self.actividad, fecha=AHORA.date() + timedelta(days=2),
            hora_inicio=time(8), hora_fin=time(12),
        )

    def test_inscripcion_hasta_justo_antes_del_cierre(self):
        with patch('django.utils.timezone.now', return_value=AHORA - timedelta(microseconds=1)):
            self.assertTrue(self.actividad.inscripciones_abiertas())
            self.assertIn(self.actividad, Actividad.vigentes())
            inscribir_voluntario(self.actividad, self.nuevo)
        self.assertFalse(self.actividad.inscripciones_abiertas())
        self.assertNotIn(self.actividad, Actividad.vigentes())

    def test_rechaza_inscripcion_al_cierre_y_despues(self):
        for instante in (AHORA, AHORA + timedelta(days=3)):
            with self.subTest(instante=instante), patch('django.utils.timezone.now', return_value=instante):
                with self.assertRaisesMessage(InscripcionError, 'no quedan jornadas'):
                    inscribir_voluntario(self.actividad, self.nuevo)
        self.assertEqual(self.actividad.cantidad_inscriptos(), 1)

    def test_entre_jornadas_permanece_abierta_si_quedan_futuras(self):
        self.futuro()
        self.assertTrue(self.actividad.inscripciones_abiertas())
        self.assertIn(self.actividad, Actividad.vigentes())
        inscribir_voluntario(self.actividad, self.nuevo)
        with self.assertRaisesMessage(ActividadError, 'jornadas vigentes o futuras'):
            self.finalizar()

    def test_no_finaliza_durante_la_ultima_jornada(self):
        with patch('django.utils.timezone.now', return_value=AHORA - timedelta(seconds=1)):
            with self.assertRaises(ActividadError):
                self.finalizar()
        self.actividad.refresh_from_db()
        self.assertEqual(self.actividad.estado, 'publicada')

    def test_sin_jornadas_no_acepta_inscripcion_ni_cierre(self):
        self.jornada.delete()
        self.assertFalse(self.actividad.inscripciones_abiertas())
        self.assertNotIn(self.actividad, Actividad.vigentes())
        with self.assertRaises(InscripcionError):
            inscribir_voluntario(self.actividad, self.nuevo)
        with self.assertRaises(ActividadError):
            self.finalizar()

    def test_cierre_persistente_e_idempotente(self):
        cerrada = self.finalizar()
        self.assertEqual(cerrada.estado, 'finalizada')
        self.assertEqual(cerrada.finalizada_en, AHORA)
        with patch('django.utils.timezone.now', return_value=AHORA + timedelta(days=1)):
            repetida = self.finalizar()
        self.assertEqual(repetida.finalizada_en, AHORA)
        self.assertEqual(cerrada.cantidad_inscriptos(), 1)
        self.assertFalse(cerrada.se_puede_editar())
        self.assertFalse(cerrada.se_puede_cancelar())
        self.assertFalse(cerrada.inscripciones_abiertas())

    def test_finalizacion_solo_creador_autorizado_en_servicio(self):
        for usuario in (self.otro, self.voluntario):
            with self.subTest(usuario=usuario.pk), self.assertRaises(PermissionDenied):
                finalizar_actividad(self.actividad, usuario)
        self.actividad.refresh_from_db()
        self.assertEqual(self.actividad.estado, 'publicada')

    def test_borrador_y_cancelada_no_se_finalizan(self):
        for estado in ('borrador', 'cancelada'):
            Actividad.objects.filter(pk=self.actividad.pk).update(estado=estado)
            with self.subTest(estado=estado), self.assertRaises(ActividadError):
                self.finalizar()

    def test_http_cierre_solo_post_y_creador(self):
        url = reverse('coordinador:finalizar', args=[self.actividad.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.client.force_login(self.voluntario)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.client.force_login(self.otro)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.client.force_login(self.coordinador)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.actividad.refresh_from_db()
        self.assertEqual(self.actividad.estado, 'publicada')
        self.assertRedirects(self.client.post(url), reverse('coordinador:gestionar'))
        self.actividad.refresh_from_db()
        self.assertEqual(self.actividad.estado, 'finalizada')

    def test_http_inscripcion_manipulada_fuera_de_horario(self):
        self.client.force_login(self.nuevo)
        url = reverse('voluntario:inscribirse', args=[self.actividad.pk])
        respuesta = self.client.post(url, {'fecha': '2099-01-01', 'estado': 'publicada'}, follow=True)
        self.assertContains(respuesta, 'Las inscripciones están cerradas')
        self.assertEqual(self.actividad.cantidad_inscriptos(), 1)

    def test_finalizada_rechaza_inscripcion_y_codigo_incluso_objeto_obsoleto(self):
        self.finalizar()
        with self.assertRaises(InscripcionError):
            inscribir_voluntario(self.actividad, self.nuevo)
        with self.assertRaises(AsistenciaError):
            confirmar_asistencia(self.actividad.pk, self.voluntario, self.actividad.codigo_asistencia)
        # El servicio de cancelación también debe leer el estado actual bajo bloqueo.
        cancelar_actividad(self.actividad, self.coordinador)
        self.actividad.refresh_from_db()
        self.assertEqual(self.actividad.estado, 'finalizada')

    def test_finalizada_permite_completar_y_corregir_asistencia(self):
        self.finalizar()
        self.client.force_login(self.coordinador)
        url = reverse('coordinador:asistencia', args=[self.actividad.pk])
        respuesta = self.client.get(url)
        self.assertTrue(respuesta.context['editable'])
        self.assertContains(respuesta, 'Guardar asistencia')
        self.assertNotContains(respuesta, self.actividad.codigo_asistencia)
        self.assertRedirects(self.client.post(url, {
            'jornada': self.jornada.pk, 'version': respuesta.context['version'],
            f'asistencia_{self.inscripcion.pk}': 'presente',
        }), f'{url}?jornada={self.jornada.pk}')
        registrar_asistencia(self.actividad, self.jornada.pk, {self.inscripcion.pk: 'ausente'}, self.coordinador, version_asistencia(self.jornada))
        self.assertEqual(self.inscripcion.asistencias.count(), 1)
        self.assertEqual(self.inscripcion.asistencias.get().estado, 'ausente')
        reporte = generar_reporte(self.coordinador)
        self.assertEqual(reporte['totales']['ausentes'], 1)

    def test_finalizada_no_permite_editar_desde_http(self):
        self.finalizar()
        self.client.force_login(self.coordinador)
        respuesta = self.client.post(reverse('coordinador:editar', args=[self.actividad.pk]), {'nombre': 'Alterada'}, follow=True)
        self.assertContains(respuesta, 'finalizada no se puede modificar')
        self.actividad.refresh_from_db()
        self.assertEqual(self.actividad.nombre, 'Actividad para cerrar')

    def test_historial_y_detalle_se_conservan_sin_acciones_de_inscripcion(self):
        self.finalizar()
        self.client.force_login(self.voluntario)
        detalle = self.client.get(reverse('voluntario:detalle', args=[self.actividad.pk]))
        self.assertContains(detalle, 'Tu asistencia')
        self.assertContains(detalle, 'fue dada por terminada')
        self.assertNotContains(detalle, 'Cancelar inscripción')
        self.assertNotContains(detalle, 'Confirmar asistencia de hoy')
        self.assertContains(self.client.get(reverse('voluntario:historial')), 'Finalizada')
        self.client.force_login(self.nuevo)
        detalle = self.client.get(reverse('voluntario:detalle', args=[self.actividad.pk]))
        self.assertNotContains(detalle, 'Confirmar inscripción')

    def test_no_se_elimina_inscripcion_pendiente_despues_del_cierre(self):
        with self.assertRaisesMessage(InscripcionError, 'se conserva en tu historial'):
            cancelar_inscripcion(self.actividad, self.voluntario)
        self.assertTrue(Inscripcion.objects.filter(pk=self.inscripcion.pk).exists())

    def test_gestion_distingue_pendientes_cierre_y_finalizadas(self):
        self.client.force_login(self.coordinador)
        url = reverse('coordinador:gestionar')
        pendiente = self.client.get(url)
        self.assertContains(pendiente, 'Dar por terminada')
        self.assertEqual(pendiente.context['pendientes_cierre'], [self.actividad])
        self.assertEqual(pendiente.context['publicadas'], [])
        self.finalizar()
        cerrada = self.client.get(url)
        self.assertNotContains(cerrada, 'Dar por terminada')
        self.assertEqual(list(cerrada.context['finalizadas']), [self.actividad])

    def test_catalogo_y_panel_no_ofrecen_actividades_sin_jornadas_vigentes(self):
        self.assertNotIn(self.actividad, filtrar_actividades_publicadas())
        self.assertEqual(resumen_inicio_voluntario(self.voluntario)['abiertas'], [])
        self.assertIsNone(resumen_inicio_voluntario(self.voluntario)['proxima'])
        self.futuro()
        self.assertIn(self.actividad, filtrar_actividades_publicadas())
        self.assertEqual(resumen_inicio_voluntario(self.voluntario)['proxima'], self.actividad)

    def test_vigencia_utiliza_asuncion_y_no_zona_del_cliente(self):
        self.jornada.hora_fin = time(23)
        self.jornada.save()
        # Día siguiente en UTC, todavía la misma jornada en Paraguay.
        with patch('django.utils.timezone.now', return_value=(AHORA + timedelta(days=1)).replace(hour=1)), timezone.override('Pacific/Auckland'):
            self.assertTrue(self.actividad.inscripciones_abiertas())
            self.assertIn(self.actividad, Actividad.vigentes())
        with patch('django.utils.timezone.now', return_value=(AHORA + timedelta(days=1)).replace(hour=2)):
            self.assertFalse(self.actividad.inscripciones_abiertas())
            self.assertNotIn(self.actividad, Actividad.vigentes())

    def test_historica_sin_horas_cierra_en_medianoche_local(self):
        self.jornada.hora_inicio = self.jornada.hora_fin = None
        self.jornada.save()
        for hora, vigente in ((2, True), (3, False)):
            with self.subTest(hora=hora), patch('django.utils.timezone.now', return_value=(AHORA + timedelta(days=1)).replace(hour=hora)):
                self.assertEqual(self.actividad.inscripciones_abiertas(), vigente)
                self.assertEqual(Actividad.vigentes().filter(pk=self.actividad.pk).exists(), vigente)
