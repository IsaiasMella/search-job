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
                          "TELEGRAM_TOKEN": "", "GEMINI_API_KEY": "nueva"})
    env = (tmp / ".env").read_text(encoding="utf-8")
    assert "TELEGRAM_TOKEN=abc123" in env      # no se borró
    assert "GEMINI_API_KEY=nueva" in env       # se agregó


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
    assert "un requisito del aviso que tu CV respalde" in html


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


# --- Telegram, que es de cada persona y no de la computadora ----------------

def test_cada_perfil_guarda_su_propio_chat_de_telegram(sitio):
    """Dos personas en la misma compu tienen que recibir sus propias ofertas."""
    base, tmp = sitio
    post(base, "/perfil-nuevo", {"nombre": "novio"})
    post(base, "/datos", {"perfil": "test", "keywords": "Python", "chat_id": "111"})
    post(base, "/datos", {"perfil": "novio", "keywords": "Java", "chat_id": "222"})

    def chat_de(nombre):
        perfil = json.loads((tmp / "profiles" / f"{nombre}.json").read_text(encoding="utf-8"))
        return {n["type"]: n for n in perfil["notifiers"]}["telegram"]["chat_id"]

    assert chat_de("test") == "111"
    assert chat_de("novio") == "222"


def test_sin_chat_propio_se_usa_el_compartido_del_env(sitio):
    base, tmp = sitio
    post(base, "/datos", {"perfil": "test", "keywords": "Python", "chat_id": "  "})
    perfil = json.loads((tmp / "profiles" / "test.json").read_text(encoding="utf-8"))
    telegram = {n["type"]: n for n in perfil["notifiers"]}["telegram"]
    assert telegram["chat_id"] == "${TELEGRAM_CHAT_ID}"


def test_el_chat_propio_se_muestra_en_el_formulario(sitio):
    base, _ = sitio
    post(base, "/datos", {"perfil": "test", "keywords": "Python", "chat_id": "98765"})
    _, html, _ = get(base, "/datos?perfil=test")
    assert "98765" in html


def test_la_clave_del_bot_sigue_siendo_compartida(sitio):
    """El token del bot es de la computadora; el chat, de cada uno."""
    base, tmp = sitio
    post(base, "/datos", {"perfil": "test", "keywords": "Python",
                          "TELEGRAM_TOKEN": "123:abc", "chat_id": "111"})
    assert "TELEGRAM_TOKEN=123:abc" in (tmp / ".env").read_text(encoding="utf-8")
    perfil = json.loads((tmp / "profiles" / "test.json").read_text(encoding="utf-8"))
    assert "123:abc" not in json.dumps(perfil)      # nunca en el perfil


# --- consejo para el CV ----------------------------------------------------

def test_la_pagina_de_consejo_muestra_lo_que_falta_en_el_cv(sitio):
    base, tmp = sitio
    (tmp / "resume" / "test.md").write_text("Analista con SQL y Excel.", encoding="utf-8")
    historial = json.loads((tmp / "state" / "test" / "job_history.json").read_text(encoding="utf-8"))
    historial[0]["description"] = ("Buscamos Analista con Snowflake. "
                                   "Snowflake y dbt son excluyentes, usamos dbt a diario.")
    (tmp / "state" / "test" / "job_history.json").write_text(json.dumps(historial), encoding="utf-8")

    _, html, _ = get(base, "/consejo?perfil=test&url=https%3A%2F%2Fempresa.com%2Fjobs%2F1")
    assert "snowflake" in html and "dbt" in html
    assert "No las agregues si no las" in html      # el aviso de no mentir
    # Sin credenciales de LLM se ofrece el botón, no un error.
    assert "qué reordenar" in html


def test_el_consejo_de_una_url_desconocida_vuelve_a_trabajos(sitio):
    base, _ = sitio
    _, html, url = get(base, "/consejo?perfil=test&url=https%3A%2F%2Fno-existe%2F1")
    assert "trabajos" in url and "No encontré" in html


def test_avisa_que_bumeran_y_zonajobs_comparten_los_avisos(tmp_path, monkeypatch):
    """Los dos son de Navent y devuelven exactamente los mismos avisos.

    Verificado a mano: Zonajobs trajo 5 de 5 idénticos a los de Bumeran, con el
    mismo id de aviso. El propio Bumeran lo dice en las páginas republicadas
    ("Este aviso fue publicado por ZonaJobs"). Sin el aviso en pantalla, quien
    no programa prende los dos y recibe todo duplicado por Telegram.
    """
    from vacantia.ui import formulario

    html = formulario.render("ana", {"keywords": ["Python"]}, [])
    assert "Misma base de avisos que Bumeran" in html
    assert "Misma base de avisos que Zonajobs" in html


