"""Dedupe por URL y por (empresa + título normalizado), entre fuentes."""

from vacantia.models import Job, normalize_company, normalize_title
from vacantia.state import State


def job(url, title="Data Scientist", company="Globant", **kw) -> Job:
    return Job(url=url, title=title, company=company, **kw)


# --- normalización ---------------------------------------------------------

def test_titulo_ignora_orden_ruido_y_parentesis():
    assert normalize_title("Senior Data Scientist (Remote)") == normalize_title(
        "data-scientist-senior"
    )


def test_titulo_distinto_no_colapsa():
    assert normalize_title("Data Scientist") != normalize_title("Data Engineer")


def test_empresa_ignora_el_pais_y_la_forma_societaria():
    assert normalize_company("Globant Argentina") == normalize_company("Globant S.A.")


def test_sin_empresa_no_hay_clave_secundaria():
    assert job("https://x/1", company="").dedupe_key == ""


# --- dedupe dentro del lote ------------------------------------------------

def test_misma_oferta_por_dos_fuentes_queda_una(tmp_path):
    st = State("test", root=tmp_path)
    careers = job("https://globant.com/jobs/data-scientist-senior",
                  title="Data Scientist Senior", source="careers")
    linkedin = job("https://linkedin.com/jobs/view/999",
                   title="Senior Data Scientist (Remote)", source="linkedin",
                   description="x" * 900, work_mode="remote", country="Argentina")
    nuevas = st.filter_new([careers, linkedin])
    assert len(nuevas) == 1


def test_se_queda_con_la_copia_mas_completa(tmp_path):
    """La de careers suele ser un título sacado del slug; la de LinkedIn trae
    modalidad, país y la descripción entera."""
    st = State("test", root=tmp_path)
    careers = job("https://globant.com/jobs/data-scientist", source="careers")
    linkedin = job("https://linkedin.com/jobs/view/999", source="linkedin",
                   description="x" * 900, work_mode="remote", country="Argentina")
    assert st.filter_new([careers, linkedin])[0].source == "linkedin"
    # y da igual el orden en que lleguen las fuentes
    st2 = State("test2", root=tmp_path)
    assert st2.filter_new([linkedin, careers])[0].source == "linkedin"


def test_ofertas_distintas_de_la_misma_empresa_sobreviven(tmp_path):
    st = State("test", root=tmp_path)
    nuevas = st.filter_new([
        job("https://x/1", title="Data Scientist"),
        job("https://x/2", title="Data Engineer"),
        job("https://x/3", title="Data Scientist", company="Mutt Data"),
    ])
    assert len(nuevas) == 3


def test_url_repetida_se_sigue_deduplicando(tmp_path):
    st = State("test", root=tmp_path)
    nuevas = st.filter_new([job("https://x/1"), job("https://x/1/?utm=a")])
    assert len(nuevas) == 1


def test_sin_empresa_no_se_pisan_entre_si(tmp_path):
    """Dos posts de google_posts sin empresa y con el mismo título son ofertas
    distintas: sin empresa no se deduplica por título."""
    st = State("test", root=tmp_path)
    nuevas = st.filter_new([
        job("https://x/1", company=""),
        job("https://x/2", company=""),
    ])
    assert len(nuevas) == 2


# --- dedupe entre corridas -------------------------------------------------

def test_la_copia_de_otra_fuente_no_vuelve_en_la_proxima_corrida(tmp_path):
    linkedin = job("https://linkedin.com/jobs/view/999",
                   title="Senior Data Scientist", source="linkedin")
    st = State("test", root=tmp_path)
    st.mark_seen(st.filter_new([linkedin]))
    st.save([linkedin])

    # Corrida siguiente: la misma búsqueda aparece en la careers page, con
    # otra URL. Sin la clave secundaria entraría como nueva.
    careers = job("https://globant.com/jobs/data-scientist-senior",
                  title="Data Scientist Senior", source="careers")
    assert State("test", root=tmp_path).filter_new([careers]) == []


def test_estado_viejo_sin_seen_alt_keys_no_rompe(tmp_path):
    import json
    d = tmp_path / "test"
    d.mkdir()
    (d / "seen_jobs.json").write_text(
        json.dumps({"seen_keys": ["https://x/1"], "last_run": None}), encoding="utf-8"
    )
    st = State("test", root=tmp_path)
    assert st.seen_alt_keys == set()
    assert st.filter_new([job("https://x/1"), job("https://x/2", title="Data Engineer")]) != []
