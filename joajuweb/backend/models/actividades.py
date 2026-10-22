# Actividades de voluntariado e inscripciones.
from datetime import datetime, time, timedelta
import secrets

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


def generar_codigo_asistencia():
    return secrets.token_hex(6).upper()


class EstadoAsistencia(models.TextChoices):
    PENDIENTE = 'pendiente', 'Pendiente'
    PRESENTE = 'presente', 'Presente'
    AUSENTE = 'ausente', 'Ausente'


class EstadoParticipacion(models.TextChoices):
    INSCRIPTO = 'inscripto', 'Inscripto'
    PENDIENTE = 'pendiente', 'Pendiente'
    PARTICIPO = 'participo', 'Presente'
    AUSENTE = 'ausente', 'Ausente'
    CANCELADA = 'cancelada', 'Cancelada'


class EstadoActividad(models.TextChoices):
    BORRADOR = 'borrador', 'Borrador'
    PUBLICADA = 'publicada', 'Publicada'
    CANCELADA = 'cancelada', 'Cancelada'
    FINALIZADA = 'finalizada', 'Finalizada'


class TipoActividad(models.TextChoices):
    AMBIENTAL = 'ambiental', 'Ambiental'
    EDUCATIVA = 'educativa', 'Educativa'
    COMUNITARIA = 'comunitaria', 'Comunitaria'
    SALUD = 'salud', 'Salud'
    CULTURAL = 'cultural', 'Cultural'
    OTRA = 'otra', 'Otra'


class AreaActividad(models.TextChoices):
    ASUNCION = 'asuncion', 'Asunción'
    CENTRAL = 'central', 'Central'
    INTERIOR = 'interior', 'Interior'
    VIRTUAL = 'virtual', 'Virtual'
    OTRA = 'otra', 'Otra'


class Actividad(models.Model):
    # Finalizada conserva el historial y la asistencia, sin nuevas inscripciones.
    nombre = models.CharField(max_length=150, verbose_name="Nombre")
    descripcion = models.TextField(verbose_name="Descripción")
    fecha = models.DateField(verbose_name="Fecha")
    cupo = models.PositiveIntegerField(
        verbose_name="Cupo",
        validators=[MinValueValidator(1)],
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoActividad.choices,
        default=TipoActividad.COMUNITARIA,
        verbose_name="Tipo",
    )
    area = models.CharField(
        max_length=20,
        choices=AreaActividad.choices,
        default=AreaActividad.ASUNCION,
        verbose_name="Área",
    )
    ubicacion = models.CharField(
        max_length=150,
        blank=True,
        default='',
        verbose_name="Ubicación",
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoActividad.choices,
        default=EstadoActividad.BORRADOR,
        verbose_name="Estado",
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='actividades_creadas',
        verbose_name="Creado por",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    finalizada_en = models.DateTimeField(null=True, blank=True, editable=False)
    codigo_asistencia = models.CharField(
        max_length=12, unique=True, default=generar_codigo_asistencia, editable=False,
    )

    class Meta:
        ordering = ['fecha', 'nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_estado_display()})"

    def esta_publicada(self):
        return self.estado == EstadoActividad.PUBLICADA

    def esta_borrador(self):
        return self.estado == EstadoActividad.BORRADOR

    def esta_cancelada(self):
        return self.estado == EstadoActividad.CANCELADA

    def esta_finalizada(self):
        return self.estado == EstadoActividad.FINALIZADA

    def se_puede_editar(self):
        return self.estado in (EstadoActividad.BORRADOR, EstadoActividad.PUBLICADA)

    def se_puede_cancelar(self):
        return self.estado == EstadoActividad.PUBLICADA

    def cantidad_inscriptos(self):
        return self.inscripciones.count()

    def cupos_disponibles(self):
        return max(0, self.cupo - self.cantidad_inscriptos())

    def tiene_cupo(self):
        return self.cupos_disponibles() > 0

    def esta_completa(self):
        return self.cantidad_inscriptos() >= self.cupo

    def ya_finalizo(self):
        if self.esta_finalizada():
            return True
        jornadas = list(self.jornadas.all())
        return bool(jornadas) and all(item.finalizo() for item in jornadas)

    def inscripciones_abiertas(self):
        ahora = timezone.now()
        return self.esta_publicada() and any(item.cierre() > ahora for item in self.jornadas.all())

    def se_puede_finalizar(self):
        return self.esta_publicada() and self.ya_finalizo()

    def permite_asistencia_manual(self):
        return self.estado in (EstadoActividad.PUBLICADA, EstadoActividad.FINALIZADA)

    def se_puede_registrar_asistencia(self):
        return (
            self.permite_asistencia_manual()
            and any(item.finalizo() for item in self.jornadas.all())
            and self.cantidad_inscriptos() > 0
        )

    def esta_inscripto(self, user):
        if not getattr(user, 'is_authenticated', False):
            return False
        return self.inscripciones.filter(voluntario=user).exists()

    def emails_inscriptos(self):
        return [
            email
            for email in self.inscripciones.values_list('voluntario__email', flat=True)
            if email
        ]

    @classmethod
    def publicadas(cls):
        return cls.objects.filter(estado=EstadoActividad.PUBLICADA)

    @classmethod
    def vigentes(cls):
        # Usar la zona del sistema, independientemente de la activada para el usuario.
        ahora = timezone.localtime(timezone.now(), timezone.get_default_timezone())
        return cls.publicadas().filter(
            models.Q(jornadas__fecha__gt=ahora.date())
            | models.Q(jornadas__fecha=ahora.date(), jornadas__hora_fin__gt=ahora.time())
            | models.Q(jornadas__fecha=ahora.date(), jornadas__hora_fin__isnull=True)
        ).distinct()


class Inscripcion(models.Model):
    # Voluntario inscripto. Sirve para avisar ante cambios o cancelación.
    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        related_name='inscripciones',
    )
    voluntario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inscripciones',
    )
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    asistencia = models.CharField(
        max_length=20,
        choices=EstadoAsistencia.choices,
        default=EstadoAsistencia.PENDIENTE,
        verbose_name="Asistencia",
    )

    class Meta:
        unique_together = ('actividad', 'voluntario')

    def __str__(self):
        return f"{self.voluntario} → {self.actividad}"

    def estado_participacion(self, jornada=None):
        # Compatibilidad para consultas de una jornada. Para varios días usar el resumen.
        if self.actividad.esta_cancelada():
            return EstadoParticipacion.CANCELADA
        if jornada is None:
            jornadas = list(self.actividad.jornadas.all())
            if len(jornadas) != 1:
                return EstadoParticipacion.INSCRIPTO if not self.actividad.ya_finalizo() else EstadoParticipacion.PENDIENTE
            jornada = jornadas[0]
        if jornada.actividad_id != self.actividad_id:
            raise ValueError('La jornada no pertenece a esta inscripción.')
        if not jornada.finalizo():
            return EstadoParticipacion.INSCRIPTO
        registro = next((item for item in self.asistencias.all() if item.jornada_id == jornada.pk), None)
        if registro and registro.estado == EstadoAsistencia.PRESENTE:
            return EstadoParticipacion.PARTICIPO
        if registro and registro.estado == EstadoAsistencia.AUSENTE:
            return EstadoParticipacion.AUSENTE
        return EstadoParticipacion.PENDIENTE

    def etiqueta_participacion(self, jornada=None):
        if jornada is None and not self.actividad.esta_cancelada() and self.actividad.jornadas.count() > 1:
            return self.resumen_asistencia()
        return EstadoParticipacion(self.estado_participacion(jornada)).label

    def resumen_asistencia(self):
        # El campo asistencia original se conserva como dato histórico, sin nuevas escrituras.
        registros = list(self.asistencias.all())
        presentes = sum(item.estado == EstadoAsistencia.PRESENTE for item in registros)
        ausentes = sum(item.estado == EstadoAsistencia.AUSENTE for item in registros)
        return f'{presentes} presente(s), {ausentes} ausente(s)'