def test_el_tilde_y_el_campo_de_reclutadores_no_se_llaman_igual():
    """Se llamaban los dos "Perfiles de reclutadores que sigo".

    Uno es el interruptor de la fuente y el otro el cuadro donde van las URLs,
    con "Empresas que sigo" en el medio. Con el mismo nombre, no se encontraba
    dónde pegarlas.
    """
    from vacantia.ui import formulario

    html = formulario.render("ana", {"keywords": ["Python"]}, [])

    # El tilde conserva el nombre de la fuente...
    assert "> Perfiles de reclutadores que sigo</label>" in html
    # ...y el cuadro de texto pasa a decir qué va adentro.
    assert '<label for="rrhh">Las URLs de esos reclutadores</label>' in html
    assert '<label for="rrhh">Perfiles de reclutadores que sigo</label>' not in html
    # Y el recuadro nombra al tilde, para que se vea que van juntos.
    assert "arriba tiene que estar tildado" in html


def test_el_recuadro_explica_que_pagina_pegar_y_cual_no():
    """Del perfil pelado de LinkedIn no sale nada: hay que ir a su actividad.

    Y de la home de una consultora tampoco: va la página que lista las
    búsquedas. Es lo que nadie se acuerda, y cuando se equivoca la fuente
    devuelve 0 sin decir por qué. Va en un recuadro aparte, no en la ayuda
    gris, porque hay que poder encontrarlo de nuevo cada vez.
    """
    from vacantia.ui import formulario

    html = formulario.render("ana", {"keywords": ["Python"]}, [])

    assert 'class="pista"' in html
    assert "El perfil de LinkedIn de la persona" in html   # ahora sí anda, por el rodeo
    assert "Búsquedas activas" in html              # lo que sí hay que pegar
    assert "0 publicación(es)" in html              # el síntoma de haberla errado
    # Y como ejemplo dentro del cuadro vacío, que se ve sin leer nada.
    assert 'placeholder="https://www.linkedin.com/in/nombre-apellido' in html


# --- el rediseño de la pantalla -------------------------------------------

def _paginas_para_auditar():
    """Todas las vistas, con datos de prueba propios (nada del CV real)."""
    from vacantia.ui import formulario, render

    perfil = {"keywords": ["Python"], "sources": [{"type": "rrhh", "enabled": True}]}
    oferta = {"url": "https://x/1", "title": "Data Scientist", "score": 70,
              "found_at": "2026-09-04", "company": "ACME", "reason": "Encaja"}
    return {
        "trabajos": render.trabajos("ana", [oferta], {"pendientes": 1}, "pendientes", []),
        "vacio": render.trabajos("ana", [], {}, "descartadas", []),
        "mensajes": render.mensajes("ana", oferta, {"dm": "a", "mail": "b"}, False, []),
        "consejo": render.consejo("ana", oferta, ["sql"], "texto", True, []),
        "datos": formulario.render("ana", perfil, []),
    }


def test_ninguna_pantalla_muestra_em_dash():
    """Se cuela sin que se note y queda de firma de texto generado.

    Se mira el texto ya renderizado, no el código: la vez que se coló fue
    dentro de un `&mdash;` y de un bloque que el grep del archivo salteaba.
    El CV de la persona no cuenta: ese texto es suyo y no se le toca.
    """
    import html as H
    import re

    for nombre, pagina in _paginas_para_auditar().items():
        sin_script = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", pagina,
                            flags=re.S | re.I)
        visible = H.unescape(re.sub(r"<[^>]+>", " ", sin_script))
        assert "\u2014" not in visible, f"em-dash visible en la pantalla '{nombre}'"
        assert "\u2013" not in visible, f"en-dash visible en la pantalla '{nombre}'"


def test_cada_filtro_vacio_dice_algo_distinto():
    """"No hay ofertas" desperdicia el momento de más atención de la pantalla.

    Sin ninguna descartada, lo útil es explicar para qué sirve descartar; en
    la primera corrida, lo útil es decir qué archivo hay que abrir.
    """
    from vacantia.ui import render

    primera = render.trabajos("ana", [], {}, "todas", [])
    sin_descartes = render.trabajos("ana", [], {}, "descartadas", [])

    assert "buscar_ahora.bat" in primera
    assert "No apliqué" in sin_descartes and "buscar_ahora.bat" not in sin_descartes


