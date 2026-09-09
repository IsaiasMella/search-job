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
    # Bumeran y Zonajobs, en "Publicado el ...". Día primero: es Argentina, y
    # al revés el 3 de agosto se convertiría en el 8 de marzo.
    ("20/08/2026", date(2026, 8, 20)),
    ("03/08/2026", date(2026, 8, 3)),
    # Computrabajo, para lo más reciente — que es justo lo que más importa.
    ("Ayer", date(2026, 9, 3)),
    ("hoy", HOY),
    ("Anteayer", date(2026, 9, 2)),
    ("Hace 6 días (actualizada)", date(2026, 8, 29)),
])
def test_lee_los_formatos_que_usan_los_portales(texto, esperado):
    assert parse_posted(texto, HOY) == esperado


def test_hace_mas_de_15_dias_se_lee_como_15_y_es_un_piso():
    """Navent deja de contar a los 15: puede tener 16 días o dos años.

    Se lee como 15 —el piso— y no como None, porque 15 ya alcanza para que
    caiga fuera de una ventana de 7 días, que es donde importa. Erra para el
    lado de que parezca más nuevo, que es la regla de siempre: mostrar de más
    antes que esconder una oferta buena.

    En la práctica casi no se usa: `portales_ar` prefiere la fecha exacta, que
    Navent escribe más abajo en la misma página.
    """
    assert parse_posted("Publicado hace más de 15 días", HOY) == date(2026, 8, 20)
    assert dias_desde(parse_posted("hace mas de 15 dias", HOY), HOY) == 15


def test_una_palabra_que_contiene_ayer_no_es_ayer():
    """"ayeres" no es una fecha, y "anteayer" no son 1 día sino 2."""
    assert parse_posted("ayeres", HOY) is None
    assert dias_desde(parse_posted("anteayer", HOY), HOY) == 2


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
