"""Indeed y Get on Board.

⚠️ Estos tests usan Markdown y JSON de ejemplo, NO los sitios reales. Prueban
que la fuente hace lo que tiene que hacer con lo que recibe; que lo que reciba
se parezca a esto se verificó a mano el 9/9/2026 y está anotado en
NOTAS-PARA-ISAIAS.md.

Los dos casos de Indeed que están acá salieron de esa prueba contra el sitio, no
de imaginar qué podría pasar: el token de sesión que cambia en cada corrida, y
el aviso que viene sin encabezado.
"""

import json

from vacantia.sources import SOURCE_REGISTRY
from vacantia.sources.getonbrd import GetOnBoardSource, _texto
from vacantia.sources.indeed import IndeedSource, _canonica, extraer_indeed

PERFIL = {"keywords": ["AI Engineer", "Python"], "filters": {"max_age_days": 7}}


def test_las_dos_estan_registradas():
    assert SOURCE_REGISTRY["indeed"] is IndeedSource
    assert SOURCE_REGISTRY["getonbrd"] is GetOnBoardSource


# --- Indeed ----------------------------------------------------------------

def test_el_token_de_sesion_no_queda_en_la_url_guardada():
    """El `bb` cambia en cada corrida.

    Si se guardara como identidad del aviso, el mismo puesto entraría de nuevo
    tres veces por día y el dedupe no lo agarraría nunca.
    """
    con_token = ("https://ar.indeed.com/rc/clk?jk=a7eef2df3e324c35"
                 "&bb=KNd8lNWQ8EoVvXUtWJFC1ZRyiFKcTEPzCFOSG8jmUZdDUux")
    otro_token = ("https://ar.indeed.com/rc/clk?jk=a7eef2df3e324c35"
                  "&bb=OTRO_TOKEN_DE_OTRA_CORRIDA_DISTINTO")
    esperada = "https://ar.indeed.com/viewjob?jk=a7eef2df3e324c35"

    assert _canonica(con_token) == esperada
    # El mismo aviso, otra corrida, la misma URL: eso es lo que hace el dedupe.
    assert _canonica(otro_token) == esperada
    assert "bb=" not in _canonica(con_token)

    # También reconoce el aviso cuando viene en el panel lateral del listado.
    assert _canonica("https://ar.indeed.com/jobs?q=AI&vjk=A7EEF2DF3E324C35") == esperada
    # Y lo que no es un aviso no se confunde con uno: acá `jk` viene pegado a
    # otra palabra, que es como Indeed arma los links de sueldos.
    assert _canonica("https://ar.indeed.com/career/salaries/AI?fromjk=abc123def456") == ""
    assert _canonica("https://ar.indeed.com/empresas") == ""


def test_los_links_del_listado_no_pierden_el_jk():
    """`PortalSource` corta el query string, y en Indeed el `jk` va ahí.

    Cortándolo, los 15 links del listado quedaban todos en
    `https://ar.indeed.com/rc/clk`, o sea uno solo.
    """
    s = IndeedSource({"type": "indeed"}, PERFIL)
    links = [
        "https://ar.indeed.com/rc/clk?jk=aaaa1111bbbb2222&bb=TOKEN1",
        "https://ar.indeed.com/rc/clk?jk=cccc3333dddd4444&bb=TOKEN2",
        "https://ar.indeed.com/career/salaries/AI?fromjk=aaaa1111bbbb2222",
        "https://ar.indeed.com/empresas",
    ]
    avisos = s.links_de_aviso(links, "")
    assert avisos == ["https://ar.indeed.com/viewjob?jk=aaaa1111bbbb2222",
                      "https://ar.indeed.com/viewjob?jk=cccc3333dddd4444"]
    # El token se guarda aparte, para bajar el detalle dentro de esta corrida.
    assert s._con_token[avisos[0]].endswith("TOKEN1")

    # El mismo aviso dos veces en el listado no se duplica.
    assert s.links_de_aviso(links, "") == []


def test_la_ventana_de_dias_se_la_pide_al_portal():
    """Indeed no dice la fecha en ningún lado, ni en el listado ni en el aviso.

    Así que la ventana la aplica el portal con `fromage`, igual que LinkedIn
    con `hours_old`. Se redondea al valor más chico que cubra lo pedido, para
    no traer de más: Indeed sólo acepta 1, 3, 7 y 14.
    """
    def fromage(dias):
        return IndeedSource({"type": "indeed", "max_age_days": dias}, PERFIL)._fromage()

    assert fromage(1) == 1
    assert fromage(2) == 3          # 2 no existe: se redondea al 3, no al 1
    assert fromage(7) == 7
    assert fromage(10) == 14
    assert fromage(60) == 14        # el techo del portal
    assert fromage(0) is None       # sin ventana


