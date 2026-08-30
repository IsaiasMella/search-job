"""Portales argentinos: Bumeran, Zonajobs y Computrabajo.

⚠️ Estos tests usan HTML/Markdown de ejemplo, NO los sitios reales. Prueban que
la fuente hace lo que tiene que hacer con lo que recibe; que lo que reciba se
parezca a esto hay que verificarlo contra el portal (ver NOTAS-PARA-ISAIAS.md).
"""

import pytest

from vacantia.sources.portales_ar import (
    BumeranSource,
    ComputrabajoSource,
    ZonajobsSource,
    slug,
)

PERFIL = {"keywords": ["Analista de Datos", "Data Scientist", "Vendedor"]}

# Cómo se ve una página de resultados de Bumeran leída en Markdown: los avisos
# mezclados con navegación, filtros y publicidad.
LISTADO_BUMERAN = """
# Empleos de Analista de Datos

[Iniciar sesión](https://www.bumeran.com.ar/login)
[Analista de Datos Semi Senior](https://www.bumeran.com.ar/empleos/analista-de-datos-semi-senior-1116543.html)
[Analista de Datos Sr](https://www.bumeran.com.ar/empleos/analista-de-datos-sr-acme-1116999.html)
[Ver más empleos](https://www.bumeran.com.ar/empleos-busqueda-analista.html)
[Empresas](https://www.bumeran.com.ar/empresas)
"""

LINKS_BUMERAN = [
    "https://www.bumeran.com.ar/login",
    "https://www.bumeran.com.ar/empleos/analista-de-datos-semi-senior-1116543.html",
    "https://www.bumeran.com.ar/empleos/analista-de-datos-sr-acme-1116999.html?utm=x",
    "https://www.bumeran.com.ar/empleos-busqueda-analista.html",
]


def fuente(cls, config=None, profile=None):
    cfg = {"type": cls.name, "api_key": "x", **(config or {})}
    return cls(cfg, profile or PERFIL)


def con_paginas(monkeypatch, src, listados, detalles=None):
    """Stubea la única llamada que sale a la red."""
    def _descargar(self, urls, con_links):
        origen = listados if con_links else (detalles or {})
        return {u: origen[u] for u in urls if u in origen}
    monkeypatch.setattr(type(src), "_descargar", _descargar)


# --- armado de la búsqueda -------------------------------------------------

@pytest.mark.parametrize("texto,esperado", [
    ("Analista de Datos", "analista-de-datos"),
    ("Diseñador Gráfico", "disenador-grafico"),
    ("  QHSE / Seguridad  ", "qhse-seguridad"),
])
def test_el_termino_se_convierte_en_slug(texto, esperado):
    assert slug(texto) == esperado


def test_cada_portal_arma_su_direccion():
    assert fuente(BumeranSource).url_de_busqueda("Data Scientist") == \
        "https://www.bumeran.com.ar/empleos-busqueda-data-scientist.html"
    assert fuente(ZonajobsSource).url_de_busqueda("Data Scientist") == \
        "https://www.zonajobs.com.ar/empleos-busqueda-data-scientist.html"
    assert fuente(ComputrabajoSource).url_de_busqueda("Data Scientist") == \
        "https://ar.computrabajo.com/trabajo-de-data-scientist"


def test_la_ciudad_entra_en_la_direccion_cuando_se_carga():
    src = fuente(BumeranSource, {"location": "Bahía Blanca"})
    assert "bahia-blanca" in src.url_de_busqueda("Vendedor")


def test_se_puede_pisar_todo_desde_el_perfil():
    """Si el portal cambia el formato, se arregla sin tocar código."""
    src = fuente(BumeranSource, {
        "search_url": "https://nuevo.com/buscar?q={query}",
        "job_url_pattern": r"nuevo\.com/aviso/\d+",
    })
    assert src.url_de_busqueda("Mozo") == "https://nuevo.com/buscar?q=mozo"
    assert src.links_de_aviso(["https://nuevo.com/aviso/42",
                               "https://nuevo.com/otra"], "") == ["https://nuevo.com/aviso/42"]


def test_rota_los_terminos_para_no_consultar_siempre_los_mismos():
    src = fuente(BumeranSource, {"max_queries": 2})
    assert len(src.terminos()) == 2
    assert set(src.terminos()) <= set(PERFIL["keywords"])


