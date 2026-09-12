"""Qué te están pidiendo: el gráfico de habilidades de Métricas.

Sale del campo `stack` que el modelo ya devolvía por cada oferta al puntuarla,
así que **no cuesta ninguna llamada extra**. Y por eso mismo sirve para
cualquier oficio: no hay ninguna lista de tecnologías escrita en el código, que
es lo que habría que mantener para siempre y aun así nunca cubriría marketing ni
seguridad e higiene. El modelo lee el aviso y devuelve lo que ese aviso pide.

Lo que se fija acá es la normalización, que es la parte que se puede romper sin
que se note: mezclar de más inventa una tendencia que no existe, y mezclar de
menos parte una habilidad real en dos barras chiquitas.
"""

from vacantia.ui import data

from tests.test_ui import HOY_ISO, _con_historial, get, sitio  # noqa: F401


def _ofertas(*stacks):
    return [{"url": f"https://e/{i}", "title": f"Oferta {i}", "aplicado": None,
             "score": 70, "found_at": HOY_ISO, "stack": s}
            for i, s in enumerate(stacks)]


def _filas(tmp, *stacks):
    _con_historial(tmp, _ofertas(*stacks))
    return dict(data.habilidades_pedidas("test")["filas"])


# --- cortar la lista --------------------------------------------------------

def test_separa_por_coma_y_tambien_por_barra(sitio):
    """El modelo agrupa alternativas: "AWS/Azure/GCP" es una entrada suya y son
    tres nubes distintas para contar."""
    _, tmp = sitio
    filas = _filas(tmp, "Python, AWS/Azure/GCP")
    assert filas == {"Python": 1, "AWS": 1, "Azure": 1, "GCP": 1}


def test_las_muletillas_no_son_habilidades(sitio):
    """"Experiencia" y "conocimientos" no nombran nada que se pueda ir a
    aprender, que es para lo que sirve este gráfico."""
    _, tmp = sitio
    filas = _filas(tmp, "Python, experiencia, conocimientos, N/A, -")
    assert filas == {"Python": 1}


def test_una_frase_larga_no_entra(sitio):
    """Cuando el modelo mete una oración donde iba un nombre, contarla agrega
    una barra única que ensucia el gráfico y no se repite nunca."""
    _, tmp = sitio
    filas = _filas(tmp, "Python, muchos años trabajando con sistemas distribuidos")
    assert filas == {"Python": 1}


def test_una_oferta_cuenta_una_vez_por_habilidad(sitio):
    """Si un aviso nombra Python cuatro veces sigue siendo UN trabajo que pide
    Python. La pregunta es en cuántas búsquedas te lo van a pedir."""
    _, tmp = sitio
    filas = _filas(tmp, "Python, Python, python")
    assert filas == {"Python": 1}


# --- normalizar sin inventar ------------------------------------------------

def test_las_mayusculas_no_parten_una_habilidad_en_dos(sitio):
    """Y gana la escritura más frecuente, que es la que usa el mercado: sale
    "PostgreSQL" y no "postgresql", sin tener una tabla de nombres propios."""
    _, tmp = sitio
    filas = _filas(tmp, "PostgreSQL", "PostgreSQL", "postgresql")
    assert filas == {"PostgreSQL": 3}


def test_el_plural_se_une_al_singular_cuando_los_dos_existen(sitio):
    """"LLMs" y "LLM" son lo mismo y hay que sumarlas, o quedan dos barras de la
    mitad del tamaño y la habilidad más pedida parece la tercera."""
    _, tmp = sitio
    filas = _filas(tmp, "LLM", "LLMs", "LLMs")
    assert filas == {"LLM": 3}


def test_una_palabra_que_termina_en_s_y_no_es_plural_queda_en_paz(sitio):
    """Es el caso que rompe una regla de "sacale la s": Kubernetes no es el
    plural de Kubernete, y Analytics no es el plural de Analytic.

    Por eso la regla la ponen los datos y no una lista: sólo se unen cuando el
    singular aparece de verdad en los avisos. Es lo que hace que esto ande igual
    en marketing o en seguridad e higiene sin saber nada del rubro.
    """
    _, tmp = sitio
    filas = _filas(tmp, "Kubernetes", "Kubernetes", "Google Analytics")
    assert filas == {"Kubernetes": 2, "Google Analytics": 1}


# --- que sirva para cualquier oficio ----------------------------------------

def test_anda_igual_con_habilidades_que_no_son_de_programacion(sitio):
    """El caso que motivó la función: la misma pantalla le tiene que servir a
    marketing y a seguridad e higiene, no sólo a quien busca puestos de AI."""
    _, tmp = sitio
    filas = _filas(tmp,
                   "Google Analytics, Meta Ads, SEO",
                   "Meta Ads, SEO, Community Management",
                   "ISO 45001, IRAM, auditoría interna")
    assert filas["Meta Ads"] == 2
    assert filas["SEO"] == 2
    assert filas["ISO 45001"] == 1
    assert filas["auditoría interna"] == 1


# --- lo que se dice en pantalla ---------------------------------------------

def test_cuenta_las_que_todavia_no_analizo(sitio):
    """Sin decirlo, un gráfico flaco se lee como "no piden nada" en vez de
    "todavía no lo miré todo"."""
    _, tmp = sitio
    _con_historial(tmp, _ofertas("Python", "", "Java"))
    r = data.habilidades_pedidas("test")
    assert r["ofertas"] == 2
    assert r["sin_datos"] == 1


def test_el_tope_corta_la_cola_larga(sitio):
    """Con todas, el gráfico deja de ser un "qué me piden" y pasa a ser un
    inventario: lo que aparece una sola vez no es una tendencia."""
    _, tmp = sitio
    _con_historial(tmp, _ofertas(*[f"Hab{i}" for i in range(40)]))
    r = data.habilidades_pedidas("test", tope=5)
    assert len(r["filas"]) == 5
    assert r["distintas"] == 40           # el total sigue siendo el real


def test_el_panel_aparece_en_metricas(sitio):
    """Y va primero: es lo único de esa pantalla que dice qué hacer con el
    tiempo libre."""
    base, tmp = sitio
    _con_historial(tmp, _ofertas("Python, RAG", "Python, LangChain", "Python"))

    _, html, _ = get(base, "/estadisticas?perfil=test")
    assert "Qué te están pidiendo" in html
    assert "Python" in html
    assert html.index("Qué te están pidiendo") < html.index("Qué tan bien te encajan")


def test_sin_ninguna_habilidad_el_panel_no_se_dibuja(sitio):
    """Un panel vacío con un título arriba ocupa lugar y no dice nada. Pasa en
    una instalación recién estrenada, antes de la primera corrida."""
    base, tmp = sitio
    _con_historial(tmp, _ofertas("", ""))
    assert "Qué te están pidiendo" not in get(base, "/estadisticas?perfil=test")[1]
