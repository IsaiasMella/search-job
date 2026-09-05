"""Archivar: el aviso ya no está, o quedó viejo.

**No es lo mismo que descartar**, y por eso es un estado aparte. El motivo de un
descarte dice algo del puesto y va al prompt de scoring como ejemplo negativo;
"el aviso ya no está" no dice nada de si servía. Mezclarlos le enseñaría al
sistema una preferencia que nadie tuvo.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from vacantia.state import State

HOY = datetime.now(timezone.utc)


def oferta(url, titulo, dias_del_aviso=0, **extra):
    return {"url": url, "title": titulo, "score": 70, "aplicado": None,
            "posted_at": (HOY - timedelta(days=dias_del_aviso)).date().isoformat(),
            "found_at": HOY.isoformat(), **extra}


@pytest.fixture
def estado(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "state" / "ana"
    d.mkdir(parents=True)
    (d / "job_history.json").write_text(json.dumps([
        oferta("https://e/nueva", "De ayer", 1),
        oferta("https://e/vieja", "De hace 20 días", 20),
        oferta("https://e/antigua", "De hace 40 días", 40),
        oferta("https://e/sinfecha", "Sin fecha", 0, posted_at="", found_at=""),
        oferta("https://e/aplicada", "Ya apliqué", 30, aplicado=True),
    ]), encoding="utf-8")
    return State("ana")


def test_archivar_no_toca_el_veredicto(estado):
    """`aplicado` sigue en None: no se descartó, sólo se sacó de la lista."""
    assert estado.archivar(["https://e/vieja"]) == 1
    guardada = {h["url"]: h for h in estado.load_history()}["https://e/vieja"]
    assert guardada["archivada"] is True
    assert guardada["fecha_archivada"]
    assert guardada["aplicado"] is None
    assert not guardada.get("motivo_descarte")


def test_no_ensucia_los_ejemplos_del_aprendizaje(estado):
    """Lo que va al prompt de scoring son las descartadas CON motivo.

    Una archivada no tiene motivo ni veredicto, así que no entra: el sistema no
    aprende "no me gustan estos puestos" cuando lo único que pasó es que bajaron
    la publicación.
    """
    estado.archivar(["https://e/vieja", "https://e/antigua"])
    assert estado.feedback_jobs(aplicado=False) == []


def test_se_puede_devolver_a_la_lista(estado):
    estado.archivar(["https://e/vieja"])
    assert estado.archivar(["https://e/vieja"], archivada=False) == 1
    guardada = {h["url"]: h for h in estado.load_history()}["https://e/vieja"]
    assert guardada["archivada"] is False and guardada["fecha_archivada"] == ""


def test_archivar_no_borra_nada_del_historial(estado):
    """Por eso se puede deshacer, y por eso no vuelven a entrar: la clave sigue
    en `seen_jobs.json` y el dedupe las saca antes de gastar nada."""
    antes = len(estado.load_history())
    estado.archivar(["https://e/vieja", "https://e/antigua"])
    assert len(estado.load_history()) == antes


def test_una_url_que_no_esta_no_rompe(estado):
    assert estado.archivar(["https://e/no-existe"]) == 0


# --- archivar las viejas de una ---------------------------------------------

def test_junta_las_mas_viejas_que_el_corte(estado):
    from vacantia.ui import data

    assert set(data.viejas_sin_marcar("ana", 30)) == {"https://e/antigua"}
    assert set(data.viejas_sin_marcar("ana", 14)) == {
        "https://e/vieja", "https://e/antigua"}


def test_no_archiva_las_que_no_dicen_cuando_se_publicaron(estado):
    """No se sabe si están viejas, y archivar por las dudas es tirar una oferta
    que puede ser de ayer."""
    from vacantia.ui import data

    assert "https://e/sinfecha" not in data.viejas_sin_marcar("ana", 7)


def test_no_toca_las_que_ya_marcaste(estado):
    """La aplicada tiene 30 días, pero ya la decidiste: no se encajona."""
    from vacantia.ui import data

    assert "https://e/aplicada" not in data.viejas_sin_marcar("ana", 14)