def test_la_pantalla_se_adapta_al_tema_del_sistema():
    """Se usa de noche y de día. Sin esto, de noche encandila."""
    from vacantia.ui.render import CSS

    assert "prefers-color-scheme: dark" in CSS
    assert "color-scheme: dark" in CSS
    # Los colores se declaran una sola vez, como tokens: si una regla escribe
    # un color suelto, el modo oscuro se olvida de esa regla.
    assert CSS.count("var(--texto)") > 3 and CSS.count("var(--papel)") > 3


def test_se_puede_navegar_con_teclado():
    from vacantia.ui.render import CSS, pagina

    assert ":focus-visible" in CSS                 # dónde estoy parado
    assert "prefers-reduced-motion" in CSS         # quien pide menos movimiento
    assert 'href="#contenido"' in pagina("t", "c", "ana", ["ana"], "trabajos")


def test_el_motivo_faltante_se_avisa_al_lado_del_campo():
    """Antes era un alert(): tapaba la pantalla y no decía cuál de las 200 ofertas."""
    from vacantia.ui.render import JS, _tarjeta

    assert "alert(" not in JS
    assert "aria-invalid" in JS
    tarjeta = _tarjeta({"url": "https://x/1", "title": "T"}, "ana", "pendientes")
    assert 'class="error-motivo"' in tarjeta


# --- filtro por antigüedad y el costo del inglés ---------------------------

def _con_historial(tmp, entradas):
    """Reescribe el historial del perfil de prueba."""
    import json as _json
    ruta = tmp / "state" / "test" / "job_history.json"
    ruta.write_text(_json.dumps(entradas), encoding="utf-8")


# Las fechas se calculan contra el día en que corren los tests, nunca fijas:
# con "2026-09-04" escrito a mano estos tests pasaban ese día y se caían al
# siguiente. Pasó de verdad, a la medianoche.
from datetime import date as _date, datetime as _dt, timezone as _tz  # noqa: E402

HOY_ISO = _dt.now(_tz.utc).isoformat()
HOY_YMD = _date.today().isoformat()

VARIADAS = [
    {"url": "https://e/nueva", "title": "Recien publicada", "aplicado": None,
     "posted_at": HOY_YMD, "found_at": HOY_ISO},
    {"url": "https://e/semana", "title": "De esta semana", "aplicado": None,
     "posted_at": "hace 3 dias", "found_at": HOY_ISO},
    {"url": "https://e/mes", "title": "Del mes pasado", "aplicado": None,
     "posted_at": "hace 1 mes", "found_at": HOY_ISO},
    {"url": "https://e/antigua", "title": "Del ano pasado", "aplicado": None,
     "posted_at": "hace 11 meses", "found_at": HOY_ISO},
    # El aviso no dice cuándo se publicó, pero sí sabemos cuándo lo vimos: la
    # tarjeta tiene que decir "visto", no "publicado".
    {"url": "https://e/solovisto", "title": "Solo visto", "aplicado": None,
     "posted_at": "", "found_at": HOY_ISO},
    # Sin NINGUNA de las dos fechas: es el caso que no se tiene que esconder.
    # Con `found_at` puesto no probaba nada, porque se caía a esa fecha.
    {"url": "https://e/sinfecha", "title": "Sin fecha", "aplicado": None,
     "posted_at": "", "found_at": ""},
]


def test_el_filtro_de_fecha_saca_las_viejas(sitio):
    """El caso real: 207 avisos, muchos del mes pasado y ya cubiertos."""
    base, tmp = sitio
    _con_historial(tmp, VARIADAS)

    _, semana, _ = get(base, "/trabajos?perfil=test&desde=7d")
    assert "Recien publicada" in semana and "De esta semana" in semana
    assert "Del mes pasado" not in semana and "Del ano pasado" not in semana

    _, todo, _ = get(base, "/trabajos?perfil=test&desde=todo")
    assert "Del ano pasado" in todo


