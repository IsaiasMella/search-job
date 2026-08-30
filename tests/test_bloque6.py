"""Ruido en google_posts y geografía rara de LinkedIn."""

import pytest

from vacantia.sources.google_posts import GooglePostsSource, pais_del_post, parece_oferta
from vacantia.sources.linkedin_jobs import split_location

TERMINOS = ["vacante", "estamos buscando", "buscamos", "se busca", "oportunidad laboral"]


# --- posts que no son ofertas ----------------------------------------------

@pytest.mark.parametrize("titulo,snippet", [
    ("Vacante: Data Scientist", "Buscamos para nuestro equipo en Buenos Aires"),
    ("Nos encontramos buscando", "Oportunidad laboral para Analista Senior"),
    ("SE BUSCA vendedor", "Para local en Bahía Blanca, jornada completa"),
])
def test_una_oferta_de_verdad_pasa(titulo, snippet):
    assert parece_oferta(titulo, snippet, TERMINOS)[0]


@pytest.mark.parametrize("titulo,snippet", [
    # Alguien buscando trabajo para sí mismo: usa el mismo vocabulario.
    ("Busco trabajo", "Estoy en búsqueda laboral activa, agradezco difusión"),
    ("Vacante", "Si saben de alguna vacante avisenme, quedé sin trabajo"),
    ("Open to work", "Buscamos entre todos una oportunidad laboral, gracias"),
    # Contenido que no es un aviso.
    ("Webinar gratuito", "Buscamos que aprendas a hacer tu CV, inscribite"),
    ("Felicitaciones al equipo", "Buscamos siempre la excelencia, gracias a todos"),
    ("Mi opinión sobre el mercado", "Estamos buscando entender qué pasa con los sueldos"),
])
def test_los_posts_que_no_son_ofertas_se_descartan(titulo, snippet):
    ok, motivo = parece_oferta(titulo, snippet, TERMINOS)
    assert not ok and motivo


def test_un_post_que_no_habla_de_ninguna_busqueda_se_descarta():
    ok, motivo = parece_oferta("Novedades del sector", "Comparto una noticia", TERMINOS)
    assert not ok and "no menciona" in motivo


def test_el_filtro_se_puede_apagar(monkeypatch):
    src = GooglePostsSource({"type": "google_posts", "solo_ofertas": False,
                             "api_key": "x"}, {"keywords": ["Data"]})
    monkeypatch.setattr(GooglePostsSource, "_search", lambda self, q: [
        {"url": "https://linkedin.com/posts/x_1", "title": "Mi reflexión",
         "snippet": "sobre el mercado", "date": ""},
    ])
    assert len(src.fetch()) == 1


def test_con_el_filtro_puesto_el_ruido_no_llega_al_scoring(monkeypatch):
    src = GooglePostsSource({"type": "google_posts", "api_key": "x", "max_queries": 1},
                            {"keywords": ["Data Scientist"]})
    monkeypatch.setattr(GooglePostsSource, "_search", lambda self, q: [
        {"url": "https://linkedin.com/posts/a_1", "title": "Vacante Data Scientist",
         "snippet": "Buscamos para Córdoba, Argentina", "date": ""},
        {"url": "https://linkedin.com/posts/b_2", "title": "Busco trabajo",
         "snippet": "Estoy en búsqueda laboral, agradezco difusión", "date": ""},
    ])
    jobs = src.fetch()
    assert len(jobs) == 1
    assert "Vacante" in jobs[0].title


# --- de qué país es el post -------------------------------------------------

@pytest.mark.parametrize("texto,esperado", [
    ("Vacante para nuestra oficina de Córdoba", "Argentina"),
    ("Buscamos en Bahía Blanca", "Argentina"),
    ("Oportunidad en México", "Mexico"),
    ("Remote, LATAM", ""),
    ("Buscamos Data Scientist", ""),
    ("Hay que resaltar el perfil", ""),      # 'salta' adentro de otra palabra
])
def test_el_pais_sale_del_texto_o_queda_vacio(texto, esperado):
    assert pais_del_post("", texto) == esperado


def test_el_pais_detectado_viaja_en_la_oferta(monkeypatch):
    src = GooglePostsSource({"type": "google_posts", "api_key": "x", "max_queries": 1},
                            {"keywords": ["Data"]})
    monkeypatch.setattr(GooglePostsSource, "_search", lambda self, q: [
        {"url": "https://linkedin.com/posts/a_1", "title": "Vacante",
         "snippet": "Buscamos Data Scientist para Rosario", "date": ""},
    ])
    assert src.fetch()[0].country == "Argentina"


def test_default_country_es_opcional_y_no_se_asume_solo(monkeypatch):
    """Por defecto no se inventa el país: lo que el aviso no dice, no filtra."""
    resultados = [{"url": "https://linkedin.com/posts/a_1", "title": "Vacante",
                   "snippet": "Buscamos Data Scientist", "date": ""}]
    monkeypatch.setattr(GooglePostsSource, "_search", lambda self, q: resultados)

    base = {"type": "google_posts", "api_key": "x", "max_queries": 1}
    perfil = {"keywords": ["Data"]}
    assert GooglePostsSource(base, perfil).fetch()[0].country == ""
    con_default = GooglePostsSource({**base, "default_country": "Argentina"}, perfil)
    assert con_default.fetch()[0].country == "Argentina"


# --- geografía de LinkedIn --------------------------------------------------

@pytest.mark.parametrize("location,esperado", [
    # El caso que da nombre al problema: Londres es un pueblo de Catamarca.
    ("Londres, Catamarca, Argentina", ("Argentina", "Londres", "Catamarca")),
    ("Bahía Blanca, Buenos Aires Province, Argentina",
     ("Argentina", "Bahía Blanca", "Buenos Aires Province")),
    ("Buenos Aires, Argentina", ("Argentina", "Buenos Aires", "")),
    ("Argentina", ("Argentina", "", "")),
    ("Buenos Aires", ("", "Buenos Aires", "")),
    ("", ("", "", "")),
])
def test_la_ciudad_es_el_primer_segmento_y_la_provincia_va_aparte(location, esperado):
    assert split_location(location) == esperado


@pytest.mark.parametrize("location", ["Remote, LATAM", "Remoto, Global", "Remote, EMEA"])
def test_latam_y_remote_no_se_toman_por_un_pais(location):
    """Poner country='LATAM' haría que un filtro país=Argentina descarte una
    oferta remota que sí sirve."""
    pais, _, _ = split_location(location)
    assert pais == ""
