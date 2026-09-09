"""La ventana de tiempo de las búsquedas por buscador.

El problema que arreglan: sin pedirle una ventana, el buscador ordena por
relevancia y la fecha no le importa. En el historial real del 7/9/2026 había
publicaciones de 2020, 2023 y 2024 mezcladas con las de esta semana, y 28 de 75
tenían más de un mes. Cada una de ésas se puntúa con el LLM y se descarta
después: cuesta cuota y ensucia el aviso.
"""

from datetime import date

import pytest

from vacantia.sources.google_posts import (
    MINUTOS_POR_DIA,
    GooglePostsSource,
    buscar_en_tinyfish,
    es_reciente,
)
from vacantia.sources.linkedin_jobs import LinkedInJobsSource
from vacantia.sources.portales_ar import (
    BumeranSource,
    ComputrabajoSource,
    ZonajobsSource,
)
from vacantia.sources.rrhh_profiles import RRHHProfilesSource

HOY = date(2026, 9, 7)


# --- la regla ---------------------------------------------------------------

@pytest.mark.parametrize("fecha,entra", [
    ("2026-09-07", True),          # hoy
    ("2026-09-01", True),          # 6 días
    ("hace 3 días", True),
    ("2026-08-25", False),         # 13 días
    ("hace 2 meses", False),
    ("27 jul 2023", False),        # de las que estaban en el historial real
    ("24 jul 2020", False),
])
def test_la_ventana_deja_pasar_lo_de_esta_semana(fecha, entra):
    assert es_reciente(fecha, 7, hoy=HOY) is entra


def test_un_post_sin_fecha_entra():
    """Lo que el aviso no dice, no filtra. Es la regla general del proyecto.

    Descartar por falta de fecha sería tapar un problema del buscador tirando
    ofertas buenas.
    """
    assert es_reciente("", 7, hoy=HOY)
    assert es_reciente("no se entiende esto", 7, hoy=HOY)


def test_con_cero_no_filtra_nada():
    """`max_age_days: 0` es la salida de emergencia si un día la ventana deja
    la corrida vacía."""
    assert es_reciente("24 jul 2020", 0, hoy=HOY)


# --- se le pide al buscador, que es donde de verdad sirve --------------------
# Filtrar después de recibir los resultados no alcanza: la página vuelve con 10
# posts viejos y nos quedamos sin ninguno. La ventana tiene que ir en la
# búsqueda para que el buscador devuelva 10 posts nuevos.

class ClienteFalso:
    """Anota con qué parámetros se llamó a la búsqueda."""

    def __init__(self):
        self.llamadas = []
        self.search = self

    def query(self, query, **kwargs):
        self.llamadas.append(kwargs)
        return type("R", (), {"results": []})()


def test_la_ventana_viaja_en_la_busqueda():
    cliente = ClienteFalso()
    buscar_en_tinyfish(cliente, "algo", "es", 10, recency_minutes=10080)
    assert cliente.llamadas == [{"language": "es", "recency_minutes": 10080}]


def test_sin_ventana_no_se_manda_el_parametro():
    """`None` y `0` tienen que quedar afuera: la API rechaza `recency_minutes=0`."""
    cliente = ClienteFalso()
    buscar_en_tinyfish(cliente, "algo", "es", 10, recency_minutes=None)
    buscar_en_tinyfish(cliente, "algo", "es", 10, recency_minutes=0)
    assert cliente.llamadas == [{"language": "es"}, {"language": "es"}]


def test_google_posts_busca_los_ultimos_siete_dias_por_defecto(monkeypatch):
    src = GooglePostsSource({"type": "google_posts", "api_key": "x"},
                            {"keywords": ["Data"]})
    assert src.max_age_days == 7

    cliente = ClienteFalso()
    src._client_obj = cliente
    src._search_tinyfish("una query")
    assert cliente.llamadas[0]["recency_minutes"] == 7 * MINUTOS_POR_DIA


def test_rrhh_usa_una_ventana_mas_ancha():
    """Se sigue a una persona puntual, que puede no publicar en tres semanas."""
    src = RRHHProfilesSource({"type": "rrhh", "api_key": "x", "profiles": []}, {})
    assert src.max_age_days == 30


def test_la_ventana_se_puede_cambiar_desde_el_perfil():
    for dias in (1, 14, 0):
        src = GooglePostsSource(
            {"type": "google_posts", "api_key": "x", "max_age_days": dias},
            {"keywords": ["Data"]},
        )
        assert src.max_age_days == dias


# --- una sola perilla, la de la persona -------------------------------------
#
# Para un AI Engineer una búsqueda de hace 7 días ya está llena de postulantes;
# para un supervisor de seguridad e higiene en el campo una de hace un mes sigue
# viva. Es la diferencia entre dos perfiles de esta misma casa, así que el
# número es de la persona y no de cada fuente: repartido en seis bloques,
# quedaban desincronizados sin que nadie se enterara.

