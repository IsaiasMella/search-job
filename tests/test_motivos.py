"""Por qué no apliqué, y qué descartó el sistema sin preguntar.

Los dos cambios salen de la misma medición, sobre el historial real del
8/9/2026 (107 ofertas, 60 descartadas a mano):

  - De los 60 motivos escritos, 46 eran la misma frase tipeada de cuatro formas
    distintas ("Estaba en ingles, osea que necesito ingles para aplicar",
    "necesitaba ingles"...). Un campo de texto obligatorio para algo que se
    repite 46 veces es trabajo al pedo, y encima no se puede contar.
  - De las 41 que esperaban una decisión, **31 el filtro ya las había
    rechazado**: el motor guarda en el historial todo lo puntuado, incluso lo
    que descartó. O sea que la lista pedía hacer a mano lo que el sistema ya
    había hecho.
"""

from datetime import date

import pytest

from vacantia.ui import data

PERFIL = {
    "min_score": 60,
    "filters": {
        "location": {"country": "Argentina", "city": "Bahía Blanca"},
        "work_modes": ["remote"],
        "language": {"allow_english": False, "max_english_level": "A2"},
    },
}


def oferta(**campos) -> dict:
    base = {
        "url": "https://e/1", "title": "AI Engineer", "company": "ACME",
        "source": "linkedin", "score": 80, "aplicado": None, "archivada": False,
        "country": "Argentina", "city": "", "work_mode": "remote",
        "posting_language": "es", "english_level": "", "requires_english": False,
        "motivo_descarte": "", "motivo_clave": "",
        "posted_at": date.today().isoformat(), "found_at": date.today().isoformat(),
    }
    return {**base, **campos}


# --- qué descartó el sistema ------------------------------------------------

def test_una_que_pide_ingles_la_descarta_el_sistema():
    clave, _ = data.motivo_del_sistema(
        oferta(requires_english=True, english_level="C1"), PERFIL["filters"])
    assert clave == "idioma"


def test_un_presencial_en_otra_ciudad_lo_descarta_el_sistema():
    """El caso concreto: presencial en Recoleta con el perfil en Bahía Blanca.

    Dos de éstas habían llegado a la lista y las descartó él a mano.
    """
    clave, _ = data.motivo_del_sistema(
        oferta(work_mode="onsite", city="Recoleta"), PERFIL["filters"])
    assert clave == "lugar"


def test_una_que_sirve_no_la_descarta_nadie():
    assert data.motivo_del_sistema(oferta(), PERFIL["filters"]) == ("", "")


def test_sin_marcar_deja_afuera_lo_que_el_filtro_ya_rechazo():
    historial = [
        oferta(url="https://e/ok"),
        oferta(url="https://e/ingles", requires_english=True, english_level="C1"),
        oferta(url="https://e/lejos", work_mode="onsite", city="Recoleta"),
    ]
    quedan = data._sin_marcar(historial, PERFIL["filters"])
    assert [o["url"] for o in quedan] == ["https://e/ok"]


def test_vuelven_solas_si_cambia_el_filtro():
    """Por eso se calcula al leer y no se guarda un campo.

    El día que suba su nivel de inglés, las 20 que hoy no llegan a la lista
    tienen que volver sin que nadie corra una migración.
    """
    o = oferta(requires_english=True, english_level="B1")
    con_a2 = {**PERFIL["filters"],
              "language": {"allow_english": False, "max_english_level": "A2"}}
    con_b2 = {**PERFIL["filters"],
              "language": {"allow_english": True, "max_english_level": "B2"}}
    assert data.motivo_del_sistema(o, con_a2)[0] == "idioma"
    assert data.motivo_del_sistema(o, con_b2)[0] == ""


def test_sin_filtros_no_se_descarta_nada():
    assert data.motivo_del_sistema(oferta(work_mode="onsite", city="Lima"), {}) == ("", "")


# --- el desplegable de motivos ----------------------------------------------

def test_el_catalogo_tiene_los_motivos_que_de_verdad_se_usaban():
    claves = [c for c, _, _ in data.MOTIVOS]
    assert claves == ["ingles", "presencial", "especial"]


def test_no_hay_una_opcion_otro_motivo_en_la_lista():
    """A propósito: obligaba a abrir el desplegable, bajar hasta "Otro" y recién
    ahí escribir. Tres pasos de más justo cuando ya tenías la mano en el
    teclado. El campo de texto está siempre visible y es opcional."""
    assert "otro" not in [c for c, _, _ in data.MOTIVOS]


@pytest.mark.parametrize("escrito,esperado", [
    # Las cuatro redacciones reales del historial, todas la misma cosa.
    ("Estaba en ingles, osea que necesito ingles para aplicar", "ingles"),
    ("necesitaba ingles", "ingles"),
    ("Necesita Inglés avanzado", "ingles"),
    ("era presencial en Buenos Aires", "presencial"),
    ("-", "especial"),
    ("Java no está en mi stack", ""),      # éste sí dice algo del puesto
    ("", ""),
])
def test_los_motivos_viejos_escritos_a_mano_se_reconocen(escrito, esperado):
    """Sin esto, los 46 descartes por inglés que ya tenía no sumarían al
    contador y el número arrancaría mintiendo."""
    assert data.clave_de_motivo(oferta(motivo_descarte=escrito)) == esperado


def test_el_motivo_elegido_le_gana_al_texto():
    o = oferta(motivo_clave="especial", motivo_descarte="algo de ingles")
    assert data.clave_de_motivo(o) == "especial"


def test_una_clave_inventada_no_se_acepta():
    assert data.clave_de_motivo(oferta(motivo_clave="cualquiera")) == ""


@pytest.mark.parametrize("o,esperado", [
    (oferta(motivo_clave="ingles"), "Piden inglés"),
    (oferta(motivo_clave="especial"), "caso especial"),
    (oferta(motivo_clave="especial", motivo_descarte="-"), "caso especial"),
    (oferta(motivo_descarte="Pide .NET"), "Pide .NET"),
    # Los dos caminos se pueden combinar.
    (oferta(motivo_clave="ingles", motivo_descarte="y encima pedía Java"),
     "Piden inglés · y encima pedía Java"),
    (oferta(), "sin motivo"),
])
def test_lo_que_se_lee_en_la_tarjeta_ya_descartada(o, esperado):
    assert data.texto_del_motivo(o) == esperado


def test_los_motivos_que_no_ensenian_estan_marcados():
    """"Piden inglés" y "es presencial" son restricciones que los filtros ya
    aplican solos: meterlas al prompt como ejemplos negativos sería enseñarle
    dos veces lo mismo y por el lado impreciso. El caso especial lo pidió él."""
    assert data.MOTIVOS_QUE_NO_ENSENIAN == {c for c, _, _ in data.MOTIVOS}
    # Lo que se escribe a mano SÍ enseña: es el descarte que dice algo del
    # puesto, y por eso queda fuera del desplegable y sin clave.
    assert data.clave_de_motivo(oferta(motivo_descarte="Pide .NET")) == ""
