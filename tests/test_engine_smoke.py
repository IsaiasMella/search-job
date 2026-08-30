"""Corrida completa de punta a punta con la fuente dummy, sin red ni LLM."""

import pytest

from vacantia import engine
from vacantia.models import Job
from vacantia.notifiers.base import Notifier

PERFIL = {
    "name": "test",
    "min_score": 0,
    "cv_path": "resume/EJEMPLO_CV.md",
    "keywords": ["Python"],
    "filters": {
        "location": {"country": "Argentina", "home_city": "Bahía Blanca"},
        "work_modes": ["remote"],
        "language": {"allow_english": True},
    },
    "llm": {"provider": "gemini"},
    "sources": [{"type": "dummy", "enabled": True}],
    "notifiers": [{"type": "console", "enabled": True}],
}


class NotifierEspia(Notifier):
    name = "console"
    enviados: list[tuple[list[Job], list[str] | None]] = []

    def send(self, jobs, notes=None) -> bool:
        NotifierEspia.enviados.append((jobs, notes))
        return True


@pytest.fixture
def sin_llm(monkeypatch):
    """Sin API keys en el entorno el scoring cae a la heurística: nada de red."""
    for var in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    NotifierEspia.enviados = []
    monkeypatch.setattr(engine, "ConsoleNotifier", NotifierEspia)


def test_corrida_completa_en_dry_run(sin_llm):
    result = engine.run(PERFIL, dry_run=True)
    assert result.fetched > 0
    assert result.scored == result.new
    assert result.matched == len(result.jobs)


def test_una_corrida_sin_coincidencias_explica_por_que(sin_llm):
    """min_score imposible: no pasa ninguna, y el aviso tiene que decir qué pasó."""
    engine.run({**PERFIL, "min_score": 101}, dry_run=True)
    jobs, notes = NotifierEspia.enviados[-1]
    assert jobs == []
    texto = "\n".join(notes)
    assert "Sin coincidencias" in texto and "min_score de 101" in texto


def test_las_vacantes_cubiertas_no_llegan_al_scoring(sin_llm, monkeypatch):
    cerrada = Job(url="https://x.com/jobs/9", title="Data Scientist",
                  company="ACME", description="La búsqueda ya está cerrada.")
    monkeypatch.setattr(engine, "collect", lambda sources, result: [cerrada])
    result = engine.run(PERFIL, dry_run=True)
    assert (result.fetched, result.filled, result.new, result.scored) == (1, 1, 0, 0)


# --- varios perfiles en la misma instalación -------------------------------

def test_correr_todos_los_perfiles_no_se_frena_con_uno_que_falla(monkeypatch, tmp_path):
    """Los perfiles de una misma PC comparten las claves, así que van uno
    después del otro; y si uno explota, los demás igual buscan."""
    from vacantia import run as run_mod

    corridos = []
    monkeypatch.setattr(run_mod, "available_profiles_reales", lambda: ["ana", "roto", "zoe"])
    monkeypatch.setattr(run_mod, "load_profile", lambda n: {"name": n})
    monkeypatch.setattr(run_mod.time, "sleep", lambda s: None)

    import vacantia.engine as engine_mod

    def falso_run(perfil, dry_run=False):
        corridos.append(perfil["name"])
        if perfil["name"] == "roto":
            raise RuntimeError("se cayó la fuente")
        return engine.RunResult()

    monkeypatch.setattr(engine_mod, "run", falso_run)
    codigo = run_mod.correr_todos(gap=0)

    assert corridos == ["ana", "roto", "zoe"]
    assert codigo == 1          # avisa que uno falló


def test_sin_perfiles_correr_todos_avisa(monkeypatch):
    from vacantia import run as run_mod
    monkeypatch.setattr(run_mod, "available_profiles_reales", lambda: [])
    assert run_mod.correr_todos(gap=0) == 2
