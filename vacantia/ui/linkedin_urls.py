"""Armar direcciones de búsqueda de publicaciones de LinkedIn, y guardarlas.

**Por qué esto existe.** Hay un agujero en el sistema que no se puede tapar
scrapeando: muchas vacantes se publican como **posteo del feed** y nunca llegan
a la pestaña Jobs, porque publicar así le sale gratis a la empresa. LinkedIn no
deja leer eso desde afuera, y Google lo indexa entre uno y tres días tarde, así
que cuando la fuente `google_posts` lo trae ya pasó lo mejor: el aviso se llenó
de postulantes.

La salida no es automatizarlo, es al revés: **la app arma la dirección y la
persona la abre**. Eso pone el trabajo del lado de la persona, pero le da lo
único que importa acá, que es llegar temprano.

Todo lo de este módulo se verificó contra LinkedIn el 10/9/2026, logueado:

    keywords=(boolean)          ->  anda, con AND/OR/NOT y comillas
    datePosted="past-24h"       ->  anda, el filtro queda aplicado
    sortBy="date_posted"        ->  anda, ordena por lo más reciente
    postedBy=["first","following"] -> anda, y el filtro dice "2 Publicado por"
    contentType=["jobs"]        ->  anda pero DEJA LA LISTA EN CERO

Ese último quedó afuera a propósito. "Anuncios de empleo" es un tipo de
contenido con formato propio de LinkedIn, no un posteo de texto libre, y
justamente los posteos que buscamos son texto libre. Combinado con cualquier
otro filtro devuelve cero resultados: un control que rompe la búsqueda no es una
opción, es una trampa.

LinkedIn acepta los valores con comillas y sin ellas, pero **devuelve la URL con
comillas**. Se arma como él la devuelve, para que la que se guarda en favoritos
sea igual a la que él genera y no haya que preguntarse si son la misma.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from vacantia.config import terminos_de_busqueda
from vacantia.log import get_logger
from vacantia.state import STATE_ROOT

logger = get_logger()

BASE = "https://www.linkedin.com/search/results/content/"

#: Los puestos que se ofrecen cuando el perfil no tiene ninguna palabra clave
#: cargada. **No es la lista que se usa normalmente**: esa sale del perfil, del
#: campo *Palabras clave* de Mi perfil, para que haya un solo lugar donde
#: agregar o sacar un puesto y no dos que se desincronizan.
#:
#: Salen de `sistema_De_likns_post_linkedin.md`: la idea es cubrir cómo escribe
#: el puesto cada reclutador, que no es una sola forma.
PUESTOS_SUGERIDOS = (
    "AI Engineer", "LLM Engineer", "GenAI Engineer", "Applied AI Engineer",
    "ML Engineer", "Machine Learning Engineer",
)


def puestos_de(perfil: dict) -> list[str]:
    """Los puestos que se ofrecen en el constructor.

    Son **las palabras clave del perfil y las de cada CV**, las mismas que usa
    el motor para buscar en los portales. Un solo lugar donde se agregan y se
    sacan: si el constructor tuviera su propia lista, agregar un puesto habría
    que hacerlo dos veces y tarde o temprano quedarían distintas.
    """
    crudas = terminos_de_busqueda(perfil or {})
    puestos = [str(k).strip() for k in crudas if str(k).strip()]
    return puestos or list(PUESTOS_SUGERIDOS)

#: Las frases con las que un reclutador anuncia que está buscando. Son las que
#: convierten una búsqueda de tema ("AI Engineer") en una de vacante.
GATILLOS_ES = (
    "buscamos", "estamos buscando", "nos encontramos en la búsqueda",
    "vacante", "posición abierta", "estamos contratando",
)
GATILLOS_EN = (
    "we're hiring", "we are looking for", "open role", "join our team",
)

LUGARES = ("Argentina", "remoto", "LATAM")

#: Lo que se saca con NOT. Sin esto, media lista son puestos junior.
EXCLUIR = ("Junior", "Semisenior", "Ssr", "trainee", "pasantía")

#: (clave, etiqueta, valor que espera LinkedIn).
CUANDO = (
    ("24h", "Últimas 24 horas", "past-24h"),
    ("semana", "Última semana", "past-week"),
    ("mes", "Último mes", "past-month"),
)

ORDEN = (
    ("recientes", "Lo más reciente primero", "date_posted"),
    ("relevancia", "Lo que LinkedIn cree más relevante", "relevance"),
)

DE_QUIEN = (
    ("todos", "Cualquiera", ()),
    ("red", "Mi red y a quien sigo", ("first", "following")),
)


def _frase(termino: str) -> str:
    """Entre comillas si tiene espacios, que es como se pide una frase exacta.

    Sin comillas, `AI Engineer` se busca como `AI` y `Engineer` por separado y
    entra cualquier cosa que diga "engineer".
    """
    termino = str(termino or "").strip()
    if not termino:
        return ""
    return f'"{termino}"' if " " in termino else termino


def _grupo(terminos) -> str:
    """`("AI Engineer" OR "LLM Engineer")`. Vacío si no hay ninguno."""
    partes = [f for t in (terminos or []) if (f := _frase(t))]
    if not partes:
        return ""
    return f"({' OR '.join(partes)})" if len(partes) > 1 else partes[0]


#: **De acá para arriba, LinkedIn devuelve cero resultados.** No da error ni
#: avisa: aplica los filtros, muestra "No se han encontrado resultados" y te deja
#: creyendo que no hay vacantes. Es la trampa más fea de todo esto.
#:
#: Medido contra el sitio el 10/9/2026, la misma tarde, con la misma cuenta:
#:
#:      70 car.  2 puestos + 2 gatillos                        trae posteos
#:      72 car.  2 puestos + 1 gatillo + lugar                 trae posteos
#:      85 car.  2 puestos + 1 gatillo + 3 NOT sueltos         trae posteos
#:      96 car.  2 puestos + 2 gatillos + lugar                trae posteos
#:     117 car.  2 puestos + 4 gatillos                        trae posteos
#:     130 car.  2 puestos + 2 gatillos + lugar + 3 NOT        CERO
#:     164 car.  2 puestos + 6 gatillos                        CERO
#:
#: El corte está entre 117 y 130. El tope queda en 110, con margen: LinkedIn
#: cambia su buscador seguido y no conviene quedar al borde. Es la advertencia
#: del markdown de investigación, ahora con el número puesto: *"si son muy
#: largos LinkedIn los interpreta mal"*.
TOPE_KEYWORDS = 110


def armar_boolean(puestos=(), gatillos=(), lugares=(), excluir=()) -> str:
    """El texto de búsqueda, con la sintaxis que LinkedIn acepta hoy.

    `AND`, `OR` y `NOT` en mayúsculas, comillas para las frases exactas y
    paréntesis para agrupar. **No** se usan comodines ni `+`/`-`: LinkedIn los
    ignora, y una búsqueda que parece filtrar y no filtra es peor que una que no
    filtra.

    **Recorta los gatillos para no pasar `TOPE_KEYWORDS`.** Se recortan ésos y
    no los puestos porque el puesto es lo que se busca, y porque los gatillos
    están ordenados de más usado a menos: sacando los últimos se pierde poco.
    Una búsqueda con cuatro gatillos que trae posteos vale infinitamente más
    que una con seis que devuelve cero.
    """
    gatillos, excluir = list(gatillos or []), list(excluir or [])
    fijos = [g for g in (_grupo(puestos), _grupo(lugares)) if g]

    def componer(cuantos_gatillos, cuantos_fuera):
        bloques = list(fijos)
        if (g := _grupo(gatillos[:cuantos_gatillos])):
            bloques.insert(1 if puestos else 0, g)
        texto = " AND ".join(bloques)
        # Cada término excluido va con su propio NOT. **`NOT (a OR b)` no
        # funciona: devuelve cero.** Verificado el 10/9/2026, misma búsqueda y
        # mismo momento:
        #
        #   ... AND buscamos NOT (Junior OR trainee OR pasantía)  ->  CERO
        #   ... AND buscamos NOT Junior                           ->  trae posteos
        #   ... AND buscamos NOT Junior NOT trainee NOT pasantía  ->  trae posteos
        #
        # LinkedIn agrupa con paréntesis en todos lados menos después de un NOT,
        # donde el grupo se come la búsqueda entera.
        # **`NOT (a OR b)` no funciona: devuelve cero resultados.** Verificado
        # contra el sitio el 10/9/2026, misma búsqueda y mismo momento:
        #
        #   ... AND buscamos NOT (Junior OR trainee OR pasantía)  ->  CERO
        #   ... AND buscamos NOT Junior                           ->  trae posteos
        #   ... AND buscamos NOT Junior NOT trainee NOT pasantía  ->  trae posteos
        #
        # LinkedIn agrupa con paréntesis en todos lados menos después de un NOT,
        # donde el grupo se come la búsqueda entera. Se emite un NOT por
        # término, que es la forma que sí respeta.
        if texto and puestos:
            for t in excluir[:cuantos_fuera]:
                if f := _frase(t):
                    texto += f" NOT {f}"
        return texto

    # **Qué se sacrifica cuando no entra todo**, en orden de importancia:
    #
    # 1. **Dos gatillos, antes que nada.** Sin gatillo la búsqueda deja de traer
    #    vacantes y trae cualquier posteo que hable de AI Engineer, que es justo
    #    lo que no sirve. Con uno solo se pierde la mitad de las formas de
    #    anunciar una búsqueda.
    # 2. **Después los NOT**, que sacan los junior, que son muchos.
    # 3. **Al final, gatillos de más**, que suman de a poco.
    #
    # Se prueban todas las combinaciones y gana la de mejor puntaje, en vez de
    # cortar en la primera que entra: cortar temprano daba "tres gatillos y cero
    # NOT" cuando "dos gatillos y tres NOT" entraba igual y filtra mejor.
    mejor, mejor_puntaje = componer(0, 0), -1
    for cuantos_gatillos in range(len(gatillos) + 1):
        for cuantos_fuera in range(len(excluir) + 1):
            texto = componer(cuantos_gatillos, cuantos_fuera)
            if len(texto) > TOPE_KEYWORDS:
                continue
            entraron = que_entro_en(texto, gatillos, excluir)
            puntaje = (min(entraron["gatillos"], 2) * 1000
                       + entraron["excluir"] * 100
                       + entraron["gatillos"])
            if puntaje > mejor_puntaje:
                mejor, mejor_puntaje = texto, puntaje
    return mejor


def que_entro_en(texto: str, gatillos=(), excluir=()) -> dict:
    """{gatillos, excluir}: cuántos de cada uno hay en un texto ya armado."""
    return {
        "gatillos": sum(1 for g in (gatillos or []) if _frase(g) in texto),
        "excluir": sum(1 for e in (excluir or []) if f"NOT {_frase(e)}" in texto),
    }


def que_entro(puestos=(), gatillos=(), lugares=(), excluir=()) -> dict:
    """{gatillos, excluir}: cuántos de cada uno sobrevivieron al recorte.

    Si se recortó algo, la persona tiene que saberlo. Si no, cree que está
    buscando "vacante" o dejando afuera "trainee", y en realidad no.
    """
    return que_entro_en(armar_boolean(puestos, gatillos, lugares, excluir),
                        gatillos, excluir)


def armar_url(texto: str, cuando: str = "24h", orden: str = "recientes",
              de_quien: str = "todos") -> str:
    """La dirección completa, lista para pegar en el navegador.

    Devuelve "" si no hay texto de búsqueda: una URL sin `keywords` abre el
    buscador vacío, y eso no es una búsqueda guardable.
    """
    texto = str(texto or "").strip()
    if not texto:
        return ""

    partes = [f"keywords={quote(texto, safe='')}"]
    if valor := dict((c, v) for c, _, v in CUANDO).get(cuando):
        partes.append(f"datePosted={quote(chr(34) + valor + chr(34), safe='')}")
    if valor := dict((c, v) for c, _, v in ORDEN).get(orden):
        partes.append(f"sortBy={quote(chr(34) + valor + chr(34), safe='')}")
    if quienes := dict((c, v) for c, _, v in DE_QUIEN).get(de_quien) or ():
        # Sin el espacio después de la coma, que es como lo devuelve LinkedIn.
        # Anda igual con espacio, pero así la URL guardada es idéntica a la suya.
        lista = json.dumps(list(quienes), separators=(",", ":"))
        partes.append(f"postedBy={quote(lista, safe='')}")
    # `origin` es el que LinkedIn agrega solo cuando aplicás filtros a mano. Va
    # para que la URL sea idéntica a la que él genera.
    partes.append("origin=FACETED_SEARCH")
    return BASE + "?" + "&".join(partes)


def nombre_sugerido(puestos=(), cuando: str = "24h", gatillos_en: bool = False) -> str:
    """Un nombre para el favorito, armado de lo que se buscó.

    Sirve para no tener que inventarlo cada vez, que es lo que hace que uno no
    guarde nada. Se puede pisar escribiendo otro.
    """
    que = (list(puestos or []) or ["Publicaciones"])[0]
    cuando_txt = dict((c, e) for c, e, _ in CUANDO).get(cuando, "")
    idioma = " en inglés" if gatillos_en else ""
    return f"{que}, {cuando_txt.lower()}{idioma}" if cuando_txt else f"{que}{idioma}"


# --- favoritos --------------------------------------------------------------
#
# Van en `state/<perfil>/` y no en el perfil porque crecen con el uso y no son
# configuración del motor: el perfil dice qué buscar automáticamente, esto es la
# libreta de búsquedas que la persona hace a mano.


def _archivo(nombre_perfil: str) -> Path:
    return STATE_ROOT / nombre_perfil / "linkedin_favoritos.json"


def favoritos(nombre_perfil: str) -> list[dict]:
    """Los guardados, del más nuevo al más viejo. [] si no hay o está roto."""
    ruta = _archivo(nombre_perfil)
    if not ruta.exists():
        return []
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning(f"{ruta} corrupto — arranco de cero")
        return []
    if not isinstance(datos, list):
        return []
    return sorted((d for d in datos if isinstance(d, dict) and d.get("url")),
                  key=lambda d: d.get("guardada", ""), reverse=True)


def _escribir(nombre_perfil: str, lista: list[dict]) -> None:
    from vacantia.ui.data import _escribir_atomico

    ruta = _archivo(nombre_perfil)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    _escribir_atomico(ruta, json.dumps(lista, indent=2, ensure_ascii=False) + "\n")


def guardada_como(nombre_perfil: str, url: str) -> str:
    """El nombre con el que ya está guardada esa dirección, o "" si no está."""
    url = str(url or "").strip()
    for guardado in favoritos(nombre_perfil):
        if guardado.get("url") == url:
            return str(guardado.get("nombre") or "")
    return ""


def guardar_favorito(nombre_perfil: str, nombre: str, url: str) -> str:
    """Guarda una búsqueda. Devuelve qué pasó: guardada / repetida / invalida.

    Son tres respuestas y no un sí o no, porque las dos formas de fallar piden
    mensajes distintos: una dirección que no es de LinkedIn está mal escrita, y
    una repetida ya está donde la persona la fue a buscar. Con un solo `False`
    para las dos, guardar algo que ya tenías contestaba "esa dirección no es una
    búsqueda de publicaciones", que es mentira y manda a corregir lo que está
    bien.

    La repetida **no se pisa**: la misma dirección dos veces no agrega nada, y
    cambiarle el nombre de callado a la que ya estaba es tocar algo que nadie
    pidió tocar. Para renombrarla, se saca y se guarda de nuevo.
    """
    url = str(url or "").strip()
    if not url.startswith(BASE):
        return "invalida"
    if guardada_como(nombre_perfil, url):
        return "repetida"

    nombre = str(nombre or "").strip() or "Búsqueda sin nombre"
    lista = favoritos(nombre_perfil)
    lista.append({"nombre": nombre, "url": url,
                  "guardada": datetime.now(timezone.utc).isoformat()})
    _escribir(nombre_perfil, lista)
    logger.info(f"[ui] Búsqueda de LinkedIn guardada: {nombre}")
    return "guardada"


def borrar_favorito(nombre_perfil: str, url: str) -> bool:
    lista = favoritos(nombre_perfil)
    quedan = [f for f in lista if f.get("url") != str(url or "").strip()]
    if len(quedan) == len(lista):
        return False
    _escribir(nombre_perfil, quedan)
    logger.info("[ui] Búsqueda de LinkedIn borrada")
    return True


# --- las postulaciones hechas desde un posteo -------------------------------
# Lo que se aplica desde un posteo de LinkedIn no entra por el scraper, así que
# no hay ninguna oferta que marcar: no existe en `job_history.json` y el
# contador de Trabajos nunca la ve. Sin esto, justo el trabajo que más cuesta
# (buscar a mano, temprano, el mismo día que se publicó) es el único que no se
# cuenta, y el número grande de la pantalla miente para abajo.
#
# Son DOS cosas y no una:
#
#   pendientes  el anotador de la tanda que estás haciendo ahora. Sube y baja
#               con el más y el menos. No cuenta para nada todavía.
#   hechas      las que confirmaste. Éstas sí suman al contador de Trabajos.
#
# Están separadas porque un número que sube solo y nunca vuelve a cero no se
# puede confirmar: no hay forma de saber si lo que ves es lo de hoy o lo de
# toda la semana. Con el anotador aparte, contás mientras mandás, confirmás al
# final y el anotador vuelve a cero. Lo pendiente **no se borra solo**: si
# cerrás la pantalla sin confirmar, sigue ahí cuando volvés.
#
# De las confirmadas se guarda la marca de tiempo y no un total, porque el
# contador de Trabajos tiene selector de período y reparto por semana: con un
# número pelado no se podría contestar "¿cuántas mandé esta semana?".


def _archivo_apliques(nombre_perfil: str) -> Path:
    return STATE_ROOT / nombre_perfil / "linkedin_postulaciones.json"


def _leer_apliques(nombre_perfil: str) -> dict:
    """{pendientes, hechas}. Tolera el formato viejo, que era sólo la lista."""
    vacio = {"pendientes": 0, "hechas": []}
    ruta = _archivo_apliques(nombre_perfil)
    if not ruta.exists():
        return vacio
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning(f"{ruta} corrupto — arranco de cero")
        return vacio
    if isinstance(datos, list):          # el formato de antes: sólo confirmadas
        datos = {"pendientes": 0, "hechas": datos}
    if not isinstance(datos, dict):
        return vacio
    hechas = datos.get("hechas")
    try:
        pendientes = max(0, int(datos.get("pendientes") or 0))
    except (TypeError, ValueError):
        pendientes = 0
    return {
        "pendientes": pendientes,
        "hechas": sorted(str(h) for h in (hechas or []) if str(h or "").strip()),
    }


def _escribir_apliques(nombre_perfil: str, datos: dict) -> None:
    from vacantia.ui.data import _escribir_atomico

    ruta = _archivo_apliques(nombre_perfil)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    _escribir_atomico(ruta, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")


def postulaciones(nombre_perfil: str) -> list[str]:
    """Las marcas de tiempo de lo **confirmado**, de la más vieja a la más nueva.

    Es lo único que suma al contador de Trabajos. Lo que está en el anotador
    todavía no pasó por la mano de nadie.
    """
    return _leer_apliques(nombre_perfil)["hechas"]


def pendientes(nombre_perfil: str) -> int:
    """Lo que hay en el anotador, sin confirmar."""
    return _leer_apliques(nombre_perfil)["pendientes"]


def sumar_pendiente(nombre_perfil: str) -> int:
    datos = _leer_apliques(nombre_perfil)
    datos["pendientes"] += 1
    _escribir_apliques(nombre_perfil, datos)
    return datos["pendientes"]


def restar_pendiente(nombre_perfil: str) -> int:
    """Uno menos. En cero no hace nada: un anotador en negativo no significa nada."""
    datos = _leer_apliques(nombre_perfil)
    if datos["pendientes"] <= 0:
        return 0
    datos["pendientes"] -= 1
    _escribir_apliques(nombre_perfil, datos)
    return datos["pendientes"]


def confirmar_pendientes(nombre_perfil: str) -> int:
    """Pasa el anotador a confirmadas y lo deja en cero. Devuelve cuántas pasaron.

    La marca de tiempo es la de ahora y no la del momento exacto de cada envío,
    que nadie anotó. Para lo que se usa (¿cuántas mandé esta semana?) el día es
    el mismo, y pedir la hora de cada una sería pedir un formulario para algo
    que se resuelve con un botón.
    """
    datos = _leer_apliques(nombre_perfil)
    cuantas = datos["pendientes"]
    if not cuantas:
        return 0
    ahora = datetime.now(timezone.utc).isoformat()
    datos["hechas"] = sorted(datos["hechas"] + [ahora] * cuantas)
    datos["pendientes"] = 0
    _escribir_apliques(nombre_perfil, datos)
    logger.info(f"[ui] {cuantas} postulaciones por LinkedIn confirmadas: "
                f"van {len(datos['hechas'])}")
    return cuantas
