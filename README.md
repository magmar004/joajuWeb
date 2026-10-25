# Joaju — Plataforma de gestión de actividades de voluntariado

## 1. Nombre y descripción

Joaju es una aplicación web para publicar y administrar actividades de voluntariado, permitir que las personas voluntarias las exploren e inscriban y registrar su participación y asistencia por jornada. Está desarrollada con Django y utiliza PostgreSQL en la configuración normal.

## 2. Funcionalidades principales

### Sitio público

- La ruta `/` muestra la página pública a visitantes y redirige a las personas autenticadas a su panel según el rol.
- `/inicio/` muestra el catálogo público de actividades publicadas y vigentes, con búsqueda por texto y filtros por temática, departamento y ciudad.
- Se puede consultar el detalle público de una actividad sin iniciar sesión. La inscripción requiere autenticación.
- Las tarjetas y los detalles muestran la fotografía de la actividad si existe; en caso contrario usan una presentación visual alternativa.
- `/ayuda/` contiene artículos estáticos desplegables y una búsqueda en el navegador.

### Voluntarios

- Consultar actividades, filtrar y buscar en el catálogo completo.
- Inscribirse o cancelar una inscripción mientras las reglas de cupo y vigencia lo permitan.
- Consultar próximas actividades, historial y recomendaciones basadas en los intereses elegidos.
- Confirmar asistencia con el código de la actividad durante una jornada habilitada. La asistencia se registra por jornada.
- Completar el perfil con foto, biografía, habilidades e intereses; elegir si se desean avisos por correo de actividades relacionadas con los intereses.

### Coordinadores

- Crear actividades como borrador o publicarlas; editar y administrar las actividades propias.
- Definir tipo, departamento, ciudad, ubicación, cupo, fechas y jornadas con horario. Se puede adjuntar una imagen opcional.
- Consultar inscriptos, registrar asistencia manual por jornada y consultar el código que los voluntarios utilizan para confirmar presencia.
- Cancelar una actividad publicada o marcarla como finalizada una vez que terminaron sus jornadas. El historial y los registros de asistencia se conservan.
- Consultar reportes por fechas y tipo, con totales de inscripciones y asistencia. Al seleccionar una actividad, el reporte presenta gráficos de ocupación y asistencia.

### Otros flujos

- Registro, inicio y cierre de sesión, y restablecimiento de contraseña mediante las vistas de autenticación de Django.
- Búsqueda de voluntarios, actividades e historial en las pantallas donde está implementada.

## 3. Roles y permisos reales

Joaju almacena sus roles en el modelo propio `Rol`, relacionado con `Usuario`. Los nombres utilizados por el código son `Voluntario` y `Coordinador`. Este modelo es distinto de los grupos y permisos estándar de Django.

| Acción | Permiso aplicado |
|---|---|
| Ver inicio, ayuda y detalles públicos de actividades vigentes | No requiere iniciar sesión. |
| Inscribirse, cancelar inscripción o ver historial propio | Requiere sesión; la inscripción está destinada a voluntarios. Los coordinadores no pueden inscribirse como voluntarios. |
| Crear o administrar actividades | Requiere sesión y rol coordinador. Las acciones sobre una actividad se limitan además a su creador. |
| Gestionar inscriptos y asistencia | Requiere sesión, rol coordinador y propiedad de la actividad en las acciones correspondientes. |
| Ver panel y reportes de coordinador | Requiere sesión y rol coordinador. |
| Consultar el historial de otra persona | Un coordinador puede consultarlo si existe una inscripción de esa persona en una actividad que creó. |
| Editar el perfil | Requiere sesión y afecta el perfil propio. |

Las vistas usan `login_required` y comprobaciones del rol. Varias operaciones sensibles también vuelven a comprobar propiedad y estado en `servicios.py`; los cierres, inscripciones y registros de asistencia usan transacciones y bloqueos de fila donde están disponibles.

Un superusuario de Django no obtiene automáticamente el rol funcional `Coordinador` ni propiedad sobre actividades. El código aplica las comprobaciones de rol y creador de actividad.

## 4. Tecnologías y versiones verificadas