def test_un_aviso_sin_fecha_no_se_esconde(sitio):
    """No tener el dato no es lo mismo que ser viejo.

    Casi la mitad de los avisos no dicen cuándo se publicaron. Si el filtro los
    tirara, "Hoy" escondería la mitad de la lista sin explicar por qué.
    """
    base, tmp = sitio
    _con_historial(tmp, VARIADAS)
    _, hoy, _ = get(base, "/trabajos?perfil=test&desde=hoy")
    assert "Sin fecha" in hoy


def test_la_tarjeta_distingue_publicado_de_visto(sitio):
    base, tmp = sitio
    _con_historial(tmp, VARIADAS)
    _, html, _ = get(base, "/trabajos?perfil=test&desde=todo")
    assert "publicado hoy" in html          # el aviso lo dijo
    assert "visto hoy" in html              # no lo dijo: es cuándo lo encontramos


def test_los_dos_filtros_se_cruzan_sin_pisarse(sitio):
    """Cambiar de estado no puede resetear el rango de fechas, ni al revés."""
    base, tmp = sitio
    _con_historial(tmp, VARIADAS)
    _, html, _ = get(base, "/trabajos?perfil=test&ver=descartadas&desde=7d")
    assert "ver=descartadas&desde=hoy" in html or "desde=hoy" in html
    assert "desde=7d&ver=aplicadas" in html or "ver=aplicadas" in html


def test_marcar_una_oferta_no_te_devuelve_a_la_lista_completa(sitio):
    """Antes cada clic reseteaba el filtro y había que volver a elegirlo."""
    base, tmp = sitio
    _con_historial(tmp, VARIADAS)
    _, _, url = post(base, "/feedback", {
        "perfil": "test", "ver": "pendientes", "desde": "7d",
        "url": "https://e/semana", "aplicado": "si",
    })
    assert "desde=7d" in url


def test_el_cartel_dice_cuantas_se_pierden_por_ingles(sitio):
    """Pedido explícito, y el pedido incluía que incomode.

    Ver sólo las ofertas en español da la impresión de que el mercado es así;
    lo que se ve es el recorte del filtro. El número lo desarma.
    """
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": "https://e/1", "title": "Con ingles", "aplicado": None, "score": 88,
         "requires_english": True, "found_at": HOY_ISO},
        {"url": "https://e/2", "title": "Sin ingles", "aplicado": None, "score": 60,
         "found_at": HOY_ISO},
    ])
    _, html, _ = get(base, "/trabajos?perfil=test&desde=todo")
    assert 'class="duele"' in html
    assert "piden inglés" in html
    assert "88" in html                     # cuánto valía la mejor que se perdió


def test_sin_ofertas_perdidas_no_hay_cartel(sitio):
    """El cartel tiene que significar algo: en cero no se muestra."""
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": "https://e/2", "title": "Sin ingles", "aplicado": None, "score": 60,
         "found_at": HOY_ISO},
    ])
    _, html, _ = get(base, "/trabajos?perfil=test&desde=todo")
    assert 'class="duele"' not in html


def test_como_me_presento_es_un_campo_aparte_del_perfil_largo():
    """En "en una línea, qué hago" la gente escribe un párrafo con el stack.

    En el mensaje al reclutador eso tiene que entrar en media frase ("soy AI
    Engineer"), así que va en su propio campo.
    """
    from vacantia.ui import formulario

    html = formulario.render("ana", {"candidate": {"headline": "AI Engineer"}}, [])
    assert '<label for="cand_headline">Cómo me presento</label>' in html
    assert 'value="AI Engineer"' in html


def test_avisa_de_las_ofertas_nuevas_sin_recargar_sola(sitio):
    """Tener que apretar F5 para ver si entró algo es una porquería.

    Pero recargar sola tampoco: si alguien está escribiendo el motivo de un
    descarte, la recarga se lo borra. Avisa con un cartel y decide la persona.
    """
    base, tmp = sitio
    _, html, _ = get(base, "/trabajos?perfil=test")

    assert 'id="novedades"' in html
    assert "vigilarNovedades('test'" in html
    assert "location.reload()" in html          # lo dispara el botón, no el timer

    # La marca cambia sólo cuando cambia el historial.
    import json as _json
    antes = _json.loads(get(base, "/novedades?perfil=test")[1])
    ruta = tmp / "state" / "test" / "job_history.json"
    ruta.write_text(_json.dumps(OFERTAS + [
        {"url": "https://e/3", "title": "Nueva", "aplicado": None,
         "found_at": "2026-09-04T10:00:00+00:00"}]), encoding="utf-8")
    despues = _json.loads(get(base, "/novedades?perfil=test")[1])

    assert despues["marca"] != antes["marca"]
    assert despues["pendientes"] == antes["pendientes"] + 1


