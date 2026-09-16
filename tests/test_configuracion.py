"""Mi perfil y Configuración, dos pantallas; y borrar un perfil entero.

Mi perfil era una sola pantalla que mezclaba lo que se toca todos los días (los
CV, las palabras, dónde) con lo que se carga una vez (las claves, el Telegram,
las fuentes). Se partió en dos. Lo que se fija acá:

* **Cada pantalla guarda sólo sus campos.** Un tilde sin marcar no viaja en el
  formulario, así que "no vino" se lee como "apagado". Eso sólo vale en la
  pantalla que dibuja el tilde: guardar Mi perfil no puede apagar las fuentes, y
  guardar Configuración no puede vaciar las palabras clave ni el CV.
* **Un solo botón primario por pantalla.**
* **Borrar un perfil pide confirmación en el lugar**, como borrar un CV, y
  después borra todo lo suyo: el perfil, los CV, las empresas, las ofertas y la
  búsqueda programada.
* **Lo compartido no se borra**, y los demás perfiles quedan intactos.

`schtasks` nunca se corre de verdad: el Programador de tareas de la máquina que
corre los tests no es asunto de los tests.
"""

import json
from html.parser import HTMLParser
from types import SimpleNamespace

import pytest

from vacantia.ui import data

from tests.test_ui import get, post, sitio  # noqa: F401


def _perfil_leido(tmp, nombre="test"):
    return json.loads((tmp / "profiles" / f"{nombre}.json").read_text(encoding="utf-8"))


def _escribir_perfil(tmp, perfil, nombre="test"):
    (tmp / "profiles" / f"{nombre}.json").write_text(json.dumps(perfil), encoding="utf-8")


def test_cada_clave_dice_donde_se_consigue(sitio):
    """"Sin cargar" sin decir dónde se consigue era un callejón sin salida.

    Los links abren en otra pestaña para no perder lo que ya estaba escrito en
    el formulario. El número de chat de Telegram es lo que nadie sabe de dónde
    sale, así que también lleva el suyo.
    """
    base, _ = sitio
    html = get(base, "/configuracion?perfil=test")[1]
    for url in ("https://t.me/BotFather", "https://aistudio.google.com/apikey",
                "https://agent.tinyfish.ai", "https://openrouter.ai/keys",
                "https://t.me/userinfobot"):
        assert f'href="{url}" target="_blank" rel="noopener noreferrer"' in html, url
    assert "Conseguila en" in html or "Se saca en" in html
    # El paso a paso del token del bot, en el signo de pregunta.
    assert "/newbot" in html


class _Formulario(HTMLParser):
    """Los campos que mandaría el navegador al apretar "Guardar cambios".

    Se leen del HTML de la pantalla y no se escriben a mano en el test: lo que se
    quiere probar es justamente qué pasa con lo que la pantalla manda y lo que
    no, y una lista a mano se desincroniza del formulario de verdad.
    """

    def __init__(self, accion: str):
        super().__init__(convert_charrefs=True)
        self.accion = accion
        self.campos: dict[str, str] = {}
        self._adentro = False
        self._area = self._select = None
        self._opcion: dict | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self._adentro = a.get("action") == self.accion
        if not self._adentro:
            return
        nombre = a.get("name")
        if tag == "input" and nombre:
            tipo = a.get("type", "text")
            if tipo == "checkbox":
                if "checked" in a:
                    self.campos[nombre] = a.get("value") or "on"
            elif tipo not in ("submit", "button"):
                self.campos[nombre] = a.get("value") or ""
        elif tag == "textarea" and nombre:
            self._area = nombre
            self.campos[nombre] = ""
        elif tag == "select" and nombre:
            self._select = nombre
        elif tag == "option" and self._select:
            self._opcion = {"valor": a.get("value"), "texto": "",
                            "elegida": "selected" in a}

    def handle_data(self, texto):
        if self._area:
            self.campos[self._area] += texto
        elif self._opcion is not None:
            self._opcion["texto"] += texto

    def handle_endtag(self, tag):
        if tag == "form":
            self._adentro = False
        elif tag == "textarea":
            self._area = None
        elif tag == "select":
            self._select = None
        elif tag == "option" and self._opcion is not None:
            valor = self._opcion["valor"] or self._opcion["texto"].strip()
            if self._opcion["elegida"] or self._select not in self.campos:
                self.campos[self._select] = valor
            self._opcion = None


