"""Cuándo se publicó un aviso, a partir de lo que escribe cada portal.

`Job.posted_at` es texto crudo: cada fuente pone lo que quiere y ninguna avisa
cuando cambia el formato. Conviven estas formas:

    "2026-08-21"        ISO, la que dan las APIs
    "hace 2 semanas"    relativa, la que muestran los portales argentinos
    "9 jun 2026"        día, mes abreviado en español, año
    "20/08/2026"        Bumeran y Zonajobs, en "Publicado el ..."
    "ayer"              Computrabajo, para lo de las últimas 24-48 h
    "hace más de 15 días" Bumeran y Zonajobs cuando dejan de contar (ver abajo)
    ""                  cuando el aviso de verdad no lo dice

Todo eso se convierte acá a una fecha, una sola vez, para poder ordenar y
filtrar por antigüedad. Lo que no se entiende devuelve None y nunca inventa:
una fecha adivinada haría desaparecer un aviso bueno de un filtro de "últimos 7
días" sin que nadie se entere.

**"hace más de 15 días" es la única que no es exacta**, y por eso se lee como
*exactamente* 15: es un piso, el aviso puede tener 16 días o 200. Se elige errar
para el lado de que parezca más nuevo, que es la misma regla de siempre —
preferimos mostrar de más antes que esconder una oferta buena. En la práctica
casi no se usa: Bumeran y Zonajobs ponen la fecha exacta más abajo en la misma
página ("Publicado el 20/08/2026") y `portales_ar` prefiere ésa.
"""

import re
import unicodedata
from datetime import date, datetime, timedelta

from vacantia.log import get_logger

logger = get_logger()

#: Días que dura cada unidad. Los meses y años son aproximados a propósito: el
#: portal que dice "hace 2 meses" tampoco sabe si son 58 días o 62.
_UNIDADES = {
    "hora": 0, "hs": 0, "h": 0,
    "dia": 1, "d": 1,
    "semana": 7, "sem": 7,
    "mes": 30, "meses": 30,
    "ano": 365, "year": 365,
}

_MESES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12,
}

#: "hace 2 semanas" y también "hace más de 15 días", que es como Bumeran y
#: Zonajobs dejan de contar. El "más de" se ignora a propósito: ver el docstring.
_RELATIVA = re.compile(r"hace\s+(?:mas\s+de\s+)?(\d+)\s+([a-z]+)")
_DIA_MES_ANIO = re.compile(r"^(\d{1,2})\s+([a-z]+)\.?\s+(\d{4})$")

#: "20/08/2026", como lo escriben Bumeran y Zonajobs. Día primero: es Argentina,
#: y leerlo al revés convertiría el 3 de agosto en el 8 de marzo.
_DIA_MES_ANIO_BARRAS = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")

#: Las que no llevan número. Computrabajo las usa para lo más reciente, que es
#: justo lo que más importa acertar.
_SIN_NUMERO = {"hoy": 0, "ayer": 1, "anteayer": 2, "antier": 2}


def _plano(texto: str) -> str:
    """Minúsculas y sin tildes: 'Hace 2 Días' y 'hace 2 dias' son lo mismo."""
    nfkd = unicodedata.normalize("NFKD", str(texto or "").strip().lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def parse_posted(texto: str, hoy: date | None = None) -> date | None:
    """El texto de `posted_at` como fecha, o None si no se entiende.

    `hoy` se puede pasar para que los tests no dependan del día que corren.
    """
    crudo = str(texto or "").strip()
    if not crudo:
        return None
    hoy = hoy or date.today()
    plano = _plano(crudo)

    # ISO, con o sin hora: "2026-08-21", "2026-08-21T10:00:00+00:00"
    try:
        return datetime.fromisoformat(crudo.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    if m := re.match(r"^(\d{4})-(\d{2})-(\d{2})", crudo):
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None

    # Relativa: "hace 2 semanas", "hace 1 mes", "hace 11 meses".
    if m := _RELATIVA.search(plano):
        cantidad, unidad = int(m[1]), m[2].rstrip("s") or m[2]
        dias = _UNIDADES.get(unidad, _UNIDADES.get(unidad + "s"))
        if dias is None:
            logger.debug(f"[fechas] Unidad desconocida en {crudo!r}")
            return None
        return hoy - timedelta(days=cantidad * dias)

    # Sin número: "ayer", "hoy". Va después de la relativa porque "hace 1 día"
    # es más específico y tiene que ganar si aparecen los dos.
    for palabra, dias in _SIN_NUMERO.items():
        if re.search(rf"\b{palabra}\b", plano):
            return hoy - timedelta(days=dias)

    # "9 jun 2026", "22 dic 2025"
    if m := _DIA_MES_ANIO.match(plano):
        mes = _MESES.get(m[2][:3])
        if mes:
            try:
                return date(int(m[3]), mes, int(m[1]))
            except ValueError:
                return None

    # "20/08/2026". Día primero: es Argentina.
    if m := _DIA_MES_ANIO_BARRAS.match(plano):
        try:
            return date(int(m[3]), int(m[2]), int(m[1]))
        except ValueError:
            return None

    logger.debug(f"[fechas] No pude leer la fecha {crudo!r}")
    return None


def fecha_de(oferta: dict, hoy: date | None = None) -> tuple[date | None, bool]:
    """(fecha, es_de_publicacion) para una oferta del historial.

    Cuando el aviso dice cuándo se publicó, se usa eso. Cuando no lo dice
    (pasa en casi la mitad), se cae a `found_at`, la fecha en que lo
    encontramos, y el segundo valor sale False.

    **Los dos no significan lo mismo y por eso se devuelve cuál es.** Un aviso
    publicado hace tres meses que recién encontramos ayer tiene `found_at` de
    ayer: usar eso como fecha de publicación lo haría parecer nuevo. La pantalla
    muestra la diferencia ("publicado" contra "visto") para que quien mira sepa
    de cuál de las dos se está hablando.
    """
    if publicada := parse_posted(oferta.get("posted_at"), hoy):
        return publicada, True
    return parse_posted(oferta.get("found_at"), hoy), False


def dias_desde(momento: date | None, hoy: date | None = None) -> int | None:
    if momento is None:
        return None
    return ((hoy or date.today()) - momento).days
