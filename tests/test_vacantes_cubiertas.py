"""Descartar avisos de búsquedas que ya se cerraron."""

import pytest

from vacantia.filters import drop_filled, filled_marker
from vacantia.models import Job


def job(url="https://x.com/jobs/1", title="Data Scientist", description="") -> Job:
    return Job(url=url, title=title, company="ACME", description=description)


@pytest.mark.parametrize("texto", [
    "Esta vacante ya fue cubierta.",
    "La vacante cubierta se dio de baja.",
    "Posición cerrada — gracias a todos los que se postularon.",
    "Búsqueda cerrada",
    "La busqueda ya esta cerrada",
    "Puesto cubierto",
    "No longer accepting applications",
    "This position has been filled",
])
def test_detecta_las_variantes_en_la_descripcion(texto):
    assert filled_marker(job(description=texto))


def test_detecta_en_la_url():
    assert filled_marker(job(url="https://x.com/empleos/busqueda-cerrada/1234"))


def test_detecta_en_el_titulo():
    assert filled_marker(job(title="Data Scientist (vacante cubierta)"))


def test_detecta_sin_tildes_y_en_mayusculas():
    assert filled_marker(job(description="POSICION CERRADA"))


@pytest.mark.parametrize("texto", [
    "Buscamos Data Scientist para una posición nueva.",
    "Nuestra oficina cerrada los feriados; el equipo trabaja remoto.",
    "Vacante abierta hasta el 30 de septiembre.",
    "",
])
def test_no_dispara_con_avisos_abiertos(texto):
    assert filled_marker(job(description=texto)) == ""


def test_drop_filled_parte_la_lista():
    abiertas = [job(url="https://x/1"), job(url="https://x/2")]
    cerrada = job(url="https://x/3", description="Búsqueda cerrada.")
    kept, dropped = drop_filled(abiertas + [cerrada])
    assert kept == abiertas
    assert [j.url for j, _ in dropped] == ["https://x/3"]
    assert dropped[0][1]  # queda registrado el texto que la delató
