# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Este es el repo de desarrollo de Isaías. Los comandos, la arquitectura y las convenciones del proyecto están en `.claude/rules/`: `proyecto.md` se carga siempre, y `pantalla.md`, `fuentes.md` y `tests.md` se cargan al tocar esas carpetas.

## Cómo trabaja Isaías

- **Al cerrar un cambio visible, actualizar:**
  - `README.md`: manual de uso y configuración.
  - `NOTAS-PARA-ISAIAS.md`: bitácora con secciones numeradas `2.N`, y el conteo de tests arriba de todo y en el bloque de comandos.
- **Commits:** sólo cuando lo pide.
- **Pruebas en el navegador:** con una copia temporal del repo y un puerto aparte, nunca con los perfiles reales. Al terminar se borra la copia y se cierra la pestaña.

## La copia de cada familiar

Cada familiar recibe una **copia independiente**: su propia carpeta, su propio repo de GitHub y su propio Claude Code. No hay vínculo con este repo: ni reciben actualizaciones ni vuelve nada de ellos.

- **`scripts/copia-familiar/`:** tiene el `CLAUDE.md` y el `.claude/settings.json` que se instalan en esa copia, y `preparar.ps1`, que los pone en su lugar. Acá son archivos sueltos: no configuran nada de este repo.
- **Si cambiás algo de `.claude/rules/`:** también le llega a las copias futuras, así que tiene que servir para las dos.
- **La guía paso a paso** está en `NOTAS-PARA-ISAIAS.md`, sección 2.32.
