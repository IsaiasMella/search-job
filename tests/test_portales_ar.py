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
    _modo,
    extraer_computrabajo,
    extraer_navent,
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


# --- empresa, ciudad y modalidad --------------------------------------------
#
# Recortes de páginas reales de aviso (agosto 2026). `city` y `work_mode` los
# llena normalmente el LLM al puntuar; sacarlos también acá es lo que mantiene
# viva la regla de ubicación cuando el modelo se cae, que fue exactamente lo
# que pasó: sin esto entró un presencial de Jujuy con el perfil en Bahía Blanca.

DETALLE_NAVENT = """# AI Engineer - Híbrido - 1878

### Descripción del puesto

Importante Banco Nacional busca perfil técnico.

* Híbrido
* Data Warehousing
* Full-time, Indeterminado

Publicado el 20/08/2026

Industria

Consultoría

Ubicación

Capital Federal, Capital Federal

Tamaño de la empresa

Entre 1 y 10 empleados

Ver más avisos de la empresa

Aliantec
"""

DETALLE_COMPUTRABAJO = """# ML / AI Engineer // Proyectos Bancarios

Kaizen Recursos Humanos - Monserrat, Capital Federal

## Descripción de la oferta

Zona y horario Laboral: REMOTO, de Lunes a Viernes de 09 a 18 hs.
"""


def test_navent_saca_empresa_ciudad_modalidad_y_fecha():
    assert extraer_navent(DETALLE_NAVENT) == {
        "title": "AI Engineer - Híbrido - 1878",
        "city": "Capital Federal",
        "company": "Aliantec",
        "work_mode": "hybrid",
        "posted_at": "20/08/2026",
    }


def test_computrabajo_saca_empresa_y_ciudad_de_la_linea_del_titulo():
    datos = extraer_computrabajo(DETALLE_COMPUTRABAJO)
    assert datos["company"] == "Kaizen Recursos Humanos"
    assert datos["city"] == "Monserrat"          # el barrio, no la provincia
    assert datos["work_mode"] == "remote"


def test_un_aviso_cross_posteado_no_rompe_la_lectura():
    """Bumeran republica avisos de Zonajobs con media página menos.

    No trae ni Ubicación ni la empresa; lo que se pueda leer se lee y el resto
    queda vacío, que es lo que hace que después no filtre de más.
    """
    cross = DETALLE_NAVENT.split("Industria")[0] + (
        "Este aviso fue publicado por ZonaJobs.\n"
    )
    datos = extraer_navent(cross)
    assert datos["work_mode"] == "hybrid"
    assert "city" not in datos and "company" not in datos


def test_la_modalidad_ambigua_queda_vacia_en_vez_de_adivinar():
    """Un aviso decía "remoto" arriba y "días presenciales (3)" abajo.

    Con "el primero que aparece gana" quedaba como remoto y se colaba un
    híbrido de Capital. Vacío no filtra, y la decisión queda para el LLM.
    """
    assert _modo("ubicación: caba. remoto. días presenciales (3)", estricto=True) == ""
    assert _modo("trabajo 100% remoto desde casa", estricto=True) == "remote"
    # Sin `estricto` —una etiqueta corta del portal— sí se queda con la primera.
    assert _modo("Híbrido") == "hybrid"


# --- cuándo se publicó ------------------------------------------------------
#
# Medido el 7/9/2026 sobre un historial de 216 avisos: los tres portales
# reportaban fecha en CERO de sus 20 avisos, y sin embargo la escriben en la
# misma página que ya bajábamos. Eso dejaba ciego al filtro de antigüedad de la
# pantalla justo en las fuentes que más lo necesitan: un aviso de Bumeran de
# dos meses pasaba el filtro de "hoy" porque no tenía fecha con qué compararse.

