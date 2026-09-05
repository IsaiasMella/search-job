"""Que nada salga por stderr durante una corrida.

Rompió una instalación real: JobSpy manda sus mensajes de éxito ("finished
scraping", nivel INFO) por stderr, y **PowerShell pinta de rojo cualquier cosa
que un programa escriba en stderr**, con su bloque de `NativeCommandError` y
`CategoryInfo`. La corrida estaba saliendo bien y en pantalla parecía un crash.
"""

import io
import logging
import sys

from vacantia.sources.linkedin_jobs import _sin_stderr


def test_lo_que_va_a_stderr_no_se_ve_pero_queda_en_el_log(caplog):
    with caplog.at_level(logging.DEBUG, logger="vacantia"):
        with _sin_stderr():
            print("finished scraping", file=sys.stderr)
    assert "finished scraping" in caplog.text


def test_devuelve_stderr_como_estaba_aunque_algo_explote():
    """Si se lo queda, el resto del programa pierde por dónde reportar."""
    original = sys.stderr
    try:
        with _sin_stderr():
            raise RuntimeError("se cayó la fuente")
    except RuntimeError:
        pass
    assert sys.stderr is original


def test_le_saca_el_stderr_a_los_loggers_de_jobspy_y_se_lo_devuelve():
    """JobSpy crea sus loggers al importarse, con un handler a stderr colgado.

    Adentro del bloque tienen que escribir por donde escribimos nosotros; al
    salir, quedar como estaban, para no romperle el logging a nadie más.
    """
    ajeno = logging.getLogger("JobSpy:DePrueba")
    suyo = logging.StreamHandler(sys.stderr)
    ajeno.handlers = [suyo]
    ajeno.propagate = False
    try:
        with _sin_stderr():
            assert suyo not in ajeno.handlers
        assert ajeno.handlers == [suyo]
        assert ajeno.propagate is False
    finally:
        ajeno.handlers = []