def test_la_busqueda_va_urlencodeada_y_no_en_slug():
    """Los otros portales ponen la búsqueda en la ruta; Indeed en el query."""
    s = IndeedSource({"type": "indeed"}, PERFIL)
    url = s.url_de_busqueda("AI Engineer")
    assert url == "https://ar.indeed.com/jobs?q=AI+Engineer&fromage=7&sort=date"

    con_lugar = IndeedSource(
        {"type": "indeed", "location": "Bahía Blanca"}, PERFIL).url_de_busqueda("Python")
    assert "l=bahia-blanca" in con_lugar and "q=Python" in con_lugar


def test_pide_lo_mas_nuevo_primero():
    """Como sólo se lee la primera página, lo que entre en esa página es todo lo
    que vamos a ver: conviene que sea lo más nuevo.

    Y el mismo aviso rinde más cuanto antes se lo ve, porque tiene menos
    postulantes. El default de Indeed es "relevancia", que no es eso.
    """
    s = IndeedSource({"type": "indeed"}, PERFIL)
    assert "&sort=date" in s.url_de_busqueda("AI Engineer")
    # Se puede volver al orden del portal poniéndolo en vacío.
    sin_orden = IndeedSource({"type": "indeed", "sort": ""}, PERFIL)
    assert "sort=" not in sin_orden.url_de_busqueda("AI Engineer")


def test_avisa_cuando_indeed_pide_cuenta_para_paginar(caplog):
    """La segunda página no existe sin cuenta: devuelve 550 bytes que lo dicen.

    No es Cloudflare ni un problema de scraping, es una decisión de Indeed. Si
    algún día alguien intenta paginar de nuevo, que el log diga por qué no vino
    nada en vez de parecer que el portal se rompió.
    """
    import logging

    s = IndeedSource({"type": "indeed"}, PERFIL)
    with caplog.at_level(logging.INFO):
        s.links_de_aviso([], "# Para ver más de una página de empleos, "
                             "crea una cuenta o inicia sesión.")
    assert "pide cuenta para pasar de la primera" in caplog.text


# Cómo se ve el detalle de un aviso leído en Markdown. La línea de estrellas
# aparece sólo en las empresas calificadas, y sin saltearla la empresa quedaba
# en "4.0 de 5 estrellas".
DETALLE = """# AI Engineer

Darwin AI

4.0 de 5 estrellas

Buenos Aires, Buenos Aires

Tiempo completo

## Descripción completa del empleo

We are looking for a highly motivated individual.
"""

# La otra maquetación, que apareció probando contra el sitio: uno de cada
# quince avisos viene sin encabezado y arranca directo acá.
DETALLE_SIN_ENCABEZADO = """## Información del empleo

### Tipo de empleo

* Tiempo completo

## Ubicación

Rosario, Santa Fe

## Descripción completa del empleo

JOB DESCRIPTION
"""


def test_lee_titulo_empresa_y_ciudad_del_aviso():
    datos = extraer_indeed(DETALLE)
    assert datos["title"] == "AI Engineer"
    assert datos["company"] == "Darwin AI"      # y no "4.0 de 5 estrellas"
    assert datos["city"] == "Buenos Aires"      # sin repetir la provincia


def test_del_aviso_sin_encabezado_saca_al_menos_la_ubicacion():
    """No tiene título ni empresa en ninguna parte del documento.

    Lo que sí tiene es la sección Ubicación, y ésa alcanza para que el filtro
    de lugar no quede ciego con ese aviso.
    """
    datos = extraer_indeed(DETALLE_SIN_ENCABEZADO)
    assert datos == {"city": "Rosario"}
    assert extraer_indeed("") == {}
    assert extraer_indeed("texto sin nada de esto") == {}


def test_el_aviso_que_no_se_pudo_leer_no_entra(monkeypatch):
    """Sin la página del aviso, el título sale del slug y queda en "viewjob".

    Eso no se puede mostrar en una tarjeta, el modelo le pone 0 igual que a una
    oferta que de verdad no sirve, y encima cuesta una llamada.
    """
    from vacantia.models import Job
    from vacantia.sources.portales_ar import PortalSource

    # Lo que dejaría el listado: uno con detalle leído y otro sin nada.
    def crudos(self):
        return [
            Job(url="https://ar.indeed.com/viewjob?jk=aaaa1111bbbb2222",
                title="AI Engineer", company="Darwin AI", source="indeed",
                description="una descripción de verdad"),
            Job(url="https://ar.indeed.com/viewjob?jk=cccc3333dddd4444",
                title="viewjob", source="indeed"),
        ]

    monkeypatch.setattr(PortalSource, "fetch", crudos)

    salida = IndeedSource({"type": "indeed"}, PERFIL).fetch()
    assert [j.title for j in salida] == ["AI Engineer"]

    # Con el detalle apagado a mano no se filtra: ahí que no haya título es lo
    # esperado, no una falla.
    apagado = IndeedSource({"type": "indeed", "fetch_description": False}, PERFIL)
    assert len(apagado.fetch()) == 2


# --- Get on Board ----------------------------------------------------------

