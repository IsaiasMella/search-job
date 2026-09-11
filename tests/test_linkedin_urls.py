"""El constructor de búsquedas de publicaciones de LinkedIn.

Los parámetros que se prueban acá **se verificaron contra LinkedIn el
10/9/2026, logueado**, y no salieron de leer documentación:

    keywords=(boolean)              anda
    datePosted="past-24h"           anda, el filtro queda aplicado
    sortBy="date_posted"            anda, ordena por lo más reciente
    postedBy=["first","following"]  anda
    contentType=["jobs"]            anda pero deja la lista en CERO

El último quedó afuera a propósito y hay un test que lo fija, para que nadie lo
agregue creyendo que mejora la búsqueda.
"""

from urllib.parse import parse_qs, quote, urlparse

from vacantia.ui import linkedin_urls as L
from vacantia.ui.render import PESTANIAS_LINKEDIN

# El fixture y los helpers viven en test_ui: una sola instalación de juguete.
from tests.test_ui import get, post, sitio  # noqa: F401


# --- el texto de búsqueda ---------------------------------------------------

def test_las_frases_van_entre_comillas_y_las_palabras_no():
    """Sin comillas, `AI Engineer` se busca como `AI` y `Engineer` sueltos, y
    entra cualquier cosa que diga "engineer"."""
    assert L._frase("AI Engineer") == '"AI Engineer"'
    assert L._frase("buscamos") == "buscamos"
    assert L._frase("  ") == ""


def test_arma_el_boolean_con_la_sintaxis_que_linkedin_acepta():
    """AND, OR y NOT en mayúsculas, comillas y paréntesis. Nada de comodines ni
    `+`/`-`: LinkedIn los ignora, y una búsqueda que parece filtrar y no filtra
    es peor que una que no filtra."""
    texto = L.armar_boolean(
        ["AI Engineer", "LLM Engineer"],
        ["buscamos"],
        ["Argentina"],
        ["Junior", "trainee"],
    )
    assert texto == ('("AI Engineer" OR "LLM Engineer") '
                     'AND buscamos AND Argentina '
                     'NOT Junior NOT trainee')
    for prohibido in ("*", " + ", " - ", "[", "]"):
        assert prohibido not in texto, prohibido
    assert len(texto) <= L.TOPE_KEYWORDS


def test_cada_exclusion_lleva_su_propio_not():
    """`NOT (a OR b)` devuelve cero resultados. Verificado contra el sitio el
    10/9/2026, misma búsqueda y mismo momento:

        ... AND buscamos NOT (Junior OR trainee)   ->  CERO
        ... AND buscamos NOT Junior NOT trainee    ->  trae posteos

    LinkedIn agrupa con paréntesis en todos lados menos después de un NOT.
    """
    texto = L.armar_boolean(["AI Engineer"], ["buscamos"], [], ["Junior", "trainee"])
    assert texto.endswith("NOT Junior NOT trainee")
    assert "NOT (" not in texto


def test_un_solo_termino_no_lleva_parentesis():
    assert L.armar_boolean(["AI Engineer"], ["buscamos"]) == '"AI Engineer" AND buscamos'


def test_sin_puestos_no_hay_busqueda():
    """El NOT solo no es una búsqueda: sin nada que buscar, LinkedIn abriría el
    buscador vacío y eso no se puede guardar en favoritos."""
    assert L.armar_boolean(excluir=["Junior"]) == ""
    assert L.armar_url("") == ""
    assert L.armar_url("   ") == ""


def test_la_busqueda_no_pasa_del_tope_que_linkedin_soporta():
    """Arriba de cierto largo LinkedIn devuelve cero y no avisa por qué.

    Medido contra el sitio el 10/9/2026: con 117 caracteres trae posteos de
    hace un minuto; con 164 devuelve "No se han encontrado resultados", sin
    filtro de lugar ni exclusiones.
    """
    texto = L.armar_boolean(["AI Engineer", "LLM Engineer"], L.GATILLOS_ES,
                            ["Argentina", "remoto"], L.EXCLUIR)
    assert len(texto) <= L.TOPE_KEYWORDS
    # Y lo que quedó afuera se puede saber, para poder decirlo en pantalla.
    entro = L.que_entro(["AI Engineer", "LLM Engineer"], L.GATILLOS_ES,
                        ["Argentina", "remoto"], L.EXCLUIR)
    assert entro["gatillos"] < len(L.GATILLOS_ES)


