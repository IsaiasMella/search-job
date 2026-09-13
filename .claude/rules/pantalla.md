---
paths:
  - "vacantia/ui/**"
---

# La pantalla

## `DESIGN.md` manda

- **Tokens:** viven en `css/tokens.css`. Ninguna regla escribe un color, un espacio o un radio sueltos.
- **Tema:** oscuro, uno solo.
- **Índigo:** sólo en lo que se puede tocar. Un solo botón primario por pantalla.
- **Colores con significado:**
  - Verde: lo que ya hiciste.
  - Rojo: errores y acciones destructivas. Un test lo controla con una lista de excepciones.
  - Azul: estado del sistema.
- **Vidrio esmerilado:** sólo en tres lugares: barra lateral, tarjeta de oferta sin marcar y toast.
- **Tarjeta de oferta:** dos controles visibles como máximo.
- **Explicaciones largas:** van en el signo de pregunta con globo (`_ayuda_al_lado` en `render.py`), no sueltas en la pantalla.

## Cosas que ya se aprendieron

- **Confirmar antes de borrar:** la confirmación se abre en el lugar (`<details>` con `button.peligro`), no con un cartel del navegador.
- **Enter en un formulario:** manda el formulario con el primer botón de envío que haya. Por eso Mi perfil tiene un botón invisible de "Guardar cambios" al principio.
- **Globos del signo de pregunta:** los que están adentro de una columna que scrollea abren hacia abajo (`abajo=True`), porque hacia arriba la columna los corta.

## Tests

Muchos tests afirman fragmentos exactos de HTML y de CSS. Si cambiás el marcado, revisá `tests/test_ui.py`, `tests/test_linkedin_urls.py` y `tests/test_varios_cv.py`.