| Componente | Versión o configuración |
|---|---|
| Python | 3.12.15 en el entorno de desarrollo. |
| Django | 6.1.1, fijado en `requirements.txt`. |
| PostgreSQL | Backend configurado. `ASISTENCIA.md` indica PostgreSQL 18.6 para el entorno local. |
| psycopg | 3.3.5, dependencia fijada. |
| Pillow | 11.3.0, dependencia fijada para los campos de imagen. |
| Bootstrap | 5.3.2, archivos locales según `static/vendor/README.md`. |
| Bootstrap Icons | 1.11.1, archivos locales. |
| Plus Jakarta Sans | Recursos locales; `static/vendor/README.md` identifica Fontsource 5.3.0. |
| Pruebas JavaScript | Dos archivos CommonJS que usan el módulo integrado `node:test`; no requieren un framework de frontend. |

El frontend utiliza plantillas Django, CSS y JavaScript. No hay `package.json` ni un framework JavaScript de interfaz. Los gráficos de los reportes se implementan con CSS y JavaScript, sin una biblioteca de gráficos externa identificada.

## 5. Arquitectura

El proyecto utiliza el patrón **Model–View–Template (MVT)** de Django. Las vistas reciben solicitudes HTTP, validan permisos y formularios, usan modelos y servicios de negocio y renderizan plantillas HTML. Los formularios están separados de los modelos y las vistas se dividen por área funcional.

`joajuweb.backend.apps.BackendConfig` registra el paquete `joajuweb.backend` con la etiqueta de aplicación `usuarios`. Esta etiqueta se utiliza en `AUTH_USER_MODEL` y en las dependencias de las migraciones.

Flujo simplificado:

```text
Navegador
   │ HTTP
   ▼
joajuweb/urls.py ──► backend/urls.py
                          │
                          ▼
                  backend/views/*
                    │          │
              forms/*     servicios.py
                    │          │
                    └────┬─────┘
                         ▼
                models/* y ORM Django
                         │
                         ▼
                    PostgreSQL
                         │
                         ▼
              templates/ + static/
```

La ruta raíz se declara como `home_view`; la aplicación incluye `/admin/` de Django y las rutas de negocio bajo el URLconf de `backend`.

## 6. Estructura del proyecto

```text
proyecto/
├── manage.py
├── requirements.txt
├── joajuweb/
│   ├── settings.py
│   ├── test_settings.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── backend/
│   │   ├── apps.py
│   │   ├── forms/
│   │   ├── models/
│   │   ├── views/
│   │   ├── servicios.py
│   │   ├── notificaciones.py
│   │   ├── urls.py
│   │   ├── migrations/
│   │   └── tests/
│   ├── templates/
│   │   ├── auth/
│   │   ├── coordinador/
│   │   ├── includes/
│   │   ├── publico/
│   │   ├── voluntario/
│   │   └── base.html
│   └── static/
│       ├── css/
│       ├── js/
│       └── vendor/
├── media/                 # archivos cargados; ignorado por Git
├── artifacts/ui/          # capturas y resultados visuales existentes
├── ASISTENCIA.md
├── HU13_PERFIL.md
├── RESUMEN_CAMBIOS_SESION.md
└── UI.md
```

Responsabilidad de archivos y paquetes principales:

