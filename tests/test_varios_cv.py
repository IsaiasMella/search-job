"""Varios CV por perfil, y qué CV mandar en cada oferta.

Una persona puede postularse con más de un perfil profesional: AI Engineer y
Full Stack, o varias variantes de QHSE. Lo que se fija acá:

* **Un perfil viejo, con un solo CV, no nota nada.** Mismo prompt byte a byte,
  mismos términos de búsqueda, ninguna línea nueva en la pantalla.
* **Cada CV amplía la búsqueda** en todas las fuentes, incluso en las que tienen
  términos propios, que antes ignoraban las palabras clave del perfil.
* **Se puntúa contra el CV que mejor encaja**, no contra el primero.
* **Las ofertas viejas reciben una recomendación estimada gratis**, marcada como
  tal, sin re-puntuar nada.
* **Un CV recién agregado y vacío no cuenta** hasta que tenga texto.
* **En Mi perfil se ve un CV por vez**, y borrar uno pide confirmación.
"""

import json
from types import SimpleNamespace

from vacantia import config, scoring
from vacantia.consejo import cv_que_mejor_encaja
from vacantia.models import Job
from vacantia.ui import data

from tests.test_ui import HOY_ISO, _con_historial, get, post, sitio  # noqa: F401

CV_AI = "# CV AI Engineer\nLangChain, RAG, LLM, agentes, Chroma, embeddings, OpenAI."
CV_FULL = "# CV Full Stack\nReact, Next.js, TypeScript, Node, FastAPI, PostgreSQL."

CVS = [{"id": "ai-engineer", "nombre": "AI Engineer", "texto": CV_AI},
       {"id": "full-stack", "nombre": "Full Stack", "texto": CV_FULL}]


def _con_dos_cvs(tmp):
    """El perfil de prueba, con dos CV escritos y sus palabras de búsqueda."""
    (tmp / "resume" / "ai.md").write_text(CV_AI, encoding="utf-8")
    (tmp / "resume" / "full.md").write_text(CV_FULL, encoding="utf-8")
    ruta = tmp / "profiles" / "test.json"
    perfil = json.loads(ruta.read_text(encoding="utf-8"))
    perfil["cvs"] = [
        {"id": "ai-engineer", "nombre": "AI Engineer", "path": "resume/ai.md",
         "palabras_clave": ["AI Engineer"]},
        {"id": "full-stack", "nombre": "Full Stack", "path": "resume/full.md",
         "palabras_clave": ["Full Stack", "React"]},
    ]
    ruta.write_text(json.dumps(perfil), encoding="utf-8")
    return perfil


def _oferta(url, descripcion, **extra):
    return {"url": url, "title": "Developer", "company": "ACME", "aplicado": None,
            "score": 70, "found_at": HOY_ISO, "description": descripcion,
            "posting_language": "es", "country": "Argentina", "work_mode": "remote",
            **extra}


def _perfil_leido(tmp):
    return json.loads((tmp / "profiles" / "test.json").read_text(encoding="utf-8"))


# --- el perfil viejo no nota nada -----------------------------------------------

def test_un_perfil_con_solo_cv_path_se_lee_como_un_cv_principal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "resume").mkdir()
    (tmp_path / "resume" / "x.md").write_text("mi CV", encoding="utf-8")
    perfil = {"cv_path": "resume/x.md", "candidate": {"headline": "AI Engineer"}}

    assert config.cvs_del_perfil(perfil) == [
        {"id": "principal", "nombre": "AI Engineer", "path": "resume/x.md",
         "palabras_clave": []}]
    assert config.load_resume(perfil) == "mi CV"
    # Sin headline, el nombre no queda vacío: una tarjeta que dijera "Mandá tu CV"
    # sin nombre no diría nada.
    assert config.cvs_del_perfil({"cv_path": "resume/x.md"})[0]["nombre"] == "Principal"


