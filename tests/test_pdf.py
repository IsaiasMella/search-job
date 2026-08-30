"""El CV en PDF. La trampa a cubrir es el guion largo: ver vacantia/pdf.py."""

import pytest

from vacantia import pdf

CV = """# Isaías Mella

Data Scientist — Bahía Blanca, Argentina

## Experiencia

- Modelos de forecasting en producción — “pipeline” completo
- Presupuesto de € 50.000 y ahorro del 12%

## Educación

Licenciatura en Ciencias de la Computación
"""


def test_encuentra_una_fuente_unicode_del_sistema():
    """Sin esto fpdf2 usa una fuente latin-1 y el guion largo la hace explotar."""
    fuente = pdf.buscar_fuente()
    assert fuente is not None, "no hay ninguna fuente Unicode instalada"
    regular, negrita = fuente
    assert regular.exists() and negrita.exists()


def test_genera_un_pdf_valido():
    salida = pdf.cv_a_pdf(CV, "CV de prueba")
    assert salida.startswith(b"%PDF-")
    assert len(salida) > 1000


def test_no_explota_con_los_caracteres_que_rompen_latin1():
    """— “ ” € • …  son los que aparecen en cualquier CV generado."""
    salida = pdf.cv_a_pdf("# Título\n\n— “comillas” € 50.000 • … ñ á é í ó ú ¿ ¡\n")
    assert salida.startswith(b"%PDF-")


def test_sin_fuente_unicode_igual_genera_el_pdf(monkeypatch):
    """El peor caso es una PC sin ninguna fuente TTF a mano: mejor un guion
    común que no tener CV."""
    monkeypatch.setattr(pdf, "buscar_fuente", lambda: None)
    salida = pdf.cv_a_pdf("# Título\n\nGuion — y comillas “así”, € 100\n")
    assert salida.startswith(b"%PDF-")


def test_un_cv_vacio_no_rompe():
    assert pdf.cv_a_pdf("").startswith(b"%PDF-")


# --- lectura del Markdown --------------------------------------------------

def test_reconoce_titulos_vinetas_y_parrafos():
    bloques = pdf.analizar(CV)
    tipos = [t for t, _ in bloques]
    assert tipos[0] == "h1"
    assert "h2" in tipos and "vineta" in tipos and "parrafo" in tipos


def test_saca_la_sintaxis_de_markdown_pero_deja_el_texto():
    bloques = dict(
        (texto, tipo) for tipo, texto in
        pdf.analizar("**Negrita** y `código`\n\n- [Mi mail](mailto:a@b.c)\n")
    )
    assert "Negrita y código" in bloques
    assert "Mi mail" in bloques


def test_las_lineas_vacias_no_generan_bloques():
    assert pdf.analizar("\n\n   \n\n") == []


@pytest.mark.parametrize("perfil,esperado", [
    ("isaias", "CV_isaias.pdf"),
    ("juan pablo", "CV_juan_pablo.pdf"),
    ("", "CV_cv.pdf"),
])
def test_el_archivo_se_llama_como_la_persona(perfil, esperado):
    assert pdf.nombre_archivo(perfil) == esperado
