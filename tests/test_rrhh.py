"""Fuente `rrhh`: seguir a personas, no palabras clave.

No se toca la red: se stubea `_descargar`, que es el único método que sale.
"""

import pytest

from vacantia.sources.rrhh_profiles import (
    RRHHProfilesSource,
    nombre_desde_url,
    parrafos_con_busqueda,
)

PERFIL = {"filters": {"language": {"allow_english": False}}}

PAGINA_CONSULTORA = """
# Consultora Sur — Búsquedas

Somos una consultora de recursos humanos con 20 años en el mercado del sur
argentino, especializada en perfiles técnicos e industriales de la zona.

Nos encontramos buscando un Analista QHSE para planta en Bahía Blanca.
Excluyente experiencia en industria petroquímica y disponibilidad inmediata.

Vacante: Operario de mantenimiento para turno rotativo en Punta Alta.
Se valora experiencia previa en plantas de proceso.

Contactanos por mail o teléfono. Nuestras oficinas atienden de 9 a 18.
"""


def fuente(urls, config=None, profile=None) -> RRHHProfilesSource:
    cfg = {"type": "rrhh", "profiles": urls, "api_key": "x", **(config or {})}
    return RRHHProfilesSource(cfg, profile or PERFIL)


def con_paginas(monkeypatch, src, paginas):
    monkeypatch.setattr(type(src), "_descargar", lambda self, urls: paginas)


# --- helpers ---------------------------------------------------------------

@pytest.mark.parametrize("url,esperado", [
    ("https://www.linkedin.com/in/ana-perez/recent-activity/all/", "Ana Perez"),
    ("https://linkedin.com/in/juan-lopez-9b8a1234", "Juan Lopez"),
    ("https://consultora.com.ar/busquedas", "consultora.com.ar"),
])
def test_saca_a_quien_hay_que_escribirle(url, esperado):
    assert nombre_desde_url(url) == esperado


def test_levanta_solo_los_parrafos_que_anuncian_busqueda():
    parrafos = parrafos_con_busqueda(PAGINA_CONSULTORA, ["nos encontramos buscando", "vacante"])
    assert len(parrafos) == 2
    assert "Analista QHSE" in parrafos[0]
    assert "Operario de mantenimiento" in parrafos[1]
    # La presentación de la empresa y el horario de atención no son ofertas.
    assert not any("20 años en el mercado" in p for p in parrafos)


def test_ignora_los_parrafos_demasiado_cortos():
    assert parrafos_con_busqueda("Vacante!\n\nBuscamos.", ["vacante", "buscamos"]) == []


# --- armado de ofertas -----------------------------------------------------

def test_una_pagina_sin_links_genera_una_oferta_por_parrafo(monkeypatch):
    url = "https://consultora.com.ar/busquedas"
    src = fuente([url])
    con_paginas(monkeypatch, src, {url: (PAGINA_CONSULTORA, [])})

    jobs = src.fetch()
    assert len(jobs) == 2
    assert all(j.company == "consultora.com.ar" and j.source == "rrhh" for j in jobs)
    assert all(j.url.startswith(url + "#") for j in jobs)
    assert "QHSE" in jobs[0].title


def test_el_hash_distingue_una_publicacion_nueva_de_la_vieja(monkeypatch):
    """La URL de la página no cambia nunca: sin el hash, una búsqueda nueva
    quedaría tapada por el dedupe del motor."""
    url = "https://consultora.com.ar/busquedas"
    src = fuente([url])

    con_paginas(monkeypatch, src, {url: (PAGINA_CONSULTORA, [])})
    antes = {j.key for j in src.fetch()}

    nueva = PAGINA_CONSULTORA + (
        "\n\nVacante: Ingeniero de procesos con experiencia en plantas de gas, "
        "para incorporación inmediata en la zona.\n"
    )
    con_paginas(monkeypatch, src, {url: (nueva, [])})
    despues = {j.key for j in src.fetch()}

    assert antes < despues and len(despues - antes) == 1


def test_los_links_a_publicaciones_ganan_sobre_el_texto(monkeypatch):
    url = "https://www.linkedin.com/in/ana-perez/recent-activity/all/"
    src = fuente([url])
    con_paginas(monkeypatch, src, {url: (
        PAGINA_CONSULTORA,
        ["https://www.linkedin.com/posts/ana-perez_vacante-activity-123",
         "https://www.linkedin.com/in/ana-perez",
         "https://www.linkedin.com/posts/ana-perez_otra-activity-456"],
    )})
    jobs = src.fetch()
    assert [j.url for j in jobs] == [
        "https://www.linkedin.com/posts/ana-perez_vacante-activity-123",
        "https://www.linkedin.com/posts/ana-perez_otra-activity-456",
    ]
    assert all(j.company == "Ana Perez" for j in jobs)


def test_tambien_agarra_links_de_aviso_comunes(monkeypatch):
    url = "https://consultora.com.ar/empleos"
    src = fuente([url])
    con_paginas(monkeypatch, src, {url: (
        "texto sin señales", ["https://consultora.com.ar/jobs/analista-qhse-1234",
                              "https://consultora.com.ar/nosotros"],
    )})
    jobs = src.fetch()
    assert [j.url for j in jobs] == ["https://consultora.com.ar/jobs/analista-qhse-1234"]


def test_una_pagina_que_no_devuelve_nada_no_rompe_la_corrida(monkeypatch):
    src = fuente(["https://a.com/x", "https://b.com/y"])
    con_paginas(monkeypatch, src, {"https://b.com/y": (PAGINA_CONSULTORA, [])})
    assert len(src.fetch()) == 2      # las de b, sin explotar por a


# --- disponibilidad --------------------------------------------------------

def test_sin_urls_la_fuente_se_saltea():
    ok, motivo = fuente([]).is_available()
    assert not ok and "perfiles de RRHH" in motivo


def test_sin_api_key_la_fuente_se_saltea(monkeypatch):
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    ok, motivo = fuente(["https://a.com"], {"api_key": ""}).is_available()
    assert not ok and "TINYFISH_API_KEY" in motivo


def test_max_profiles_acota_cuantas_paginas_se_bajan():
    src = fuente([f"https://a.com/{i}" for i in range(20)], {"max_profiles": 5})
    assert len(src.urls) == 5
