# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- copia-familiar: este archivo lo instala scripts/copia-familiar/preparar.ps1 -->

Esta es la copia de vacantia de **una persona de la familia**, en su propia computadora y con su propio repo de GitHub. Los comandos, la arquitectura y las convenciones están en `.claude/rules/`.

## Con quién hablás

Con alguien que **no programa**. Usa vacantia para buscar trabajo, y te va a pedir que le expliques cosas o que le cambies algo.

- **Lenguaje:** castellano llano, sin jerga. Si hace falta un término técnico, explicalo en una frase.
- **Antes de tocar código o archivos:** contá en dos o tres líneas qué vas a cambiar y para qué, y **esperá su OK**.
- **Después:** decí qué cambió en la pantalla o en lo que hace, no qué archivo tocaste.
- **Si piden algo que puede romper la búsqueda o gastar plata** (claves, más pedidos por corrida, sacar topes), avisá el riesgo antes.
- **Para que vea un cambio en Python:** decile que cierre la ventana negra de `abrir.bat` y la vuelva a abrir.

## Cómo se guardan los cambios (ramas)

La persona no maneja nada de esto: lo hacés vos.

- **`main` es la versión que funciona.** Nunca edites ni hagas commit directo sobre `main`.
- **Cada pedido es una rama:** desde `main`, `git switch -c cambio/<descripcion-corta>`.
- **Mientras trabajás:** commits chicos con mensajes en castellano que digan qué cambia para la persona.
- **Al terminar:** `.venv\Scripts\python.exe -m pytest tests -q`.
  - **Si pasa:** `git switch main`, `git merge --no-ff cambio/<...>` y `git push`. Las dos cosas piden confirmación: es a propósito.
  - **Si no pasa:** explicá qué falló. Si no se puede arreglar sin riesgo, dejá la rama sin unir y volvé a `main`.
- **Volver atrás un cambio ya unido:** `git revert -m 1 <merge>`. **Nunca** se borra historial: nada de `reset --hard`, `push --force` ni borrar ramas con `-D`.
- **Antes de empezar cualquier pedido:** `git status` tiene que estar limpio. Si hay cambios sueltos, preguntá qué son antes de seguir.

## Lo que no se toca

- **`.env`:** las claves. No se lee ni se edita; se cargan desde la pantalla, en Mi perfil.
- **`state/`:** las ofertas guardadas y lo que la persona marcó. Sólo lo escribe el programa.
- **`scripts/`:** el instalador.
- **`NOTAS-PARA-ISAIAS.md`:** la historia de cómo se construyó el programa. Sirve para consultar por qué algo es como es, pero no se edita. Los cambios de esta copia se documentan en `README.md`.
- **`DESIGN.md`:** las reglas visuales. Si un pedido las contradice, avisalo antes de hacerlo.

## Costos

- **`--dry-run` y "Buscar ahora"** hacen búsquedas de verdad y gastan las claves de la persona (Gemini, TinyFish). No los corras sin permiso.
- **Los tests no gastan nada.** Correlos siempre.
