"""Leer el `posted_at` que escribe cada portal.

Los cuatro formatos salieron del historial real de un perfil (207 avisos,
septiembre 2026): 52 en ISO, 60 relativas en español, 3 con mes abreviado y 92
vacías. Si un portal cambia el formato, lo que falla es un test de acá y no el
filtro de la pantalla en silencio.
"""

from datetime import date

import pytest

from vacantia.fechas import dias_desde, fecha_de, parse_posted

HOY = date(2026, 9, 4)


@pytest.mark.parametrize("texto,esperado", [
    ("2026-08-21", date(2026, 8, 21)),
    ("2026-08-21T10:00:00+00:00", date(2026, 8, 21)),
    ("hace 1 mes", date(2026, 8, 5)),
    ("hace 2 semanas", date(2026, 8, 21)),
    ("hace 11 meses", date(2025, 10, 9)),
    ("hace 3 dias", date(2026, 9, 1)),
    ("Hace 3 días", date(2026, 9, 1)),        # mayúsculas y tildes dan igual
    ("hace 5 horas", HOY),
    ("9 jun 2026", date(2026, 6, 9)),
    ("22 dic 2025", date(2025, 12, 22)),
])
def test_lee_los_formatos_que_usan_los_portales(texto, esperado):
    assert parse_posted(texto, HOY) == esperado


@pytest.mark.parametrize("texto", ["", "   ", None, "vaya uno a saber",
                                   "próximamente", "2026-13-45"])
def test_lo_que_no_entiende_devuelve_nada_en_vez_de_inventar(texto):
    """Una fecha adivinada hace desaparecer un aviso bueno de un filtro."""
    assert parse_posted(texto, HOY) is None


def test_prefiere_cuando_se_publico_sobre_cuando_lo_vimos():
    oferta = {"posted_at": "hace 3 meses", "found_at": "2026-09-04"}
    momento, es_publicacion = fecha_de(oferta, HOY)
    assert es_publicacion is True
    assert dias_desde(momento, HOY) == 90


def test_sin_fecha_de_publicacion_cae_a_cuando_lo_vimos_y_lo_dice():
    """Casi la mitad de los avisos no dicen cuándo se publicaron.

    La fecha en que lo encontramos es un piso, no la de publicación: el aviso
    puede ser mucho más viejo. Por eso se devuelve cuál de las dos es, y la
    pantalla escribe "visto" en vez de "publicado".
    """
    oferta = {"posted_at": "", "found_at": "2026-08-26"}
    momento, es_publicacion = fecha_de(oferta, HOY)
    assert es_publicacion is False
    assert momento == date(2026, 8, 26)


def test_sin_ninguna_de_las_dos_no_hay_fecha():
    assert fecha_de({}, HOY) == (None, False)