TODAS = [
    (GooglePostsSource, {"type": "google_posts", "api_key": "x"}),
    (RRHHProfilesSource, {"type": "rrhh", "api_key": "x", "profiles": []}),
    (BumeranSource, {"type": "bumeran", "api_key": "x"}),
    (ZonajobsSource, {"type": "zonajobs", "api_key": "x"}),
    (ComputrabajoSource, {"type": "computrabajo", "api_key": "x"}),
    (LinkedInJobsSource, {"type": "linkedin"}),
]


@pytest.mark.parametrize("cls,config", TODAS)
def test_la_ventana_del_perfil_la_heredan_todas_las_fuentes(cls, config):
    perfil = {"keywords": ["Data"], "filters": {"max_age_days": 45}}
    assert cls(config, perfil).max_age_days == 45


@pytest.mark.parametrize("cls,config", TODAS)
def test_sin_nada_puesto_cada_fuente_usa_su_default(cls, config):
    src = cls(config, {"keywords": ["Data"]})
    assert src.max_age_days == cls.max_age_days_default


@pytest.mark.parametrize("cls,config", TODAS)
def test_el_bloque_de_la_fuente_le_gana_al_perfil(cls, config):
    """El escape para el caso puntual. No es lo que se espera que se toque."""
    perfil = {"keywords": ["Data"], "filters": {"max_age_days": 45}}
    assert cls({**config, "max_age_days": 3}, perfil).max_age_days == 3


@pytest.mark.parametrize("cls,config", TODAS)
def test_cero_apaga_la_ventana_y_no_es_lo_mismo_que_no_configurarla(cls, config):
    """`0` es un valor, no un vacío: por eso se compara contra None."""
    perfil = {"keywords": ["Data"], "filters": {"max_age_days": 0}}
    assert cls(config, perfil).max_age_days == 0


def test_los_dos_perfiles_de_la_casa_conviven():
    """El caso que da origen a todo esto, escrito como test."""
    isaias = {"keywords": ["AI Engineer"], "filters": {"max_age_days": 7}}
    papa = {"keywords": ["Seguridad e Higiene"], "filters": {"max_age_days": 45}}
    cfg = {"type": "computrabajo", "api_key": "x"}
    assert ComputrabajoSource(cfg, isaias).max_age_days == 7
    assert ComputrabajoSource(cfg, papa).max_age_days == 45


def test_linkedin_traduce_la_ventana_a_horas():
    """Era la única fuente que ya tenía ventana, en horas y con otro nombre."""
    perfil = {"keywords": ["Data"], "filters": {"max_age_days": 3}}
    assert LinkedInJobsSource({"type": "linkedin"}, perfil).hours_old == 72
    # Un `hours_old` puesto a mano sigue mandando: no se le rompe el perfil a
    # nadie que ya lo tuviera configurado.
    src = LinkedInJobsSource({"type": "linkedin", "hours_old": 24}, perfil)
    assert src.hours_old == 24
    # Y 0 días son 0 horas, que es justo lo que jobspy entiende como sin filtro.
    sin_ventana = {"keywords": ["Data"], "filters": {"max_age_days": 0}}
    assert LinkedInJobsSource({"type": "linkedin"}, sin_ventana).hours_old == 0


# --- segunda vuelta, sobre lo que igual se cuela -----------------------------

def _fuente(**extra):
    return GooglePostsSource(
        {"type": "google_posts", "api_key": "x", "max_queries": 1,
         "solo_ofertas": False, **extra},
        {"keywords": ["Data"]},
    )


def _resultado(url, fecha):
    return {"url": url, "title": "Vacante Data", "snippet": "Buscamos", "date": fecha}


def test_un_post_viejo_que_se_cuela_no_llega_al_scoring(monkeypatch):
    """El buscador aproxima la ventana, y `google_cse` filtra por día pero no
    siempre respeta el borde. Lo que pase igual se corta acá."""
    monkeypatch.setattr(GooglePostsSource, "_search", lambda self, q: [
        _resultado("https://linkedin.com/posts/a_1", date.today().isoformat()),
        _resultado("https://linkedin.com/posts/b_2", "24 jul 2020"),
        _resultado("https://linkedin.com/posts/c_3", ""),
    ])
    jobs = _fuente().fetch()
    urls = [j.url for j in jobs]
    assert "https://linkedin.com/posts/a_1" in urls   # de hoy
    assert "https://linkedin.com/posts/c_3" in urls   # sin fecha
    assert "https://linkedin.com/posts/b_2" not in urls


def test_la_fecha_que_devuelve_el_buscador_queda_en_la_oferta(monkeypatch):
    """Sin pedir ventana la API devolvía `date` vacío en los 10 resultados, y
    por eso la mitad del historial no tenía `posted_at`."""
    hoy = date.today().isoformat()
    monkeypatch.setattr(GooglePostsSource, "_search", lambda self, q: [
        _resultado("https://linkedin.com/posts/a_1", hoy),
    ])
    assert _fuente().fetch()[0].posted_at == hoy