def test_los_ids_salen_del_nombre_y_no_se_repiten():
    """El id es lo que se guarda en cada oferta: no puede depender de tildes ni
    de mayúsculas, y dos CV con el mismo id serían indistinguibles."""
    assert config.id_de_cv("Full Stack") == "full-stack"
    assert config.id_de_cv("Técnico QHSE") == "tecnico-qhse"
    assert config.id_de_cv("") == "cv"
    perfil = {"cvs": [{"nombre": "Full Stack", "path": "a.md"},
                      {"nombre": "full stack", "path": "b.md"},
                      {"nombre": "Sin archivo"}]}
    assert [cv["path"] for cv in config.cvs_del_perfil(perfil)] == ["a.md"]


def test_un_cv_vacio_no_cuenta(tmp_path, monkeypatch):
    """"Agregar otro CV" lo crea vacío. Si contara, todas las tarjetas pasarían a
    recomendar contra un CV que no dice nada."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "lleno.md").write_text("algo", encoding="utf-8")
    (tmp_path / "vacio.md").write_text("  \n", encoding="utf-8")
    perfil = {"cvs": [{"nombre": "Lleno", "path": "lleno.md"},
                      {"nombre": "Vacío", "path": "vacio.md"}]}
    assert [cv["id"] for cv in config.cvs_con_texto(perfil)] == ["lleno"]


# --- cada CV amplía la búsqueda -----------------------------------------------------

PERFIL_CON_CVS = {
    "keywords": ["Python"],
    "cvs": [{"nombre": "AI Engineer", "path": "a.md", "palabras_clave": ["AI Engineer", "python"]},
            {"nombre": "Full Stack", "path": "b.md", "palabras_clave": ["Full Stack", "React"]}],
}


def test_los_terminos_suman_los_de_cada_cv_sin_repetir():
    assert config.terminos_de_busqueda(PERFIL_CON_CVS) == [
        "Python", "AI Engineer", "Full Stack", "React"]
    # Con términos propios de la fuente, van primero y los de los CV se suman.
    assert config.terminos_de_busqueda(PERFIL_CON_CVS, ["LLM Engineer"]) == [
        "LLM Engineer", "AI Engineer", "python", "Full Stack", "React"]


def test_un_perfil_de_un_cv_busca_lo_mismo_que_antes():
    perfil = {"keywords": ["QHSE", "HSE"]}
    assert config.terminos_de_busqueda(perfil) == ["QHSE", "HSE"]
    assert config.terminos_de_busqueda(perfil, ["Supervisor"]) == ["Supervisor"]


def test_todas_las_fuentes_buscan_con_los_terminos_de_los_cv():
    """Era el agujero: LinkedIn, Indeed y Get on Board tienen términos propios e
    ignoraban las palabras clave, así que un CV de Full Stack no traía ni una
    oferta de Full Stack."""
    from vacantia.sources import careers, getonbrd, google_posts, linkedin_jobs, portales_ar
    from vacantia.ui.linkedin_urls import puestos_de

    combos = linkedin_jobs.build_searches(
        PERFIL_CON_CVS, {"search_terms": ["LLM Engineer"], "locations": ["Argentina"],
                         "max_searches": 0})
    assert ("Full Stack", "Argentina") in combos

    consultas = google_posts.build_queries(PERFIL_CON_CVS, {"roles": ["LLM Engineer"],
                                                            "max_queries": 0})
    assert any("Full Stack" in q for q in consultas)

    fuente = SimpleNamespace(config={"search_terms": ["LLM Engineer"]},
                             profile=PERFIL_CON_CVS, max_queries=0)
    assert "Full Stack" in portales_ar.PortalSource.terminos(fuente)
    clase_getonbrd = next(v for v in vars(getonbrd).values()
                          if isinstance(v, type) and "terminos" in vars(v))
    assert "Full Stack" in clase_getonbrd.terminos(fuente)

    assert '"Full Stack"' in careers.build_search_query("acme.com", PERFIL_CON_CVS)
    assert "Full Stack" in puestos_de(PERFIL_CON_CVS)


# --- la estimación gratis ---------------------------------------------------------

def test_la_estimacion_elige_el_cv_que_menos_palabras_le_faltan():
    react = Job(url="u", title="Frontend", description="React Next.js TypeScript React Next.js")
    rag = Job(url="u", title="AI", description="LangChain RAG embeddings LangChain RAG")
    assert cv_que_mejor_encaja(react, CVS) == "full-stack"
    assert cv_que_mejor_encaja(rag, CVS) == "ai-engineer"
    # Sin nada que comparar, gana el primero: es el CV principal.
    assert cv_que_mejor_encaja(Job(url="u", title=""), CVS) == "ai-engineer"
    assert cv_que_mejor_encaja(react, []) == ""


# --- el scoring ------------------------------------------------------------------------

PERFIL_SCORING = {"min_score": 60, "llm": {},
                  "candidate": {"name": "I", "profile": "AI Engineer: conecto modelos"}}


def _capturar_prompt(monkeypatch, respuesta):
    capturas = []

    def falso(cfg, messages, **_):
        capturas.append(messages[0]["content"])
        return respuesta

    monkeypatch.setattr(scoring, "chat_with_llm", falso)
    return capturas


def test_con_un_cv_el_prompt_es_byte_a_byte_el_de_siempre(monkeypatch):
    capturas = _capturar_prompt(monkeypatch, '[{"job_number": 1, "score": 80}]')
    jobs = [Job(url="https://e/1", title="Dev", description="Python")]
    scoring._score_batch_with_llm(jobs, [{"id": "principal", "texto": "MI CV"}],
                                  PERFIL_SCORING, 60)

    esperado = scoring.SCORE_PROMPT.format(
        candidate_profile=scoring.build_candidate_profile(PERFIL_SCORING),
        resume_summary="MI CV", jobs_text=scoring._jobs_text(jobs), min_score=60)
    assert capturas[-1] == esperado
    assert jobs[0].cv_recomendado == ""


def test_un_cv_vacio_no_convierte_el_prompt_en_uno_de_varios(monkeypatch):
    """El CV recién agregado y todavía vacío no llega al modelo: el prompt sigue
    siendo el de un solo CV y la oferta no trae recomendación."""
    capturas = _capturar_prompt(monkeypatch, '[{"job_number": 1, "score": 80}]')
    monkeypatch.setattr(scoring, "has_llm_credentials", lambda cfg: True)
    jobs = [Job(url="https://e/1", title="Dev", description="Python")]
    scoring.score_jobs(jobs, [{"id": "a", "nombre": "A", "texto": "MI CV"},
                              {"id": "b", "nombre": "B", "texto": "   "}], PERFIL_SCORING)

    assert "RESUME SUMMARY" in capturas[-1]
    assert "CANDIDATE CVs" not in capturas[-1]
    assert jobs[0].cv_recomendado == ""


def test_con_dos_cvs_el_modelo_ve_los_dos_y_elige(monkeypatch):
    capturas = _capturar_prompt(
        monkeypatch, '[{"job_number": 1, "score": 85, "cv": "full-stack", "reason": "r"}]')
    jobs = [Job(url="https://e/1", title="Dev React", description="React")]
    scoring._score_batch_with_llm(jobs, CVS, PERFIL_SCORING, 60)

    prompt = capturas[-1]
    assert 'id="ai-engineer"' in prompt and 'id="full-stack"' in prompt
    assert '"cv": "id of the CV' in prompt
    assert "RESUME SUMMARY" not in prompt
    # El "qué hago" del perfil describe UNO de los CV y sesgaba contra el otro.
    assert "conecto modelos" not in prompt
    assert jobs[0].cv_recomendado == "full-stack"


def test_si_el_modelo_contesta_el_nombre_se_guarda_el_id(monkeypatch):
    _capturar_prompt(monkeypatch, '[{"job_number": 1, "score": 85, "cv": "Full Stack"}]')
    jobs = [Job(url="https://e/1", title="Dev")]
    scoring._score_batch_with_llm(jobs, CVS, PERFIL_SCORING, 60)
    assert jobs[0].cv_recomendado == "full-stack"


def test_si_el_modelo_inventa_un_cv_se_usa_la_estimacion(monkeypatch):
    _capturar_prompt(monkeypatch, '[{"job_number": 1, "score": 85, "cv": "marketing"}]')
    jobs = [Job(url="https://e/1", title="Dev", description="React Next.js TypeScript")]
    scoring._score_batch_with_llm(jobs, CVS, PERFIL_SCORING, 60)
    assert jobs[0].cv_recomendado == "full-stack"


def test_la_heuristica_sin_modelo_tambien_recomienda_cv():
    jobs = [Job(url="https://e/1", title="Dev", description="React Next.js TypeScript")]
    scoring._score_batch_heuristic(jobs, CVS, {"keywords": ["React"]}, 60)
    assert jobs[0].cv_recomendado == "full-stack"


def test_el_triaje_sigue_aceptando_un_cv_como_texto():
    """`triage` y `score_jobs` recibían el CV como texto suelto. Se sigue
    aceptando, para no romper a quien todavía los llame así."""
    solo = [Job(url="https://e/2", title="Dev", description="Python")]
    assert scoring.triage(solo, "MI CV", {"max_new_per_run": 5}) == (solo, [])


# --- la pantalla -------------------------------------------------------------------------

def test_con_un_cv_ninguna_oferta_dice_que_cv_mandar(sitio):
    base, tmp = sitio
    _con_historial(tmp, [_oferta("https://e/1", "React Next.js")])
    ofertas, _, _ = data.ofertas("test", "todas")
    assert all("_cv" not in o for o in ofertas)
    assert "Mandá tu CV" not in get(base, "/trabajos?perfil=test&ver=todas")[1]


def test_con_dos_cvs_cada_oferta_dice_cual_mandar(sitio):
    base, tmp = sitio
    _con_dos_cvs(tmp)
    _con_historial(tmp, [
        _oferta("https://e/modelo", "LangChain RAG", cv_recomendado="full-stack"),
        _oferta("https://e/vieja", "React Next.js TypeScript React"),
        _oferta("https://e/borrado", "React Next.js TypeScript", cv_recomendado="ya-no-existe"),
    ])
    por_url = {o["url"]: o["_cv"] for o in data.ofertas("test", "todas")[0]}

    # Lo que dijo el modelo se respeta, aunque las palabras digan otra cosa.
    assert por_url["https://e/modelo"] == {"id": "full-stack", "nombre": "Full Stack",
                                           "estimado": False}
    # Las viejas se estiman, y lo dicen.
    assert por_url["https://e/vieja"]["id"] == "full-stack"
    assert por_url["https://e/vieja"]["estimado"] is True
    # Un CV borrado no deja la oferta sin recomendación: se vuelve a estimar.
    assert por_url["https://e/borrado"]["estimado"] is True

    html = get(base, "/trabajos?perfil=test&ver=todas")[1]
    assert "Mandá tu CV <b>Full Stack</b>" in html
    assert 'class="cv-estimado"' in html


def test_consejo_compara_contra_el_cv_de_esa_oferta(sitio):
    """Con el CV equivocado, "React" figuraba como palabra que falta aunque el
    CV de Full Stack la tiene."""
    base, tmp = sitio
    _con_dos_cvs(tmp)
    url = "https://e/react"
    _con_historial(tmp, [_oferta(url, "React Next.js TypeScript React Next.js",
                                 cv_recomendado="full-stack")])

    html = get(base, f"/consejo?perfil=test&url={url}")[1]
    assert "Comparando con tu CV <b>Full Stack</b>" in html
    assert "<li>react</li>" not in html

    assert "Escrito para tu CV <b>Full Stack</b>" in get(
        base, f"/mensajes?perfil=test&url={url}")[1]


def test_con_un_cv_consejo_no_nombra_ningun_cv(sitio):
    base, tmp = sitio
    url = "https://e/react"
    _con_historial(tmp, [_oferta(url, "React")])
    assert "Comparando con tu CV" not in get(base, f"/consejo?perfil=test&url={url}")[1]


# --- Mi perfil ---------------------------------------------------------------------------

def test_con_un_cv_no_hay_selector_ni_boton_de_borrar(sitio):
    base, tmp = sitio
    uno = get(base, "/datos?perfil=test")[1]
    assert 'class="grilla cv activo" id="cv-principal"' in uno
    assert 'name="cv_principal_texto"' in uno
    assert "Agregar otro CV" in uno
    assert 'id="cv-elegido"' not in uno
    assert "Borrar este CV" not in uno           # tiene que quedar al menos uno


def test_con_varios_cvs_se_ve_uno_por_vez_y_se_elige_cual(sitio):
    """Con cinco o seis CV uno abajo del otro, con el texto entero, Mi perfil era
    una columna interminable. Se ve uno por vez y se cambia con el desplegable."""
    base, tmp = sitio
    _con_dos_cvs(tmp)

    html = get(base, "/datos?perfil=test")[1]
    assert 'id="cv-elegido"' in html
    assert 'onchange="elegirCv(this.value)"' in html
    # Todos los CV están en el formulario, así lo no guardado no se pierde...
    assert 'name="cv_ai-engineer_texto"' in html and 'name="cv_full-stack_texto"' in html
    # ...pero sólo uno está a la vista: el primero, si nadie pidió otro.
    assert html.count('class="grilla cv activo"') == 1
    assert 'class="grilla cv activo" id="cv-ai-engineer"' in html
    assert html.count("Borrar este CV") == 2

    elegido = get(base, "/datos?perfil=test&cv=full-stack")[1]
    assert 'class="grilla cv activo" id="cv-full-stack"' in elegido
    assert '<option value="full-stack" selected>' in elegido
    # Uno que no existe (lo acaban de borrar) cae en el primero.
    assert 'class="grilla cv activo" id="cv-ai-engineer"' in get(
        base, "/datos?perfil=test&cv=no-existe")[1]


def test_despues_de_guardar_se_sigue_viendo_el_cv_que_estabas_editando(sitio):
    base, tmp = sitio
    _con_dos_cvs(tmp)
    _, html, url = post(base, "/datos", {"perfil": "test", "keywords": "Python",
                                         "cv_elegido": "full-stack"})
    assert "cv=full-stack" in url
    assert 'class="grilla cv activo" id="cv-full-stack"' in html


def test_enter_en_un_campo_guarda_y_no_agrega_ni_borra_cvs(sitio):
    """Enter manda el formulario con el PRIMER botón de envío que encuentra. Ése
    era "Agregar otro CV", así que un Enter en cualquier campo agregaba un CV; con
    el borrado habría sido peor. El primer botón tiene que ser el de guardar."""
    base, tmp = sitio
    _con_dos_cvs(tmp)
    html = get(base, "/datos?perfil=test")[1]
    formulario = html[html.index('<form class="datos" method="post" action="/datos">'):]
    primer_boton = formulario[formulario.index('type="submit"') - 80:formulario.index('type="submit"') + 120]
    assert "formaction" not in primer_boton
    assert "enviar-por-defecto" in primer_boton


def test_guardar_escribe_nombre_palabras_y_texto_de_cada_cv(sitio):
    base, tmp = sitio
    _con_dos_cvs(tmp)
    post(base, "/datos", {
        "perfil": "test", "keywords": "Python",
        "cv_ai-engineer_nombre": "AI", "cv_ai-engineer_palabras": "LLM Engineer, RAG",
        "cv_ai-engineer_texto": "# AI nuevo",
        "cv_full-stack_nombre": "Full Stack Python", "cv_full-stack_palabras": "Next.js",
        "cv_full-stack_texto": "# Full nuevo",
    })
    perfil = _perfil_leido(tmp)
    assert [(c["id"], c["nombre"], c["palabras_clave"]) for c in perfil["cvs"]] == [
        ("ai-engineer", "AI", ["LLM Engineer", "RAG"]),
        # Renombrar no cambia el id: las ofertas que lo recomiendan siguen andando.
        ("full-stack", "Full Stack Python", ["Next.js"]),
    ]
    assert perfil["cv_path"] == "resume/ai.md"      # sigue al primero
    assert (tmp / "resume" / "full.md").read_text(encoding="utf-8") == "# Full nuevo"


def test_el_campo_cv_de_antes_sigue_guardando_en_el_primero(sitio):
    base, tmp = sitio
    post(base, "/datos", {"perfil": "test", "keywords": "Python", "cv": "# Viejo"})
    assert (tmp / "resume" / "test.md").read_text(encoding="utf-8") == "# Viejo"


def test_agregar_un_cv_lo_crea_vacio_y_lo_deja_a_la_vista(sitio):
    base, tmp = sitio
    _con_historial(tmp, [_oferta("https://e/1", "React")])
    _, html, url = post(base, "/cv-nuevo", {"perfil": "test", "keywords": "Python"})

    perfil = _perfil_leido(tmp)
    assert [c["id"] for c in perfil["cvs"]] == ["principal", "cv-2"]
    assert (tmp / "resume" / "test-cv-2.md").read_text(encoding="utf-8") == ""
    # La pantalla vuelve con el CV nuevo a la vista, que es el que hay que llenar.
    assert "cv=cv-2" in url
    assert 'class="grilla cv activo" id="cv-cv-2"' in html
    # Vacío no cuenta: ninguna tarjeta empieza a recomendar.
    assert "Mandá tu CV" not in get(base, "/trabajos?perfil=test&ver=todas")[1]


def test_borrar_un_cv_pide_confirmar_y_despues_borra_su_archivo(sitio):
    """El botón que borra está adentro de la confirmación, con el nombre del CV a
    la vista. Una vez confirmado, es definitivo: se va del perfil y su texto."""
    base, tmp = sitio
    _con_dos_cvs(tmp)

    html = get(base, "/datos?perfil=test")[1]
    confirmacion = html[html.index('<details class="borrar-cv">'):]
    confirmacion = confirmacion[:confirmacion.index("</details>")]
    assert "<summary>Borrar este CV</summary>" in confirmacion
    assert "no se puede recuperar" in confirmacion
    assert 'formaction="/cv-borrar"' in confirmacion
    assert "Cancelar" in confirmacion

    _, pagina, _ = post(base, "/cv-borrar", {"perfil": "test", "keywords": "Python",
                                              "cv_borrar": "full-stack"})
    assert [c["id"] for c in _perfil_leido(tmp)["cvs"]] == ["ai-engineer"]
    assert not (tmp / "resume" / "full.md").exists()
    assert "Borré el CV «Full Stack»" in pagina


def test_nunca_se_borra_el_ultimo_cv(sitio):
    base, tmp = sitio
    _, pagina, _ = post(base, "/cv-borrar", {"perfil": "test", "keywords": "Python",
                                              "cv_borrar": "principal"})
    assert [c["id"] for c in _perfil_leido(tmp)["cvs"]] == ["principal"]
    assert (tmp / "resume" / "test.md").exists()
    assert "Tiene que quedar al menos un CV." in pagina


def test_no_se_borra_un_archivo_que_lee_otro_perfil(sitio):
    """Si dos CV apuntan al mismo texto, borrar uno no puede dejar al otro vacío."""
    base, tmp = sitio
    _con_dos_cvs(tmp)
    papa = _perfil_leido(tmp)
    papa["name"] = "papa"
    papa["cvs"] = [{"id": "prestado", "nombre": "Prestado", "path": "resume/full.md",
                    "palabras_clave": []}]
    (tmp / "profiles" / "papa.json").write_text(json.dumps(papa), encoding="utf-8")

    post(base, "/cv-borrar", {"perfil": "test", "keywords": "Python",
                              "cv_borrar": "full-stack"})
    assert [c["id"] for c in _perfil_leido(tmp)["cvs"]] == ["ai-engineer"]
    assert (tmp / "resume" / "full.md").exists()


# --- Telegram ------------------------------------------------------------------------------

def test_telegram_dice_que_cv_mandar_solo_con_varios_cv():
    from vacantia.notifiers.telegram import _nombres_de_cv, format_message

    job = Job(url="https://e/1", title="Dev", cv_recomendado="full-stack")
    nombres = {"ai-engineer": "AI Engineer", "full-stack": "Full Stack"}
    assert "CV: Full Stack" in format_message([job], "h", nombres)
    assert "CV:" not in format_message([job], "h", {})
    assert _nombres_de_cv({"cv_path": "x.md"}) == {}
    assert _nombres_de_cv(PERFIL_CON_CVS) == nombres
