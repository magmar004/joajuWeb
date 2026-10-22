import os
import subprocess
import sys
import textwrap

from django.conf import settings
from django.test import SimpleTestCase


class MigracionAsistenciaTests(SimpleTestCase):
    def test_upgrade_con_datos_historicos(self):
        # Proceso y base en memoria independientes: comienza realmente en 0009.
        script = textwrap.dedent('''
            import django
            django.setup()
            from django.db import connection
            from django.db.migrations.executor import MigrationExecutor
            executor = MigrationExecutor(connection)
            anterior = [('usuarios', '0009_usuario_foto')]
            executor.migrate(anterior)
            apps = executor.loader.project_state(anterior).apps
            Usuario = apps.get_model('usuarios', 'Usuario')
            Actividad = apps.get_model('usuarios', 'Actividad')
            Inscripcion = apps.get_model('usuarios', 'Inscripcion')
            coordinador = Usuario.objects.create(username='coord')
            voluntario = Usuario.objects.create(username='vol')
            ids = []
            for estado in ('presente', 'ausente', 'pendiente'):
                actividad = Actividad.objects.create(nombre=estado, descripcion='Prueba', fecha='2026-10-01', cupo=3, creado_por=coordinador)
                Inscripcion.objects.create(actividad=actividad, voluntario=voluntario, asistencia=estado)
                ids.append(actividad.pk)
            executor = MigrationExecutor(connection)
            destino = [('usuarios', '0010_asistencia_por_jornada')]
            executor.migrate(destino)
            apps = executor.loader.project_state(destino).apps
            Actividad = apps.get_model('usuarios', 'Actividad')
            Jornada = apps.get_model('usuarios', 'JornadaActividad')
            Asistencia = apps.get_model('usuarios', 'AsistenciaJornada')
            Inscripcion = apps.get_model('usuarios', 'Inscripcion')
            codigos = list(Actividad.objects.values_list('codigo_asistencia', flat=True))
            assert len(codigos) == len(set(codigos)) == 3
            assert all(len(codigo) == 12 for codigo in codigos)
            assert Jornada.objects.count() == 3
            assert not Jornada.objects.exclude(hora_inicio=None, hora_fin=None).exists()
            assert Asistencia.objects.count() == 2
            assert set(Asistencia.objects.values_list('estado', flat=True)) == {'presente', 'ausente'}
            assert set(Asistencia.objects.values_list('origen', flat=True)) == {'historico'}
            assert all(item.actualizado_en is None and item.registrado_por_id is None for item in Asistencia.objects.all())
            assert set(Inscripcion.objects.values_list('asistencia', flat=True)) == {'presente', 'ausente', 'pendiente'}
        ''')
        entorno = dict(os.environ, DJANGO_SETTINGS_MODULE='joajuweb.test_settings')
        resultado = subprocess.run([sys.executable, '-B', '-c', script], env=entorno, cwd=settings.BASE_DIR, capture_output=True, text=True, timeout=30)
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