def _como_el_navegador(base, pantalla):
    """Abre la pantalla y devuelve lo que mandaría su formulario, sin tocar nada."""
    lector = _Formulario(f"/{pantalla}")
    lector.feed(get(base, f"/{pantalla}?perfil=test")[1])
    assert lector.campos, f"no encontré el formulario de /{pantalla}"
    return lector.campos


# --- dos pestañas ------------------------------------------------------------------

def test_mi_perfil_y_configuracion_son_dos_pestanas(sitio):
    base, _ = sitio
    html = get(base, "/configuracion?perfil=test")[1]
    lateral = html[html.index("<aside"):html.index("</aside>")]
    assert 'href="/datos?perfil=test"' in lateral
    assert ('class="nav-item activa" href="/configuracion?perfil=test" '
            'aria-current="page"') in lateral
    assert "<h1>Configuración de test</h1>" in html


def test_cada_pantalla_muestra_solo_sus_campos(sitio):
    base, _ = sitio
    mi_perfil = get(base, "/datos?perfil=test")[1]
    configuracion = get(base, "/configuracion?perfil=test")[1]

    de_mi_perfil = ('name="cv_principal_texto"', 'name="keywords"', 'name="excluir_titulos"',
                    'name="pais"', 'name="ciudad"', 'name="modo_remote"',
                    'name="allow_english"', 'name="max_english_level"', 'name="empresas"',
                    'name="rrhh"', 'name="cand_name"', 'name="cand_not_suitable"')
    de_configuracion = ('name="TELEGRAM_TOKEN"', 'name="chat_id"', 'name="fuente_careers"',
                        'name="min_score"', 'name="top_n"', 'name="max_new_per_run"',
                        'name="max_age_days"', 'name="notify_when_empty"',
                        'action="/perfil-nuevo"', 'action="/perfil-borrar"')
    for campo in de_mi_perfil:
        assert campo in mi_perfil and campo not in configuracion, campo
    for campo in de_configuracion:
        assert campo in configuracion and campo not in mi_perfil, campo


def test_cada_pantalla_tiene_un_solo_primario(sitio):
    """"Crear perfil" era primario abajo de Mi perfil: dos botones del mismo peso
    en la misma pantalla. Crear y borrar son mantenimiento."""
    base, _ = sitio
    for pantalla in ("datos", "configuracion"):
        html = get(base, f"/{pantalla}?perfil=test")[1]
        contenido = html[html.index("<main"):]
        assert contenido.count('class="primario"') == 1, pantalla
        assert '<button class="primario" type="submit">Guardar cambios</button>' in contenido


def test_configuracion_va_al_pie_abajo_de_buscar_ahora():
    """Configuración se carga una vez: arriba, al lado de lo que se usa todos
    los días, competía por la vista. Va abajo del botón de buscar, con aire
    entre la ventana de días y el botón."""
    from vacantia.ui.estilos import CSS
    from vacantia.ui.render import pagina

    html = pagina("t", "c", "ana", ["ana"], "trabajos", {"ultima": "hoy", "ventana": 7})
    lateral = html[html.index("<aside"):html.index("</aside>")]
    assert (lateral.index('class="estado"') < lateral.index('id="corrida"')
            < lateral.index('href="/configuracion?perfil=ana"'))
    assert lateral.index(">Mi perfil<") < lateral.index('class="estado"')
    assert "--estado-aire-boton: 10px;" in CSS
    assert ".estado .corrida { margin-top: calc(var(--spacing-xs) + var(--estado-aire-boton)); }" in CSS