#: Recorte real de Computrabajo (7/9/2026). La fecha del aviso va suelta al
#: final de la descripción, y abajo el portal lista ofertas ajenas con las suyas.
DETALLE_COMPUTRABAJO_CON_SIMILARES = """# Senior Python Engineer

B&B Consultores - Retiro, Capital Federal

## Descripción de la oferta

Seleccionamos Senior Python Engineer. Remoto.

Palabras clave: senior, sr, ingeniero

Hace 6 días (actualizada)

Acerca de B&B Consultores

## Ofertas similares

* ### Senior Backend Python Developer

  Kaizen Recursos Humanos - Monserrat, Capital Federal

  Ayer
* ### Desarrollador Python

  Provincia NET - San Nicolás, Capital Federal

  Hace 9 horas
"""


def test_computrabajo_saca_la_fecha_del_aviso_y_no_la_de_los_similares():
    """La trampa: al pie lista ocho avisos ajenos, cada uno con su fecha.

    "Ayer" y "Hace 9 horas" son de otros avisos. Agarrar la primera fecha del
    documento entero daría uno recién publicado cuando en realidad tiene 6 días.
    """
    datos = extraer_computrabajo(DETALLE_COMPUTRABAJO_CON_SIMILARES)
    assert datos["posted_at"] == "Hace 6 días"


def test_navent_prefiere_la_fecha_exacta_a_la_del_titulo():
    """Bumeran y Zonajobs dicen las dos, y la de arriba deja de contar a los 15.

    "Publicado hace más de 15 días" puede ser 16 días o dos años. La exacta está
    más abajo en la misma página, así que se la busca aparte.
    """
    con_las_dos = DETALLE_NAVENT.replace(
        "### Descripción del puesto",
        "## Publicado hace más de 15 días\n\n### Descripción del puesto",
    )
    assert extraer_navent(con_las_dos)["posted_at"] == "20/08/2026"


def test_navent_cae_a_la_vaga_cuando_no_esta_la_exacta():
    sin_exacta = DETALLE_NAVENT.replace("Publicado el 20/08/2026", "")
    sin_exacta = sin_exacta.replace(
        "### Descripción del puesto",
        "## Publicado hace más de 15 días\n\n### Descripción del puesto",
    )
    assert extraer_navent(sin_exacta)["posted_at"] == "hace más de 15 días"


def test_un_aviso_sin_fecha_no_inventa_ninguna():
    """Sin fecha el aviso igual entra: lo que no dice, no filtra."""
    assert "posted_at" not in extraer_computrabajo(DETALLE_COMPUTRABAJO)
    assert "posted_at" not in extraer_navent(
        DETALLE_NAVENT.replace("Publicado el 20/08/2026", "")
    )


def test_la_fecha_del_portal_llega_a_la_oferta(monkeypatch):
    """De punta a punta: lo que dice la página termina en `Job.posted_at`."""
    src = fuente(ComputrabajoSource, {"max_queries": 1})
    url = src.url_de_busqueda(src.terminos()[0])
    aviso = ("https://ar.computrabajo.com/ofertas-de-trabajo/"
             "oferta-de-trabajo-de-senior-python-engineer-en-retiro-F5A35EBD")
    con_paginas(
        monkeypatch, src,
        listados={url: ("", [aviso])},
        detalles={aviso: (DETALLE_COMPUTRABAJO_CON_SIMILARES, [])},
    )
    assert src.fetch()[0].posted_at == "Hace 6 días"


def test_un_aviso_viejo_no_llega_al_scoring(monkeypatch):
    """El filtro corre después de bajar el detalle, porque ahí aparece la fecha.

    Se paga la descarga igual; lo que se ahorra es lo caro, que es puntuar con
    el LLM un aviso de hace dos meses que ya está cubierto.
    """
    src = fuente(ComputrabajoSource, {"max_queries": 1, "max_age_days": 7})
    url = src.url_de_busqueda(src.terminos()[0])
    base = "https://ar.computrabajo.com/ofertas-de-trabajo/oferta-de-trabajo-de-"
    nuevo_, viejo_ = base + "nuevo-en-caba-A1", base + "viejo-en-caba-B2"
    con_paginas(
        monkeypatch, src,
        listados={url: ("", [nuevo_, viejo_])},
        detalles={
            nuevo_: (DETALLE_COMPUTRABAJO_CON_SIMILARES.replace(
                "Hace 6 días (actualizada)", "Ayer"), []),
            viejo_: (DETALLE_COMPUTRABAJO_CON_SIMILARES.replace(
                "Hace 6 días (actualizada)", "Hace 2 meses"), []),
        },
    )
    assert [j.url for j in src.fetch()] == [nuevo_]


