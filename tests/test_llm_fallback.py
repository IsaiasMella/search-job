"""La cadena de modelos: cuándo conviene seguir probando y cuándo no.

El 4/9/2026 el scoring estuvo caído tres corridas seguidas y el log mandaba a
revisar "la cuota diaria", cuando lo que pasaba era que la cuenta de Gemini se
había quedado sin crédito (429 `prepayment credits are depleted`). Estos tests
fijan la diferencia entre las dos cosas.
"""

import pytest
from openai import RateLimitError

from vacantia.llm import _es_falla_de_cuenta, chat_with_fallback

MENSAJES = [{"role": "user", "content": "hola"}]


class LLMQueFalla:
    """Un cliente que siempre tira la misma excepción, y las cuenta."""

    def __init__(self, error):
        self.error = error
        self.intentos = []
        self.chat = self

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        self.intentos.append(kwargs["model"])
        raise self.error


def rate_limit(mensaje):
    """Un RateLimitError como el que arma la librería de OpenAI."""
    class RespuestaFalsa:
        status_code = 429
        headers = {}
        request = None
    return RateLimitError(mensaje, response=RespuestaFalsa(), body=None)


@pytest.mark.parametrize("mensaje,es_de_cuenta", [
    ("Error code: 429 - Your prepayment credits are depleted.", True),
    ("Error code: 429 - billing account not configured", True),
    ("API key not valid. Please pass a valid API key.", True),
    ("Error code: 429 - Resource has been exhausted (quota).", False),
    ("Error code: 503 - The model is overloaded.", False),
])
def test_distingue_un_problema_de_cuenta_de_uno_de_cuota(mensaje, es_de_cuenta):
    assert _es_falla_de_cuenta(Exception(mensaje)) is es_de_cuenta


def test_sin_credito_no_prueba_los_otros_modelos():
    """Probar el modelo siguiente no arregla que la cuenta esté en cero.

    Antes reintentaba los 3 modelos 2 veces cada uno, con 3s de espera: 18
    segundos para llegar a la misma nada, y por lote.
    """
    llm = LLMQueFalla(rate_limit("Error code: 429 - Your prepayment credits are depleted."))

    with pytest.raises(RuntimeError, match="La cuenta del proveedor no puede responder"):
        chat_with_fallback(llm, ["modelo-a", "modelo-b", "modelo-c"], MENSAJES)

    assert llm.intentos == ["modelo-a"]


def test_un_rate_limit_de_verdad_sigue_probando_los_demas():
    """Acá sí: el límite es por modelo, y el siguiente puede estar libre."""
    llm = LLMQueFalla(rate_limit("Error code: 429 - Resource has been exhausted (quota)."))

    with pytest.raises(RuntimeError, match="Fallaron los 3 modelos"):
        chat_with_fallback(llm, ["modelo-a", "modelo-b", "modelo-c"], MENSAJES)

    # Dos intentos por modelo: el reintento y la pasada final.
    assert llm.intentos == ["modelo-a"] * 2 + ["modelo-b"] * 2 + ["modelo-c"] * 2


def test_un_modelo_dado_de_baja_deja_pasar_al_siguiente():
    """Es lo que evitó que la corrida se cayera cuando Google retiró los 2.5."""
    llm = LLMQueFalla(Exception("Error code: 404 - models/gemini-2.5-flash is no longer available"))

    with pytest.raises(RuntimeError, match="Fallaron los 2 modelos"):
        chat_with_fallback(llm, ["viejo", "nuevo"], MENSAJES)

    # Un 404 no se reintenta: no va a existir en 3 segundos.
    assert llm.intentos == ["viejo", "nuevo"]