def test_las_fuentes_van_en_dos_listas_ordenadas(sitio):
    """Sueltas en una fila, cada tilde caía a una altura distinta según lo largo
    de su nota. Van en dos listas, un tilde por renglón, y la nota en el signo
    de pregunta."""
    from vacantia.ui import formulario

    base, _ = sitio
    html = get(base, "/configuracion?perfil=test")[1]
    assert '<fieldset class="fuentes"><legend>Portales de empleo</legend>' in html
    assert '<fieldset class="fuentes"><legend>Lo que seguís</legend>' in html
    for tipo, _, _ in formulario.FUENTES:
        assert html.count(f'name="fuente_{tipo}"') == 1, tipo
    # La nota de Zonajobs está, pero en el globo y no suelta abajo del tilde.
    zonajobs = html[html.index('name="fuente_zonajobs"'):]
    assert zonajobs.index('class="globo">Misma base de avisos que Bumeran') < zonajobs.index("</li>")


def test_lo_que_seguis_dice_cuanto_hay_cargado(sitio):
    """Prender "Empresas que sigo" sin ninguna cargada es una fuente que devuelve
    cero todos los días sin decir por qué."""
    base, tmp = sitio
    html = get(base, "/configuracion?perfil=test")[1]
    assert '<a class="cargadas" href="/datos?perfil=test#empresas">1 empresa</a>' in html
    assert '<a class="cargadas" href="/datos?perfil=test#rrhh">ninguna cargada</a>' in html


def test_bumeran_y_zonajobs_prendidos_avisa_que_llegan_duplicados(sitio):
    base, tmp = sitio
    assert "te van a llegar duplicados" not in get(base, "/configuracion?perfil=test")[1]
    post(base, "/configuracion", {"perfil": "test", "fuente_bumeran": "1",
                                  "fuente_zonajobs": "1"})
    assert "te van a llegar duplicados" in get(base, "/configuracion?perfil=test")[1]


# --- cada pantalla guarda sólo lo suyo ---------------------------------------------

def test_guardar_mi_perfil_no_apaga_fuentes_ni_avisos(sitio):
    """El incidente que se evita: todos los tildes de Configuración faltan en el
    formulario de Mi perfil, y leídos como "apagado" apagaban todas las fuentes."""
    base, tmp = sitio
    perfil = _perfil_leido(tmp)
    perfil.update(min_score=75, top_n=8, max_new_per_run=12, notify_when_empty=True)
    perfil["filters"]["max_age_days"] = 30
    perfil["sources"] = [
        {"type": "careers", "enabled": True, "companies_file": "companies.json"},
        {"type": "linkedin", "enabled": True, "search_terms": ["AI Engineer"]},
        {"type": "rrhh", "enabled": True, "profiles": ["https://linkedin.com/in/a"]},
        {"type": "bumeran", "enabled": False},
    ]
    perfil["notifiers"] = [{"type": "telegram", "enabled": True, "chat_id": "111"}]
    _escribir_perfil(tmp, perfil)
    (tmp / ".env").write_text("TELEGRAM_TOKEN=abc123\n", encoding="utf-8")

    campos = _como_el_navegador(base, "datos")
    campos["keywords"] = "Python, Go"
    post(base, "/datos", campos)

    despues = _perfil_leido(tmp)
    assert despues["keywords"] == ["Python", "Go"]
    assert despues["sources"] == perfil["sources"]
    assert despues["notify_when_empty"] is True
    assert (despues["min_score"], despues["top_n"], despues["max_new_per_run"]) == (75, 8, 12)
    assert despues["filters"]["max_age_days"] == 30
    assert despues["notifiers"] == perfil["notifiers"]
    assert (tmp / ".env").read_text(encoding="utf-8") == "TELEGRAM_TOKEN=abc123\n"


