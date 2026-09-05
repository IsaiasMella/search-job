"""Lo que se descarta ANTES de gastar una llamada al modelo.

Los filtros de ubicación corren después del scoring, porque el país y la ciudad
los saca el LLM leyendo el aviso. Pero hay avisos que no hacía falta leer: sobre
un historial real de 267, 86 traían en el TÍTULO un puesto que la persona no
hace, y 34 de ésos igual pasaron el min_score y llegaron a la notificación.
"""

from vacantia.filters import descartar_antes_de_puntuar, excluido_por_titulo
from vacantia.models import Job

PERFIL = {
    "filters": {
        "location": {"country": "Argentina", "city": ["Bahía Blanca"]},
        "work_modes": ["remote"],
        "excluir_titulos": ["Machine Learning", "Data Steward", "MLOps"],
    }
}


def job(**kw):
    return Job(**{"url": "https://x/1", "title": "AI Engineer", **kw})


# --- por título -------------------------------------------------------------

def test_descarta_el_puesto_que_la_persona_no_hace():
    quedan, fuera = descartar_antes_de_puntuar([
        job(title="Staff MLOps Engineer"),
        job(title="Data Steward Mid / Custodio Técnico"),
        job(title="AI Engineer Senior"),
    ], PERFIL)
    assert [j.title for j in quedan] == ["AI Engineer Senior"]
    assert len(fuera) == 2
    assert "MLOps" in fuera[0][1]


def test_no_le_importan_las_mayusculas_ni_las_tildes():
    assert excluido_por_titulo(job(title="MACHINE LEARNING Engineer"),
                               ["machine learning"])
    assert excluido_por_titulo(job(title="Cientifico de datos"),
                               ["Científico de Datos"])


def test_mira_el_titulo_y_no_la_descripcion():
    """Un aviso de AI Engineer nombra "machine learning" entre las tecnologías
    del equipo todo el tiempo. Descartarlo por eso sería tirar una oferta buena.
    """
    quedan, fuera = descartar_antes_de_puntuar([
        job(title="AI Engineer",
            description="El equipo trabaja con machine learning y MLOps."),
    ], PERFIL)
    assert len(quedan) == 1 and not fuera


def test_sin_lista_configurada_no_descarta_nada():
    """Un perfil que no lo configure tiene que seguir andando igual que antes."""
    quedan, fuera = descartar_antes_de_puntuar(
        [job(title="Staff MLOps Engineer")], {"filters": {}})
    assert len(quedan) == 1 and not fuera


# --- por país ---------------------------------------------------------------

def test_descarta_cuando_la_fuente_ya_dijo_el_pais():
    quedan, fuera = descartar_antes_de_puntuar([
        job(title="Python Developer", country="Colombia"),
        job(title="Python Developer", country="Argentina"),
    ], PERFIL)
    assert len(quedan) == 1 and quedan[0].country == "Argentina"
    assert "Colombia" in fuera[0][1]


def test_sin_pais_no_se_descarta_y_lo_resuelve_el_scoring():
    """Lo que la fuente no sabe queda vacío y no filtra: se puntúa igual."""
    quedan, fuera = descartar_antes_de_puntuar(
        [job(title="Python Developer", country="")], PERFIL)
    assert len(quedan) == 1 and not fuera


# --- el caso peligroso ------------------------------------------------------

def test_un_hibrido_sin_ciudad_NO_se_descarta_antes_de_puntuar():
    """La razón por la que acá no se filtra por modalidad.

    La regla dice que un presencial o híbrido EN TUS CIUDADES entra aunque
    pidas sólo remoto. Para saber que es en Bahía Blanca hace falta la ciudad,
    y ésa la completa el LLM al puntuar. Si acá se descartara por modalidad, un
    híbrido en Bahía Blanca se perdería antes de que nadie mire dónde es.
    """
    quedan, fuera = descartar_antes_de_puntuar(
        [job(title="Python Developer", work_mode="hybrid", city="")], PERFIL)
    assert len(quedan) == 1, "un híbrido sin ciudad tiene que llegar al scoring"
    assert not fuera


def test_tampoco_descarta_por_ciudad_sola():
    quedan, _ = descartar_antes_de_puntuar(
        [job(title="Python Developer", city="Rosario", work_mode="onsite")], PERFIL)
    assert len(quedan) == 1
