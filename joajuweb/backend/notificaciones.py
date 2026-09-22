# Avisos por correo a voluntarios inscriptos (en local salen por consola).
from django.conf import settings
from django.core.mail import EmailMessage


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
