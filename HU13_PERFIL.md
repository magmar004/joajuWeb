# Resumen de cambios — HU13 (Perfil Ampliado de Voluntario)

## Resumen general

Se implementó el perfil ampliado para los voluntarios en la plataforma JoajuWeb. Ahora los usuarios pueden registrar su biografía ("Sobre mí"), sus habilidades/competencias y sus áreas de interés desde su perfil.

Además, se adaptó la pantalla de perfil para ofrecer una vista de lectura con etiquetas y un modo de edición con sugerencias rápidas de intereses (+ Medio Ambiente, + Educación, etc.).

## Cambios realizados

- **Base de datos y Modelos:** Nuevos campos `biografia`, `habilidades` e `intereses` en el modelo `Usuario` (`models/usuarios.py`) y migración `0012` aplicada con éxito.
- **Formularios:** Actualización de `PerfilForm` (`forms/auth.py`) agregando los nuevos campos y sugerencias interactivas.
- **Interfaz (Frontend):** Ajuste en `templates/perfil.html` para alternar entre modo lectura y modo edición mediante un botón superior.