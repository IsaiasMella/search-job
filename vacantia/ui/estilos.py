"""La hoja de estilos. **El CSS vive en `css/*.css`, no acá.**

Este módulo es sólo el cargador: junta los archivos en el orden correcto y le
pega adelante las `@font-face`, que son lo único que se genera desde Python
porque dependen de qué archivos hay en disco.

Hasta hace poco las 1500 líneas de CSS eran strings de Python. Escribir CSS
adentro de comillas significa no tener resaltado, ni autocompletado, ni linter,
ni forma de que el editor te avise que te comiste una llave. Era la mitad de la
razón por la que tocar la pantalla se sentía peor de lo que es.

Se lee de disco **en cada pedido**, no una vez al importar. Editás un `.css`,
apretás F5 y lo ves: no hay que reiniciar el servidor. Son 75 KB leídos de un
disco local para una app que usan tres personas en la misma máquina.

Tres cosas que conviene tener presentes antes de tocar nada:

* **Un solo tema, oscuro.** La app se usa en escritorio, la usan cinco
  personas, y duplicar la paleta sólo agrega superficie de error. No hay
  `prefers-color-scheme: light` y no se agrega uno con `filter: invert`.
* **El vidrio esmerilado se gasta en tres lugares y nada más:** la barra
  lateral, las tarjetas de oferta sin marcar y el cartel de novedades. Una
  tarjeta de métrica con vidrio y una tarjeta de oferta con vidrio se ven
  iguales y destruyen la jerarquía.
* **El índigo conduce la interacción y no decora.** Si algo es índigo, se
  puede tocar. Nada de títulos, íconos ni bordes índigo por gusto.

`DESIGN.md` manda sobre todo esto: los tokens del front matter salen como
variables CSS en `css/tokens.css`, y **ninguna regla escribe un color, un
espacio o un radio sueltos**. Si un componente necesita un valor que no está,
se agrega como token; no se improvisa abajo.
"""

from pathlib import Path

#: Dónde busca las fuentes propias. Si los archivos no están, el CSS ni
#: siquiera declara las `@font-face` y todo cae en la pila del sistema, que es
#: lo que se ve hoy. **Nunca se llama a un CDN**: la app corre en una máquina
#: que puede estar sin internet, y una fuente que tarda 3 segundos en llegar es
#: una pantalla que parpadea al abrir.
FUENTES_DIR = Path(__file__).parent / "fuentes"

#: (archivo, familia, peso). Inter en tres pesos porque la escala usa 400, 500
#: y 600, y pedirle al navegador que engorde un 400 a 600 lo emborrona.
FUENTES = (
    ("Inter-Regular.woff2", "Inter", "400"),
    ("Inter-Medium.woff2", "Inter", "500"),
    ("Inter-SemiBold.woff2", "Inter", "600"),
    ("JetBrainsMono-Regular.woff2", "JetBrains Mono", "400"),
)

#: Dónde están los archivos de estilos.
CSS_DIR = Path(__file__).parent / "css"

#: El orden en que se concatenan, que es el orden en que se leen y también el
#: orden en que mandan: tokens primero (los define), después base (elementos
#: sueltos), shell (el marco), controles (botones y campos), piezas (los
#: componentes) y al final las dos pantallas con reglas propias.
#:
#: **El orden importa de verdad**: una regla de `piezas` que pise a una de
#: `controles` depende de estar después. No los reordenes por prolijidad.
ORDEN = ("tokens", "base", "shell", "controles", "piezas", "graficos", "linkedin")


def _font_faces() -> str:
    """Las `@font-face` de las fuentes que de verdad están en disco."""
    reglas = []
    for archivo, familia, peso in FUENTES:
        if not (FUENTES_DIR / archivo).exists():
            continue
        reglas.append(
            f"@font-face {{ font-family: '{familia}'; font-weight: {peso};\n"
            f"  font-style: normal; font-display: swap;\n"
            f"  src: url('/fuentes/{archivo}') format('woff2'); }}"
        )
    return "\n".join(reglas)


def bloque(nombre: str) -> str:
    """Un archivo de `css/`, tal cual está en disco.

    Se lee en binario y se decodifica a mano: `Path.read_text()` en Windows
    traduce los finales de línea y el contenido dejaría de ser byte por byte el
    que se escribió.
    """
    return (CSS_DIR / f"{nombre}.css").read_bytes().decode("utf-8")


def hoja() -> str:
    """La hoja completa, recién leída del disco.

    Se sirve como archivo aparte en `/estilos.css` y no embebida en el `<head>`:
    así el navegador la cachea entre pantallas, y sobre todo se la puede abrir
    en las herramientas del navegador como lo que es, un archivo de CSS.
    """
    return "\n".join((_font_faces(), *(bloque(n) for n in ORDEN)))


def __getattr__(nombre: str) -> str:
    """`estilos.CSS`, `estilos.TOKENS`, `estilos.PIEZAS`... siguen andando.

    Son los nombres que usaban los tests y `render` cuando el CSS era un string
    de Python. Ahora leen el archivo en el momento, así que además de no romper
    nada, un test que mira el CSS mira el que está en disco ahora mismo y no el
    que había cuando se importó el módulo.
    """
    if nombre == "CSS":
        return hoja()
    if nombre.lower() in ORDEN:
        return bloque(nombre.lower())
    raise AttributeError(f"module {__name__!r} no tiene {nombre!r}")