def test_un_aviso_sin_fecha_igual_entra(monkeypatch):
    """Lo que el aviso no dice, no filtra. Esconderlo sería peor que mostrarlo."""
    src = fuente(ComputrabajoSource, {"max_queries": 1, "max_age_days": 7})
    url = src.url_de_busqueda(src.terminos()[0])
    aviso = ("https://ar.computrabajo.com/ofertas-de-trabajo/"
             "oferta-de-trabajo-de-sin-fecha-en-caba-C3")
    con_paginas(
        monkeypatch, src,
        listados={url: ("", [aviso])},
        detalles={aviso: (DETALLE_COMPUTRABAJO, [])},   # este recorte no trae fecha
    )
    jobs = src.fetch()
    assert len(jobs) == 1 and jobs[0].posted_at == ""


def test_con_la_ventana_apagada_pasa_todo(monkeypatch):
    src = fuente(ComputrabajoSource, {"max_queries": 1, "max_age_days": 0})
    url = src.url_de_busqueda(src.terminos()[0])
    aviso = ("https://ar.computrabajo.com/ofertas-de-trabajo/"
             "oferta-de-trabajo-de-viejo-en-caba-D4")
    con_paginas(
        monkeypatch, src,
        listados={url: ("", [aviso])},
        detalles={aviso: (DETALLE_COMPUTRABAJO_CON_SIMILARES.replace(
            "Hace 6 días (actualizada)", "Hace 3 años"), [])},
    )
    assert len(src.fetch()) == 1


def test_el_titulo_del_aviso_pisa_al_del_slug(monkeypatch):
    """El del slug trae pegado el id y rompía el dedupe por empresa+título."""
    src = fuente(ComputrabajoSource, {"max_queries": 1})
    url = src.url_de_busqueda(src.terminos()[0])
    aviso = ("https://ar.computrabajo.com/ofertas-de-trabajo/"
             "oferta-de-trabajo-de-ml-ai-engineer-en-monserrat-B4D6A5C13906829B")
    con_paginas(
        monkeypatch, src,
        listados={url: ("", [aviso + "#lc=ListOffers-Score4-0"])},
        detalles={aviso: (DETALLE_COMPUTRABAJO, [])},
    )
    job = src.fetch()[0]
    assert job.title == "ML / AI Engineer // Proyectos Bancarios"
    assert job.company == "Kaizen Recursos Humanos"
    assert job.city == "Monserrat"
    assert job.work_mode == "remote"
    assert job.dedupe_key                       # ahora sí tiene con qué deduplicar


def test_el_mismo_aviso_en_dos_posiciones_de_la_lista_es_uno_solo(monkeypatch):
    """Computrabajo cuelga la posición en el fragmento: `#lc=ListOffers-Score4-N`."""
    src = fuente(ComputrabajoSource, {"max_queries": 1, "fetch_description": False})
    url = src.url_de_busqueda(src.terminos()[0])
    aviso = ("https://ar.computrabajo.com/ofertas-de-trabajo/"
             "oferta-de-trabajo-de-ml-ai-engineer-en-monserrat-B4D6A5C13906829B")
    con_paginas(monkeypatch, src, {url: ("", [
        aviso + "#lc=ListOffers-Score4-0",
        aviso + "#lc=ListOffers-Score4-7",
    ])})
    assert len(src.fetch()) == 1
