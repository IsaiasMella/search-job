"""El aviso de una corrida sin resultados tiene que distinguir
'no hubo ofertas' de 'se rompió algo'."""

from vacantia.engine import RunResult, empty_run_notes
from vacantia.filters import FilterStats


def stats(**by_reason) -> FilterStats:
    st = FilterStats()
    for etiqueta, n in by_reason.items():
        st.by_reason[etiqueta] = n
    st.dropped = sum(by_reason.values())
    return st


def test_corrida_sana_lo_dice_explicitamente():
    r = RunResult(fetched=40, new=5, scored=5, sources_used=["careers", "linkedin"])
    texto = "\n".join(empty_run_notes(r, stats(), 60))
    assert "40" in texto and "careers, linkedin" in texto
    assert "Ningún error" in texto
    assert "min_score de 60" in texto


def test_una_fuente_caida_aparece_en_el_aviso():
    r = RunResult(fetched=0, sources_used=["linkedin"],
                  skipped=["fuente 'careers' no disponible (falta TINYFISH_API_KEY)"])
    texto = "\n".join(empty_run_notes(r, stats(), 60))
    assert "TINYFISH_API_KEY" in texto
    assert "Ningún error" not in texto


def test_desglosa_los_motivos_de_descarte():
    r = RunResult(fetched=20, new=8, filled=2, deferred=1, scored=7,
                  sources_used=["linkedin"])
    texto = "\n".join(empty_run_notes(r, stats(language=4, work_mode=3), 60))
    assert "10 ya vistas o repetidas" in texto   # 20 - 8 nuevas - 2 cubiertas
    assert "2 ya cubiertas" in texto
    assert "1 diferidas para la próxima corrida" in texto
    assert "7 descartadas por los filtros" in texto
    assert "4 por language" in texto and "3 por work_mode" in texto


def test_sin_fuentes_no_miente_diciendo_que_esta_todo_bien():
    r = RunResult(fetched=0, sources_used=[], skipped=["sin fuentes disponibles"])
    texto = "\n".join(empty_run_notes(r, stats(), 60))
    assert "ninguna" in texto and "sin fuentes disponibles" in texto
