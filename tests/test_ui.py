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
        "pais": "Argentina", "ciudad": "Bahía Blanca, Punta Alta",
        "modo_remote": "1", "modo_hybrid": "1",
        "max_english_level": "B1",
        "cv": "# CV nuevo\nPython.",
        "empresas": "ACME | https://acme.com/jobs | acme.com\nGlobant | https://globant.com/jobs |",
        "rrhh": "https://linkedin.com/in/recluta1\n",
        "cand_name": "Test", "cand_profile": "", "cand_seeking": "", "cand_not_suitable": "",
    })
    post(base, "/configuracion", {
        "perfil": "test",
        "min_score": "70", "top_n": "8", "max_new_per_run": "30",
        "notify_when_empty": "1",
        "fuente_careers": "1", "fuente_linkedin": "1",
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
    post(base, "/configuracion", {"perfil": "test",
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
    post(base, "/configuracion", {"perfil": "test", "chat_id": "111"})
    post(base, "/configuracion", {"perfil": "novio", "chat_id": "222"})

    def chat_de(nombre):
        perfil = json.loads((tmp / "profiles" / f"{nombre}.json").read_text(encoding="utf-8"))
        return {n["type"]: n for n in perfil["notifiers"]}["telegram"]["chat_id"]

    assert chat_de("test") == "111"
    assert chat_de("novio") == "222"


def test_sin_chat_propio_se_usa_el_compartido_del_env(sitio):
    base, tmp = sitio
    post(base, "/configuracion", {"perfil": "test", "chat_id": "  "})
    perfil = json.loads((tmp / "profiles" / "test.json").read_text(encoding="utf-8"))
    telegram = {n["type"]: n for n in perfil["notifiers"]}["telegram"]
    assert telegram["chat_id"] == "${TELEGRAM_CHAT_ID}"


def test_el_chat_propio_se_muestra_en_el_formulario(sitio):
    base, _ = sitio
    post(base, "/configuracion", {"perfil": "test", "chat_id": "98765"})
    _, html, _ = get(base, "/configuracion?perfil=test")
    assert "98765" in html


def test_la_clave_del_bot_sigue_siendo_compartida(sitio):
    """El token del bot es de la computadora; el chat, de cada uno."""
    base, tmp = sitio
    post(base, "/configuracion", {"perfil": "test",
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

    html = formulario.render_configuracion("ana", {"keywords": ["Python"]}, [])
    assert "Misma base de avisos que Bumeran" in html
    assert "Misma base de avisos que Zonajobs" in html


def test_el_tilde_y_el_campo_de_reclutadores_no_se_llaman_igual():
    """Se llamaban los dos "Perfiles de reclutadores que sigo".

    Uno es el interruptor de la fuente y el otro el cuadro donde van las URLs,
    con "Empresas que sigo" en el medio. Con el mismo nombre, no se encontraba
    dónde pegarlas.

    Desde que Mi perfil y Configuración son dos pantallas, además viven en
    lugares distintos: el tilde en Configuración y las URLs en Mi perfil.
    """
    from vacantia.ui import formulario

    perfil = {"keywords": ["Python"]}
    configuracion = formulario.render_configuracion("ana", perfil, [])
    mi_perfil = formulario.render_datos("ana", perfil, [])

    # El tilde conserva el nombre de la fuente...
    assert "> Perfiles de reclutadores que sigo</label>" in configuracion
    # ...y el cuadro de texto pasa a decir qué va adentro.
    assert '<label for="rrhh">Las URLs de esos reclutadores</label>' in mi_perfil
    assert '<label for="rrhh">Perfiles de reclutadores que sigo</label>' not in mi_perfil
    # Con la fuente apagada, Mi perfil nombra al tilde y lleva a donde se prende,
    # para que se vea que van juntos aunque no estén uno al lado del otro...
    assert "prendas <b>Perfiles de reclutadores que sigo</b> en" in mi_perfil
    assert '<a href="/configuracion?perfil=ana">Configuración</a>' in mi_perfil
    # ...y con la fuente prendida no lo recuerda: un aviso que está siempre deja
    # de leerse.
    prendida = formulario.render_datos(
        "ana", {"sources": [{"type": "rrhh", "enabled": True}]}, [])
    assert "prendas <b>Perfiles de reclutadores que sigo</b>" not in prendida


def test_el_recuadro_explica_que_pagina_pegar_y_cual_no():
    """Del perfil pelado de LinkedIn no sale nada: hay que ir a su actividad.

    Y de la home de una consultora tampoco: va la página que lista las
    búsquedas. Es lo que nadie se acuerda, y cuando se equivoca la fuente
    devuelve 0 sin decir por qué.

    Los ejemplos van siempre a la vista, abajo del cuadro, porque hay que poder
    encontrarlos de nuevo cada vez. Eran un recuadro de catorce renglones que
    pesaba más que el campo; ahora son tres renglones, y el porqué va detrás del
    signo de pregunta, que se lee una vez.
    """
    from vacantia.ui import formulario

    html = formulario.render_datos("ana", {"keywords": ["Python"]}, [])

    assert 'class="ejemplos"' in html
    assert "<code>linkedin.com/in/nombre-apellido</code><span>el perfil de la persona" in html
    assert '<span class="mal">No sirve</span><code>consultora.com.ar</code>' in html
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
        "datos": formulario.render_datos("ana", perfil, []),
        "configuracion": formulario.render_configuracion("ana", perfil, []),
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

    Sin ninguna descartada, lo útil es explicar para qué sirve descartar; en la
    primera corrida, lo útil es el botón que corre la primera búsqueda.
    """
    from vacantia.ui import render

    primera = render.trabajos("ana", [], {}, "todas", [])
    sin_descartes = render.trabajos("ana", [], {}, "descartadas", [])

    # La salida está donde el vacío se arregla buscando, y no donde no.
    assert "Buscar ahora" in primera and 'action="/buscar"' in primera
    assert "No apliqué" in sin_descartes and "Buscar ahora" not in sin_descartes


def test_la_pantalla_no_nombra_ningun_archivo_ni_comando():
    """Si hay que ejecutar algo, es un botón con nombre humano.

    Mientras la pantalla decía "doble clic en `buscar_ahora.bat`", la pantalla
    no era la app: era la documentación de otro programa. Y para poder decirlo
    hubo que construir el botón, que es lo que faltaba.
    """
    import html as H
    import re

    for nombre, pagina in _paginas_para_auditar().items():
        sin_script = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", pagina,
                            flags=re.S | re.I)
        visible = H.unescape(re.sub(r"<[^>]+>", " ", sin_script))
        for prohibido in (".bat", ".ps1", ".py", "python -m", "doble clic"):
            assert prohibido not in visible, f"'{prohibido}' en la pantalla '{nombre}'"


def test_la_pantalla_es_oscura_y_una_sola():
    """Un solo tema, el oscuro. No hay modo claro y no se improvisa uno.

    La app se usa en escritorio, la usan cinco personas y siempre de noche o
    con la ventana al lado. Mantener dos paletas era mantener dos veces cada
    color, y la mitad de las veces la segunda se olvidaba.
    """
    from vacantia.ui.render import CSS

    assert "color-scheme: dark" in CSS
    assert "prefers-color-scheme: light" not in CSS
    assert "filter: invert" not in CSS          # el atajo que no se toma


def test_ninguna_regla_escribe_un_color_suelto():
    """Los colores se declaran una vez, arriba, como tokens semánticos.

    Si una regla escribe un hex propio, cambiar la paleta deja esa regla atrás
    y nadie se entera hasta que se ve en pantalla. La única excepción es la
    flecha del desplegable, que lleva el color adentro de un SVG.
    """
    import re

    from vacantia.ui.render import CSS

    # Todo lo que está fuera del bloque :root de tokens.
    inicio = CSS.index(":root {")
    reglas = CSS[:inicio] + CSS[CSS.index("\n}", inicio):]
    sueltos = [linea.strip() for linea in reglas.splitlines()
               if re.search(r"#[0-9A-Fa-f]{3,8}\b", linea) and "svg" not in linea]
    assert sueltos == [], sueltos
    assert CSS.count("var(--color-text-primary)") > 3
    assert CSS.count("var(--color-surface)") > 3


def _contraste(a: str, b: str) -> float:
    """La relación de contraste de WCAG entre dos colores en hexadecimal."""
    def luminancia(hexa):
        canales = (int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))
        r, g, b_ = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
                    for c in canales)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b_

    la, lb = luminancia(a), luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def test_todo_par_de_texto_y_fondo_cumple_wcag_aa():
    """4.5:1 en texto normal. El par más ajustado del sistema es el terciario
    sobre la superficie elevada: si alguien lo baja, falla acá.

    Éste es el que agarró que el índigo de acción (#6366E8) daba 4.13:1 como
    color de texto: sirve de relleno de botón con texto blanco, pero no para un
    link índigo sobre fondo oscuro. De ahí salió el token de link aparte.
    """
    import re

    from vacantia.ui.estilos import TOKENS

    valores = dict(re.findall(r"(--[\w-]+):\s*(#[0-9A-Fa-f]{6});", TOKENS))
    # Los semánticos apuntan a primitivos: se resuelve una vuelta.
    for clave, valor in re.findall(r"(--[\w-]+):\s*var\((--[\w-]+)\);", TOKENS):
        if valor in valores:
            valores[clave] = valores[valor]

    fondos = ("--color-background", "--color-surface", "--color-surface-raised")
    textos = ("--color-text-primary", "--color-text-secondary",
              "--color-text-tertiary", "--color-link", "--color-success",
              "--color-warning", "--color-danger", "--color-info")
    for texto in textos:
        for fondo in fondos:
            r = _contraste(valores[texto], valores[fondo])
            assert r >= 4.5, f"{texto} sobre {fondo}: {r:.2f}:1"

    # El texto de estado sobre su propia superficie.
    for color in ("success", "warning", "danger", "info"):
        r = _contraste(valores[f"--color-{color}"], valores[f"--color-{color}-surface"])
        assert r >= 4.5, f"{color} sobre su surface: {r:.2f}:1"

    # Y el texto del botón primario, en reposo y en hover.
    for fondo in ("--color-action", "--color-action-hover"):
        r = _contraste(valores["--color-text-on-action"], valores[fondo])
        assert r >= 4.5, f"texto del botón sobre {fondo}: {r:.2f}:1"


def test_buscar_ahora_es_un_boton_y_no_un_archivo(sitio, monkeypatch):
    """El `.bat` que había que ir a abrir al Explorador, adentro de la app.

    Corre en un proceso aparte a propósito: la búsqueda tarda minutos y el
    servidor atiende de a un pedido, así que hacerla adentro dejaría la pantalla
    congelada hasta que termine.
    """
    from vacantia.ui import corrida

    arrancadas = []

    class Falso:
        def poll(self):
            return None if arrancadas and arrancadas[-1][1] else 0

    def falso_popen(orden, **kw):
        arrancadas.append((orden, kw.get("sigue", False)))
        return Falso()

    monkeypatch.setattr(corrida.subprocess, "Popen", falso_popen)
    monkeypatch.setattr(corrida, "_proceso", None)

    base, _ = sitio
    _, html, url = post(base, "/buscar", {"perfil": "test"})
    assert "/trabajos" in url and "perfil=test" in url
    assert "Buscando ofertas" in html            # el aviso, en castellano llano

    orden = arrancadas[0][0]
    assert orden[1:3] == ["-m", "vacantia.run"]
    assert orden[3:] == ["--profile", "test"]    # sólo el perfil que lo pidió


def test_no_arranca_dos_busquedas_encimadas(sitio, monkeypatch):
    """Los límites del plan gratis son de la cuenta, no del perfil."""
    from vacantia.ui import corrida

    class Corriendo:
        def poll(self):
            return None                      # sigue vivo

    monkeypatch.setattr(corrida, "_proceso", Corriendo())
    assert corrida.esta_corriendo()

    arranco, mensaje = corrida.arrancar("test")
    assert arranco is False
    assert "Ya hay una búsqueda en curso" in mensaje

    # Y mientras tanto la pantalla no ofrece buscar de nuevo: en vez del botón,
    # el pie de la barra lateral cuenta en qué etapa va.
    base, _ = sitio
    _, html, _ = get(base, "/trabajos?perfil=test")
    assert "Buscar ahora" not in html
    assert "Arrancando la búsqueda" in html
    # Y pregunta seguido, que es lo que hace que se vea avanzar.
    assert 'hx-trigger="every 2s"' in html


def test_linkedin_urls_abre_en_publicaciones(sitio):
    """Publicaciones va primero porque es la que resuelve el agujero real.

    Los posteos del muro nunca llegan a la pestaña de empleos, y el buscador los
    indexa uno a tres días tarde. Jobs ya lo cubre el scraper.
    """
    base, _ = sitio

    _, defecto, _ = get(base, "/linkedin?perfil=test")
    assert "LinkedIn URLs" in defecto
    assert 'class="pestania activa" href="/linkedin?perfil=test&tab=publicaciones"' in defecto
    # Y el orden de las pestañas, no sólo cuál está activa.
    assert defecto.index(">Publicaciones<") < defecto.index(">Jobs<")

    _, jobs, _ = get(base, "/linkedin?perfil=test&tab=jobs")
    assert 'class="pestania activa" href="/linkedin?perfil=test&tab=jobs"' in jobs
    assert '<input type="hidden" name="tab" value="jobs">' in jobs

    # Una pestaña inventada cae en Publicaciones y no rompe.
    _, rara, _ = get(base, "/linkedin?perfil=test&tab=cualquiera")
    assert 'class="datos armador"' in rara

    # Y está en la barra lateral, abajo de Trabajos, adentro de "Buscar".
    lateral = defecto[defecto.index("<aside"):defecto.index("</aside>")]
    assert lateral.index(">Buscar<") < lateral.index(">Trabajos<") \
        < lateral.index(">LinkedIn URLs<") < lateral.index(">Métricas<")


def test_publicaciones_va_en_dos_columnas_y_la_pantalla_no_se_mueve():
    """Los controles a la izquierda, lo que sale a la derecha.

    En una sola columna la dirección aparecía abajo de todo, fuera de pantalla,
    y como el constructor es un GET cada intento recargaba la página y el
    navegador la abría arriba. Partido en dos, el resultado nace al lado de los
    controles y la página en sí ya no scrollea: se mueve cada columna adentro.
    """
    from vacantia.ui.estilos import CSS
    from vacantia.ui.render import linkedin

    html = linkedin("ana", "publicaciones", [], url="https://x/y",
                    guardados=[{"nombre": "AI hoy", "url": "https://x/y",
                                "guardada": "2026-09-10T10:00:00+00:00"}])

    izq = html.index('class="lado controles"')
    der = html.index('class="lado resultado"')
    assert izq < der, "los controles van primero"
    # El constructor a la izquierda; la dirección y las guardadas a la derecha.
    assert izq < html.index('class="datos armador"') < der
    assert der < html.index('class="url-generada"')
    assert der < html.index("Tus búsquedas guardadas")

    # El alto lo pone el viewport, y lo que scrollea es cada columna.
    assert "main:has(> .taller)" in CSS
    assert "height: 100dvh; overflow: hidden;" in CSS
    assert ".taller > .lado {" in CSS

    # Y abajo de 1100px vuelve a ser una sola columna: dos rendijas no son dos
    # columnas, y con la lateral arriba 100dvh se pasa de largo.
    angosto = CSS[CSS.index("@media (max-width: 1100px)"):]
    assert "height: auto; overflow: visible;" in angosto[:600]


def test_sin_armar_la_columna_derecha_dice_que_va_a_aparecer_ahi():
    """La columna existe siempre, así que el hueco se nombra."""
    from vacantia.ui.render import linkedin

    html = linkedin("ana", "publicaciones", [])
    assert "Todavía no armaste ninguna." in html
    assert "Armar la\n  búsqueda" in html or "Armar la búsqueda" in html


def test_el_constructor_vuelve_al_lugar_donde_estabas():
    """Armar la búsqueda recarga la página: la columna volvía arriba de todo.

    Es la misma cura que la lista de ofertas, pero sobre el scroll de la
    columna y no el de la ventana, porque acá la ventana no scrollea.
    """
    from vacantia.ui.render import JS

    assert "vacantia:taller" in JS
    assert "form.armador" in JS
    assert "recordarTaller" in JS and "volverAlTaller" in JS


def test_las_pestanias_son_navegacion_y_no_un_filtro():
    """Las píldoras filtran una lista; las pestañas cambian de contenido.

    Por eso van arriba del contenido y no adentro de una tarjeta, y por eso son
    links y no botones de un formulario.
    """
    from vacantia.ui.render import linkedin

    html = linkedin("ana", "jobs", [])
    assert '<nav class="pestanias"' in html
    assert html.index('class="pestanias"') < html.index('class="taller"')
    nav = html[html.index('<nav class="pestanias"'):html.index("</nav>")]
    assert "<button" not in nav and nav.count("<a ") == 2


def test_como_viene_funcionando_reemplaza_la_ventana_negra(sitio):
    """Lo que mostraba la pantalla de estado, adentro de Métricas.

    Si está programado, cuándo corrió, qué encontró, si avisó por Telegram y de
    qué se quejó. Sin nombres de archivo y sin abrir una consola.
    """
    from vacantia.ui import render

    salud = {"corriendo": False, "cuando": "hoy 16:30", "duracion": "41 segundos",
             "encontro": [("recolectadas", 125), ("nuevas", 78)],
             "telegram": "hoy 16:31",
             "problemas": ["[rrhh] sin contenido en https://a.com/x"],
             "programada": [{"nombre": "Vacantia - ana", "estado": "Listo",
                             "proxima": "9/9/2026 12:00:00"}]}
    html = render.estadisticas(
        "ana", {"sin_marcar": 1, "aplicadas": 2, "descartadas": 3, "archivadas": 4,
                "total": 5, "ingles": {}, "sistema": {}, "motivos": {},
                "por_fuente": {}, "max_age_days": 7},
        "todo", [], salud=salud)

    assert "Cómo viene funcionando" in html
    assert "Vacantia - ana" in html and "9/9/2026 12:00:00" in html
    assert "recolectadas" in html and "125" in html
    assert "41 segundos" in html
    assert "hoy 16:31" in html
    # Las quejas del registro son texto de máquina: van adentro del desplegable.
    assert "Ver los últimos avisos del registro" in html
    assert 'class="registro"' in html

    # Y sin datos no inventa nada.
    sin_salud = render.estadisticas(
        "ana", {"sin_marcar": 0, "aplicadas": 0, "descartadas": 0, "archivadas": 0,
                "total": 0, "ingles": {}, "sistema": {}, "motivos": {},
                "por_fuente": {}, "max_age_days": 7}, "todo", [])
    assert "Cómo viene funcionando" not in sin_salud


def test_la_fecha_de_marcado_se_lee_en_la_hora_de_aca(sitio):
    """Se guarda en UTC, y hay que pasarla a la hora local ANTES del día.

    Cortando los diez primeros caracteres del texto, todo lo que marcabas entre
    las 21:00 y la medianoche quedaba con la fecha de mañana en UTC, y al día
    siguiente la tarjeta decía "Aplicaste hoy" a algo de ayer. Son tres horas
    por día, justo las que más se usa la pantalla.
    """
    from datetime import datetime, timedelta, timezone

    from vacantia.ui.render import _cuando_marcada

    ayer_local = datetime.now().astimezone() - timedelta(days=1)
    en_utc = ayer_local.astimezone(timezone.utc).isoformat()
    assert _cuando_marcada({"fecha_feedback": en_utc})[0] == "ayer"

    ahora = datetime.now().astimezone().astimezone(timezone.utc).isoformat()
    assert _cuando_marcada({"fecha_feedback": ahora})[0] == "hoy"

    # Una fecha sola, sin hora, sigue funcionando como siempre.
    hoy = datetime.now().astimezone().date().isoformat()
    assert _cuando_marcada({"fecha_feedback": hoy})[0] == "hoy"
    assert _cuando_marcada({"fecha_feedback": ""})[0] == ""


def test_las_fuentes_las_sirve_la_app_y_nunca_un_cdn(sitio):
    """La máquina puede estar sin internet, y una fuente que tarda tres segundos
    en llegar es una pantalla que parpadea al abrir.

    Si los archivos no están en `vacantia/ui/fuentes/`, el CSS ni siquiera
    declara las `@font-face` y todo cae en la pila del sistema. Lo que no puede
    pasar nunca es que la pantalla salga a buscar algo a internet.
    """
    from vacantia.ui import estilos
    from vacantia.ui.render import CSS

    for prohibido in ("fonts.googleapis", "fonts.gstatic", "cdn.", "//http", "https://"):
        assert prohibido not in CSS, prohibido
    # Inter primero y la pila del sistema atrás, para que se vea algo igual.
    assert "--font-sans: Inter," in CSS and "system-ui" in CSS
    assert '--font-mono: "JetBrains Mono"' in CSS and "monospace" in CSS

    # Las declara sólo si están en disco, y las sirve la propia app.
    if not any((estilos.FUENTES_DIR / a).exists() for a, _, _ in estilos.FUENTES):
        assert "@font-face" not in CSS
    # Y la ruta no deja pedir cualquier archivo del disco: sólo salen los
    # nombres de la lista blanca, así que el path no se arma con la URL.
    import urllib.error

    base, _ = sitio
    for camino in ("/fuentes/../../.env", "/fuentes/cualquiera.woff2"):
        with pytest.raises(urllib.error.HTTPError) as e:
            get(base, camino)
        assert e.value.code == 404


def test_el_menu_de_tres_puntos_se_dibuja_arriba_de_la_tarjeta_siguiente():
    """El panel quedaba tapado por la oferta de abajo.

    Y no se arregla subiéndole el z-index al panel, por más alto que se ponga:
    el `backdrop-filter` del vidrio esmerilado convierte cada tarjeta en un
    contexto de apilado propio, y adentro de ese contexto el panel se dibuja
    con su tarjeta. Entre tarjetas hermanas manda el orden del documento. Lo
    que hay que levantar es la tarjeta entera.
    """
    from vacantia.ui.render import CSS

    regla = CSS[CSS.index(".oferta:has(.menu[open])"):]
    regla = regla[:regla.index("}") + 1]
    assert "position: relative" in regla
    assert "z-index: var(--z-dropdown)" in regla

    # Y el panel sigue teniendo el suyo, para las tarjetas ya marcadas, que no
    # llevan vidrio y por lo tanto no arman contexto propio.
    panel = CSS[CSS.index(".menu .panel {"):]
    assert "z-index: var(--z-dropdown)" in panel[:panel.index("}")]


def test_el_vidrio_esmerilado_se_gasta_en_tres_lugares():
    """Si todo es vidrio, nada se destaca.

    La barra lateral, la tarjeta de oferta sin marcar y el cartel de novedades.
    Una tarjeta de métrica con vidrio y una de oferta con vidrio se ven iguales
    y destruyen la jerarquía, así que el efecto se cuenta.
    """
    import re

    from vacantia.ui.render import CSS

    con_vidrio = re.findall(r"\n(\.[\w.-]+)\s*\{[^}]*var\(--glass-background\)", CSS)
    assert sorted(con_vidrio) == [".lateral", ".oferta", ".toast"], con_vidrio
    # El cartel de novedades es un toast más y no un cuarto componente. Cuando
    # se definió aparte, con su propio vidrio, el efecto pasó a estar en cuatro
    # lugares y dejó de destacar nada: eso es lo que agarró este test.
    # El cartel vive en el shell y no en Trabajos: así buscar desde Métricas
    # también avisa. Sigue siendo un toast y no un cuarto componente con vidrio
    # propio, que es lo que este test agarró cuando se definió aparte.
    from vacantia.ui.render import pagina
    assert 'class="toast novedades"' in pagina("T", "", "ana", ["ana"], "trabajos")
    # Y la que ya está marcada lo pierde: se distingue de un vistazo lo que
    # queda por hacer de lo que ya está hecho.
    assert ".oferta.marcada" in CSS and "backdrop-filter: none" in CSS


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


def test_el_aviso_se_abre_sin_contarle_al_portal_de_donde_venimos():
    """`rel="noreferrer"` no es privacidad: sin él, Computrabajo se rompe.

    La pantalla corre en `http://127.0.0.1:8756`. Si el navegador manda ese
    referrer, Computrabajo lo guarda en su cookie `extrfr`, y desde ahí todos los
    pedidos al sitio llevan una URL a loopback adentro de una cookie — la firma
    de un SSRF. Su firewall contesta 403 en el sitio entero hasta que se borre.
    No fallaba un aviso: el primer clic desde acá rompía todos los siguientes.

    Verificado el 7/9/2026 armando la cookie a mano contra el portal:
    `extrfr=http://127.0.0.1:8756/trabajos` -> 403, sin la cookie -> 200.

    `noreferrer` implica `noopener`, así que la pestaña nueva sigue sin poder
    tocar a la que la abrió.
    """
    from vacantia.ui.render import _tarjeta, consejo, mensajes

    oferta = {"url": "https://ar.computrabajo.com/x", "title": "T"}
    # Las cuatro pantallas que enlazan al aviso en el portal.
    salidas = [
        _tarjeta(oferta, "ana", "pendientes"),
        _tarjeta({**oferta, "archivada": True}, "ana", "archivadas"),
        mensajes("ana", oferta, {"DM": "hola"}, True, []),
        consejo("ana", oferta, [], "texto", True, []),
    ]
    for html in salidas:
        assert 'href="https://ar.computrabajo.com/x"' in html
        assert 'rel="noreferrer"' in html
        assert 'rel="noopener"' not in html


# --- descartar sin escribir, y volver a donde estabas -----------------------

def test_los_desplegables_se_ven_como_el_resto_de_los_controles():
    """Tres de los cuatro `select` no tenían una línea de CSS y salía el control
    crudo del sistema operativo, que no se parece a nada del resto."""
    from vacantia.ui.render import CSS

    regla = CSS[CSS.index(chr(10) + "select {"):]
    regla = regla[:regla.index("}")]
    # Mismo borde, mismo radio y misma superficie que los botones y los inputs.
    for token in ("var(--color-border)", "var(--rounded-sm)", "var(--color-surface)",
                  "var(--color-text-primary)", "var(--select-arrow)",
                  "var(--control-height)"):
        assert token in regla, token
    # La flecha nativa no se puede pintar: se saca y se dibuja la nuestra.
    assert "appearance: none" in regla
    # Vivos como los botones: hover, foco visible y transición.
    assert "select:hover" in CSS and "select:focus" in CSS
    assert "transition" in regla


def test_la_flecha_del_desplegable_usa_el_gris_de_los_tokens():
    """Va como token porque el color viaja adentro del SVG y no se puede
    referenciar una variable ahí. Si alguien cambia la paleta y se olvida de la
    flecha, falla esto y no la pantalla."""
    from vacantia.ui.render import CSS

    # text-secondary, tal como está definido arriba en los primitivos.
    assert "--neutral-300: #9AA0B4;" in CSS
    assert "%239AA0B4" in CSS


def test_el_nombre_de_la_app_lleva_al_home():
    from vacantia.ui.render import pagina

    html = pagina("Métricas", "", "ana", ["ana"], "estadisticas")
    assert 'href="/trabajos?perfil=ana" class="marca-app"' in html
    assert "VACANTIA" in html


def test_el_estado_del_sistema_esta_siempre_a_la_vista():
    """Cuándo buscó y cuándo vuelve a buscar es el antídoto de la ansiedad.

    La pregunta que más pesa buscando trabajo no es "¿hay ofertas?" sino "¿esto
    es todo lo que hay?". Por eso el dato tiene un lugar fijo al pie de la barra
    lateral, en todas las pantallas, y no un tooltip escondido.
    """
    from vacantia.ui.render import pagina

    estado = {"ultima": "hoy 16:30", "proxima": "hoy 23:59", "ventana": 7}
    for tab in ("trabajos", "estadisticas", "datos"):
        html = pagina("t", "c", "ana", ["ana"], tab, estado)
        assert 'class="estado"' in html
        assert "Última búsqueda: hoy 16:30" in html
        assert "Próxima: hoy 23:59" in html
        assert "últimos <span class='valor'>7</span> días" in html

    # Sin datos no se inventa nada: el bloque directamente no se dibuja.
    assert 'class="estado"' not in pagina("t", "c", "ana", ["ana"], "trabajos")


def test_la_navegacion_agrupa_por_lo_que_la_persona_hace():
    """Primero buscar, y abajo, separado, revisar y configurar."""
    from vacantia.ui.render import pagina

    html = pagina("t", "c", "ana", ["ana"], "trabajos")
    # Acotado a la barra lateral: en la página entera, las mismas palabras
    # aparecen antes en los comentarios de la hoja de estilos.
    lateral = html[html.index("<aside"):html.index("</aside>")]
    assert lateral.index(">Buscar<") < lateral.index(">Trabajos<") < lateral.index(">Métricas<")
    assert lateral.index(">Métricas<") < lateral.index(">Mi perfil<") < lateral.index(">Configuración<")
    assert 'aria-current="page"' in lateral       # dónde estoy parado


def test_el_motivo_se_elige_de_una_lista_o_se_escribe():
    """Los dos caminos a la vista, y con cualquiera alcanza.

    No hay opción "Otro motivo" en la lista: obligaba a abrir el desplegable,
    bajar hasta "Otro" y recién ahí escribir, tres pasos de más justo cuando ya
    tenías la mano en el teclado.
    """
    from vacantia.ui.render import _tarjeta

    html = _tarjeta({"url": "https://x/1", "title": "T"}, "ana", "pendientes")
    assert 'name="motivo_clave"' in html
    for clave in ("ingles", "presencial", "especial"):
        assert f'value="{clave}"' in html
    assert 'value="otro"' not in html
    # El campo de texto está siempre visible: no se esconde ni hace falta
    # elegir nada para llegar a él. (La tarjeta tiene otros inputs que sí son
    # `type=hidden`, así que se mira sólo la etiqueta de este campo.)
    campo = html[html.index('name="motivo"'):]
    campo = campo[:campo.index(">")]
    assert "placeholder" in campo
    assert "hidden" not in campo


def test_marcar_guarda_donde_estabas_antes_de_enviar():
    """La regresión que me comí escribiendo esto.

    `form.submit()` NO dispara el evento 'submit', así que un listener sobre el
    formulario no alcanza: hay que guardar la posición dentro de `marcar()`. Sin
    esto, marcar la oferta 30 te devolvía arriba de todo, que es justo lo que
    había que arreglar.
    """
    from vacantia.ui.render import JS

    # El cuerpo de marcar(), hasta donde arranca la funcion siguiente. Se
    # corta con salto de linea + "function" porque adentro hay un
    # setTimeout(function(){...}) que si no partiria el texto antes de tiempo.
    marcar = JS.split("function marcar(")[1].split(chr(10) + "function ")[0]
    assert "recordarScroll()" in marcar, "marcar() tiene que guardar el scroll"
    # Antes de mandar, no después: se compara contra el setTimeout que envía y
    # no contra el texto "form.submit()", que también aparece en un comentario.
    assert marcar.index("recordarScroll()") < marcar.index("setTimeout(")


def test_descartar_con_un_motivo_de_la_lista_no_pide_texto(sitio):
    base, tmp = sitio
    _con_historial(tmp, [{"url": "https://e/1", "title": "Una", "aplicado": None,
                          "score": 70, "found_at": HOY_ISO, "posted_at": HOY_YMD}])
    _, _, url = post(base, "/feedback", {
        "perfil": "test", "url": "https://e/1", "aplicado": "no",
        "motivo_clave": "ingles", "motivo": "",
    })
    assert "error" not in url
    guardada = json.loads((tmp / "state" / "test" / "job_history.json")
                          .read_text(encoding="utf-8"))[0]
    assert guardada["aplicado"] is False
    assert guardada["motivo_clave"] == "ingles"


def test_descartar_escribiendo_y_sin_elegir_nada_tambien_vale(sitio):
    """El caso de todos los días: ya tenías la mano en el teclado."""
    base, tmp = sitio
    _con_historial(tmp, [{"url": "https://e/1", "title": "Una", "aplicado": None,
                          "score": 70, "found_at": HOY_ISO, "posted_at": HOY_YMD}])
    _, _, url = post(base, "/feedback", {
        "perfil": "test", "url": "https://e/1", "aplicado": "no",
        "motivo_clave": "", "motivo": "Pide .NET y no lo uso",
    })
    assert "error" not in url
    guardada = json.loads((tmp / "state" / "test" / "job_history.json")
                          .read_text(encoding="utf-8"))[0]
    assert guardada["aplicado"] is False
    assert guardada["motivo_descarte"] == "Pide .NET y no lo uso"
    assert guardada["motivo_clave"] == ""


def test_sin_elegir_ni_escribir_no_pasa(sitio):
    base, tmp = sitio
    _con_historial(tmp, [{"url": "https://e/1", "title": "Una", "aplicado": None,
                          "score": 70, "found_at": HOY_ISO, "posted_at": HOY_YMD}])
    _, _, url = post(base, "/feedback", {
        "perfil": "test", "url": "https://e/1", "aplicado": "no",
        "motivo_clave": "", "motivo": "   ",
    })
    assert "error" in url
    guardada = json.loads((tmp / "state" / "test" / "job_history.json")
                          .read_text(encoding="utf-8"))[0]
    assert guardada["aplicado"] is None      # no se marcó nada


def test_una_clave_inventada_no_se_guarda(sitio):
    base, tmp = sitio
    _con_historial(tmp, [{"url": "https://e/1", "title": "Una", "aplicado": None,
                          "score": 70, "found_at": HOY_ISO, "posted_at": HOY_YMD}])
    post(base, "/feedback", {
        "perfil": "test", "url": "https://e/1", "aplicado": "no",
        "motivo_clave": "borrar_todo", "motivo": "un motivo escrito",
    })
    guardada = json.loads((tmp / "state" / "test" / "job_history.json")
                          .read_text(encoding="utf-8"))[0]
    assert guardada["motivo_clave"] == ""
    assert guardada["motivo_descarte"] == "un motivo escrito"


# --- el número grande y la pestaña Números ----------------------------------

def test_sin_marcar_es_un_numero_grande_y_el_filtro_un_desplegable(sitio):
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": f"https://e/{i}", "title": f"Una {i}", "aplicado": None,
         "score": 70, "found_at": HOY_ISO, "posted_at": HOY_YMD}
        for i in range(3)
    ])
    _, html, _ = get(base, "/trabajos?perfil=test")
    assert '<span class="numero">3</span>' in html
    assert 'class="filtro-fecha"' in html
    assert '<select id="desde"' in html


def test_en_las_otras_pestanias_el_numero_grande_no_va(sitio):
    """Ahí el número es un archivo, no una tarea pendiente."""
    base, tmp = sitio
    _con_historial(tmp, [{"url": "https://e/1", "title": "Una", "aplicado": True,
                          "score": 70, "found_at": HOY_ISO, "posted_at": HOY_YMD}])
    _, html, _ = get(base, "/trabajos?perfil=test&ver=aplicadas")
    assert 'class="cuantas"' not in html
    assert 'class="filtro-fecha"' in html      # el filtro sí sigue


def test_la_pagina_de_numeros_abre_y_muestra_los_totales(sitio):
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": "https://e/1", "title": "Una", "aplicado": True, "score": 70,
         "found_at": HOY_ISO, "posted_at": HOY_YMD},
        {"url": "https://e/2", "title": "Otra", "aplicado": False, "score": 40,
         "motivo_clave": "ingles", "found_at": HOY_ISO, "posted_at": HOY_YMD},
    ])
    codigo, html, _ = get(base, "/estadisticas?perfil=test")
    assert codigo == 200
    assert "Métricas" in html
    assert "Piden inglés" in html


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
    """Cambiar de estado no puede resetear el rango de fechas, ni al revés.

    La antigüedad pasó de cuatro botones a un desplegable, así que el estado
    viaja en un campo oculto del formulario y no pegado en cada link. Lo que se
    prueba es lo mismo: que cada eje conserve el valor del otro.
    """
    base, tmp = sitio
    _con_historial(tmp, VARIADAS)
    _, html, _ = get(base, "/trabajos?perfil=test&ver=descartadas&desde=7d")
    # El desplegable de fechas se lleva puesto el estado elegido...
    assert '<input type="hidden" name="ver" value="descartadas">' in html
    assert '<option value="hoy"' in html
    assert 'value="7d" selected' in html
    # ...y los botones de estado, el rango elegido.
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


def test_lo_que_se_pierde_por_ingles_se_cuenta_en_metricas(sitio):
    """Ver sólo las ofertas en español da la impresión de que el mercado es así;
    lo que se ve es el recorte del filtro, y el número lo desarma.

    Pero el número vive acá, no arriba de la lista de trabajos: ahí la persona
    vino a aplicar, y lo primero que leería sería lo que se pierde. Acá vino a
    mirar números, y el número viene con la salida al lado.
    """
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": "https://e/1", "title": "Con ingles", "aplicado": None, "score": 88,
         "requires_english": True, "found_at": HOY_ISO},
        {"url": "https://e/2", "title": "Sin ingles", "aplicado": None, "score": 60,
         "found_at": HOY_ISO},
    ])
    _, html, _ = get(base, "/estadisticas?perfil=test")
    assert "piden un inglés más alto" in html
    assert "88" in html                     # cuánto valía la mejor que se perdió
    # Y la salida, que es lo que lo convierte en información accionable.
    assert "Cambiar mi nivel de inglés" in html
    assert 'href="/datos?perfil=test"' in html


def test_arriba_de_la_lista_no_va_ningun_recuento_de_perdidas(sitio):
    """La regla dura del rediseño.

    Nunca mostrar lo que la persona se pierde antes de mostrarle lo que puede
    hacer. El cartel de "87 ofertas que no podés tomar" era lo primero que se
    leía al abrir Trabajos, todos los días, antes de la primera oferta.
    """
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": "https://e/1", "title": "Con ingles", "aplicado": None, "score": 88,
         "requires_english": True, "found_at": HOY_ISO},
        {"url": "https://e/2", "title": "Sin ingles", "aplicado": None, "score": 60,
         "found_at": HOY_ISO},
    ])
    _, html, _ = get(base, "/trabajos?perfil=test&desde=todo")
    assert "no podés tomar" not in html
    assert "se te escapan" not in html
    assert "piden un inglés más alto" not in html


def test_sin_ofertas_perdidas_no_hay_cartel(sitio):
    """El cartel tiene que significar algo: en cero no se muestra."""
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": "https://e/2", "title": "Sin ingles", "aplicado": None, "score": 60,
         "found_at": HOY_ISO},
    ])
    _, html, _ = get(base, "/estadisticas?perfil=test")
    assert 'class="callout atencion"' not in html


def test_como_me_presento_es_un_campo_aparte_del_perfil_largo():
    """En "en una línea, qué hago" la gente escribe un párrafo con el stack.

    En el mensaje al reclutador eso tiene que entrar en media frase ("soy AI
    Engineer"), así que va en su propio campo.
    """
    from vacantia.ui import formulario

    html = formulario.render_datos("ana", {"candidate": {"headline": "AI Engineer"}}, [])
    assert '<label for="cand_headline">Cómo me presento</label>' in html
    assert 'value="AI Engineer"' in html


def test_avisa_de_las_ofertas_nuevas_sin_recargar_sola(sitio):
    """Tener que apretar F5 para ver si entró algo es una porquería.

    Pero recargar sola tampoco: si alguien está escribiendo el motivo de un
    descarte, la recarga se lo borra. Avisa con un cartel y decide la persona.
    """
    import json as _json
    import re

    base, tmp = sitio
    _, html, _ = get(base, "/trabajos?perfil=test")

    # El cartel vive escondido en el shell y es el blanco fijo del aviso.
    assert '<div class="toast novedades" id="novedades" role="status"></div>' in html

    # Quien pregunta es el cartel de la corrida, con cómo estaba el historial al
    # abrir metido en la dirección. Ese par es lo que hace que el aviso diga
    # "entraron 3" y no "hay 211".
    pedido = re.search(r'id="corrida" hx-get="([^"]+)"', html).group(1).replace("&amp;", "&")
    assert "marca=" in pedido and "pend=" in pedido

    # Sin cambios en el historial no hay nada que avisar: el aviso vuelve vacío,
    # y vacío de verdad. Si volviera escondido pisaría al que la persona está
    # mirando y el cartel desaparecería solo a los dos segundos.
    _, quieto, _ = get(base, pedido)
    assert "novedades" not in quieto

    # Entra una oferta con la pantalla abierta.
    ruta = tmp / "state" / "test" / "job_history.json"
    ruta.write_text(_json.dumps(OFERTAS + [
        {"url": "https://e/3", "title": "Nueva", "aplicado": None,
         "found_at": "2026-09-04T10:00:00+00:00"}]), encoding="utf-8")
    _, avisa, _ = get(base, pedido)

    assert "Entró 1 oferta nueva" in avisa
    # `hx-swap-oob` es lo que le deja tocar un cartel que no es el que pidió.
    assert 'id="novedades" role="status" hx-swap-oob="true"' in avisa
    assert "location.reload()" in avisa          # lo dispara el botón, no el reloj


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


# --- la banda de recién publicadas ------------------------------------------
#
# Ordenar sólo por puntaje contesta "cuál encaja mejor con mi CV", que no es la
# misma pregunta que "a cuál me conviene postularme ahora": una de 92 de hace
# seis días ya tiene cien postulantes y una de 88 de esta mañana no tiene
# ninguno. La banda sube lo reciente SIN tocar el puntaje que se muestra.

def _dias_atras(n):
    from datetime import timedelta
    return (_date.today() - timedelta(days=n)).isoformat()


def test_lo_de_hoy_sube_arriba_de_lo_de_la_semana_pasada(sitio):
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": "https://e/vieja", "title": "Encaja un poco mejor pero es vieja",
         "aplicado": None, "score": 92, "found_at": HOY_ISO,
         "posted_at": _dias_atras(6)},
        {"url": "https://e/hoy", "title": "Encaja bien y es de hoy",
         "aplicado": None, "score": 88, "found_at": HOY_ISO, "posted_at": HOY_YMD},
    ])
    _, html, _ = get(base, "/trabajos?perfil=test")
    assert html.index("Encaja bien y es de hoy") < html.index("Encaja un poco mejor")
    assert "Recién publicadas" in html
    # El puntaje que se muestra no se toca: sigue diciendo qué tan bien encaja.
    assert ">92<" in html and ">88<" in html


def test_una_mala_de_hoy_no_sube_por_ser_de_hoy(sitio):
    """La lección que ya estaba aprendida y que la banda podía reintroducir.

    Ser de hoy no vuelve buena a una oferta mala. Sólo ordena entre las que ya
    llegan al puntaje que la persona pidió.
    """
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": "https://e/mala", "title": "De hoy pero no sirve",
         "aplicado": None, "score": 10, "found_at": HOY_ISO, "posted_at": HOY_YMD},
        {"url": "https://e/buena", "title": "De hace una semana y encaja",
         "aplicado": None, "score": 90, "found_at": HOY_ISO,
         "posted_at": _dias_atras(6)},
    ])
    _, html, _ = get(base, "/trabajos?perfil=test")
    assert html.index("De hace una semana y encaja") < html.index("De hoy pero no sirve")


def test_sin_fecha_no_cuenta_como_reciente(sitio):
    """No sabemos que sea nueva, y ponerla arriba sería inventarlo.

    `found_at` es de hoy para todo lo que entró en la corrida de hoy: usarlo
    metería en "recién publicadas" un aviso de hace tres meses.
    """
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": "https://e/sinfecha", "title": "Sin fecha", "aplicado": None,
         "score": 95, "found_at": HOY_ISO, "posted_at": ""},
        {"url": "https://e/hoy", "title": "Con fecha de hoy", "aplicado": None,
         "score": 70, "found_at": HOY_ISO, "posted_at": HOY_YMD},
    ])
    _, html, _ = get(base, "/trabajos?perfil=test")
    assert html.index("Con fecha de hoy") < html.index("Sin fecha")


def test_si_no_hay_ninguna_reciente_no_se_dibuja_la_banda(sitio):
    """Un rótulo que encabeza la lista entera no separa nada."""
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": "https://e/1", "title": "Vieja", "aplicado": None, "score": 90,
         "found_at": HOY_ISO, "posted_at": _dias_atras(20)},
    ])
    _, html, _ = get(base, "/trabajos?perfil=test")
    assert "Recién publicadas" not in html


def test_si_son_todas_recientes_tampoco(sitio):
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": f"https://e/{i}", "title": f"Nueva {i}", "aplicado": None,
         "score": 80 + i, "found_at": HOY_ISO, "posted_at": HOY_YMD}
        for i in range(3)
    ])
    _, html, _ = get(base, "/trabajos?perfil=test")
    assert "Recién publicadas" not in html


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


def test_aplique_va_por_cuando_la_marcaste_y_no_por_puntaje(sitio):
    """Es para revisar, no para elegir.

    "¿A quién le mandé el CV esta semana?" se contesta con lo último arriba.
    Ordenarla por puntaje mezclaba lo de ayer con lo de hace tres semanas.
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


def test_descarte_va_por_puntaje_para_poder_auditar_lo_bueno(sitio):
    """Acá la pregunta es otra: no "¿qué hice ayer?" sino "¿me equivoqué al
    descartar algo bueno?".

    Por fecha, una de 90 quedaba quinta, abajo de dos de 0, y las que hay que
    mirar son justamente las de arriba.
    """
    base, tmp = sitio
    _con_historial(tmp, [
        {**_marcada("https://e/floja", "Floja pero recién descartada", "ACME",
                    False, "2026-09-09T10:00:00+00:00", "no sirve"), "score": 0},
        {**_marcada("https://e/buena", "Buena y descartada hace rato", "Otra SA",
                    False, "2026-08-01T10:00:00+00:00", "no sirve"), "score": 90},
        {**_marcada("https://e/media", "Del medio", "Tercera",
                    False, "2026-09-08T10:00:00+00:00", "no sirve"), "score": 45},
    ])
    _, html, _ = get(base, "/trabajos?perfil=test&ver=descartadas")
    assert (html.index("Buena y descartada hace rato")
            < html.index("Del medio")
            < html.index("Floja pero recién descartada"))


def test_a_descarte_no_se_le_aplican_los_filtros_del_sistema(sitio):
    """Lo que descartaste vos se muestra siempre, aunque el filtro también la
    sacara por idioma o por lugar.

    Si no, revisar tus propios descartes mostraría una lista recortada sin
    decirlo, que es justo lo contrario de para lo que sirve esa pestaña.
    """
    base, tmp = sitio
    _con_historial(tmp, [
        {**_marcada("https://e/1", "Descartada y además pide inglés", "ACME",
                    False, HOY_ISO, "no sirve"),
         "score": 90, "requires_english": True, "english_level": "C1"},
    ])
    _, html, _ = get(base, "/trabajos?perfil=test&ver=descartadas")
    assert "Descartada y además pide inglés" in html
    # Y no llega a Sin marcar, que es donde el filtro sí manda.
    assert "Descartada y además pide inglés" not in get(
        base, "/trabajos?perfil=test&ver=pendientes")[1]


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


def test_la_tarjeta_no_muestra_mas_de_dos_controles(sitio):
    """La regla dura de la tarjeta de oferta.

    Antes se veían seis a la vez para una sola oferta: dos botones enfrentados,
    el desplegable de motivos, el campo de texto y "Ya no está". Ahora se ven
    "Apliqué" y "No apliqué", y nada más: el bloque de motivo se despliega al
    marcar "No apliqué" y el resto vive en el menú de tres puntos.
    """
    import re

    from vacantia.ui.render import _tarjeta

    html = _tarjeta({"url": "https://x/1", "title": "T", "score": 70},
                    "ana", "pendientes")

    # Lo que se ve sin abrir nada: todo lo que está fuera de un <details>.
    a_la_vista = re.sub(r"<details.*?</details>", "", html, flags=re.S)
    assert a_la_vista.count("<button") == 1          # sólo el primario
    assert "Apliqué" in a_la_vista
    assert "motivo_clave" not in a_la_vista          # el desplegable, adentro
    assert 'name="motivo"' not in a_la_vista         # el campo de texto, adentro
    assert "Ya no está" not in a_la_vista            # el archivar, en el menú

    # Y el disparador del bloque de motivo es el segundo control, en secundario.
    assert "<summary>No apliqué</summary>" in html
    # Los links auxiliares tampoco compiten: viven en el menú.
    assert "Mensaje para escribirle" in html
    assert "Mensaje para escribirle" not in a_la_vista


def test_los_dos_botones_de_la_tarjeta_no_compiten(sitio):
    """"Apliqué" verde contra "No apliqué" rojo obligaba a decidir antes de leer.

    Y encima usaba rojo para un estado que no es un error: no aplicar a una
    oferta es una decisión normal. Ahora hay un solo primario, que es la acción
    que la persona vino a hacer.
    """
    base, _ = sitio
    _, html, _ = get(base, "/trabajos?perfil=test")

    assert 'class="primario" name="aplicado" value="si"' in html
    assert 'class="verde"' not in html and 'class="rojo"' not in html


def test_ningun_estado_neutral_se_pinta_de_rojo(sitio):
    """Rojo es error o destrucción, nada más.

    "Descartada" y "Archivada" no son errores: son decisiones tomadas, y se
    pintan con neutrales. El verde sí queda, porque marca lo que ya hiciste.
    """
    import re

    from vacantia.ui.render import _tarjeta

    descartada = _tarjeta({"url": "https://x/1", "title": "T", "aplicado": False,
                           "motivo_clave": "ingles"}, "ana", "descartadas")
    archivada = _tarjeta({"url": "https://x/2", "title": "T", "archivada": True},
                         "ana", "archivadas")
    aplicada = _tarjeta({"url": "https://x/3", "title": "T", "aplicado": True},
                        "ana", "aplicadas")

    assert 'class="marca"' in descartada and 'class="marca"' in archivada
    assert 'class="marca si"' in aplicada          # verde: lo que ya hiciste

    # Y en el CSS, danger sólo aparece donde hay un error de verdad.
    from vacantia.ui.render import CSS
    usos = re.findall(r"\n([^\n{]+)\{[^}]*var\(--color-danger\)", CSS)
    for selector in usos:
        # Y en acciones destructivas de verdad, que DESIGN.md también le reserva:
        # borrar un CV borra su texto y no se puede recuperar.
        assert any(p in selector for p in (".mal", ".error", ".aviso.error",
                                           ".borrar-cv", ".peligro")), selector


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


# --- auditar el filtro automático ------------------------------------------
#
# La primera semana de prueba: el sistema descarta solo por idioma y por lugar,
# y un día trajo 23 ofertas nuevas de las cuales 20 las sacó el filtro. Sin
# poder revisar esos descartes no hay forma de saber si el filtro está bien
# calibrado o si está tirando media lista a la basura.

def _filtrada(url, titulo, score=90):
    """Una oferta que el filtro saca por idioma."""
    return {"url": url, "title": titulo, "score": score, "aplicado": None,
            "requires_english": True, "english_level": "C1",
            "found_at": HOY_ISO, "posted_at": HOY_YMD}


def test_las_que_saca_el_filtro_tienen_su_propia_pestania(sitio):
    """No llegan a Sin marcar, y hasta ahora no llegaban a ningún lado."""
    base, tmp = sitio
    _con_historial(tmp, [
        _filtrada("https://e/1", "La saca el filtro", 95),
        {"url": "https://e/2", "title": "Esta sí llega", "score": 70,
         "aplicado": None, "found_at": HOY_ISO, "posted_at": HOY_YMD},
    ])

    _, pendientes, _ = get(base, "/trabajos?perfil=test&ver=pendientes")
    assert "Esta sí llega" in pendientes
    assert "La saca el filtro" not in pendientes

    _, filtradas, _ = get(base, "/trabajos?perfil=test&ver=filtradas")
    assert "La saca el filtro" in filtradas
    assert "Esta sí llega" not in filtradas
    # Y se lee el motivo que dio el sistema, que es lo que hay que auditar.
    assert "Piden un inglés más alto que el tuyo" in filtradas
    # Con las dos respuestas a la vista, y ninguna en rojo.
    assert "Bien descartada" in filtradas and "Mal descartada" in filtradas
    assert 'class="rojo"' not in filtradas


def test_la_pildora_de_filtradas_se_encuentra_de_un_vistazo(sitio):
    """No es una pestaña más: es la tarea de la semana de prueba.

    Se pinta en el azul de "estado del sistema", que es lo que son esas
    ofertas: algo que decidió el sistema. **No en el índigo de acción**, que
    convertiría la píldora en un botón, y **no en rojo**, que en este sistema
    significa error o destrucción y un descarte del filtro no es ninguna de las
    dos. El color no viaja solo: lo acompañan la palabra y el embudo.
    """
    import re

    from vacantia.ui.render import CSS

    base, _ = sitio
    _, html, _ = get(base, "/trabajos?perfil=test")
    fila = html[html.index('class="filtros"'):html.index("</div>", html.index('class="filtros"'))]

    # Sólo esta píldora lleva la marca, y lleva su ícono.
    assert fila.count("revisar") == 1
    pildora = fila[fila.index("class='revisar'"):]
    assert "<svg" in pildora[:pildora.index("</a>")]
    assert "Filtradas" in pildora[:pildora.index("</a>")]

    regla = CSS[CSS.index(".filtros a.revisar {"):]
    regla = regla[:regla.index("}")]
    assert "var(--color-info)" in regla and "var(--color-info-surface)" in regla
    assert "var(--color-action)" not in regla
    assert "var(--color-danger)" not in regla


def test_mal_descartada_vuelve_a_sin_marcar(sitio):
    """Es el punto de marcarla: si el filtro se equivocó, la oferta sigue
    estando y todavía se le puede aplicar."""
    base, tmp = sitio
    _con_historial(tmp, [_filtrada("https://e/1", "El filtro se equivocó", 95)])

    _, _, url = post(base, "/revisar-filtro", {
        "perfil": "test", "url": "https://e/1", "revision": "mal", "desde": "todo"})
    assert "error" not in url

    _, pendientes, _ = get(base, "/trabajos?perfil=test&ver=pendientes")
    assert "El filtro se equivocó" in pendientes
    assert "Apliqué" in pendientes                  # ya se le puede aplicar

    # Y sale de Filtradas: se revisa una vez y no vuelve a aparecer.
    _, filtradas, _ = get(base, "/trabajos?perfil=test&ver=filtradas")
    assert "El filtro se equivocó" not in filtradas

    guardada = json.loads((tmp / "state" / "test" / "job_history.json")
                          .read_text(encoding="utf-8"))[0]
    assert guardada["revision_filtro"] == "mal"
    assert guardada["fecha_revision_filtro"]
    assert guardada["aplicado"] is None             # no es un veredicto de la oferta


def test_bien_descartada_queda_encajonada(sitio):
    """Se va de Filtradas y no vuelve a Sin marcar: el filtro acertó."""
    base, tmp = sitio
    _con_historial(tmp, [_filtrada("https://e/1", "Bien sacada")])

    post(base, "/revisar-filtro", {
        "perfil": "test", "url": "https://e/1", "revision": "bien", "desde": "todo"})

    assert "Bien sacada" not in get(base, "/trabajos?perfil=test&ver=filtradas")[1]
    assert "Bien sacada" not in get(base, "/trabajos?perfil=test&ver=pendientes")[1]
    # Sigue en el historial: no se borra nada.
    assert "Bien sacada" in get(base, "/trabajos?perfil=test&ver=todas")[1]


def test_el_marcador_cuenta_las_dos_y_es_acumulativo(sitio):
    """Con dos días de muestra, un porcentaje sobre lo de hoy no dice nada.

    El marcador cuenta contra el historial entero y no contra el rango de
    fechas que esté elegido, para poder mirar la semana completa.
    """
    base, tmp = sitio
    _con_historial(tmp, [_filtrada(f"https://e/{i}", f"Filtrada {i}")
                         for i in range(4)])

    # Sin revisar nada, el marcador dice qué va a pasar en vez de mostrar ceros.
    _, vacio, _ = get(base, "/trabajos?perfil=test&ver=filtradas")
    assert 'class="callout marcador"' in vacio
    assert "Acá se revisa si el sistema descartó bien" in vacio
    assert '<span class="valor">0</span>' not in vacio

    for i, revision in enumerate(("bien", "bien", "mal")):
        post(base, "/revisar-filtro", {"perfil": "test", "url": f"https://e/{i}",
                                       "revision": revision, "desde": "todo"})

    _, html, _ = get(base, "/trabajos?perfil=test&ver=filtradas")
    assert '<span class="valor">2</span> bien descartadas' in html
    assert '<span class="valor">1</span> mal descartadas' in html
    # El progreso hacia la meta, y no un porcentaje de aciertos: con 3 revisadas
    # un "100% de aciertos" suena a veredicto y todavía no lo es.
    assert "Sobre 3 revisadas. Con 40 ya se puede decir" in html
    assert "te faltan 37" in html

    # Acumulativo: filtrar por fecha no lo achica.
    _, con_filtro, _ = get(base, "/trabajos?perfil=test&ver=filtradas&desde=hoy")
    assert "Sobre 3 revisadas" in con_filtro

    # Y el marcador vive sólo acá: en Sin marcar no va ningún recuento.
    _, otras, _ = get(base, "/trabajos?perfil=test&ver=pendientes")
    assert "bien descartadas" not in otras


def test_una_revision_inventada_no_se_guarda(sitio):
    base, tmp = sitio
    _con_historial(tmp, [_filtrada("https://e/1", "Una")])
    _, _, url = post(base, "/revisar-filtro", {
        "perfil": "test", "url": "https://e/1", "revision": "cualquiera"})
    assert "error" in url
    guardada = json.loads((tmp / "state" / "test" / "job_history.json")
                          .read_text(encoding="utf-8"))[0]
    assert "revision_filtro" not in guardada


def test_en_filtradas_manda_el_puntaje_y_no_la_fecha(sitio):
    """Las de más puntaje son las que más duele perder si el filtro se
    equivocó, así que son las primeras que hay que mirar."""
    base, tmp = sitio
    _con_historial(tmp, [
        _filtrada("https://e/floja", "Floja pero nueva", 55),
        _filtrada("https://e/buena", "Buena y vieja", 95),
    ])
    _, html, _ = get(base, "/trabajos?perfil=test&ver=filtradas")
    assert html.index("Buena y vieja") < html.index("Floja pero nueva")
    # Sin la banda de recientes: acá la pregunta no es a cuál postularse.
    assert "Recién publicadas" not in html


def test_debajo_de_50_no_se_revisa(sitio):
    """Si el filtro se equivocó con una de 20, esa oferta no te iba a servir.

    Revisar ese tramo es gastar la atención donde el error no tiene
    consecuencia, y son las que más quedan cuando el pozo se va agotando.
    """
    base, tmp = sitio
    _con_historial(tmp, [
        _filtrada("https://e/vale", "Vale revisarla", 50),      # el borde entra
        _filtrada("https://e/justo-abajo", "Justo abajo", 49),
        _filtrada("https://e/no-vale", "No vale la pena", 20),
        _filtrada("https://e/cero", "Ni ahí", 0),
    ])
    _, html, _ = get(base, "/trabajos?perfil=test&ver=filtradas")
    assert "Vale revisarla" in html
    for fuera in ("Justo abajo", "No vale la pena", "Ni ahí"):
        assert fuera not in html, fuera

    # El contador de la píldora dice lo que hay para revisar, no el total: si
    # dijera 4 y la lista mostrara 1, el número estaría mintiendo.
    assert ">Filtradas <span class=\"cuenta\">1</span>" in html


def test_cuando_no_queda_nada_dice_por_que(sitio):
    """Una pantalla vacía sin explicación se lee como "se terminaron las ofertas"."""
    base, tmp = sitio
    _con_historial(tmp, [
        _filtrada("https://e/1", "Puntúa poco", 30),
        _filtrada("https://e/2", "Puntúa poco también", 10),
    ])
    _, html, _ = get(base, "/trabajos?perfil=test&ver=filtradas")
    assert "No queda ninguna por revisar" in html
    assert "Quedan 2 que el" in html          # cuántas quedaron abajo del corte
    assert "puntúan menos de 50" in html
    # Y la salida: buscar más, que es lo único que puede traer una de 50 o más.
    assert "Buscar ahora" in html


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


def test_la_explicacion_larga_vive_detras_del_signo_de_pregunta():
    """Tres renglones de texto chico al lado del botón que importa competían
    con él. Escondido detrás del ícono, está cuando se busca y no antes.

    Se abre con el mouse y también con el foco: quien tabula no pasa el mouse
    por ningún lado. Y el texto está en el DOM desde el principio, para que un
    lector de pantalla lo lea como nota del rótulo.
    """
    from vacantia.ui.estilos import CSS
    from vacantia.ui.render import linkedin

    html = linkedin("ana", "publicaciones", [])
    assert 'class="ayuda-al-lado" tabindex="0" role="note"' in html
    assert "Contá acá lo que vayas mandando" in html
    # El rótulo va arriba del control, no al costado.
    assert html.index("Apliqué desde acá") < html.index('class="stepper"')

    assert ".ayuda-al-lado:hover .globo" in CSS
    assert ".ayuda-al-lado:focus-within .globo" in CSS


def test_el_anotador_es_una_sola_pieza_y_solo_el_numero_va_en_verde():
    """Tres cajas iguales no dicen que se tocan juntas ni cuál es el número.

    Y el verde acá significa lo que ya hiciste: el más y el menos todavía no
    son nada, así que van en neutro.
    """
    from vacantia.ui.estilos import CSS
    from vacantia.ui.render import linkedin

    html = linkedin("ana", "publicaciones", [], apliques={"pendientes": 3,
                                                          "confirmadas": 8})
    assert '<b class="numero">3</b>' in html
    assert "Ya sumaste 8." in html
    # Sin nada anotado, no hay nada que confirmar ni que sacar.
    vacio = linkedin("ana", "publicaciones", [])
    assert vacio.count("disabled") == 2

    stepper = CSS[CSS.index(".stepper {"):CSS.index(".apliques .confirmar {")]
    assert "var(--color-success)" in stepper.split(".stepper .numero {")[1]
    assert "var(--color-success)" not in stepper.split(".stepper .numero {")[0]
