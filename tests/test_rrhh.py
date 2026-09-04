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


def con_busqueda(monkeypatch, src, por_perfil):
    """Stubea el buscador: {url del perfil: [urls de sus posts]}.

    Un perfil de LinkedIn no se puede leer, así que la fuente le pregunta al
    buscador cuáles son sus publicaciones. Eso es lo que se reemplaza acá.
    """
    monkeypatch.setattr(type(src), "posts_de",
                        lambda self, url: list(por_perfil.get(url, [])))


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
    url = "https://consultora.com.ar/busquedas"
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


def test_reconoce_un_perfil_de_persona_de_linkedin():
    """Probado el 4/9/2026: LinkedIn devuelve la página vacía sin sesión.

    Da igual el formato de la URL. Como el síntoma es "0 publicaciones", que se
    lee igual que un error de configuración, el log tiene que decir que la culpa
    no es de quien la pegó.
    """
    from vacantia.sources.rrhh_profiles import es_perfil_de_linkedin

    assert es_perfil_de_linkedin("https://www.linkedin.com/in/ana/recent-activity/all/")
    assert es_perfil_de_linkedin("https://linkedin.com/in/ana-perez-2472/")
    # Una consultora sí se puede leer, y una página de empresa no se probó.
    assert not es_perfil_de_linkedin("https://consultora.com.ar/busquedas")
    assert not es_perfil_de_linkedin("https://www.linkedin.com/company/acme/")
    assert not es_perfil_de_linkedin("")


def test_con_la_busqueda_apagada_un_perfil_de_linkedin_avisa_que_no_va_a_traer(
        monkeypatch, caplog):
    """Sin el rodeo por el buscador, un perfil de LinkedIn no puede dar nada.

    El síntoma sería "0 publicaciones", que se lee igual que un error de
    configuración, así que el log tiene que decir cuál es la causa.
    """
    import logging

    src = fuente(["https://www.linkedin.com/in/ana-perez/recent-activity/all/"],
                 {"buscar_posts": False})
    con_paginas(monkeypatch, src, {})

    with caplog.at_level(logging.WARNING):
        assert src.fetch() == []
    assert "LinkedIn no deja leerlo" in caplog.text


# --- seguir a una persona sin poder leer su perfil -------------------------

def test_saca_el_slug_del_perfil():
    from vacantia.sources.rrhh_profiles import slug_de_perfil

    assert slug_de_perfil(
        "https://www.linkedin.com/in/renzo-bazan-reyna-247214182/recent-activity/all/"
    ) == "renzo-bazan-reyna-247214182"
    assert slug_de_perfil("https://consultora.com.ar/busquedas") == ""


def test_un_perfil_de_linkedin_se_reemplaza_por_sus_posts(monkeypatch):
    """La vuelta al bloqueo: el perfil no se lee, los posts sí.

    Para quien carga la URL no cambia nada: pega el perfil y anda.
    """
    # Un slug real de LinkedIn: nombre más el identificador numérico largo,
    # que `nombre_desde_url` recorta para dejar el nombre a secas.
    perfil = "https://www.linkedin.com/in/ana-perez-247214182/recent-activity/all/"
    post = "https://www.linkedin.com/posts/ana-perez-247214182_vacante-activity-123"
    src = fuente([perfil])
    con_busqueda(monkeypatch, src, {perfil: [post]})
    con_paginas(monkeypatch, src, {post: (PAGINA_CONSULTORA, [])})

    jobs = src.fetch()
    assert jobs, "el post tendría que haberse leído"
    # El aviso queda a nombre de la persona, no del post: es a quien le escribís.
    assert all(j.company == "Ana Perez" for j in jobs)
    assert all(j.raw["perfil_rrhh"] == perfil for j in jobs)


def test_descarta_los_posts_de_otra_persona_con_el_mismo_nombre(monkeypatch):
    """Buscando "Renzo Bazan" el buscador devolvió tres personas distintas.

    El slug del perfil es lo único que las separa sin equivocarse.
    """
    perfil = "https://www.linkedin.com/in/renzo-bazan-reyna-247214182/"
    mios = "https://www.linkedin.com/posts/renzo-bazan-reyna-247214182_hiring-activity-1"
    otro = "https://www.linkedin.com/posts/renzo-bazan-loayza-52435072_otra-activity-2"

    src = fuente([perfil])
    monkeypatch.setattr(
        "vacantia.sources.google_posts.buscar_en_tinyfish",
        lambda *a, **k: [{"url": mios, "title": "", "snippet": "", "date": ""},
                         {"url": otro, "title": "", "snippet": "", "date": ""}],
    )
    monkeypatch.setattr(type(src), "_cliente", lambda self: object())

    assert src.posts_de(perfil) == [mios]


def test_una_pagina_normal_no_pasa_por_el_buscador(monkeypatch):
    """La consultora se lee directo: gastar una búsqueda ahí sería al pedo."""
    url = "https://consultora.com.ar/busquedas"
    src = fuente([url])
    llamadas = []
    monkeypatch.setattr(type(src), "posts_de",
                        lambda self, u: llamadas.append(u) or [])
    con_paginas(monkeypatch, src, {url: (PAGINA_CONSULTORA, [])})

    src.fetch()
    assert llamadas == []


def test_ignora_la_navegacion_de_linkedin(monkeypatch):
    """Cada página de post trae 226 links y uno solo parece aviso: el menú.

    Es `/jobs/search?trk=public_post_guest_nav_menu_jobs`, el botón "Empleos"
    de la barra de arriba. Sin filtrarlo, cada post generaba un aviso falso
    apuntando al buscador de LinkedIn, siempre el mismo.
    """
    url = "https://consultora.com.ar/busquedas"
    src = fuente([url])
    con_paginas(monkeypatch, src, {url: ("", [
        "https://www.linkedin.com/jobs/search?trk=public_post_guest_nav_menu_jobs",
        "https://www.linkedin.com/login",
        "https://consultora.com.ar/jobs/analista-de-datos-123",
    ])})
    assert [j.url for j in src.fetch()] == [
        "https://consultora.com.ar/jobs/analista-de-datos-123"
    ]
