# Recursos estáticos existentes, servidos localmente

Se conserva la misma biblioteca, versión y tipografía que ya usaba Joaju.
No se requiere npm para ejecutar la aplicación.

| Recurso | Versión / origen | Licencia |
| --- | --- | --- |
| Bootstrap | 5.3.2, paquete npm `bootstrap` | MIT, `bootstrap/LICENSE` |
| Bootstrap Icons | 1.11.1, paquete npm `bootstrap-icons` | MIT, `bootstrap-icons/LICENSE.md` |
| Plus Jakarta Sans | Paquete `@fontsource/plus-jakarta-sans` 5.3.0; pesos 400, 500, 600, 700; Latin y Latin Extended | SIL Open Font License, `plus-jakarta-sans/LICENSE` |

Los archivos minificados de Bootstrap e iconos se conservan sin modificaciones.
La hoja de fuentes conserva las declaraciones del paquete y omite el formato
WOFF para servir los archivos WOFF2 incluidos. Las licencias originales están
adjuntas. Estos recursos reemplazan sus enlaces remotos en `templates/base.html`.