# --- paginación y orden ----------------------------------------------------

def _muchas(n, score_de=lambda i: 50):
    return [{"url": f"https://e/{i}", "title": f"Oferta {i}", "aplicado": None,
             "score": score_de(i), "found_at": HOY_ISO, "posted_at": HOY_YMD}
            for i in range(n)]


def test_el_puntaje_cero_se_ve(sitio):
    """`esc(0)` devolvía vacío porque el cero es falsy.

    La caja del puntaje salía en blanco, y justo el 0 es el que más importa
    mostrar: es el que dice "esto no es para vos".
    """
    from vacantia.ui.render import esc

    assert esc(0) == "0"
    assert esc(None) == ""

    base, tmp = sitio
    _con_historial(tmp, [{"url": "https://e/0", "title": "No es para vos",
                          "aplicado": None, "score": 0, "found_at": HOY_ISO}])
    _, html, _ = get(base, "/trabajos?perfil=test")
    assert ">0<span class=\"de\">" in html


def test_muestra_de_a_veinte(sitio):
    base, tmp = sitio
    _con_historial(tmp, _muchas(45))
    _, html, _ = get(base, "/trabajos?perfil=test")

    assert html.count('class="oferta"') == 20
    assert "Página 1 de 3" in html
    assert "45 ofertas" in html


def test_se_puede_pasar_de_pagina_sin_perder_los_filtros(sitio):
    base, tmp = sitio
    _con_historial(tmp, _muchas(45))
    _, html, _ = get(base, "/trabajos?perfil=test&ver=pendientes&desde=todo&p=2")

    assert "Página 2 de 3" in html
    assert "ver=pendientes&desde=todo&p=3" in html    # siguientes, con los filtros
    assert "ver=pendientes&desde=todo&p=1" in html    # anteriores


def test_una_pagina_que_no_existe_cae_en_la_ultima(sitio):
    base, tmp = sitio
    _con_historial(tmp, _muchas(45))
    for pedida in ("99", "0", "-3", "hola"):
        _, html, _ = get(base, f"/trabajos?perfil=test&p={pedida}")
        assert "Página" in html and "de 3" in html


def test_sin_suficientes_ofertas_no_dibuja_la_barra(sitio):
    base, tmp = sitio
    _con_historial(tmp, _muchas(5))
    _, html, _ = get(base, "/trabajos?perfil=test")
    assert 'class="paginas"' not in html


def test_primero_las_que_mejor_encajan_y_no_las_mas_nuevas(sitio):
    """Ordenar por fecha abría la lista con lo peor.

    Las que puntúan 0 son las que directamente no son para uno, y si entraron
    hoy quedaban arriba de todo: tres avisos de Lima en 0 antes que 29 ofertas
    de 80 para arriba.
    """
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": "https://e/mala", "title": "Recien entrada pero no sirve",
         "aplicado": None, "score": 0, "found_at": HOY_ISO, "posted_at": HOY_YMD},
        {"url": "https://e/buena", "title": "Vieja pero encaja",
         "aplicado": None, "score": 90, "found_at": "2026-08-01T10:00:00+00:00",
         "posted_at": "2026-08-01"},
    ])
    _, html, _ = get(base, "/trabajos?perfil=test")
    assert html.index("Vieja pero encaja") < html.index("Recien entrada pero no sirve")


def test_marcar_una_oferta_te_deja_en_la_misma_pagina(sitio):
    base, tmp = sitio
    _con_historial(tmp, _muchas(45))
    _, _, url = post(base, "/feedback", {
        "perfil": "test", "ver": "pendientes", "desde": "todo", "p": "2",
        "url": "https://e/25", "aplicado": "si",
    })
    assert "p=2" in url


def test_los_puestos_excluidos_se_editan_desde_la_pantalla(sitio):
    """Cada término que se agrega acá es una llamada al modelo que no se paga."""
    base, tmp = sitio
    post(base, "/datos", {
        "perfil": "test", "keywords": "Python",
        "min_score": "60", "top_n": "5", "max_new_per_run": "30",
        "pais": "Argentina", "ciudad": "", "max_english_level": "A2",
        "excluir_titulos": "Data Steward, MLOps , Machine Learning",
        "cv": "# CV", "empresas": "", "rrhh": "",
        "cand_name": "Test", "cand_headline": "", "cand_profile": "",
        "cand_seeking": "", "cand_not_suitable": "",
    })
    perfil = json.loads((tmp / "profiles" / "test.json").read_text(encoding="utf-8"))
    assert perfil["filters"]["excluir_titulos"] == [
        "Data Steward", "MLOps", "Machine Learning"]

    _, html, _ = get(base, "/datos?perfil=test")
    assert 'name="excluir_titulos"' in html
    assert "Data Steward, MLOps, Machine Learning" in html