def test_cuando_hay_que_recortar_los_gatillos_van_primero():
    """Sin gatillo, la búsqueda deja de traer vacantes y trae cualquier posteo
    que hable de AI Engineer, que es justo lo que no sirve.

    Es el bug que tuvo esto mientras se construía: con todo tildado quedaban los
    cinco NOT y cero gatillos.
    """
    entro = L.que_entro(["AI Engineer", "LLM Engineer"], L.GATILLOS_ES,
                        ["Argentina", "remoto"], L.EXCLUIR)
    assert entro["gatillos"] >= 2, "los gatillos son lo que busca vacantes"

    # Y con lugar de por medio, que ocupa, siguen entrando dos.
    texto = L.armar_boolean(["AI Engineer"], L.GATILLOS_ES, ["Argentina"], L.EXCLUIR)
    assert "buscamos" in texto


# --- la dirección -----------------------------------------------------------

def _params(url):
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


def test_la_url_lleva_los_parametros_verificados_contra_linkedin():
    url = L.armar_url('"AI Engineer" AND buscamos', "24h", "recientes", "red")
    assert url.startswith(L.BASE)
    p = _params(url)
    assert p["keywords"] == '"AI Engineer" AND buscamos'
    # Con comillas adentro del valor: LinkedIn acepta las dos formas pero
    # devuelve ésta, y así la guardada es igual a la que él genera.
    assert p["datePosted"] == '"past-24h"'
    assert p["sortBy"] == '"date_posted"'
    assert p["postedBy"] == '["first","following"]'    # sin espacio, como él
    assert p["origin"] == "FACETED_SEARCH"


def test_las_opciones_del_desplegable_son_las_que_linkedin_entiende():
    assert _params(L.armar_url("x", cuando="semana"))["datePosted"] == '"past-week"'
    assert _params(L.armar_url("x", cuando="mes"))["datePosted"] == '"past-month"'
    assert _params(L.armar_url("x", orden="relevancia"))["sortBy"] == '"relevance"'
    # "Cualquiera" no manda el parámetro, en vez de mandarlo vacío.
    assert "postedBy" not in _params(L.armar_url("x", de_quien="todos"))
    # Y un valor inventado no rompe: cae en no mandar el filtro.
    assert "datePosted" not in _params(L.armar_url("x", cuando="cualquiera"))


def test_el_filtro_de_anuncios_de_empleo_quedo_afuera_a_proposito():
    """`contentType=["jobs"]` existe y funciona, pero deja la lista en cero.

    "Anuncios de empleo" es un tipo de contenido con formato propio de LinkedIn,
    no un posteo de texto libre, y justamente los posteos que buscamos son texto
    libre. Probado el 10/9/2026: combinado con cualquier otro filtro devuelve
    cero resultados. Un control que rompe la búsqueda no es una opción.
    """
    assert "contentType" not in L.armar_url("x", "24h", "recientes", "red")
    assert "contentType" not in L.BASE


def test_lo_que_se_escribe_va_urlencodeado():
    """El texto lleva comillas, paréntesis y acentos: sin encodear, la URL se
    corta en el primer espacio."""
    url = L.armar_url('("AI Engineer") NOT (pasantía)')
    assert " " not in url
    assert '%22' in url and '%28' in url
    assert _params(url)["keywords"] == '("AI Engineer") NOT (pasantía)'


# --- los favoritos ----------------------------------------------------------

def test_guarda_y_saca_una_busqueda(sitio):
    url = L.armar_url('"AI Engineer" AND buscamos')
    assert L.favoritos("test") == []

    assert L.guardar_favorito("test", "AI en español", url) == "guardada"
    guardados = L.favoritos("test")
    assert len(guardados) == 1
    assert guardados[0]["nombre"] == "AI en español"
    assert guardados[0]["url"] == url
    assert guardados[0]["guardada"]

    assert L.borrar_favorito("test", url) is True
    assert L.favoritos("test") == []
    assert L.borrar_favorito("test", url) is False


def test_guardar_dos_veces_la_misma_no_la_duplica(sitio):
    """Ensuciaría la lista sin agregar nada, y encima la dejaría irreconocible:
    dos filas iguales con nombres distintos y la misma dirección.

    Tampoco se pisa la que ya estaba: renombrar de callado algo que la persona
    no fue a renombrar es tocar lo que nadie pidió tocar.
    """
    url = L.armar_url('"AI Engineer"')
    L.guardar_favorito("test", "Primer nombre", url)
    assert L.guardar_favorito("test", "Nombre corregido", url) == "repetida"
    guardados = L.favoritos("test")
    assert len(guardados) == 1
    assert guardados[0]["nombre"] == "Primer nombre"
    assert L.guardada_como("test", url) == "Primer nombre"


