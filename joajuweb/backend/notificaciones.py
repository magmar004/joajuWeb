# Avisos por correo a voluntarios inscriptos (en local salen por consola).
from django.conf import settings
from django.core.mail import EmailMessage

from joajuweb.backend.models import Usuario


def notificar_inscriptos(actividad, asunto, cuerpo):
    destinatarios = actividad.emails_inscriptos()
    if not destinatarios:
        return 0
    remitente = getattr(settings, 'DEFAULT_FROM_EMAIL', 'joaju@localhost')
    EmailMessage(asunto, cuerpo, remitente, destinatarios).send(using='default')
    return len(destinatarios)


def avisar_modificacion(actividad, cambios):
    detalle = '\n'.join(f'- {item}' for item in cambios)
    return notificar_inscriptos(
        actividad,
        f'Joaju: se actualizó "{actividad.nombre}"',
        (
            f'Hola,\n\nLa actividad "{actividad.nombre}" en la que estás inscripto cambió:\n\n'
            f'{detalle}\n\n'
            f'Fecha actual: {actividad.fecha.strftime("%d/%m/%Y")}\n'
            f'Cupo: {actividad.cupo}\n\n'
            'Saludos,\nJoaju'
        ),
    )


def avisar_cancelacion(actividad):
    return notificar_inscriptos(
        actividad,
        f'Joaju: se canceló "{actividad.nombre}"',
        (
            f'Hola,\n\nLa actividad "{actividad.nombre}" del '
            f'{actividad.fecha.strftime("%d/%m/%Y")} fue cancelada.\n\n'
            'Saludos,\nJoaju'
        ),
    )


def avisar_actividad_publicada(actividad):
    if not actividad.esta_publicada() or not actividad.tipo:
        return 0
    destinatarios = list(
        Usuario.objects.filter(
            roles__nombre__iexact='Voluntario',
            recibir_avisos_actividades=True,
            intereses_actividad__codigo=actividad.tipo,
        )
        .exclude(email__isnull=True)
        .exclude(email='')
        .values_list('email', flat=True)
        .distinct()
    )
    if not destinatarios:
        return 0

    lugar = actividad.get_ubicacion_completa()
    cuerpo = (
        f'Hola,\n\nSe publicó una nueva actividad de la temática '
        f'{actividad.get_tipo_display()} que coincide con tus intereses:\n\n'
        f'{actividad.nombre}\n'
        f'Fecha: {actividad.fecha:%d/%m/%Y}\n'
        f'Lugar: {lugar}\n\n'
        f'{actividad.descripcion}\n\n'
        'Ingresá a Joaju para ver los detalles e inscribirte.\n\n'
        'Recibís este aviso porque activaste las notificaciones de actividades '
        'según tus intereses. Podés desactivarlas desde tu perfil.\n\n'
        'Saludos,\nJoaju'
    )
    mensaje = EmailMessage(
        f'Joaju: nueva actividad de {actividad.get_tipo_display()}',
        cuerpo,
        getattr(settings, 'DEFAULT_FROM_EMAIL', 'joaju@localhost'),
        bcc=destinatarios,
    )
    return len(destinatarios) if mensaje.send(using='default', fail_silently=True) else 0