- `joajuweb/settings.py`: configuración general, base de datos, autenticación, archivos estáticos y multimedia, zona horaria y correo.
- `joajuweb/test_settings.py`: configuración prevista para pruebas aisladas con SQLite en memoria; ver limitación en [Pruebas](#12-pruebas-comandos-y-limitaciones-conocidas).
- `joajuweb/backend/models/usuarios.py`: `Usuario`, `Rol` y `TipoInteresActividad`.
- `joajuweb/backend/models/actividades.py`: actividad, inscripción, jornadas y asistencias.
- `joajuweb/backend/forms/`: formularios de autenticación, perfil, actividades y jornadas.
- `joajuweb/backend/views/`: vistas de autenticación, actividad, historial, perfil y reportes.
- `joajuweb/backend/servicios.py`: reglas de negocio, autorización por propietario, inscripción, asistencia, reportes, filtros y recomendaciones.
- `joajuweb/backend/notificaciones.py`: mensajes de correo por cambios/publicación.
- `joajuweb/backend/migrations/`: migraciones `0001` a `0016`.
- `joajuweb/templates/`: páginas HTML y componentes reutilizados.
- `joajuweb/static/css/` y `joajuweb/static/js/`: estilos e interacciones de frontend.
- `joajuweb/static/vendor/`: Bootstrap, Bootstrap Icons, fuentes y licencias correspondientes.
- `joajuweb/backend/tests/`: pruebas del backend y de JavaScript.

## 7. Requisitos previos y versiones verificadas

1. Python 3.12 o una versión compatible con Django 6.1.1. El entorno de desarrollo utiliza Python 3.12.15.
2. PostgreSQL instalado y en ejecución, con una base de datos creada. La conexión debe coincidir con los valores configurados en `settings.py` o con las variables `POSTGRES_*`.
3. Git para clonar y actualizar el repositorio.
4. Node.js únicamente para ejecutar las pruebas JavaScript de `node:test`; no es necesario para ejecutar la aplicación web.

La versión de PostgreSQL puede variar según la instalación. Confirmá que el servicio local use la versión y el puerto configurados para tu entorno.

## 8. Instalación y configuración paso a paso

Los ejemplos siguientes usan PowerShell en Windows, acorde con los archivos y el entorno local revisados.

### 8.1 Crear y activar un entorno virtual

Desde la raíz del repositorio:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 8.2 Instalar dependencias

```powershell
python -m pip install -r requirements.txt
```

### 8.3 Configurar PostgreSQL

El servicio y la base deben estar disponibles antes de migrar. En `settings.py`, los valores predeterminados son:

- Base: `joaju_db`
- Usuario: `postgres`
- Host: `localhost`
- Puerto: `5432`

La guía existente `ASISTENCIA.md` documenta el servicio local en el puerto `5433`; por eso, confirmá el puerto real y definí la variable correspondiente. El archivo `.env` está ignorado por Git, pero `settings.py` no lo carga automáticamente: Django lee estas opciones desde el entorno del proceso.

Ejemplo de variables temporales para una sesión de PowerShell (reemplazá el marcador de contraseña por un valor local; no lo guardes en Git):

```powershell
$env:POSTGRES_DB = "joaju_db"
$env:POSTGRES_USER = "postgres"
$env:POSTGRES_PASSWORD = "<contraseña local de PostgreSQL>"
$env:POSTGRES_HOST = "localhost"
$env:POSTGRES_PORT = "5433"
```

Usá `5433` solo si ése es el puerto configurado para tu servidor; si utilizás el puerto predeterminado de PostgreSQL, definí `5432` o quitá `POSTGRES_PORT`.

### 8.4 Aplicar las migraciones y ejecutar

```powershell
python manage.py migrate
python manage.py runserver
```

`migrate` necesita que la base indicada exista y que el servidor acepte la conexión. No es necesario crear una base SQLite para el uso normal; SQLite aparece solamente en la configuración prevista para pruebas.

## 9. Base de datos, migraciones y superusuario

El modelo de usuario está configurado mediante `AUTH_USER_MODEL = 'usuarios.Usuario'`. Las entidades principales son:

- `Usuario`, `Rol`, `TipoInteresActividad`
- `Actividad`, `Inscripcion`, `JornadaActividad`, `AsistenciaJornada`

Relaciones y restricciones relevantes:

- Usuario–rol y usuario–interés son relaciones muchos-a-muchos.
- Actividad tiene un creador (`Usuario`) y puede tener inscripciones y jornadas.
- Inscripción une actividad y voluntario; existe unicidad actividad-voluntario.
- Jornada pertenece a una actividad; la fecha es única por actividad y las horas se validan.
- AsistenciaJornada relaciona inscripción y jornada; existe unicidad inscripción-jornada y el estado guardado debe ser presente o ausente.
- El código de asistencia de actividad es único.

Las migraciones cubren el esquema inicial, roles, actividades e inscripciones, tipos y ubicaciones, foto de perfil, asistencia por jornada, finalización, perfil ampliado, imagen de actividad, departamento/ciudad, intereses estructurados y preferencia de avisos (`0001`–`0016`). `0010_asistencia_por_jornada` migra registros históricos al modelo por jornada; `0015_intereses_estructurados` crea el catálogo y mapea términos reconocidos del campo de texto existente; `0016_usuario_recibir_avisos_actividades` agrega la preferencia booleana.

Comandos de administración:

```powershell
python manage.py showmigrations
python manage.py migrate
python manage.py createsuperuser
```

`showmigrations` solo consulta el estado; `migrate` modifica el esquema y los datos según las migraciones. No ejecutes este último contra una base con datos importantes sin tener respaldo y confirmar la conexión.

`createsuperuser` crea una cuenta administrativa de Django, pero no asigna automáticamente un `Rol` de Joaju. Los paneles funcionales comprueban la relación con `Rol`; una cuenta de superusuario no se convierte automáticamente en coordinador. El repositorio no contiene un `admin.py` de la aplicación que registre explícitamente todos los modelos de Joaju en el admin.

En la base configurada durante esta revisión, `showmigrations` mostró todas las migraciones aplicadas. Esto describe ese entorno concreto; una instalación nueva todavía debe ejecutar `migrate`.

## 10. Ejecución local y URL

Con el entorno virtual activado, PostgreSQL configurado y las migraciones aplicadas:

```powershell
python manage.py runserver
```

Abrí <http://127.0.0.1:8000/>. La ruta `/` presenta la página pública a visitantes y redirige a usuarios autenticados al panel de su rol. `/inicio/` muestra el catálogo público incluso para usuarios autenticados.

### Rutas principales

| Ruta | Acceso y propósito |
|---|---|
| `/` | Inicio público para visitantes; redirige usuarios autenticados según su rol. |
| `/inicio/` | Catálogo público de actividades. |
| `/actividades/<id>/` | Detalle público de una actividad vigente. |
| `/ayuda/` | Centro de ayuda estático. |
| `/registro/`, `/login/`, `/logout/` | Registro y autenticación. |
| `/reset_password/`, `/reset_password_sent/`, `/reset/<uid>/<token>/`, `/reset_password_complete/` | Restablecimiento de contraseña. |
| `/perfil/` | Perfil del usuario autenticado. |
| `/voluntario/` | Panel del voluntario. Bajo esta ruta también están historial, catálogo, detalle, inscripción, baja y confirmación de asistencia. |
| `/coordinador/` | Panel del coordinador. Bajo esta ruta están publicación, gestión, edición, inscriptos, participación, asistencia, reportes, cancelación y finalización. |
| `/admin/` | Sitio de administración de Django. |

## 11. Archivos multimedia y estáticos

La configuración actual define:

- `STATIC_URL = 'static/'`
- `STATICFILES_DIRS = [JOAJUWEB_DIR / 'static']`
- `MEDIA_URL = '/media/'`
- `MEDIA_ROOT = BASE_DIR / 'media'`

Las imágenes cargadas se guardan en el almacenamiento local de Django: `perfiles/` y `actividades/` bajo `MEDIA_ROOT`. El URLconf añade el servicio de archivos multimedia durante desarrollo cuando `DEBUG` está activo. Esto no es una estrategia de entrega de multimedia para producción.

Los CSS, scripts, Bootstrap, iconos y fuentes están versionados bajo `joajuweb/static/`. `STATIC_ROOT` y el almacenamiento de archivos estáticos y multimedia para producción deben configurarse según el entorno de despliegue. La carpeta `media/` está excluida por `.gitignore`.

## 12. Pruebas, comandos y limitaciones conocidas

### Comandos previstos por la documentación

Comprobación de configuración:

```powershell
python -B manage.py check
```

El comando de pruebas backend documentado es:

```powershell
python -B manage.py test --settings=joajuweb.test_settings --noinput
```

En la copia inspeccionada ese comando actualmente se detiene antes de descubrir pruebas: `test_settings.py` define `MAILERS`, mientras que importa el `EMAIL_BACKEND` de `settings.py`. Django 6.1.1 informa que no permite ambos ajustes de correo. La configuración de pruebas debe corregirse antes de considerar ese comando reproducible.

Las pruebas de JavaScript se ejecutan con Node.js:

```powershell
node --test joajuweb/backend/tests/asistencia_ui.test.cjs
node --test joajuweb/backend/tests/jornada_ui.test.cjs
```

Las pruebas JavaScript requieren Node.js.

### Pruebas incluidas

- `test_publico.py`: página pública, visibilidad de actividades, acceso a detalles y restricción de inscripción sin sesión.
- `test_actividad_imagen.py`: formatos y tamaño de imagen, creación y reemplazo de foto.
- `test_asistencia.py`: permisos, códigos, asistencia, inscripciones, concurrencia lógica, reportes y reglas horarias.
- `test_concurrencia_asistencia.py`: confirmaciones simultáneas; depende de soporte de bloqueo de filas.
- `test_finalizacion.py`: cierre, límites horarios e historial.
- `test_migracion_asistencia.py`: migración de asistencias históricas.
- `asistencia_ui.test.cjs` y `jornada_ui.test.cjs`: búsqueda/marcación masiva y selección de jornadas en scripts de interfaz.

### Estado de las pruebas y cobertura pendiente

En una ejecución aislada de 85 pruebas backend con SQLite en memoria y correo en memoria, 83 pasaron, una falló y una se omitió. Se excluyó `test_migracion_asistencia.py` porque inicia un subproceso que vuelve a cargar la configuración `test_settings.py`. La prueba fallida, `test_inicio_publico_muestra_actividades_vigentes_y_busca_por_nombre`, espera búsqueda solo por nombre, pero el servicio también busca en descripción, ubicación, ciudad y departamento. Debe resolverse esa discrepancia entre el comportamiento y la aserción de la prueba.

La prueba de concurrencia se omite con SQLite porque no implementa `SELECT FOR UPDATE`; su comportamiento requiere una ejecución con PostgreSQL. Faltan pruebas específicas para avisos por intereses, recomendaciones, búsqueda del centro de ayuda y selección de los gráficos del reporte. No hay una medición de cobertura configurada.

`makemigrations --check --dry-run` no detectó diferencias entre modelos y migraciones en el entorno de desarrollo. La base de datos local tiene aplicadas las migraciones vigentes.

## 13. Configuración actual del correo

`settings.py` configura:

```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'Joaju <joaju@localhost>'
```

Con el backend de consola, los correos de restablecimiento de contraseña y avisos se escriben en la salida del proceso de desarrollo; no se entregan por un servidor SMTP. `notificaciones.py` selecciona voluntarios que habilitaron avisos y cuyos intereses coinciden con el tipo de actividad. La función de envío usa `fail_silently=True`, por lo que una falla de envío no necesariamente resulta visible para el usuario.

Para un despliegue real se necesita configurar un backend de correo y una dirección de remitente válidos fuera del backend de consola. Esa integración no está configurada en el repositorio.

## 14. Seguridad y preparación para producción

La configuración actual está preparada para desarrollo, no para producción:

- `DEBUG=True`.
- `ALLOWED_HOSTS=[]`.
- `SECRET_KEY` está definida en el código, no leída de una variable de entorno.
- `settings.py` incluye valores de respaldo para conectarse a PostgreSQL y una clave de desarrollo; deben reemplazarse mediante configuración segura antes de publicar.
- No está configurado HTTPS obligatorio, cookies seguras, almacenamiento cloud ni entrega de archivos estáticos/media para producción.
- El correo usa backend de consola.

Antes de publicar el sistema, reemplazá los valores de desarrollo por configuración segura externa, desactivá `DEBUG`, definí `ALLOWED_HOSTS`, usá secretos fuera del repositorio, configurá PostgreSQL y correo de producción y elegí un mecanismo apropiado para archivos estáticos y multimedia. La lista no reemplaza la revisión completa de despliegue y seguridad de Django.

## 15. Documentación complementaria

- [ASISTENCIA.md](ASISTENCIA.md): asistencia por jornada, operación y reglas de cierre.
- [HU13_PERFIL.md](HU13_PERFIL.md): perfil ampliado e intereses.
- [UI.md](UI.md): distribución visual y verificaciones documentadas.
- [RESUMEN_CAMBIOS_SESION.md](RESUMEN_CAMBIOS_SESION.md): resumen de una sesión anterior.
- [requirements.txt](requirements.txt): dependencias Python.
- [joajuweb/settings.py](joajuweb/settings.py): configuración de ejecución.
- [joajuweb/test_settings.py](joajuweb/test_settings.py): configuración aislada prevista para pruebas.
- [static/vendor/README.md](joajuweb/static/vendor/README.md): versiones y licencias de recursos locales.
- [Capturas de interfaz](artifacts/ui/): evidencia visual existente.

## 16. Estado y limitaciones conocidas

- La configuración normal utiliza PostgreSQL en `settings.py`; `test_settings.py` cambia a SQLite en memoria, pero el ajuste de correo `MAILERS` hace que Django 6.1.1 rechace la configuración.
- El puerto predeterminado del código es 5432, mientras `ASISTENCIA.md` documenta 5433 para el entorno local. Confirmá cuál corresponde al servicio en uso.
- Una prueba pública espera búsqueda por nombre únicamente, pero el servicio también busca en descripción y ubicación; el criterio funcional y la prueba no coinciden.
- El catálogo público y las pantallas de participación no tienen paginación; las listas grandes pueden requerirla.
- Los avisos por correo están implementados, pero el backend actual es de consola y no realiza entregas externas.
- Una base de datos nueva debe inicializarse ejecutando las migraciones.