# --- extracción de avisos --------------------------------------------------

def test_separa_los_avisos_de_la_navegacion(monkeypatch):
    src = fuente(BumeranSource, {"max_queries": 1, "fetch_description": False})
    url = src.url_de_busqueda(src.terminos()[0])
    con_paginas(monkeypatch, src, {url: (LISTADO_BUMERAN, LINKS_BUMERAN)})

    jobs = src.fetch()
    assert [j.url for j in jobs] == [
        "https://www.bumeran.com.ar/empleos/analista-de-datos-semi-senior-1116543.html",
        "https://www.bumeran.com.ar/empleos/analista-de-datos-sr-acme-1116999.html",
    ]
    assert all(j.source == "bumeran" and j.country == "Argentina" for j in jobs)
    assert "Analista De Datos" in jobs[0].title


def test_encuentra_los_avisos_aunque_no_vengan_links(monkeypatch):
    """Si el portal arma los links por JavaScript, `links` llega vacío y las
    direcciones quedan sueltas dentro del texto."""
    src = fuente(BumeranSource, {"max_queries": 1, "fetch_description": False})
    url = src.url_de_busqueda(src.terminos()[0])
    con_paginas(monkeypatch, src, {url: (LISTADO_BUMERAN, [])})
    assert len(src.fetch()) == 2


def test_no_repite_el_mismo_aviso_entre_dos_busquedas(monkeypatch):
    src = fuente(ZonajobsSource, {"max_queries": 2, "fetch_description": False})
    aviso = "https://www.zonajobs.com.ar/empleos/analista-1234.html"
    urls = [src.url_de_busqueda(t) for t in src.terminos()]
    con_paginas(monkeypatch, src, {u: ("", [aviso]) for u in urls})
    assert len(src.fetch()) == 1


def test_results_wanted_pone_el_techo(monkeypatch):
    src = fuente(BumeranSource, {"max_queries": 1, "results_wanted": 1,
                                 "fetch_description": False})
    url = src.url_de_busqueda(src.terminos()[0])
    con_paginas(monkeypatch, src, {url: (LISTADO_BUMERAN, LINKS_BUMERAN)})
    assert len(src.fetch()) == 1


def test_baja_el_detalle_de_cada_aviso(monkeypatch):
    src = fuente(BumeranSource, {"max_queries": 1})
    url = src.url_de_busqueda(src.terminos()[0])
    aviso = "https://www.bumeran.com.ar/empleos/analista-de-datos-semi-senior-1116543.html"
    con_paginas(
        monkeypatch, src,
        listados={url: (LISTADO_BUMERAN, LINKS_BUMERAN)},
        detalles={aviso: ("Buscamos Analista de Datos con SQL y Power BI.", [])},
    )
    jobs = {j.url: j for j in src.fetch()}
    assert "Power BI" in jobs[aviso].description


def test_una_busqueda_que_no_devuelve_nada_no_rompe(monkeypatch):
    src = fuente(ComputrabajoSource, {"max_queries": 2, "fetch_description": False})
    con_paginas(monkeypatch, src, {})
    assert src.fetch() == []


def test_computrabajo_reconoce_sus_avisos(monkeypatch):
    src = fuente(ComputrabajoSource, {"max_queries": 1, "fetch_description": False})
    url = src.url_de_busqueda(src.terminos()[0])
    con_paginas(monkeypatch, src, {url: ("", [
        "https://ar.computrabajo.com/ofertas-de-trabajo/oferta-de-trabajo-de-analista-en-caba-A1B2C3",
        "https://ar.computrabajo.com/empresas/acme",
    ])})
    jobs = src.fetch()
    assert len(jobs) == 1 and "analista" in jobs[0].url


# --- disponibilidad --------------------------------------------------------

def test_sin_api_key_se_saltea(monkeypatch):
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    ok, motivo = fuente(BumeranSource, {"api_key": ""}).is_available()
    assert not ok and "TINYFISH_API_KEY" in motivo


def test_sin_keywords_se_saltea():
    ok, motivo = fuente(BumeranSource, profile={"keywords": []}).is_available()
    assert not ok and "keywords" in motivo