def test_guardar_configuracion_no_vacia_palabras_ni_cv(sitio):
    base, tmp = sitio
    perfil = _perfil_leido(tmp)
    perfil["keywords"] = ["Python", "SQL"]
    perfil["filters"].update(excluir_titulos=["MLOps"], work_modes=["hybrid"],
                             language={"allow_english": True, "max_english_level": "B2"})
    perfil["filters"]["location"] = {"country": "Argentina", "city": ["La Plata", "Tandil"]}
    perfil["candidate"] = {"name": "Test", "headline": "AI Engineer", "seeking": "Remoto"}
    perfil["sources"].append({"type": "rrhh", "enabled": True,
                              "profiles": ["https://linkedin.com/in/a"]})
    _escribir_perfil(tmp, perfil)
    cv = (tmp / "resume" / "test.md").read_bytes()
    empresas = (tmp / "companies.json").read_bytes()

    campos = _como_el_navegador(base, "configuracion")
    campos["min_score"] = "80"
    post(base, "/configuracion", campos)

    despues = _perfil_leido(tmp)
    assert despues["min_score"] == 80
    for clave in ("keywords", "candidate", "cv_path"):
        assert despues[clave] == perfil[clave], clave
    for clave in ("excluir_titulos", "work_modes", "language", "location"):
        assert despues["filters"][clave] == perfil["filters"][clave], clave
    rrhh = {s["type"]: s for s in despues["sources"]}["rrhh"]
    assert rrhh == {"type": "rrhh", "enabled": True, "profiles": ["https://linkedin.com/in/a"]}
    assert (tmp / "resume" / "test.md").read_bytes() == cv
    assert (tmp / "companies.json").read_bytes() == empresas


def test_un_pedido_con_campos_de_la_otra_pantalla_no_los_toca(sitio):
    """Una pestaña abierta desde antes de partir la pantalla manda todo junto a
    /datos. Lo que no es de Mi perfil se ignora, en vez de pisar Configuración."""
    base, tmp = sitio
    post(base, "/datos", {"perfil": "test", "keywords": "Go", "min_score": "5",
                          "chat_id": "999", "fuente_linkedin": "1"})
    perfil = _perfil_leido(tmp)
    assert perfil["keywords"] == ["Go"]
    assert perfil["min_score"] == 60
    assert {s["type"]: s["enabled"] for s in perfil["sources"]} == {"careers": True}
    assert "999" not in json.dumps(perfil)

    post(base, "/configuracion", {"perfil": "test", "min_score": "70", "keywords": "",
                                  "cv": "", "cand_name": ""})
    perfil = _perfil_leido(tmp)
    assert perfil["min_score"] == 70
    assert perfil["keywords"] == ["Go"] and perfil["candidate"]["name"] == "Test"
    assert (tmp / "resume" / "test.md").read_text(encoding="utf-8") == "# CV de prueba\n"


def test_pegar_urls_de_reclutadores_no_prende_la_fuente(sitio):
    """Prender una fuente es de Configuración. Si la fuente no existía, cargar
    URLs en Mi perfil la crea apagada."""
    base, tmp = sitio
    post(base, "/datos", {"perfil": "test", "rrhh": "https://linkedin.com/in/a\n"})
    rrhh = {s["type"]: s for s in _perfil_leido(tmp)["sources"]}["rrhh"]
    assert rrhh == {"type": "rrhh", "enabled": False, "profiles": ["https://linkedin.com/in/a"]}


def test_un_nombre_invalido_vuelve_a_configuracion(sitio):
    """El error tiene que aparecer donde está el campo que hay que corregir."""
    base, _ = sitio
    _, html, url = post(base, "/perfil-nuevo", {"perfil": "test", "nombre": "María"})
    assert "/configuracion" in url and "aviso error" in html


# --- borrar un perfil --------------------------------------------------------------

@pytest.fixture
def tareas(monkeypatch):
    """`schtasks` de mentira: anota qué se le pidió y contesta lo que diga el test.

    `respuestas` es {"/Query" | "/Delete": código de salida o excepción}.
    """
    pedidos: list[list[str]] = []
    respuestas: dict[str, object] = {"/Query": 0, "/Delete": 0}

    def falso(args, **_):
        pedidos.append(list(args))
        respuesta = respuestas[args[1]]
        if isinstance(respuesta, Exception):
            raise respuesta
        return SimpleNamespace(returncode=respuesta, stdout="",
                               stderr="ERROR: Acceso denegado.")

    monkeypatch.setattr(data.subprocess, "run", falso)
    return SimpleNamespace(pedidos=pedidos, respuestas=respuestas)


