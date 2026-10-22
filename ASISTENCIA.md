# Asistencia por jornada

Las actividades contienen una jornada por fecha de Asunción, Paraguay, con horas
de inicio y cierre dentro de ese día local (`America/Asuncion`). La inscripción
comprende toda la actividad. Los horarios de
días distintos pueden ser diferentes y las fechas no necesitan ser consecutivas.

## Uso

1. Al crear o editar una actividad, cargar su primera fecha y las jornadas.
2. El coordinador creador entra a **Gestionar actividades → Asistencia** para
   consultar el código de la actividad y elegir la jornada.
   Al elegir otra fecha, la pantalla se actualiza automáticamente. Se pueden
   consultar jornadas futuras; solo la carga manual depende de su cierre.
   Si hay marcas sin guardar, se pide confirmación antes de cambiar de jornada.
   **Ver jornada** permite realizar la consulta también sin JavaScript.
   **Ver inscritos** muestra la lista completa de voluntarios, aun si se
   inscribieron fuera del horario de una jornada. La pantalla de asistencia
   distingue el total inscrito de los habilitados para el día seleccionado.
3. Cada voluntario entra a **Detalle y asistencia** e ingresa el código durante
   la jornada: inicio incluido, cierre excluido. Debe confirmar cada día.
4. Al cerrar una jornada, el coordinador puede marcar todos presentes, buscar,
   corregir estados y guardar. El botón incluye también las filas filtradas.

Solo el coordinador creador puede consultar el código y registrar o corregir
asistencia manual. Los superusuarios no tienen acceso adicional en este módulo.
El código nunca se incorpora al HTML del voluntario.

## Integridad

- `AsistenciaJornada` es la fuente de verdad; hay una restricción única por
  inscripción y jornada. `Inscripcion.asistencia` conserva el dato previo a la
  migración y no recibe nuevas escrituras ni alimenta los reportes.
- El código solo crea un presente si aún no existe registro; no reemplaza estados.
- Cada guardado manual compara una versión firmada del horario, inscritos y
  asistencias. Un formulario desactualizado requiere revisión y un nuevo envío.
- Las operaciones del módulo bloquean primero la actividad dentro de una
  transacción, incluyendo inscripción, baja, cancelación y modificación.
- Una inscripción posterior o igual al cierre queda fuera de esa jornada. Los
  registros históricos ya existentes se conservan aunque su inscripción sea posterior.
- No se permite la baja de una inscripción con asistencia ni cambiar la fecha o
  las jornadas de una actividad que ya tenga asistencia registrada.
- Reportes e historial cuentan presentes y ausentes por jornada, sin convertir
  varios días en un único estado global. Los filtros de reporte usan la fecha
  de cada jornada y mantienen el conteo de inscripciones distintas.

## Migración

`0010_asistencia_por_jornada` agrega los modelos, genera un código distinto para
cada actividad y lleva los estados resueltos existentes a una jornada histórica
en la fecha original. No asigna horas, autor ni momento de marcación desconocidos.
Sin horario, el código está deshabilitado y el registro manual se habilita una
vez transcurrido ese día local. Las jornadas históricas sin registros pueden
configurarse desde Editar; las que ya tienen asistencia conservan sus datos.

Aplicar con el entorno y PostgreSQL del proyecto disponibles:

```powershell
.\.venv\Scripts\python.exe -B manage.py migrate
```

La migración de datos es irreversible: regresar a un único estado por inscripción
perdería la asistencia diaria. La recuperación requiere restaurar una copia de la
base anterior. La migración ya se aplicó correctamente a la base local `joaju_db`.

## Entorno local instalado

- PostgreSQL 18.6 y pgAdmin 4 instalados mediante WinGet desde el instalador EDB.
- Servicio de Windows: `postgresql-x64-18`.
- Servidor: `localhost`; puerto: `5433`; base: `joaju_db`; usuario: `postgres`.
- Contraseña: la configurada en `POSTGRES_PASSWORD` o su valor local en
  `joajuweb/settings.py`.