def test_la_repetida_se_avisa_sin_tratarla_de_direccion_mal_escrita(sitio):
    """Con un solo `False` para los dos casos, guardar algo que ya tenías
    contestaba "esa dirección no es una búsqueda de publicaciones": mentira, y
    encima manda a corregir lo que está bien."""
    base, _ = sitio
    url = L.armar_url('"AI Engineer" AND buscamos')
    datos = {"perfil": "test", "url": url, "nombre": "La que sirve"}

    post(base, "/linkedin-favorito", datos)
    _, html, destino = post(base, "/linkedin-favorito", datos)
    assert "ya estaba guardada" in html and "La que sirve" in html
    assert "error" not in destino
    assert len(L.favoritos("test")) == 1


def test_no_guarda_cualquier_direccion(sitio):
    """El favorito es una búsqueda de publicaciones, no un link cualquiera."""
    assert L.guardar_favorito("test", "x", "https://google.com") == "invalida"
    assert L.guardar_favorito("test", "x", "") == "invalida"
    assert L.favoritos("test") == []


def test_una_busqueda_sin_nombre_igual_se_puede_guardar(sitio):
    url = L.armar_url('"AI Engineer"')
    L.guardar_favorito("test", "", url)
    assert L.favoritos("test")[0]["nombre"] == "Búsqueda sin nombre"