BORRAR_TAREA = ["schtasks", "/Delete", "/TN", "Vacantia - maria", "/F"]


def _con_maria(tmp):
    """Un segundo perfil con todo lo que se puede tener: dos CV, empresas propias,
    ofertas guardadas y favoritos de LinkedIn."""
    data.crear_perfil("maria")
    data.agregar_cv("maria")
    (tmp / "companies-maria.json").write_text('[{"name": "Techint"}]', encoding="utf-8")
    estado = tmp / "state" / "maria"
    estado.mkdir(parents=True)
    (estado / "job_history.json").write_text("[]", encoding="utf-8")
    (estado / "linkedin_favoritos.json").write_text("[]", encoding="utf-8")


def _archivos(tmp):
    """Todo lo que hay en la instalación de juguete, byte por byte. El registro no:
    lo escribe cada pedido."""
    return {p.relative_to(tmp).as_posix(): p.read_bytes()
            for p in tmp.rglob("*") if p.is_file() and p.suffix != ".log"}


def test_borrar_un_perfil_pide_confirmar(sitio, tareas):
    """Como "Borrar este CV": la confirmación se abre en el lugar, con el nombre
    a la vista, y recién ahí aparece el botón que borra."""
    base, tmp = sitio
    html = get(base, "/configuracion?perfil=test")[1]
    formulario = html[html.index('<form class="borrar-perfil" method="post" action="/perfil-borrar">'):]
    formulario = formulario[:formulario.index("</form>")]
    confirmacion = formulario[formulario.index('<details class="borrar-cv">'):]

    assert "<summary>Borrar el perfil de test</summary>" in confirmacion
    assert ("<p>Se borra <b>test</b> con todo: CV, ofertas guardadas y lo que marcaste. "
            "No se puede recuperar.</p>") in confirmacion
    boton = confirmacion[confirmacion.index('<button class="peligro"'):]
    boton = boton[:boton.index("</button>")]
    assert 'type="submit"' in boton and 'name="perfil_borrar"' in boton
    assert 'value="test"' in boton
    assert "Cancelar" in confirmacion
    # Abrir la pantalla no borra nada ni le pide nada a Windows.
    assert (tmp / "profiles" / "test.json").exists() and tareas.pedidos == []
    assert "perfil-borrar" not in get(base, "/datos?perfil=test")[1]


def test_borrar_un_perfil_se_lleva_todo_lo_suyo(sitio, tareas):
    base, tmp = sitio
    _con_maria(tmp)
    assert (tmp / "resume" / "maria-cv-2.md").exists()

    _, html, url = post(base, "/perfil-borrar", {"perfil": "maria", "perfil_borrar": "maria"})

    for resto in ("profiles/maria.json", "resume/maria.md", "resume/maria-cv-2.md",
                  "companies-maria.json", "state/maria"):
        assert not (tmp / resto).exists(), resto
    assert BORRAR_TAREA in tareas.pedidos
    # Vuelve al primer perfil que queda, y ya no figura en el selector.
    assert "/configuracion" in url and "perfil=test" in url
    assert "Borré el perfil «maria» con todo." in html
    assert 'value="maria"' not in html


def test_borrar_un_perfil_no_toca_a_los_demas(sitio, tareas):
    base, tmp = sitio
    _con_maria(tmp)
    antes = _archivos(tmp)

    post(base, "/perfil-borrar", {"perfil": "maria", "perfil_borrar": "maria"})

    assert _archivos(tmp) == {k: v for k, v in antes.items() if "maria" not in k}
    assert "example.json" in {p.name for p in (tmp / "profiles").iterdir()}