- Zona horaria de la aplicación y predeterminada de la base: `America/Asuncion`.
  Las fechas y horas de jornadas se ingresan e interpretan en horario de Paraguay.
  Al cambiar desde UTC se conservaron, por decisión del usuario, los valores de
  fecha y hora escritos: 08:00–23:59 ahora significa 08:00–23:59 de Asunción.
  Los instantes de inscripción y marcación existentes no se modificaron.
  Django conserva `USE_TZ=True` y utiliza UTC internamente para los instantes.
  El servidor solo escucha en `localhost`.
- Todas las migraciones están aplicadas, incluida `0011_finalizacion_actividad`.
- Las 77 pruebas de backend pasaron con PostgreSQL, incluida la confirmación
  concurrente, los límites de horario local y los listados de inscritos, sin
  omisiones. También pasaron las 10 pruebas de JavaScript, incluidas la selección
  automática de jornada y la protección de marcas sin guardar.

## Cierre de actividades e inscripciones

- Las inscripciones se cierran automáticamente en el instante de cierre de la
  última jornada, utilizando la hora del servidor y `America/Asuncion`. Esto se
  valida en el backend bajo el mismo bloqueo de actividad que las demás
  operaciones. No basta con que la actividad siga publicada o tenga cupo.
- Si quedan jornadas futuras, incluso entre dos jornadas, la inscripción sigue
  abierta. Una actividad sin jornadas no acepta inscripciones.
- El catálogo y el panel de próximas actividades solo ofrecen actividades
  publicadas con al menos una jornada vigente o futura.
- En **Gestionar actividades → Pendientes de cierre**, el coordinador creador
  puede pulsar **Dar por terminada** cuando todas las jornadas hayan terminado.
  La acción exige POST, comprueba propiedad y horarios nuevamente en el backend
  y guarda el estado `finalizada` junto con `finalizada_en`.
- No se adelanta el cierre de jornadas vigentes o futuras. Para interrumpir una
  actividad antes de tiempo se conserva la acción existente de cancelación.
- Las actividades finalizadas aparecen en su propia sección y no se pueden
  editar, cancelar ni volver a publicar. Repetir el cierre no altera su fecha.
  El código ya no permite confirmar asistencia ni se muestra en la pantalla.
- La asistencia manual sigue habilitada para completar y corregir los registros
  diarios de actividades finalizadas, con las validaciones de versiones y
  duplicados existentes. Finalizar no genera presentes ni ausentes automáticos.
- Se conservan las inscripciones, jornadas, asistencias, reportes e historial.
  No se permite eliminar la inscripción una vez terminadas todas las jornadas,
  aunque aún no se haya cargado su asistencia.
- `0011_finalizacion_actividad` agrega el nuevo estado y la fecha de cierre; no
  cierra actividades existentes ni modifica sus horarios o registros históricos.
- Se verificaron en Edge los flujos de cierre, asistencia masiva con búsqueda
  y guardado posterior al cierre, consulta del historial y bloqueo de acciones
  de inscripción. Se comprobaron cuatro pantallas a 1440, 768 y 390 píxeles,
  sin desbordamientos horizontales ni errores de JavaScript. Evidencia en
  `artifacts/ui/cierre/`.

## Verificación

```powershell
.\.venv\Scripts\python.exe -B manage.py check
.\.venv\Scripts\python.exe -B manage.py makemigrations --check --dry-run --settings=joajuweb.test_settings
.\.venv\Scripts\python.exe -B manage.py test --settings=joajuweb.test_settings --noinput
node --test joajuweb/backend/tests/asistencia_ui.test.cjs
node --test joajuweb/backend/tests/jornada_ui.test.cjs
```

`test_settings` usa SQLite en memoria y correo en memoria; no modifica la
configuración normal ni requiere nuevas dependencias. Se verifica también una
actualización real desde la migración 0009 con datos históricos en otra base
aislada. Las pruebas JavaScript verifican la lógica con un DOM de prueba, sin
reemplazar una revisión visual en navegador.

La prueba simultánea de dos confirmaciones se omite con SQLite, que no implementa
bloqueos de fila. Para ejecutarla, usar PostgreSQL como en la última verificación:

```powershell
.\.venv\Scripts\python.exe -B manage.py test --noinput
```
