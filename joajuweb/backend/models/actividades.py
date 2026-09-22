# Actividades de voluntariado e inscripciones.
from datetime import date

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


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
    # Borrador = oculta; publicada = visible; cancelada = oculta y notificada.
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

    def se_puede_editar(self):
        return self.estado != EstadoActividad.CANCELADA

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
        return self.fecha <= date.today()

    def se_puede_registrar_asistencia(self):
        return (
            self.esta_publicada()
            and self.ya_finalizo()
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

    def estado_participacion(self):
        if self.actividad.esta_cancelada():
            return EstadoParticipacion.CANCELADA
        if not self.actividad.ya_finalizo():
            return EstadoParticipacion.INSCRIPTO
        if self.asistencia == EstadoAsistencia.PRESENTE:
            return EstadoParticipacion.PARTICIPO
        if self.asistencia == EstadoAsistencia.AUSENTE:
            return EstadoParticipacion.AUSENTE
        return EstadoParticipacion.PENDIENTE

    def etiqueta_participacion(self):
        return EstadoParticipacion(self.estado_participacion()).label
