"""Modo consejo: qué reordenar del CV para un aviso, sin reescribirlo."""

from vacantia import consejo
from vacantia.models import Job

CV = """# Ana Pérez
Analista de datos con 6 años de experiencia.

## Experiencia
- Reportes en Power BI para el área comercial.
- Consultas y modelado en SQL sobre bases de 10 millones de filas.
- Automatizaciones en Python.
"""

AVISO = Job(
    url="https://x.com/1",
    title="Analista de Datos Senior",
    company="ACME",
    description=(
        "Buscamos Analista de Datos Senior para el equipo comercial. "
        "Requisitos: SQL avanzado, Power BI, y experiencia con Snowflake. "
        "Deseable conocimiento de dbt y de modelado dimensional. "
        "Trabajamos con Snowflake todos los días y con dbt para transformar. "
    ),
)

PERFIL = {"llm": {}}


# --- lo que no necesita LLM -------------------------------------------------

def test_marca_lo_que_el_aviso_pide_y_el_cv_no_dice():
    faltantes = consejo.faltan_en_el_cv(AVISO, CV)
    assert "snowflake" in faltantes
    assert "dbt" in faltantes


def test_no_marca_lo_que_el_cv_ya_dice():
    faltantes = consejo.faltan_en_el_cv(AVISO, CV)
    assert "sql" not in faltantes
    assert not any(t.startswith("power") for t in faltantes)


def test_ignora_el_relleno_de_cualquier_aviso():
    faltantes = consejo.faltan_en_el_cv(AVISO, CV)
    for relleno in ("buscamos", "requisitos", "experiencia", "equipo", "deseable"):
        assert relleno not in faltantes


def test_un_par_cuyas_palabras_ya_estan_no_es_un_hueco_real():
    """'modelado dimensional' con 'modelado' en el CV es redacción, no falta de
    experiencia."""
    cv = CV + "\nModelado dimensional de datos.\n"
    assert "modelado dimensional" not in consejo.faltan_en_el_cv(AVISO, cv)


def test_los_terminos_de_dos_palabras_cuentan_como_uno():
    texto = "Power BI y Power BI para reportes. Power BI es excluyente."
    assert "power bi" in consejo.terminos_del_aviso(texto)


def test_lo_que_el_cv_incorpora_deja_de_aparecer():
    cv = CV + "\nSnowflake, dbt y modelado dimensional.\n"
    faltantes = consejo.faltan_en_el_cv(AVISO, cv)
    assert "snowflake" not in faltantes and "dbt" not in faltantes


def test_la_lista_tiene_un_techo():
    aviso = Job(url="u", title="Puesto", description=" ".join(
        f"herramienta{i}" for i in range(80)))
    assert len(consejo.faltan_en_el_cv(aviso, "CV vacío", limite=5)) == 5


def test_un_aviso_sin_descripcion_no_rompe():
    assert consejo.faltan_en_el_cv(Job(url="u", title="Puesto"), CV) == []


# --- el consejo escrito -----------------------------------------------------

def test_sin_credenciales_no_intenta_nada():
    texto, escrito = consejo.consejo_con_llm(AVISO, CV, PERFIL)
    assert texto == "" and escrito is False


def test_si_el_modelo_falla_no_tira_la_pantalla(monkeypatch):
    monkeypatch.setattr(consejo, "has_llm_credentials", lambda cfg: True)
    def explota(*a, **k):
        raise RuntimeError("sin cuota")
    monkeypatch.setattr(consejo, "chat_with_llm", explota)
    assert consejo.consejo_con_llm(AVISO, CV, PERFIL) == ("", False)


def test_el_prompt_prohibe_reescribir_el_cv_e_inventar(monkeypatch):
    capturado = {}
    monkeypatch.setattr(consejo, "has_llm_credentials", lambda cfg: True)
    monkeypatch.setattr(
        consejo, "chat_with_llm",
        lambda cfg, messages, **k: capturado.setdefault("p", messages[0]["content"]) and "ok",
    )
    consejo.consejo_con_llm(AVISO, CV, PERFIL)
    prompt = capturado["p"]
    assert "NO reescribas el CV" in prompt and "NO inventes experiencia" in prompt
    assert "QUÉ SUBIR" in prompt and "QUÉ NO TOCAR" in prompt
    assert "Snowflake" in prompt and "Power BI" in prompt      # aviso y CV


def test_devuelve_lo_que_escribio_el_modelo(monkeypatch):
    monkeypatch.setattr(consejo, "has_llm_credentials", lambda cfg: True)
    monkeypatch.setattr(consejo, "chat_with_llm", lambda cfg, **k: "  QUÉ SUBIR\n- SQL  ")
    texto, escrito = consejo.consejo_con_llm(AVISO, CV, PERFIL)
    assert escrito is True and texto == "QUÉ SUBIR\n- SQL"