def test_lo_que_usa_otro_perfil_no_se_borra(sitio, tareas):
    """Un CV que lee otro perfil, o una lista de empresas que comparte, se quedan:
    borrar a una persona no puede dejar a la otra sin su CV ni sus empresas."""
    base, tmp = sitio
    _con_maria(tmp)
    maria = _perfil_leido(tmp, "maria")
    maria["cvs"].append({"id": "prestado", "nombre": "Prestado", "path": "resume/test.md",
                         "palabras_clave": []})
    _escribir_perfil(tmp, maria, "maria")
    test = _perfil_leido(tmp)
    test["sources"][0]["companies_file"] = "companies-maria.json"
    _escribir_perfil(tmp, test)

    post(base, "/perfil-borrar", {"perfil": "maria", "perfil_borrar": "maria"})

    assert not (tmp / "profiles" / "maria.json").exists()
    assert not (tmp / "resume" / "maria.md").exists()          # ése era sólo suyo
    assert (tmp / "resume" / "test.md").read_text(encoding="utf-8") == "# CV de prueba\n"
    assert (tmp / "companies-maria.json").exists()


def test_una_lista_de_empresas_que_no_lleva_su_nombre_no_se_borra(sitio, tareas):
    """El `companies.json` de antes de separar las listas: aunque sólo lo use el
    perfil que se borra, no es suyo."""
    base, tmp = sitio
    test = _perfil_leido(tmp)
    test["sources"][0]["companies_file"] = "companies-test.json"
    _escribir_perfil(tmp, test)
    _con_maria(tmp)
    maria = _perfil_leido(tmp, "maria")
    for fuente in maria["sources"]:
        if fuente["type"] == "careers":
            fuente["companies_file"] = "companies.json"
    _escribir_perfil(tmp, maria, "maria")

    post(base, "/perfil-borrar", {"perfil": "maria", "perfil_borrar": "maria"})
    assert (tmp / "companies.json").exists()


def test_example_nunca_se_borra(sitio, tareas):
    base, tmp = sitio
    _, html, _ = post(base, "/perfil-borrar", {"perfil": "test", "perfil_borrar": "example"})
    assert "aviso error" in html
    assert (tmp / "profiles" / "example.json").exists()
    assert tareas.pedidos == []


def test_borrar_el_ultimo_perfil_lleva_a_la_bienvenida(sitio, tareas):
    base, tmp = sitio
    _, html, _ = post(base, "/perfil-borrar", {"perfil": "test", "perfil_borrar": "test"})
    assert "Bienvenido a vacantia" in html
    assert "Borré el perfil «test» con todo." in html
    assert [p.name for p in (tmp / "profiles").iterdir()] == ["example.json"]
    assert not (tmp / "state" / "test").exists()


@pytest.mark.parametrize("respuestas", [{"/Delete": 1}, {"/Query": OSError("sin schtasks")}])
def test_si_la_tarea_no_se_deja_sacar_avisa_y_el_perfil_se_borra_igual(sitio, tareas,
                                                                       respuestas):
    base, tmp = sitio
    _con_maria(tmp)
    tareas.respuestas.update(respuestas)

    _, html, url = post(base, "/perfil-borrar", {"perfil": "maria", "perfil_borrar": "maria"})

    assert not (tmp / "profiles" / "maria.json").exists()
    assert "perfil=test" in url
    assert "Borré el perfil «maria» con todo." in html
    assert "aviso error" in html and "No pude sacar su búsqueda programada" in html
    assert "«Vacantia - maria»" in html


def test_sin_tarea_programada_no_se_intenta_sacar(sitio, tareas):
    """Un perfil creado desde la pantalla no tiene tarea hasta reinstalar.
    Decirle "no pude sacarla" lo mandaría a buscar un problema que no existe."""
    base, tmp = sitio
    _con_maria(tmp)
    tareas.respuestas["/Query"] = 1

    _, html, _ = post(base, "/perfil-borrar", {"perfil": "maria", "perfil_borrar": "maria"})

    assert BORRAR_TAREA not in tareas.pedidos
    assert "No tenía búsqueda programada en esta computadora." in html
    assert "aviso error" not in html
