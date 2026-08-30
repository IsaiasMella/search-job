"""Campos de feedback en Job y su persistencia en el estado.

Es sólo el guardado: la UI que lo escribe (pestaña Trabajos) todavía no existe.
"""

import json

from vacantia.models import Job
from vacantia.state import State


def job(url="https://x.com/jobs/1", **kw) -> Job:
    return Job(url=url, title="Data Scientist", company="ACME", **kw)


def estado_con(tmp_path, *jobs) -> State:
    st = State("test", root=tmp_path)
    st.save(list(jobs))
    return st


# --- el modelo -------------------------------------------------------------

def test_los_campos_arrancan_vacios():
    j = job()
    assert (j.aplicado, j.motivo_descarte, j.fecha_feedback) == (None, "", "")


def test_el_feedback_sobrevive_al_ida_y_vuelta_a_dict():
    j = job(aplicado=False, motivo_descarte="Pide 5 años de Java",
            fecha_feedback="2026-08-30T12:00:00+00:00")
    copia = Job.from_dict(json.loads(json.dumps(j.to_dict())))
    assert copia.aplicado is False
    assert copia.motivo_descarte == "Pide 5 años de Java"
    assert copia.fecha_feedback == "2026-08-30T12:00:00+00:00"


def test_los_estados_viejos_sin_los_campos_siguen_cargando():
    viejo = {"url": "https://x/1", "title": "Data Scientist", "score": 80}
    assert Job.from_dict(viejo).aplicado is None


# --- persistencia ----------------------------------------------------------

def test_guarda_el_veredicto_en_el_historial(tmp_path):
    st = estado_con(tmp_path, job())
    assert st.record_feedback("https://x.com/jobs/1", aplicado=False,
                              motivo_descarte="Es presencial en Buenos Aires")

    guardada = State("test", root=tmp_path).load_history()[0]
    assert guardada["aplicado"] is False
    assert guardada["motivo_descarte"] == "Es presencial en Buenos Aires"
    assert guardada["fecha_feedback"]  # se estampa sola


def test_la_url_con_querystring_encuentra_la_misma_oferta(tmp_path):
    st = estado_con(tmp_path, job())
    assert st.record_feedback("https://x.com/jobs/1/?utm_source=telegram", aplicado=True)


def test_una_url_desconocida_avisa_en_vez_de_perder_el_dato(tmp_path):
    st = estado_con(tmp_path, job())
    assert st.record_feedback("https://otra.com/9", aplicado=True) is False


def test_el_feedback_no_se_pierde_cuando_la_oferta_vuelve_a_aparecer(tmp_path):
    st = estado_con(tmp_path, job())
    st.record_feedback("https://x.com/jobs/1", aplicado=True)

    # Corrida siguiente: la misma oferta vuelve a entrar al historial.
    otra = State("test", root=tmp_path)
    otra.save([job(), job(url="https://x.com/jobs/2")])

    history = {h["url"]: h for h in State("test", root=tmp_path).load_history()}
    assert history["https://x.com/jobs/1"]["aplicado"] is True
    assert history["https://x.com/jobs/2"]["aplicado"] is None


def test_tambien_actualiza_last_run(tmp_path):
    """Es el archivo que lee el drafter y el que va a leer la UI."""
    st = estado_con(tmp_path, job())
    st.record_feedback("https://x.com/jobs/1", aplicado=True)
    ultima = json.loads((tmp_path / "test" / "last_run.json").read_text(encoding="utf-8"))
    assert ultima[0]["aplicado"] is True


def test_las_descartadas_salen_de_la_mas_nueva_a_la_mas_vieja(tmp_path):
    st = estado_con(tmp_path, job("https://x/1"), job("https://x/2"), job("https://x/3"))
    st.record_feedback("https://x/1", False, "muy junior", fecha_feedback="2026-08-01T00:00:00Z")
    st.record_feedback("https://x/2", False, "pide inglés", fecha_feedback="2026-08-20T00:00:00Z")
    st.record_feedback("https://x/3", True)

    descartadas = st.feedback_jobs(aplicado=False)
    assert [j.url for j in descartadas] == ["https://x/2", "https://x/1"]
    assert descartadas[0].motivo_descarte == "pide inglés"
    assert [j.url for j in st.feedback_jobs(aplicado=True)] == ["https://x/3"]
    assert len(st.feedback_jobs()) == 3
    assert len(st.feedback_jobs(limit=2)) == 2


def test_sin_feedback_no_devuelve_nada(tmp_path):
    st = estado_con(tmp_path, job())
    assert st.feedback_jobs() == []


def test_historial_corrupto_no_rompe(tmp_path):
    st = estado_con(tmp_path, job())
    (tmp_path / "test" / "job_history.json").write_text("{ roto", encoding="utf-8")
    assert State("test", root=tmp_path).load_history() == []