# --- las pestañas de marcadas, para revisar después ------------------------

def _marcada(url, titulo, empresa, aplicado, cuando, motivo=""):
    return {"url": url, "title": titulo, "company": empresa, "score": 70,
            "aplicado": aplicado, "motivo_descarte": motivo,
            "fecha_feedback": cuando, "found_at": HOY_ISO}


def test_al_marcarla_se_va_de_sin_marcar_y_aparece_en_su_pestana(sitio):
    """Es lo que evita perder la cuenta de a cuáles ya les diste bola."""
    base, _ = sitio
    post(base, "/feedback", {"perfil": "test", "ver": "pendientes",
                             "url": "https://empresa.com/jobs/1", "aplicado": "si"})

    _, pendientes, _ = get(base, "/trabajos?perfil=test&ver=pendientes")
    _, aplicadas, _ = get(base, "/trabajos?perfil=test&ver=aplicadas")
    assert "Data Scientist" not in pendientes
    assert "Data Scientist" in aplicadas


def test_las_marcadas_van_por_cuando_las_marcaste_y_no_por_puntaje(sitio):
    """Estas pestañas son para revisar, no para elegir.

    "¿A quién le mandé el CV esta semana?" se contesta con lo último arriba.
    Ordenarlas por puntaje mezclaba lo de ayer con lo de hace tres semanas.
    """
    base, tmp = sitio
    _con_historial(tmp, [
        {**_marcada("https://e/vieja", "Postulada hace tiempo", "ACME", True,
                    "2026-08-01T10:00:00+00:00"), "score": 95},
        {**_marcada("https://e/nueva", "Postulada recién", "Otra SA", True,
                    "2026-09-04T10:00:00+00:00"), "score": 60},
    ])
    _, html, _ = get(base, "/trabajos?perfil=test&ver=aplicadas")
    assert html.index("Postulada recién") < html.index("Postulada hace tiempo")


def test_la_tarjeta_dice_cuando_la_marcaste(sitio):
    """Sin la fecha, "Aplicaste" no sirve para saber si ya pasó el tiempo de
    esperar respuesta."""
    from datetime import datetime, timedelta, timezone

    base, tmp = sitio
    ayer = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    _con_historial(tmp, [
        _marcada("https://e/1", "Le mandé el CV", "ACME", True, ayer),
        _marcada("https://e/2", "No servía", "Otra SA", False, ayer, "pide inglés"),
    ])

    _, aplicadas, _ = get(base, "/trabajos?perfil=test&ver=aplicadas")
    assert "Aplicaste" in aplicadas and "ayer" in aplicadas

    _, descartadas, _ = get(base, "/trabajos?perfil=test&ver=descartadas")
    assert "Descartada ayer" in descartadas
    assert "pide inglés" in descartadas      # el motivo, para acordarse por qué


def test_el_cartel_del_ingles_no_aparece_cuando_estas_revisando(sitio):
    """En "Apliqué" y "Descarté" ya decidiste: ahí el cartel es ruido."""
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": "https://e/1", "title": "Con ingles", "score": 88, "aplicado": True,
         "requires_english": True, "fecha_feedback": HOY_ISO, "found_at": HOY_ISO},
        {"url": "https://e/2", "title": "Pendiente", "score": 70, "aplicado": None,
         "requires_english": True, "found_at": HOY_ISO},
    ])
    assert 'class="duele"' in get(base, "/trabajos?perfil=test&ver=pendientes")[1]
    assert 'class="duele"' not in get(base, "/trabajos?perfil=test&ver=aplicadas")[1]
    assert 'class="duele"' not in get(base, "/trabajos?perfil=test&ver=descartadas")[1]


