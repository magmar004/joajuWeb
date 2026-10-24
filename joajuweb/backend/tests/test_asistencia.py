from datetime import datetime, time, timedelta, timezone as tz
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from joajuweb.backend.forms.actividades import ActividadForm, JornadasFormSet
from joajuweb.backend.models import Actividad, AsistenciaJornada, Inscripcion, JornadaActividad, Rol, Usuario
from joajuweb.backend.servicios import (
    ActividadError, AsistenciaError, InscripcionError, cancelar_actividad,
    cancelar_inscripcion, confirmar_asistencia, generar_reporte, inscribir_voluntario,
    inscripciones_de_jornada, modificar_actividad, registrar_asistencia,
    resumen_inicio_voluntario, version_asistencia,
)


AHORA = datetime(2026, 10, 21, 15, tzinfo=tz.utc)  # 12:00 de Asunción.


class AsistenciaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        rol = Rol.objects.get(nombre='Coordinador')
        cls.coordinador = Usuario.objects.create_user('coord', first_name='Coordinador')
        cls.coordinador.roles.add(rol)
        cls.otro = Usuario.objects.create_user('otro-coord')
        cls.otro.roles.add(rol)
        cls.voluntario = Usuario.objects.create_user('ana', first_name='Ana', last_name='Pérez', email='ana@example.com')
        cls.segundo = Usuario.objects.create_user('luis', first_name='Luis', last_name='Gómez')
        cls.no_inscripto = Usuario.objects.create_user('sin-inscripcion')
        cls.actividad = Actividad.objects.create(nombre='Actividad de varios días', descripcion='Prueba', fecha=AHORA.date(), cupo=10, estado='publicada', creado_por=cls.coordinador)
        cls.jornada = JornadaActividad.objects.create(actividad=cls.actividad, fecha=AHORA.date(), hora_inicio=time(10), hora_fin=time(13))
        cls.manana = JornadaActividad.objects.create(actividad=cls.actividad, fecha=(AHORA + timedelta(days=1)).date(), hora_inicio=time(10), hora_fin=time(13))
        cls.inscripcion = Inscripcion.objects.create(actividad=cls.actividad, voluntario=cls.voluntario)
        cls.inscripcion2 = Inscripcion.objects.create(actividad=cls.actividad, voluntario=cls.segundo)
        Inscripcion.objects.filter(actividad=cls.actividad).update(fecha_inscripcion=AHORA - timedelta(days=1))

    def setUp(self):
        self.reloj = patch('django.utils.timezone.now', return_value=AHORA)
        self.reloj.start()
        self.addCleanup(self.reloj.stop)

    def confirmar(self, usuario=None, codigo=None):
        return confirmar_asistencia(self.actividad.pk, usuario or self.voluntario, codigo if codigo is not None else self.actividad.codigo_asistencia)

    def guardar(self, marcas=None, version=None, usuario=None, jornada=None):
        jornada = jornada or self.jornada
        return registrar_asistencia(
            self.actividad, jornada.pk,
            marcas if marcas is not None else {self.inscripcion.pk: 'presente', self.inscripcion2.pk: 'presente'},
            usuario or self.coordinador, version or version_asistencia(jornada),
        )

    def cerrado(self):
        return patch('django.utils.timezone.now', return_value=AHORA + timedelta(hours=2))

    def test_codigo_valido_actualiza_solo_jornada_actual(self):
        registro = self.confirmar()
        self.assertEqual(registro.estado, 'presente')
        self.assertEqual(registro.origen, 'codigo')
        self.assertEqual(registro.registrado_por, self.voluntario)
        self.assertEqual(registro.actualizado_en, AHORA)
        self.assertEqual(registro.jornada, self.jornada)
        self.assertFalse(self.manana.asistencias.exists())

    def test_codigo_incorrecto_y_no_ascii(self):
        for codigo in ('INCORRECTO', '', 'ñ' * 12):
            with self.subTest(codigo=codigo), self.assertRaisesMessage(AsistenciaError, 'incorrecto'):
                self.confirmar(codigo=codigo)
        self.assertEqual(AsistenciaJornada.objects.count(), 0)

    def test_codigo_de_otra_actividad(self):
        otra = Actividad.objects.create(nombre='Otra', descripcion='Otra', fecha=AHORA.date(), cupo=1, creado_por=self.coordinador)
        with self.assertRaisesMessage(AsistenciaError, 'otra actividad'):
            self.confirmar(codigo=otra.codigo_asistencia)

    def test_horario_antes_despues_y_limites(self):
        for hora in (9, 13, 14):
            with self.subTest(hora=hora), patch('django.utils.timezone.now', return_value=AHORA.replace(hour=hora + 3)), self.assertRaisesMessage(AsistenciaError, 'fuera del horario'):
                self.confirmar()
        with patch('django.utils.timezone.now', return_value=AHORA.replace(hour=13)):
            self.assertEqual(self.confirmar().estado, 'presente')

    def test_horario_no_depende_de_zona_del_cliente(self):
        with timezone.override('Pacific/Auckland'):
            self.assertEqual(self.confirmar().jornada, self.jornada)

    def test_no_inscripto(self):
        with self.assertRaisesMessage(AsistenciaError, 'No estás inscripto'):
            self.confirmar(usuario=self.no_inscripto)

    def test_cancelada_y_borrador(self):
        for estado in ('cancelada', 'borrador'):
            Actividad.objects.filter(pk=self.actividad.pk).update(estado=estado)
            with self.subTest(estado=estado), self.assertRaisesMessage(AsistenciaError, 'no está disponible'):
                self.confirmar()

    def test_confirmacion_repetida(self):
        self.confirmar()
        with self.assertRaisesMessage(AsistenciaError, 'ya fue registrada'):
            self.confirmar()
        self.assertEqual(AsistenciaJornada.objects.count(), 1)

    def test_puede_confirmar_cada_dia(self):
        self.confirmar()
        with patch('django.utils.timezone.now', return_value=AHORA + timedelta(days=1)):
            self.confirmar()
        self.assertEqual(self.inscripcion.asistencias.count(), 2)

    def test_codigo_no_reemplaza_ausente(self):
        AsistenciaJornada.objects.create(inscripcion=self.inscripcion, jornada=self.jornada, estado='ausente', origen='manual')
        with self.assertRaisesMessage(AsistenciaError, 'ausente'):
            self.confirmar()
        self.assertEqual(self.inscripcion.asistencias.get().estado, 'ausente')

    def test_marcacion_masiva_y_correccion_individual(self):
        with self.cerrado():
            self.assertEqual(self.guardar(), 2)
            self.guardar({self.inscripcion.pk: 'ausente', self.inscripcion2.pk: 'presente'})
            registro = self.inscripcion.asistencias.get()
            self.assertEqual(registro.estado, 'ausente')
            self.assertEqual(registro.version, 2)
            self.guardar()
            self.assertEqual(self.inscripcion.asistencias.get().estado, 'presente')
        self.assertEqual(AsistenciaJornada.objects.count(), 2)

    def test_manual_prohibido_durante_jornada(self):
        with self.assertRaisesMessage(AsistenciaError, 'terminar la jornada'):
            self.guardar()
        self.assertFalse(AsistenciaJornada.objects.exists())

    def test_manual_permitido_al_cierre_con_evento_aun_vigente(self):
        with patch('django.utils.timezone.now', return_value=AHORA.replace(hour=16)):
            self.guardar()
            self.assertFalse(self.actividad.ya_finalizo())

    def test_guardado_incompleto_no_escribe_nada(self):
        with self.cerrado(), self.assertRaises(AsistenciaError):
            self.guardar({self.inscripcion.pk: 'presente'})
        self.assertFalse(AsistenciaJornada.objects.exists())

    def test_guardado_invalido_no_escribe_nada(self):
        with self.cerrado(), self.assertRaises(AsistenciaError):
            self.guardar({self.inscripcion.pk: 'presente', self.inscripcion2.pk: 'inventado'})
        self.assertFalse(AsistenciaJornada.objects.exists())

    def test_transaccion_revierte_un_fallo_parcial(self):
        original = AsistenciaJornada.save
        def fallar_en_segundo(registro, *args, **kwargs):
            if registro.inscripcion_id == self.inscripcion2.pk:
                raise RuntimeError('Fallo simulado')
            return original(registro, *args, **kwargs)
        with self.cerrado(), patch.object(AsistenciaJornada, 'save', fallar_en_segundo), self.assertRaises(RuntimeError):
            self.guardar()
        self.assertFalse(AsistenciaJornada.objects.exists())

    def test_formulario_desactualizado_no_pisa_codigo(self):
        version = version_asistencia(self.jornada)
        self.confirmar()
        with self.cerrado(), self.assertRaisesMessage(AsistenciaError, 'Cambiaron'):
            self.guardar(version=version)
        self.assertEqual(AsistenciaJornada.objects.count(), 1)

    def test_dos_formularios_manuales_no_se_sobrescriben(self):
        version = version_asistencia(self.jornada)
        with self.cerrado():
            self.guardar(version=version)
            with self.assertRaisesMessage(AsistenciaError, 'Cambiaron'):
                self.guardar({self.inscripcion.pk: 'ausente', self.inscripcion2.pk: 'ausente'}, version=version)
        self.assertEqual(self.inscripcion.asistencias.get().estado, 'presente')

    def test_version_manipulada_rechazada(self):
        with self.cerrado(), self.assertRaisesMessage(AsistenciaError, 'no es válido'):
            self.guardar(version='manipulada')

    def test_inscripcion_posterior_excluida_de_jornada_cerrada(self):
        Inscripcion.objects.filter(pk=self.inscripcion2.pk).update(fecha_inscripcion=AHORA + timedelta(hours=2))
        self.assertEqual(list(inscripciones_de_jornada(self.jornada)), [self.inscripcion])
        self.assertEqual(inscripciones_de_jornada(self.manana).count(), 2)
        with self.cerrado():
            self.guardar({self.inscripcion.pk: 'presente'})
        self.assertFalse(self.inscripcion2.asistencias.exists())

    def test_fila_de_otra_actividad_no_modificable(self):
        otra = Actividad.objects.create(nombre='Otra', descripcion='Otra', fecha=AHORA.date(), cupo=1, creado_por=self.coordinador)
        ajena = Inscripcion.objects.create(actividad=otra, voluntario=self.voluntario)
        with self.cerrado(), self.assertRaises(AsistenciaError):
            self.guardar({self.inscripcion.pk: 'presente', self.inscripcion2.pk: 'presente', ajena.pk: 'ausente'})
        self.assertFalse(AsistenciaJornada.objects.exists())

    def test_restriccion_unicidad_en_bd(self):
        registro = self.confirmar()
        with self.assertRaises(IntegrityError), transaction.atomic():
            AsistenciaJornada.objects.create(inscripcion=registro.inscripcion, jornada=registro.jornada, estado='presente', origen='codigo')

    def test_autorizacion_servicios(self):
        for usuario in (self.otro, self.voluntario, AnonymousUser()):
            with self.subTest(usuario=str(usuario)), self.cerrado(), self.assertRaises(PermissionDenied):
                self.guardar(usuario=usuario)
        with self.assertRaises(PermissionDenied):
            self.confirmar(usuario=self.coordinador)

    def test_baja_impedida_si_tiene_asistencia(self):
        self.confirmar()
        with self.assertRaisesMessage(InscripcionError, 'asistencia registrada'):
            cancelar_inscripcion(self.actividad, self.voluntario)
        self.assertTrue(Inscripcion.objects.filter(pk=self.inscripcion.pk).exists())

    def test_baja_sin_asistencia_y_codigo_posterior(self):
        cancelar_inscripcion(self.actividad, self.voluntario)
        with self.assertRaisesMessage(AsistenciaError, 'No estás inscripto'):
            self.confirmar()

    def test_reportes_por_jornada_sin_duplicar_inscripciones(self):
        self.confirmar()
        with self.cerrado():
            self.guardar({self.inscripcion.pk: 'presente', self.inscripcion2.pk: 'ausente'})
        with patch('django.utils.timezone.now', return_value=AHORA + timedelta(days=1)):
            self.confirmar()
        reporte = generar_reporte(self.coordinador)
        self.assertEqual(reporte['totales']['presentes'], 2)
        self.assertEqual(reporte['totales']['ausentes'], 1)
        self.assertEqual(reporte['voluntarios'][0].n_inscripciones, 1)
        reporte = generar_reporte(self.coordinador, self.manana.fecha, self.manana.fecha)
        self.assertEqual(reporte['totales']['presentes'], 1)
        self.assertEqual(reporte['totales']['ausentes'], 0)
        self.assertEqual(len(reporte['inscripciones'][0].registros_reporte), 1)

    def test_actividad_vigente_multidia_aparece_en_inicio(self):
        with patch('django.utils.timezone.now', return_value=AHORA + timedelta(days=1)):
            self.assertEqual(resumen_inicio_voluntario(self.voluntario)['proxima'], self.actividad)

    def test_vista_permisos_y_codigo_oculto_al_voluntario(self):
        url = reverse('coordinador:asistencia', args=[self.actividad.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.voluntario)
        self.assertEqual(self.client.get(url).status_code, 302)
        respuesta = self.client.get(reverse('voluntario:detalle', args=[self.actividad.pk]))
        self.assertContains(respuesta, 'Código de asistencia')
        self.assertNotContains(respuesta, self.actividad.codigo_asistencia)
        self.client.force_login(self.coordinador)
        self.assertContains(self.client.get(url), self.actividad.codigo_asistencia)

    def test_http_confirmacion_post_y_csrf(self):
        url = reverse('voluntario:confirmar_asistencia', args=[self.actividad.pk])
        self.client.force_login(self.voluntario)
        self.assertEqual(self.client.get(url).status_code, 405)
        seguro = Client(enforce_csrf_checks=True)
        seguro.force_login(self.voluntario)
        self.assertEqual(seguro.post(url, {'codigo': self.actividad.codigo_asistencia}).status_code, 403)
        respuesta = self.client.post(url, {'codigo': self.actividad.codigo_asistencia}, follow=True)
        self.assertContains(respuesta, 'Confirmaste tu asistencia')
        self.assertEqual(AsistenciaJornada.objects.count(), 1)

    def test_vista_manual_preserva_selecciones_ante_error(self):
        self.client.force_login(self.coordinador)
        url = reverse('coordinador:asistencia', args=[self.actividad.pk])
        with self.cerrado():
            respuesta = self.client.post(url, {'jornada': self.jornada.pk, 'version': version_asistencia(self.jornada), f'asistencia_{self.inscripcion.pk}': 'ausente'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Marcá presente o ausente')
        self.assertEqual(respuesta.context['filas'][0]['estado'], 'ausente')
        self.assertFalse(AsistenciaJornada.objects.exists())

    def test_manual_cancelada_rechazada(self):
        cancelar_actividad(self.actividad, self.coordinador)
        with self.cerrado(), self.assertRaises(AsistenciaError):
            self.guardar()

    def test_jornada_ajena_rechazada(self):
        otra = Actividad.objects.create(nombre='Otra', descripcion='Otra', fecha=AHORA.date(), cupo=1, creado_por=self.coordinador)
        jornada = JornadaActividad.objects.create(actividad=otra, fecha=AHORA.date(), hora_inicio=time(8), hora_fin=time(9))
        with self.cerrado(), self.assertRaises(AsistenciaError):
            self.guardar(jornada=jornada)

    def datos_formulario(self):
        return {
            'nombre': self.actividad.nombre, 'descripcion': 'Descripción actualizada', 'fecha': str(self.actividad.fecha),
            'cupo': 10, 'tipo': 'comunitaria', 'departamento': 'central', 'ciudad': 'San Lorenzo', 'ubicacion': 'Asunción',
            'jornadas-TOTAL_FORMS': 2, 'jornadas-INITIAL_FORMS': 2,
            'jornadas-0-id': self.jornada.pk, 'jornadas-0-fecha': str(self.jornada.fecha),
            'jornadas-0-hora_inicio': '10:00', 'jornadas-0-hora_fin': '13:00',
            'jornadas-1-id': self.manana.pk, 'jornadas-1-fecha': str(self.manana.fecha),
            'jornadas-1-hora_inicio': '10:00', 'jornadas-1-hora_fin': '13:00',
        }

    def formularios(self, datos):
        actividad = Actividad.objects.get(pk=self.actividad.pk)
        form = ActividadForm(datos, instance=actividad)
        jornadas = JornadasFormSet(datos, instance=actividad, prefix='jornadas')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(jornadas.is_valid(), jornadas.errors)
        return form, jornadas

    def test_reprogramacion_prohibida_con_asistencia(self):
        self.confirmar()
        datos = self.datos_formulario()
        datos['jornadas-1-hora_fin'] = '14:00'
        form, jornadas = self.formularios(datos)
        with self.assertRaisesMessage(ActividadError, 'reprogramar'):
            modificar_actividad(form, self.coordinador, jornadas)
        self.manana.refresh_from_db()
        self.assertEqual(self.manana.hora_fin, time(13))

    def test_editar_otros_datos_con_asistencia(self):
        self.confirmar()
        form, jornadas = self.formularios(self.datos_formulario())
        actividad, avisos = modificar_actividad(form, self.coordinador, jornadas)
        self.assertEqual(actividad.descripcion, 'Descripción actualizada')
        self.assertEqual(avisos, 1)

    def test_cambio_horario_sin_asistencia_invalida_horario_viejo(self):
        datos = self.datos_formulario()
        datos['jornadas-0-hora_inicio'] = '12:30'
        form, jornadas = self.formularios(datos)
        modificar_actividad(form, self.coordinador, jornadas)
        with self.assertRaisesMessage(AsistenciaError, 'fuera del horario'):
            self.confirmar()

    def test_formset_rechaza_fechas_duplicadas_y_horario_invertido(self):
        for campo, valor in [('jornadas-1-fecha', str(self.jornada.fecha)), ('jornadas-0-hora_fin', '09:00'), ('jornadas-0-hora_fin', '')]:
            datos = self.datos_formulario()
            datos[campo] = valor
            with self.subTest(campo=campo, valor=valor):
                form = JornadasFormSet(datos, instance=self.actividad, prefix='jornadas')
                self.assertFalse(form.is_valid())

    def test_publicacion_con_jornadas_desde_http(self):
        self.client.force_login(self.coordinador)
        datos = self.datos_formulario()
        datos.update({'accion': 'publicar', 'nombre': 'Nueva', 'jornadas-INITIAL_FORMS': 0})
        del datos['jornadas-0-id']
        del datos['jornadas-1-id']
        respuesta = self.client.post(reverse('coordinador:publicar'), datos)
        self.assertEqual(respuesta.status_code, 302)
        nueva = Actividad.objects.get(nombre='Nueva')
        self.assertEqual(nueva.jornadas.count(), 2)
        self.assertNotEqual(nueva.codigo_asistencia, self.actividad.codigo_asistencia)

    def test_jornada_historica_sin_horario(self):
        self.jornada.hora_inicio = self.jornada.hora_fin = None
        self.jornada.save()
        with self.assertRaisesMessage(AsistenciaError, 'fuera del horario'):
            self.confirmar()
        with self.cerrado(), self.assertRaises(AsistenciaError):
            self.guardar()
        with patch('django.utils.timezone.now', return_value=AHORA + timedelta(days=1)):
            self.guardar()

    def test_inscripcion_al_cierre_excluida(self):
        Inscripcion.objects.filter(pk=self.inscripcion2.pk).update(fecha_inscripcion=self.jornada.cierre())
        self.assertEqual(list(inscripciones_de_jornada(self.jornada)), [self.inscripcion])

    def test_superusuario_sin_propiedad_no_puede_modificar(self):
        administrador = Usuario.objects.create_superuser('admin', 'admin@example.com', 'solo-prueba')
        self.client.force_login(administrador)
        url = reverse('coordinador:asistencia', args=[self.actividad.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        administrador.roles.add(Rol.objects.get(nombre='Coordinador'))
        self.assertEqual(self.client.get(url).status_code, 404)
        with self.cerrado(), self.assertRaises(PermissionDenied):
            self.guardar(usuario=administrador)

    def test_reportes_excluyen_huecos_entre_jornadas(self):
        self.manana.fecha = self.manana.fecha + timedelta(days=2)
        self.manana.save()
        dia_sin_jornada = self.jornada.fecha + timedelta(days=1)
        reporte = generar_reporte(self.coordinador, dia_sin_jornada, dia_sin_jornada)
        self.assertEqual(reporte['totales']['actividades'], 0)

    def test_resumen_no_usa_estado_historico_obsoleto(self):
        Inscripcion.objects.filter(pk=self.inscripcion.pk).update(asistencia='ausente')
        self.confirmar()
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.resumen_asistencia(), '1 presente(s), 0 ausente(s)')

    def test_vistas_historial_reporte_y_formularios_renderizan(self):
        self.confirmar()
        self.client.force_login(self.voluntario)
        self.assertContains(self.client.get(reverse('voluntario:historial')), '1 presente(s), 0 ausente(s)')
        self.client.force_login(self.coordinador)
        self.assertContains(self.client.get(reverse('coordinador:reportes')), 'por jornada')
        self.assertContains(self.client.get(reverse('coordinador:publicar')), 'Agregar jornada')
        self.assertContains(self.client.get(reverse('coordinador:editar', args=[self.actividad.pk])), 'Agregar jornada')

    def test_reprogramar_desde_http_muestra_error_sin_modificar(self):
        self.confirmar()
        datos = self.datos_formulario()
        datos['jornadas-1-hora_fin'] = '14:00'
        self.client.force_login(self.coordinador)
        respuesta = self.client.post(reverse('coordinador:editar', args=[self.actividad.pk]), datos)
        self.assertContains(respuesta, 'No se puede reprogramar')
        self.manana.refresh_from_db()
        self.assertEqual(self.manana.hora_fin, time(13))

    def test_post_manual_alterado_durante_jornada_no_escribe(self):
        self.client.force_login(self.coordinador)
        respuesta = self.client.post(reverse('coordinador:asistencia', args=[self.actividad.pk]), {
            'jornada': self.jornada.pk, 'version': version_asistencia(self.jornada),
            f'asistencia_{self.inscripcion.pk}': 'presente', f'asistencia_{self.inscripcion2.pk}': 'presente',
        })
        self.assertContains(respuesta, 'El registro manual solo está disponible')
        self.assertFalse(AsistenciaJornada.objects.exists())

    def test_horas_de_jornada_interpretadas_en_asuncion(self):
        self.assertEqual(timezone.get_default_timezone_name(), 'America/Asuncion')
        self.assertEqual(self.jornada.inicio().astimezone(tz.utc), AHORA.replace(hour=13))
        self.assertEqual(self.jornada.cierre().astimezone(tz.utc), AHORA.replace(hour=16))
        for mes in (1, 7, 10):
            fecha = datetime(2026, mes, 21, tzinfo=timezone.get_default_timezone())
            self.assertEqual(fecha.utcoffset(), timedelta(hours=-3))

    def test_inicio_local_no_se_confunde_con_utc(self):
        with patch('django.utils.timezone.now', return_value=AHORA.replace(hour=12)):
            with self.assertRaisesMessage(AsistenciaError, 'fuera del horario'):
                self.confirmar()
        with patch('django.utils.timezone.now', return_value=AHORA.replace(hour=13)):
            self.assertEqual(self.confirmar().estado, 'presente')

    def test_inscripcion_antes_de_cierre_local_no_es_excluida_por_utc(self):
        # 14:00 UTC = 11:00 de Asunción; la jornada cierra a las 13:00 locales.
        Inscripcion.objects.filter(pk=self.inscripcion2.pk).update(fecha_inscripcion=AHORA.replace(hour=14))
        self.assertEqual(inscripciones_de_jornada(self.jornada).count(), 2)
        self.assertEqual(self.confirmar(usuario=self.segundo).estado, 'presente')

    def test_fecha_local_jornada_cuando_utc_ya_es_dia_siguiente(self):
        self.jornada.hora_inicio = time(20)
        self.jornada.hora_fin = time(23)
        self.jornada.save()
        # 01:00 UTC del día siguiente todavía son las 22:00 de esta jornada.
        con_horario_local = (AHORA + timedelta(days=1)).replace(hour=1)
        with patch('django.utils.timezone.now', return_value=con_horario_local):
            self.assertEqual(self.confirmar().jornada, self.jornada)
            with self.assertRaisesMessage(AsistenciaError, 'terminar la jornada'):
                self.guardar()
        with patch('django.utils.timezone.now', return_value=con_horario_local.replace(hour=2)):
            self.guardar()

    def test_historica_cierra_en_medianoche_de_asuncion(self):
        self.jornada.hora_inicio = self.jornada.hora_fin = None
        self.jornada.save()
        siguiente = AHORA + timedelta(days=1)
        self.assertEqual(self.jornada.cierre().astimezone(tz.utc), siguiente.replace(hour=3))
        with patch('django.utils.timezone.now', return_value=siguiente.replace(hour=2)):
            self.assertFalse(self.jornada.finalizo())
        with patch('django.utils.timezone.now', return_value=siguiente.replace(hour=3)):
            self.assertTrue(self.jornada.finalizo())

    def test_gestion_y_lista_muestran_todos_los_inscritos_aun_despues_del_cierre(self):
        Inscripcion.objects.filter(pk=self.inscripcion2.pk).update(fecha_inscripcion=self.jornada.cierre() + timedelta(minutes=1))
        self.client.force_login(self.coordinador)
        gestion = self.client.get(reverse('coordinador:gestionar'))
        self.assertContains(gestion, 'Ver inscritos (2)')
        listado = self.client.get(reverse('coordinador:inscritos', args=[self.actividad.pk]))
        self.assertContains(listado, 'Ana Pérez')
        self.assertContains(listado, 'Luis Gómez')
        self.assertEqual(listado.context['inscripciones'].count(), 2)
        self.assertNotContains(listado, self.actividad.codigo_asistencia)
        asistencia = self.client.get(reverse('coordinador:asistencia', args=[self.actividad.pk]))
        self.assertEqual(asistencia.context['total_inscritos'], 2)
        self.assertEqual(asistencia.context['inscritos_excluidos'], 1)
        self.assertEqual(len(asistencia.context['filas']), 1)
        self.assertContains(asistencia, 'Siguen inscritos en la actividad')

    def test_listado_de_inscritos_tiene_permisos_del_creador(self):
        url = reverse('coordinador:inscritos', args=[self.actividad.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.voluntario)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.coordinador)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_lista_visible_antes_de_inicio_sin_habilitar_manual(self):
        self.client.force_login(self.coordinador)
        with patch('django.utils.timezone.now', return_value=AHORA.replace(hour=12)):
            respuesta = self.client.get(reverse('coordinador:asistencia', args=[self.actividad.pk]))
            self.assertContains(respuesta, 'Ana Pérez')
            self.assertContains(respuesta, 'Luis Gómez')
            self.assertNotContains(respuesta, 'id="marcar-presentes"')
            self.assertFalse(respuesta.context['editable'])

    def test_cambiar_zona_invalida_formulario_anterior(self):
        with self.settings(TIME_ZONE='UTC'):
            version_utc = version_asistencia(self.jornada)
        with self.cerrado(), self.assertRaisesMessage(AsistenciaError, 'Cambiaron'):
            self.guardar(version=version_utc)

    def test_se_puede_consultar_jornada_futura_antes_del_cierre_de_la_primera(self):
        self.client.force_login(self.coordinador)
        respuesta = self.client.get(
            reverse('coordinador:asistencia', args=[self.actividad.pk]),
            {'jornada': self.manana.pk},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['jornada'].pk, self.manana.pk)
        self.assertFalse(respuesta.context['editable'])
        self.assertContains(respuesta, f'data-jornada-actual="{self.manana.pk}"')
        self.assertNotContains(respuesta, 'Guardar asistencia')

    def test_seleccion_explicita_no_se_reemplaza_por_ultima_jornada_cerrada(self):
        self.client.force_login(self.coordinador)
        with self.cerrado():
            respuesta = self.client.get(
                reverse('coordinador:asistencia', args=[self.actividad.pk]),
                {'jornada': self.manana.pk},
            )
        self.assertEqual(respuesta.context['jornada'].pk, self.manana.pk)
        self.assertFalse(respuesta.context['editable'])
        self.assertEqual(len(respuesta.context['filas']), 2)