def test_no_necesita_ninguna_credencial():
    """Es la única fuente que no scrapea y no gasta una sola credencial.

    Por eso conviene tenerla prendida: cuando las demás se saltean por falta de
    TINYFISH_API_KEY, ésta sigue trayendo.
    """
    s = GetOnBoardSource({"type": "getonbrd"}, PERFIL)
    assert s.is_available() == (True, "")
    assert GetOnBoardSource({"type": "getonbrd"}, {}).is_available()[0] is False


def test_la_descripcion_html_se_pasa_a_texto():
    """Es lo que va al prompt del que puntúa: con las etiquetas adentro, la
    mitad del presupuesto de tokens se lo comen los `<strong>`."""
    assert _texto("<ul><li>Python</li><li>FastAPI</li></ul>") == "Python\nFastAPI"
    assert _texto("<p>Hola &amp; chau<br>Segunda</p>") == "Hola & chau\nSegunda"
    assert _texto("") == ""
    assert _texto(None) == ""


# Un aviso tal como lo devuelve la API, recortado. La estructura es la real,
# verificada el 9/9/2026 contra /api/v0/search/jobs.
CRUDO = {
    "type": "job",
    "id": "ai-engineer-niuro-remote",
    "links": {"public_url": "https://www.getonbrd.com/jobs/ai-engineer-niuro-remote"},
    "attributes": {
        "title": "AI Back-end Engineer",
        "description": "<ul><li>Experiencia con <strong>Python</strong></li></ul>",
        "functions": "<div>Diseñar servicios</div>",
        "desirable": "",
        "projects": "",
        "remote": True,
        "remote_modality": "fully_remote",
        "countries": ["Remote"],
        "published_at": 1788205797,
        "category_name": "Machine Learning & AI",
        "applications_count": 97,
        "min_salary": 2300,
        "max_salary": 2800,
        "company": {"data": {"id": 6322, "type": "company"}},
    },
}


def _fuente(**config):
    s = GetOnBoardSource({"type": "getonbrd", **config}, PERFIL)
    s._empresas[6322] = "Niuro"       # como si ya la hubiera resuelto
    return s


def test_arma_el_aviso_con_todo_lo_que_hace_falta_para_puntuarlo():
    job = _fuente()._a_job(CRUDO, "AI Engineer")
    assert job.url == "https://www.getonbrd.com/jobs/ai-engineer-niuro-remote"
    assert job.title == "AI Back-end Engineer"
    assert job.company == "Niuro"
    assert job.work_mode == "remote"
    assert job.posted_at == "2026-08-31"          # el sello unix, como fecha
    assert "Python" in job.description and "<strong>" not in job.description
    assert "Diseñar servicios" in job.description  # los cuatro campos, juntos


def test_remote_no_es_un_pais():
    """La API lo mezcla en `countries`, y ponerlo en `country` hacía que el
    filtro de ubicación lo comparara contra "Argentina" y lo tirara."""
    job = _fuente(country_code="AR")._a_job(CRUDO, "AI Engineer")
    assert job.country == "Argentina"
    assert job.work_mode == "remote"

    con_pais = {**CRUDO, "attributes": {**CRUDO["attributes"],
                                        "countries": ["Chile"], "remote": False,
                                        "remote_modality": "hybrid"}}
    otro = _fuente()._a_job(con_pais, "AI Engineer")
    assert otro.country == "Chile" and otro.work_mode == "hybrid"


def test_un_aviso_sin_url_o_sin_titulo_no_entra():
    s = _fuente()
    assert s._a_job({"attributes": {"title": "X"}, "links": {}}, "q") is None
    assert s._a_job({"attributes": {"title": ""}, "links": {"public_url": "u"}}, "q") is None
    assert s._a_job({}, "q") is None


def test_una_fecha_rota_no_tumba_la_corrida():
    roto = {**CRUDO, "attributes": {**CRUDO["attributes"], "published_at": "ayer"}}
    job = _fuente()._a_job(roto, "AI Engineer")
    assert job is not None and job.posted_at == ""


def test_la_empresa_se_pide_una_sola_vez_por_id(monkeypatch):
    """Varios avisos comparten empresa, y sin el nombre `Job.dedupe_key`
    devuelve "" y el dedupe por empresa+título no corre."""
    pedidos = []
    s = GetOnBoardSource({"type": "getonbrd"}, PERFIL)

    def falso_get(self, ruta, **params):
        pedidos.append(ruta)
        return {"data": {"attributes": {"name": "Niuro"}}}

    monkeypatch.setattr(GetOnBoardSource, "_get", falso_get)
    for _ in range(3):
        assert s._empresa(CRUDO["attributes"]) == "Niuro"
    assert pedidos == ["companies/6322"]          # una sola vez, no tres

    # Un aviso sin empresa no rompe ni pide nada.
    assert s._empresa({}) == ""
    assert len(pedidos) == 1


def test_la_api_caida_no_tumba_la_corrida(monkeypatch):
    monkeypatch.setattr(GetOnBoardSource, "_get", lambda self, ruta, **p: {})
    assert GetOnBoardSource({"type": "getonbrd"}, PERFIL).fetch() == []