def test_al_marcar_se_ve_cual_se_fue(sitio):
    """Con dos ofertas de 90 pegadas, la lista vuelve y se ve igual.

    Dos mitades para el mismo problema: la tarjeta se va animada (se ve CUÁL en
    el momento) y el aviso de arriba la nombra (se lee DESPUÉS, y funciona
    aunque el JavaScript no corra).
    """
    from vacantia.ui.render import CSS, JS

    base, _ = sitio
    _, html, _ = get(base, "/trabajos?perfil=test")
    assert 'onclick="return marcar(this, false)"' in html    # Apliqué
    assert 'onclick="return marcar(this, true)"' in html     # No apliqué
    assert ".oferta.yendose" in CSS and "@keyframes sale" in CSS

    # `form.submit()` no manda el botón apretado: sin reponerlo a mano, el
    # servidor no sabría si fue "apliqué" o "no apliqué".
    assert "oculto.name = boton.name" in JS
    assert "prefers-reduced-motion" in JS                    # quien pide quieto, quieto

    _, _, url = post(base, "/feedback", {
        "perfil": "test", "ver": "pendientes",
        "url": "https://empresa.com/jobs/1", "aplicado": "si"})
    assert "Aplicaste+a" in url and "Data+Scientist" in url


def test_al_descartar_el_aviso_tambien_la_nombra(sitio):
    base, _ = sitio
    _, _, url = post(base, "/feedback", {
        "perfil": "test", "ver": "pendientes", "url": "https://empresa.com/jobs/2",
        "aplicado": "no", "motivo": "es junior"})
    assert "Descartaste" in url and "Analista+de+Datos" in url


# --- archivar --------------------------------------------------------------

def test_archivar_saca_de_sin_marcar_sin_descartar(sitio):
    """Archivar no es descartar: no pide motivo y no toca el veredicto.

    Si se guardara como descarte, el motivo "el aviso ya no está" iría al
    prompt de scoring como ejemplo negativo y le enseñaría al sistema una
    preferencia que nadie tuvo.
    """
    base, _ = sitio
    post(base, "/archivar", {"perfil": "test", "ver": "pendientes",
                             "url": "https://empresa.com/jobs/1", "archivar": "1"})

    historial = {h["url"]: h for h in State("test").load_history()}
    guardada = historial["https://empresa.com/jobs/1"]
    assert guardada["archivada"] is True
    assert guardada["aplicado"] is None          # sigue sin veredicto

    assert "Data Scientist" not in get(base, "/trabajos?perfil=test&ver=pendientes")[1]
    assert "Data Scientist" in get(base, "/trabajos?perfil=test&ver=archivadas")[1]
    assert "Data Scientist" not in get(base, "/trabajos?perfil=test&ver=descartadas")[1]


def test_se_puede_devolver_una_archivada_a_la_lista(sitio):
    base, _ = sitio
    post(base, "/archivar", {"perfil": "test", "url": "https://empresa.com/jobs/1",
                             "archivar": "1"})
    _, html, _ = get(base, "/trabajos?perfil=test&ver=archivadas")
    assert "Devolver a la lista" in html

    post(base, "/archivar", {"perfil": "test", "url": "https://empresa.com/jobs/1",
                             "archivar": "0"})
    assert "Data Scientist" in get(base, "/trabajos?perfil=test&ver=pendientes")[1]


def test_archivar_las_viejas_de_una(sitio):
    """Con 43 avisos de más de una semana, archivarlos de a uno es al pedo."""
    from datetime import date, timedelta

    base, tmp = sitio
    viejo = (date.today() - timedelta(days=20)).isoformat()
    _con_historial(tmp, [
        {"url": "https://e/vieja", "title": "De hace 20 días", "aplicado": None,
         "score": 70, "posted_at": viejo, "found_at": HOY_ISO},
        {"url": "https://e/nueva", "title": "De hoy", "aplicado": None,
         "score": 70, "posted_at": HOY_YMD, "found_at": HOY_ISO},
    ])
    _, html, _ = get(base, "/trabajos?perfil=test")
    assert "Archivar los avisos viejos" in html
    assert "Más de 14 días (1)" in html          # dice cuántas antes de apretar

    _, html, _ = post(base, "/archivar-viejas", {"perfil": "test", "dias": "14"})
    assert "De hace 20 días" not in html
    assert "De hoy" in html


def test_el_boton_de_archivar_solo_aparece_donde_sirve(sitio):
    """En Apliqué o Descarté ya decidiste: ahí no hay nada que encajonar."""
    base, _ = sitio
    assert "Archivar los avisos viejos" not in get(
        base, "/trabajos?perfil=test&ver=aplicadas")[1]
