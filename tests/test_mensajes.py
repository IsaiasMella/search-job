"""Moldes de mensaje para el reclutador (COSTOS.md §10). Son borradores."""

from vacantia import mensajes
from vacantia.models import Job

PERFIL = {
    "candidate": {"name": "Isaías Mella", "phone": "291-4000000",
                  "profile": "Data scientist"},
    "llm": {},
}
JOB = Job(url="https://x.com/1", title="Data Scientist Senior", company="Ana Perez",
          description="Buscamos Data Scientist con Python y SQL.")


def test_el_dm_no_pasa_de_cuatro_lineas():
    """Lo leen en el celular entre 200 mensajes."""
    texto = mensajes.molde(JOB, PERFIL, "dm")
    assert len([l for l in texto.splitlines() if l.strip()]) <= 4


def test_el_dm_pone_a_quien_hay_que_escribirle_y_el_puesto():
    texto = mensajes.molde(JOB, PERFIL, "dm")
    assert "Ana Perez" in texto and "Data Scientist Senior" in texto


def test_el_mail_lleva_asunto_nombre_y_telefono():
    texto = mensajes.molde(JOB, PERFIL, "mail")
    assert texto.startswith("Asunto:")
    assert "Isaías Mella" in texto and "291-4000000" in texto


def test_sin_telefono_no_queda_un_guion_colgado():
    texto = mensajes.molde(JOB, {"candidate": {"name": "Ana"}}, "mail")
    assert not texto.rstrip().endswith("—")


def test_los_huecos_que_completa_el_llm_quedan_marcados():
    """Sin credenciales el molde sale con las llaves puestas: deja claro qué
    falta, que es mejor que un mensaje genérico disfrazado de personalizado."""
    texto, con_llm = mensajes.generar(JOB, "CV", PERFIL, "dm")
    assert con_llm is False
    assert "{" in texto and "}" in texto


def test_si_el_llm_falla_devuelve_el_molde(monkeypatch):
    monkeypatch.setattr(mensajes, "has_llm_credentials", lambda cfg: True)
    def explota(*a, **k):
        raise RuntimeError("sin cuota")
    monkeypatch.setattr(mensajes, "chat_with_llm", explota)
    texto, con_llm = mensajes.generar(JOB, "CV", PERFIL, "dm")
    assert con_llm is False and "Ana Perez" in texto


def test_usa_el_llm_cuando_hay_credenciales(monkeypatch):
    monkeypatch.setattr(mensajes, "has_llm_credentials", lambda cfg: True)
    monkeypatch.setattr(mensajes, "chat_with_llm",
                        lambda cfg, **k: "Hola Ana, vi la búsqueda.")
    texto, con_llm = mensajes.generar(JOB, "CV", PERFIL, "dm")
    assert con_llm is True and texto == "Hola Ana, vi la búsqueda."


def test_el_prompt_lleva_las_tres_reglas_y_el_aviso(monkeypatch):
    capturado = {}
    monkeypatch.setattr(mensajes, "has_llm_credentials", lambda cfg: True)
    monkeypatch.setattr(mensajes, "chat_with_llm",
                        lambda cfg, messages, **k: capturado.setdefault(
                            "p", messages[0]["content"]) and "ok")
    mensajes.generar(JOB, "CV con Python", PERFIL, "mail")
    prompt = capturado["p"]
    assert "Cero adjetivos" in prompt and "4 líneas" in prompt
    assert "Buscamos Data Scientist" in prompt and "CV con Python" in prompt
