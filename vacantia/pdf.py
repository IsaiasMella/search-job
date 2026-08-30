"""El CV en PDF, para el botón de descarga de la pestaña Trabajos.

Nada de "apretá Ctrl+P y elegí Guardar como PDF": un botón y listo. El usuario
más difícil de este sistema tiene 62 años.

⚠️ La trampa de fpdf2, documentada en la sección 10 de COSTOS.md y verificada
ahí: las fuentes que trae por defecto son latin-1 y **explotan** con el guion
largo (—), las comillas tipográficas y el símbolo de euro, que aparecen todo el
tiempo en un CV:

    FPDFUnicodeEncodingException: Character "—" ... outside the range of
    characters supported by the font

Por eso lo primero que hace `cv_a_pdf` es registrar una fuente Unicode del
sistema (Arial, Calibri, Segoe UI o Times en Windows; DejaVu en Linux). Si no
encontrara ninguna, avisa y sanea el texto en vez de reventar: es preferible un
PDF con un guion común a no tener PDF.
"""

import re
import unicodedata
from pathlib import Path

from vacantia.log import get_logger

logger = get_logger()

#: Familias a probar, en orden. Cada una es (regular, negrita). Están todas en
#: cualquier Windows; las dos últimas son para Linux/macOS por si algún día
#: corre ahí.
FAMILIAS = (
    ("arial.ttf", "arialbd.ttf"),
    ("calibri.ttf", "calibrib.ttf"),
    ("segoeui.ttf", "segoeuib.ttf"),
    ("times.ttf", "timesbd.ttf"),
    ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
    ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"),
)

DIRECTORIOS = (
    Path(r"C:\Windows\Fonts"),
    Path.home() / "AppData/Local/Microsoft/Windows/Fonts",
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype/liberation"),
    Path("/Library/Fonts"),
    Path("/System/Library/Fonts/Supplemental"),
)

#: Reemplazos para el caso sin fuente Unicode. Sólo los caracteres que rompen
#: latin-1 y que de verdad aparecen en un CV.
_REEMPLAZOS = {
    "—": "-", "–": "-", "‑": "-", "“": '"', "”": '"', "‘": "'", "’": "'",
    "€": "EUR", "•": "-", "…": "...", "→": "->", "™": "(TM)", "©": "(c)",
}


def buscar_fuente() -> tuple[Path, Path] | None:
    """(regular, negrita) de la primera familia Unicode que esté instalada."""
    for regular, negrita in FAMILIAS:
        for carpeta in DIRECTORIOS:
            ruta = carpeta / regular
            if ruta.exists():
                ruta_b = carpeta / negrita
                return ruta, (ruta_b if ruta_b.exists() else ruta)
    return None


def _sanear(texto: str) -> str:
    """Último recurso: saca lo que latin-1 no soporta sin perder legibilidad."""
    for malo, bueno in _REEMPLAZOS.items():
        texto = texto.replace(malo, bueno)
    return "".join(c for c in texto if unicodedata.category(c) != "Cc" or c == "\n")


# --- lectura del Markdown ---------------------------------------------------

_ENFASIS_RE = re.compile(r"(\*\*|__|\*|_|`)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_VINETA_RE = re.compile(r"^\s*([-*+•]|\d+[.)])\s+")


def _limpiar(linea: str) -> str:
    """Saca la sintaxis de Markdown dejando el texto. `[Ana](mailto:x)` -> `Ana`."""
    linea = _LINK_RE.sub(r"\1", linea)
    return _ENFASIS_RE.sub("", linea).rstrip()


def analizar(markdown: str) -> list[tuple[str, str]]:
    """El CV como [(tipo, texto)] — tipo: h1 | h2 | vineta | parrafo | linea.

    No es un parser de Markdown: es lo justo para que un CV se vea como un CV.
    Lo que no reconoce, lo escribe como párrafo, que es el peor caso aceptable.
    """
    bloques: list[tuple[str, str]] = []
    for cruda in (markdown or "").splitlines():
        linea = cruda.rstrip()
        if not linea.strip():
            continue
        if set(linea.strip()) <= {"-", "_", "*", "="} and len(linea.strip()) >= 3:
            bloques.append(("linea", ""))
            continue
        if linea.lstrip().startswith("#"):
            nivel = len(linea) - len(linea.lstrip("#").lstrip())
            texto = _limpiar(linea.lstrip("#").strip())
            bloques.append(("h1" if linea.startswith("# ") else "h2", texto))
            continue
        if _VINETA_RE.match(linea):
            bloques.append(("vineta", _limpiar(_VINETA_RE.sub("", linea))))
            continue
        bloques.append(("parrafo", _limpiar(linea)))
    return bloques


# --- generación -------------------------------------------------------------

def cv_a_pdf(markdown: str, titulo: str = "CV") -> bytes:
    """Devuelve el PDF como bytes. No escribe a disco: lo sirve la UI."""
    from fpdf import FPDF

    fuente = buscar_fuente()
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(18, 16, 18)
    pdf.add_page()
    pdf.set_title(titulo)

    if fuente:
        regular, negrita = fuente
        pdf.add_font("cv", "", str(regular))
        pdf.add_font("cv", "B", str(negrita))
        familia = "cv"
        texto_de = lambda t: t                      # noqa: E731
        logger.debug(f"[pdf] Fuente Unicode: {regular.name}")
    else:
        # Sin fuente Unicode el guion largo revienta la generación entera.
        logger.warning(
            "[pdf] No encontré ninguna fuente Unicode del sistema — reemplazo "
            "los caracteres que la fuente por defecto no soporta."
        )
        familia = "Helvetica"
        texto_de = _sanear

    ancho = pdf.w - pdf.l_margin - pdf.r_margin
    for tipo, texto in analizar(markdown):
        texto = texto_de(texto)
        if tipo == "linea":
            pdf.ln(2)
            y = pdf.get_y()
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(3)
        elif tipo == "h1":
            pdf.set_font(familia, "B", 16)
            pdf.multi_cell(ancho, 8, texto)
            pdf.ln(1)
        elif tipo == "h2":
            pdf.ln(2)
            pdf.set_font(familia, "B", 12)
            pdf.multi_cell(ancho, 6, texto)
        elif tipo == "vineta":
            pdf.set_font(familia, "", 10)
            pdf.multi_cell(ancho, 5, f"  •  {texto}" if fuente else f"  -  {texto}")
        else:
            pdf.set_font(familia, "", 10)
            pdf.multi_cell(ancho, 5, texto)

    salida = pdf.output()
    return bytes(salida)


def nombre_archivo(perfil: str) -> str:
    limpio = re.sub(r"[^A-Za-z0-9_-]+", "_", perfil).strip("_") or "cv"
    return f"CV_{limpio}.pdf"
