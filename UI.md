# Distribución visual de Joaju

Se mantienen la paleta, el símbolo de marca, Plus Jakarta Sans, los botones,
bordes redondeados y sombras. Las pantallas usan distribuciones distintas según
la tarea; el contenedor de aplicación llega a 1360 px y conserva márgenes fluidos.

## Pantallas

- Asistencia: resumen y jornada en una columna secundaria, lista y controles en
  la principal. En móvil el resumen es compacto y, al registrar manualmente,
  la lista aparece antes del código complementario. Guardado visible en escritorio.
- Inscritos: listado amplio con datos personales y fecha alineados; conserva el
  mismo buscador.
- Actividades y participación: rejillas de una, dos o tres columnas según el
  ancho; acciones alineadas y publicadas primero en la pantalla de gestión.
- Crear y editar: información general y calendario en paralelo en escritorio;
  las jornadas agrupan fecha y horas en filas compactas.
- Detalle del voluntario: descripción, jornadas y asistencia en el área principal;
  cupos, inscripción y confirmación por código en el área complementaria.
- Perfil: foto y cuenta a un lado, datos personales y contacto al otro, dentro
  del mismo formulario multipart.
- Reportes: métricas arriba, actividades y voluntarios en paralelo y detalle de
  inscripciones a todo el ancho.
- Paneles: accesos en rejilla y bloques de bienvenida con acciones claras. El
  inicio del voluntario presenta los datos de próxima actividad y oportunidades
  que ya proporciona la vista.
- Login, registro, recuperación y estados: anchos apropiados para lectura y
  formularios, espaciado uniforme y adaptación vertical en móvil.
- Navegación: accesos a las rutas existentes según el rol y sección activa visible.

## Implementación

Los cambios de esta etapa son de plantillas, recursos estáticos y documentación.
No se modificaron vistas Python, servicios, modelos, permisos, configuración ni
migraciones. Se conservaron los nombres de campos, acciones de formularios y
selectores que utilizan los scripts existentes.

`static/css/layouts.css` contiene los ajustes, limitados al cuerpo `.joaju-ui`.
Las páginas del admin no heredan esta hoja. Bootstrap 5.3.2, Bootstrap Icons
1.11.1 y la misma tipografía se sirven localmente, con sus licencias en
`static/vendor`, sin necesitar npm para ejecutar Joaju.

Se incorporan foco visible, enlace para saltar al contenido, un título principal
por página, controles y botones de al menos 44 px, saltos de línea para datos
largos y respeto a la preferencia de movimiento reducido. Los contrastes medidos
son 5.22:1 para texto secundario sobre tarjetas, 4.71:1 sobre el panel lila,
7.24:1 para texto del botón principal y 3.37:1 para bordes de entradas.

## Verificación realizada

- 56 pruebas de backend aprobadas con PostgreSQL.
- 4 pruebas JavaScript existentes aprobadas.
- 25 vistas y estados en Edge a 320, 390, 768, 1024 y 1440 px: 125 comprobaciones
  sin desbordamiento horizontal de página, identificadores duplicados, recursos
  fallidos o errores JavaScript. Se verificaron título principal, contenido y
  tamaño de botones.
- 17 comprobaciones de interacción en navegador: búsqueda, marcación masiva con
  filtro, corrección individual, estado sin coincidencias, persistencia, agregar
  jornadas, errores de formulario, privacidad y uso del código, publicación,
  edición, perfil, inscripción, baja, filtros de reportes/catálogo y cierre
  accesible de alertas.
- Revisión visual de capturas de escritorio y móvil con datos sintéticos.
- `manage.py check`, consistencia de migraciones y `git diff --check` correctos.

La previsualización utilizó una base SQLite temporal con datos sintéticos y un
servidor local independiente; no modificó las actividades ni los voluntarios de
la base del proyecto. Playwright se instaló en una carpeta temporal para esta
verificación, fuera del proyecto. Esta revisión se ejecutó en Edge; no reemplaza
una auditoría completa de accesibilidad ni comprobaciones en otros motores.

Comandos de regresión disponibles:

```powershell
.\.venv\Scripts\python.exe -B manage.py test --noinput
node --test joajuweb/backend/tests/asistencia_ui.test.cjs
.\.venv\Scripts\python.exe -B manage.py check
.\.venv\Scripts\python.exe -B manage.py makemigrations --check --dry-run
```

## Evidencias

- [Asistencia en escritorio](artifacts/ui/asistencia-escritorio.png)
- [Asistencia en móvil](artifacts/ui/asistencia-movil.png)
- [Actividades](artifacts/ui/actividades-escritorio.png)
- [Formulario de actividad](artifacts/ui/formulario-escritorio.png)
- [Perfil](artifacts/ui/perfil-escritorio.png)
- [Login](artifacts/ui/login-escritorio.png)
- [Registro de comprobaciones](artifacts/ui/verificacion.json)