class JornadaActividad(models.Model):
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE, related_name='jornadas')
    fecha = models.DateField()
    # NULL solo para jornadas migradas cuyo horario se desconoce.
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)

    class Meta:
        ordering = ['fecha', 'pk']
        constraints = [
            models.UniqueConstraint(fields=['actividad', 'fecha'], name='jornada_unica_por_dia'),
            models.CheckConstraint(
                condition=(
                    models.Q(hora_inicio__isnull=True, hora_fin__isnull=True)
                    | models.Q(hora_inicio__isnull=False, hora_fin__isnull=False, hora_fin__gt=models.F('hora_inicio'))
                ), name='jornada_horario_valido',
            ),
        ]

    def __str__(self):
        return self.fecha.strftime('%d/%m/%Y')

    def clean(self):
        if bool(self.hora_inicio) != bool(self.hora_fin):
            raise ValidationError('Completá ambas horas de la jornada.')
        if self.hora_inicio and self.hora_fin <= self.hora_inicio:
            raise ValidationError('La hora de cierre debe ser posterior al inicio, en el mismo día de Asunción.')

    def inicio(self):
        if self.hora_inicio is None:
            return None
        return timezone.make_aware(datetime.combine(self.fecha, self.hora_inicio), timezone.get_default_timezone())

    def cierre(self):
        if self.hora_fin is None:
            # Sin inventar horas históricas: manual disponible después de ese día local.
            return timezone.make_aware(datetime.combine(self.fecha + timedelta(days=1), time.min), timezone.get_default_timezone())
        return timezone.make_aware(datetime.combine(self.fecha, self.hora_fin), timezone.get_default_timezone())

    def finalizo(self):
        return timezone.now() >= self.cierre()

    def esta_activa(self):
        inicio = self.inicio()
        return inicio is not None and inicio <= timezone.now() < self.cierre()


class AsistenciaJornada(models.Model):
    class Origen(models.TextChoices):
        CODIGO = 'codigo', 'Código'
        MANUAL = 'manual', 'Coordinador'
        HISTORICO = 'historico', 'Registro histórico'

    inscripcion = models.ForeignKey(Inscripcion, on_delete=models.PROTECT, related_name='asistencias')
    jornada = models.ForeignKey(JornadaActividad, on_delete=models.PROTECT, related_name='asistencias')
    estado = models.CharField(max_length=20, choices=EstadoAsistencia.choices)
    origen = models.CharField(max_length=20, choices=Origen.choices)
    actualizado_en = models.DateTimeField(null=True, blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['jornada__fecha', 'pk']
        constraints = [
            models.UniqueConstraint(fields=['inscripcion', 'jornada'], name='asistencia_unica_por_jornada'),
            models.CheckConstraint(condition=models.Q(estado__in=['presente', 'ausente']), name='asistencia_estado_resuelto'),
        ]

    def clean(self):
        if self.inscripcion_id and self.jornada_id and self.inscripcion.actividad_id != self.jornada.actividad_id:
            raise ValidationError('La inscripción y la jornada deben pertenecer a la misma actividad.')