def test_un_archivo_de_favoritos_roto_no_rompe_la_pantalla(sitio):
    base, tmp = sitio
    ruta = tmp / "state" / "test" / "linkedin_favoritos.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("{ esto no es json", encoding="utf-8")
    assert L.favoritos("test") == []
    assert get(base, "/linkedin?perfil=test")[0] == 200


# --- la pantalla ------------------------------------------------------------

def test_publicaciones_va_primero():
    """Es la que resuelve el agujero real: Jobs ya lo cubre el scraper."""
    assert PESTANIAS_LINKEDIN[0][0] == "publicaciones"


def test_al_abrir_no_hay_ninguna_direccion_armada(sitio):
    """Una dirección que nadie pidió no es una búsqueda, es ruido."""
    base, _ = sitio
    _, html, _ = get(base, "/linkedin?perfil=test")
    assert 'class="datos armador"' in html          # el constructor sí
    assert 'class="url-generada"' not in html       # la dirección no
    assert "Todavía no guardaste ninguna" in html


def test_el_constructor_arma_la_direccion_sin_javascript(sitio):
    """Es un `form method=get`, como el filtro de antigüedad y el de perfil.

    Eso trae algo gratis: lo elegido queda en la dirección de esta misma
    pantalla, así que volver con el botón de atrás te devuelve el constructor
    como lo dejaste.
    """
    base, _ = sitio
    # El perfil de prueba tiene "Python" como palabra clave, y de ahí salen los
    # puestos que ofrece el constructor.
    _, html, _ = get(base, "/linkedin?perfil=test&tab=publicaciones"
                           "&puesto=Python"
                           "&lugar=Argentina&idioma=es&sin_junior=1"
                           "&cuando=24h&orden=recientes&de_quien=red")
    assert 'class="url-generada"' in html
    assert "search%2Fresults%2Fcontent" in html or "search/results/content" in html
    assert "Abrir en LinkedIn" in html
    # Y lo elegido vuelve tildado, para poder retocarlo sin rehacerlo.
    assert 'value="Python" checked' in html
    assert 'value="Argentina" checked' in html
    assert "sin_junior" in html


def test_los_puestos_salen_de_las_palabras_clave_del_perfil(sitio):
    """Un solo lugar donde se agregan y se sacan.

    Si el constructor tuviera su propia lista, agregar un puesto habría que
    hacerlo dos veces, y tarde o temprano quedarían distintas.
    """
    base, _ = sitio

    _, antes, _ = get(base, "/linkedin?perfil=test")
    assert 'value="Python"' in antes
    assert 'value="GenAI Engineer"' not in antes      # no está en el perfil

    # Se agrega desde Mi perfil, y aparece acá sin tocar nada más.
    post(base, "/datos", {
        "perfil": "test", "keywords": "Python, GenAI Engineer, LLM Engineer",
        "min_score": "60", "top_n": "5", "max_new_per_run": "30",
        "pais": "Argentina", "ciudad": "", "max_english_level": "A2",
        "cv": "# CV", "empresas": "", "rrhh": "", "cand_name": "Test",
        "cand_headline": "", "cand_profile": "", "cand_seeking": "",
        "cand_not_suitable": "",
    })
    _, despues, _ = get(base, "/linkedin?perfil=test")
    assert 'value="GenAI Engineer"' in despues
    assert 'value="LLM Engineer"' in despues

    # Y sacarla de las palabras clave la saca de acá.
    post(base, "/datos", {
        "perfil": "test", "keywords": "Python",
        "min_score": "60", "top_n": "5", "max_new_per_run": "30",
        "pais": "Argentina", "ciudad": "", "max_english_level": "A2",
        "cv": "# CV", "empresas": "", "rrhh": "", "cand_name": "Test",
        "cand_headline": "", "cand_profile": "", "cand_seeking": "",
        "cand_not_suitable": "",
    })
    _, final, _ = get(base, "/linkedin?perfil=test")
    assert 'value="GenAI Engineer"' not in final
    assert 'value="Python"' in final
    # Y la pantalla dice de dónde salen, para que no haya que adivinarlo.
    assert "Salen de <b>Palabras clave</b>" in final


def test_sin_palabras_clave_ofrece_las_sugeridas(sitio):
    """Un constructor sin ninguna opción no se puede usar. Con el perfil vacío
    se ofrecen los puestos del clúster, que es de donde arrancó todo esto."""
    from vacantia.ui.linkedin_urls import PUESTOS_SUGERIDOS, puestos_de

    assert puestos_de({"keywords": []}) == list(PUESTOS_SUGERIDOS)
    assert puestos_de({}) == list(PUESTOS_SUGERIDOS)
    assert puestos_de({"keywords": ["  ", ""]}) == list(PUESTOS_SUGERIDOS)
    # Con palabras clave, mandan ésas y no las sugeridas.
    assert puestos_de({"keywords": ["AI Engineer"]}) == ["AI Engineer"]


def test_la_direccion_se_ve_entera_y_nunca_detras_de_un_boton(sitio):
    """Es un texto largo con comillas y paréntesis que LinkedIn a veces
    interpreta distinto. Si algo sale raro, lo primero que se mira es esto."""
    from vacantia.ui.estilos import CSS

    base, _ = sitio
    _, html, _ = get(base, "/linkedin?perfil=test&puesto=AI+Engineer")
    # La URL entera está en el texto de la página, no sólo en el href.
    assert "keywords=%22AI%20Engineer%22" in html

    regla = CSS[CSS.index(chr(10) + ".url-generada {"):]
    regla = regla[:regla.index("}")]
    assert "overflow-wrap: anywhere" in regla       # se corta, no se trunca
    assert "var(--font-mono)" in regla
    assert "var(--color-background)" in regla       # como pide el sistema


def test_guardar_desde_la_pantalla_y_que_aparezca_en_la_lista(sitio):
    base, _ = sitio
    url = L.armar_url('"AI Engineer" AND buscamos')

    _, html, _ = post(base, "/linkedin-favorito",
                      {"perfil": "test", "url": url, "nombre": "La que sirve"})
    assert "La que sirve" in html
    assert "Todavía no guardaste ninguna" not in html

    # Y sacarla la saca.
    _, despues, _ = post(base, "/linkedin-favorito",
                         {"perfil": "test", "url": url, "borrar": "1"})
    assert "La que sirve" not in despues


def test_guardar_una_direccion_que_no_es_de_linkedin_avisa(sitio):
    base, _ = sitio
    _, _, destino = post(base, "/linkedin-favorito",
                         {"perfil": "test", "url": "https://google.com", "nombre": "x"})
    assert "error" in destino


def test_copiar_avisa_porque_el_portapapeles_no_se_ve(sitio):
    """Es el único toast de la app. Guardar un favorito no lleva uno: el
    favorito aparece en la lista, y avisar lo que ya se ve es ruido."""
    from vacantia.ui.render import JS

    base, _ = sitio
    _, html, _ = get(base, "/linkedin?perfil=test&puesto=AI+Engineer")
    assert "Copiar link" in html and "onclick=\"copiar(" in html
    assert "Link copiado" in JS
    assert "4000" in JS                              # los 4 segundos del sistema
    # Sin navigator.clipboard se cae a seleccionar el texto, que deja el Ctrl+C
    # a un paso en vez de dejar a la persona sin nada.
    assert "seleccionar" in JS

    _, guardado, _ = post(base, "/linkedin-favorito",
                          {"perfil": "test", "url": L.armar_url('"AI"'), "nombre": "x"})
    assert "Guardado en favoritos" not in guardado


# --- el contador de lo aplicado desde acá -----------------------------------


def test_el_anotador_sube_baja_y_no_cuenta_hasta_que_lo_confirmas(sitio):
    """Lo aplicado desde un posteo no tiene ninguna oferta detrás.

    No entró por el scraper, no está en `job_history.json` y no hay tarjeta que
    marcar. Sin este anotador, justo el trabajo que más cuesta (buscar a mano,
    temprano) es el único que no se cuenta.

    Y son dos pasos y no uno: un número que sube y nunca vuelve a cero no se
    puede confirmar ni corregir.
    """
    base, _ = sitio

    _, html, _ = get(base, "/linkedin?perfil=test")
    assert "Apliqué desde acá" in html and "Confirmar" in html
    assert L.pendientes("test") == 0 and L.postulaciones("test") == []

    post(base, "/linkedin-apliques", {"perfil": "test", "suma": "1"})
    post(base, "/linkedin-apliques", {"perfil": "test", "suma": "1"})
    assert L.pendientes("test") == 2
    # Todavía no cuenta para nada: nadie lo confirmó.
    assert L.postulaciones("test") == []

    # Restar saca del anotador, que es el toque que se acaba de errar.
    post(base, "/linkedin-apliques", {"perfil": "test", "menos": "1"})
    assert L.pendientes("test") == 1

    # Confirmar lo pasa a firme y deja el anotador en cero.
    _, html, _ = post(base, "/linkedin-apliques", {"perfil": "test", "confirmar": "1"})
    assert L.pendientes("test") == 0
    assert len(L.postulaciones("test")) == 1
    assert "Sumaste 1 postulación" in html      # y se dice, porque no se ve

    # En cero, ni restar ni confirmar rompen ni dejan un número negativo.
    post(base, "/linkedin-apliques", {"perfil": "test", "menos": "1"})
    post(base, "/linkedin-apliques", {"perfil": "test", "confirmar": "1"})
    assert L.pendientes("test") == 0
    assert len(L.postulaciones("test")) == 1


def test_el_anotador_sigue_ahi_cuando_volves(sitio):
    """No se borra solo. Si se borrara al recargar, contar sería inútil: armar
    una búsqueda ya recarga la pantalla."""
    base, _ = sitio
    post(base, "/linkedin-apliques", {"perfil": "test", "suma": "1"})

    _, html, _ = get(base, "/linkedin?perfil=test&puesto=AI+Engineer")
    assert '<b class="numero">1</b>' in html
    assert L.pendientes("test") == 1
    post(base, "/linkedin-apliques", {"perfil": "test", "confirmar": "1"})


def test_anotar_no_te_hace_perder_la_busqueda_recien_armada(sitio):
    """El contador es un POST adentro de un formulario GET.

    Sin la vuelta explícita, anotar te devolvía la pantalla en blanco y había
    que rearmar la dirección que estabas por usar.
    """
    base, _ = sitio
    volver = "perfil=test&tab=publicaciones&puesto=AI+Engineer&idioma=es"

    _, _, destino = post(base, f"/linkedin-apliques?volver={quote(volver)}",
                         {"perfil": "test", "suma": "1"})
    assert "puesto=AI+Engineer" in destino
    assert "tab=publicaciones" in destino

    # Lo que venga en `volver` y no sea del constructor no llega al redirect:
    # ese valor vuelve del navegador y termina en un header Location.
    _, _, sucio = post(base, "/linkedin-apliques?volver=" + quote("perfil=test&pum=1"),
                       {"perfil": "test", "suma": "1"})
    assert "pum" not in sucio


def test_lo_aplicado_desde_linkedin_suma_al_contador_grande(sitio):
    """Es el mismo trabajo: mandar un CV. El número tiene que decirlo todo."""
    from vacantia.ui import data

    base, _ = sitio
    antes = data.aplicadas_en("test", "30d")

    post(base, "/linkedin-apliques", {"perfil": "test", "suma": "1"})
    post(base, "/linkedin-apliques", {"perfil": "test", "confirmar": "1"})
    despues = data.aplicadas_en("test", "30d")
    assert despues["cuantas"] == antes["cuantas"] + 1
    assert despues["a_mano"] == 1
    # Y también en el reparto por semana: si no, el total y las barras se
    # contradicen en la misma tarjeta.
    assert (sum(n for _, n in despues["por_semana"])
            == sum(n for _, n in antes["por_semana"]) + 1)

    # Y la pantalla dice de dónde salió, para que el total no suba solo.
    _, html, _ = get(base, "/trabajos?perfil=test&ver=pendientes")
    assert "desde un posteo de LinkedIn" in html
