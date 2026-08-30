"""La UI local: levanta el servidor de verdad y le pega con urllib."""

import json
import shutil
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from vacantia.state import State
from vacantia.ui.server import Handler

REPO = Path(__file__).resolve().parent.parent

OFERTAS = [
    {
        "url": "https://empresa.com/jobs/1",
        "title": "Data Scientist",
        "company": "ACME",
        "source": "linkedin",
        "score": 82,
        "reason": "Encaja con el CV",
        "found_at": "2026-08-29T10:00:00+00:00",
        "aplicado": None,
        "motivo_descarte": "",
        "fecha_feedback": "",
    },
    {
        "url": "https://empresa.com/jobs/2",
        "title": "Analista de Datos Jr",
        "company": "Otra SA",
        "source": "careers",
        "score": 45,
        "found_at": "2026-08-28T10:00:00+00:00",
        "aplicado": None,
        "motivo_descarte": "",
        "fecha_feedback": "",
    },
]


@pytest.fixture
def sitio(tmp_path, monkeypatch):
    """Una instalación de juguete, con su propio perfil y su propio historial."""
    (tmp_path / "profiles").mkdir()
    (tmp_path / "resume").mkdir()
    shutil.copyfile(REPO / "profiles" / "example.json", tmp_path / "profiles" / "example.json")
    (tmp_path / "profiles" / "test.json").write_text(json.dumps({
        "name": "test",
        "cv_path": "resume/test.md",
        "keywords": ["Python"],
        "min_score": 60,
        "top_n": 5,
        "filters": {"location": {"country": "Argentina", "city": "", "home_city": ""},
                    "work_modes": ["remote"],
                    "language": {"allow_english": False, "max_english_level": "A2"}},
        "candidate": {"name": "Test"},
        "sources": [{"type": "careers", "enabled": True, "companies_file": "companies.json"}],
        "notifiers": [{"type": "console", "enabled": True}],
    }, indent=2), encoding="utf-8")
    (tmp_path / "resume" / "test.md").write_text("# CV de prueba\n", encoding="utf-8")
    (tmp_path / "companies.json").write_text(
        json.dumps([{"name": "ACME", "careers_url": "https://acme.com/jobs",
                     "search_domain": "acme.com", "use_search": False}]), encoding="utf-8")
    estado = tmp_path / "state" / "test"
    estado.mkdir(parents=True)
    (estado / "job_history.json").write_text(json.dumps(OFERTAS), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{servidor.server_port}", tmp_path
    servidor.shutdown()
    servidor.server_close()


def get(base, ruta):
    with urlopen(base + ruta) as r:
        return r.status, r.read().decode("utf-8"), r.url


def post(base, ruta, campos):
    req = Request(base + ruta, data=urlencode(campos).encode("utf-8"), method="POST")
    with urlopen(req) as r:                     # urllib sigue el 303 solo
        return r.status, r.read().decode("utf-8"), r.url


# --- pestaña Trabajos ------------------------------------------------------

def test_la_raiz_lleva_a_trabajos(sitio):
    base, _ = sitio
    _, html, url = get(base, "/")
    assert "/trabajos" in url
    assert "Data Scientist" in html


def test_lista_las_ofertas_con_su_puntaje(sitio):
    base, _ = sitio
    _, html, _ = get(base, "/trabajos?perfil=test")
    assert "Data Scientist" in html and "82" in html
    assert "https://empresa.com/jobs/1" in html
    assert "Apliqué" in html and "No apliqué" in html


def test_marcar_que_aplique_lo_guarda(sitio):
    base, tmp = sitio
    post(base, "/feedback", {"perfil": "test", "ver": "pendientes",
                             "url": "https://empresa.com/jobs/1", "aplicado": "si"})
    historial = {h["url"]: h for h in State("test").load_history()}
    guardada = historial["https://empresa.com/jobs/1"]
    assert guardada["aplicado"] is True
    assert guardada["fecha_feedback"]


def test_descartar_guarda_el_motivo(sitio):
    base, _ = sitio
    post(base, "/feedback", {"perfil": "test", "ver": "pendientes",
                             "url": "https://empresa.com/jobs/2",
                             "aplicado": "no", "motivo": "Es junior"})
    historial = {h["url"]: h for h in State("test").load_history()}
    assert historial["https://empresa.com/jobs/2"]["aplicado"] is False
    assert historial["https://empresa.com/jobs/2"]["motivo_descarte"] == "Es junior"


def test_descartar_sin_motivo_no_guarda_nada(sitio):
    """El motivo es obligatorio: es lo único que después sirve para aprender."""
    base, _ = sitio
    _, html, _ = post(base, "/feedback", {"perfil": "test", "ver": "pendientes",
                                          "url": "https://empresa.com/jobs/2",
                                          "aplicado": "no", "motivo": "   "})
    assert "motivo" in html.lower()
    historial = {h["url"]: h for h in State("test").load_history()}
    assert historial["https://empresa.com/jobs/2"]["aplicado"] is None


def test_los_filtros_separan_pendientes_de_marcadas(sitio):
    base, _ = sitio
    post(base, "/feedback", {"perfil": "test", "ver": "pendientes",
                             "url": "https://empresa.com/jobs/1", "aplicado": "si"})
    _, pendientes, _ = get(base, "/trabajos?perfil=test&ver=pendientes")
    assert "Data Scientist" not in pendientes
    _, aplicadas, _ = get(base, "/trabajos?perfil=test&ver=aplicadas")
    assert "Data Scientist" in aplicadas


# --- pestaña Mis datos -----------------------------------------------------

def test_el_formulario_trae_los_datos_actuales(sitio):
    base, _ = sitio
    _, html, _ = get(base, "/datos?perfil=test")
    assert "Python" in html and "Argentina" in html
    assert "CV de prueba" in html


def test_guardar_escribe_el_perfil_el_cv_y_las_empresas(sitio):
    base, tmp = sitio
    post(base, "/datos", {
        "perfil": "test",
        "keywords": "Python, SQL",
        "min_score": "70", "top_n": "8", "max_new_per_run": "30",
        "pais": "Argentina", "ciudad": "Bahía Blanca, Punta Alta",
        "modo_remote": "1", "modo_hybrid": "1",
        "max_english_level": "B1",
        "notify_when_empty": "1",
        "cv": "# CV nuevo\nPython.",
        "empresas": "ACME | https://acme.com/jobs | acme.com\nGlobant | https://globant.com/jobs |",
        "rrhh": "https://linkedin.com/in/recluta1\n",
        "fuente_careers": "1", "fuente_linkedin": "1",
        "cand_name": "Test", "cand_profile": "", "cand_seeking": "", "cand_not_suitable": "",
    })

    perfil = json.loads((tmp / "profiles" / "test.json").read_text(encoding="utf-8"))
    assert perfil["keywords"] == ["Python", "SQL"]
    assert perfil["min_score"] == 70 and perfil["top_n"] == 8
    assert perfil["filters"]["location"]["city"] == ["Bahía Blanca", "Punta Alta"]
    assert "home_city" not in perfil["filters"]["location"]
    assert perfil["filters"]["work_modes"] == ["remote", "hybrid"]
    assert perfil["filters"]["language"]["allow_english"] is False   # no vino tildado
    assert perfil["notify_when_empty"] is True

    fuentes = {s["type"]: s for s in perfil["sources"]}
    assert fuentes["careers"]["enabled"] is True
    assert fuentes["google_posts"]["enabled"] is False      # existía y se apagó
    assert fuentes["rrhh"]["profiles"] == ["https://linkedin.com/in/recluta1"]

    assert (tmp / "resume" / "test.md").read_text(encoding="utf-8").startswith("# CV nuevo")
    empresas = json.loads((tmp / "companies.json").read_text(encoding="utf-8"))
    assert [c["name"] for c in empresas] == ["ACME", "Globant"]
    # El use_search de ACME no estaba en el formulario y no se perdió.
    assert empresas[0]["use_search"] is False


def test_guardar_no_pisa_las_claves_con_vacio(sitio):
    base, tmp = sitio
    (tmp / ".env").write_text("TELEGRAM_TOKEN=abc123\n", encoding="utf-8")
    post(base, "/datos", {"perfil": "test", "keywords": "Python",
                          "TELEGRAM_TOKEN": "", "TELEGRAM_CHAT_ID": "555"})
    env = (tmp / ".env").read_text(encoding="utf-8")
    assert "TELEGRAM_TOKEN=abc123" in env      # no se borró
    assert "TELEGRAM_CHAT_ID=555" in env       # se agregó


# --- CV en PDF -------------------------------------------------------------

def test_el_boton_de_descargar_el_cv_devuelve_un_pdf(sitio):
    base, _ = sitio
    from urllib.request import urlopen
    with urlopen(base + "/cv.pdf?perfil=test") as r:
        cuerpo = r.read()
        assert r.headers["Content-Type"] == "application/pdf"
        assert "CV_test.pdf" in r.headers["Content-Disposition"]
    assert cuerpo.startswith(b"%PDF-")


def test_sin_cv_cargado_avisa_en_vez_de_bajar_un_pdf_vacio(sitio):
    base, tmp = sitio
    (tmp / "resume" / "test.md").write_text("      ", encoding="utf-8")
    _, html, url = get(base, "/cv.pdf?perfil=test")
    assert "Mis datos" in html and "trabajos" in url


# --- crear perfil ----------------------------------------------------------

def test_crear_perfil_deja_todo_en_blanco_listo_para_completar(sitio):
    base, tmp = sitio
    _, html, url = post(base, "/perfil-nuevo", {"nombre": "maria"})
    assert "perfil=maria" in url
    perfil = json.loads((tmp / "profiles" / "maria.json").read_text(encoding="utf-8"))
    assert perfil["name"] == "maria"
    assert perfil["cv_path"] == "resume/maria.md"
    assert (tmp / "resume" / "maria.md").exists()


@pytest.mark.parametrize("nombre", ["", "a", "María", "raro!", "example", "test"])
def test_nombres_invalidos_o_repetidos_se_rechazan(sitio, nombre):
    """Vacío, muy corto, con acentos, con símbolos, la plantilla, o uno repetido.

    Los espacios sí se aceptan: "juan pablo" se guarda como juan_pablo.
    """
    base, tmp = sitio
    antes = sorted(p.name for p in (tmp / "profiles").glob("*.json"))
    _, html, _ = post(base, "/perfil-nuevo", {"nombre": nombre})
    assert "aviso error" in html
    assert sorted(p.name for p in (tmp / "profiles").glob("*.json")) == antes


# --- mensajes para el reclutador -------------------------------------------

def test_la_pagina_de_mensajes_trae_los_dos_moldes(sitio):
    base, _ = sitio
    _, html, _ = get(base, "/mensajes?perfil=test&url=https%3A%2F%2Fempresa.com%2Fjobs%2F1")
    assert "DM por LinkedIn" in html and "Mail a RRHH" in html
    assert "Data Scientist" in html and "ACME" in html
    # Sin credenciales de LLM, los huecos quedan a la vista para completar.
    assert "{tu logro" in html or "logro" in html


def test_una_url_que_no_esta_vuelve_a_trabajos(sitio):
    base, _ = sitio
    _, html, url = get(base, "/mensajes?perfil=test&url=https%3A%2F%2Fno-existe.com%2F9")
    assert "trabajos" in url and "No encontré" in html


def test_el_perfil_nuevo_sale_del_molde_con_los_huecos_a_la_vista(sitio):
    """No se inventan datos de nadie: se crea en blanco y lo completa la persona."""
    base, tmp = sitio
    post(base, "/perfil-nuevo", {"nombre": "juan pablo"})     # el espacio se normaliza
    perfil = json.loads((tmp / "profiles" / "juan_pablo.json").read_text(encoding="utf-8"))
    assert perfil["keywords"] == []
    assert "COMPLETAR" in perfil["candidate"]["name"]
    assert "_comentario" not in perfil          # la nota es del molde
    cv = (tmp / "resume" / "juan_pablo.md").read_text(encoding="utf-8")
    assert "PEGAR CV ACÁ" in cv


def test_el_perfil_nuevo_aparece_en_el_selector(sitio):
    base, _ = sitio
    post(base, "/perfil-nuevo", {"nombre": "maria"})
    _, html, _ = get(base, "/trabajos?perfil=test")
    assert 'value="maria"' in html and 'value="test"' in html


def test_una_sola_ciudad_se_guarda_como_texto(sitio):
    base, tmp = sitio
    post(base, "/datos", {"perfil": "test", "keywords": "Python", "pais": "Argentina",
                          "ciudad": "  La Plata  "})
    perfil = json.loads((tmp / "profiles" / "test.json").read_text(encoding="utf-8"))
    assert perfil["filters"]["location"]["city"] == "La Plata"


def test_el_formulario_muestra_la_ciudad_de_un_perfil_viejo_con_home_city(sitio):
    base, tmp = sitio
    ruta = tmp / "profiles" / "test.json"
    perfil = json.loads(ruta.read_text(encoding="utf-8"))
    perfil["filters"]["location"] = {"country": "Argentina", "city": "",
                                     "home_city": "Bahía Blanca"}
    ruta.write_text(json.dumps(perfil), encoding="utf-8")
    _, html, _ = get(base, "/datos?perfil=test")
    assert "Bahía Blanca" in html
