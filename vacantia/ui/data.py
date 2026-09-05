"""Lectura y escritura de los archivos que edita la UI.

La UI no habla con el motor: escribe sobre los mismos archivos que el motor ya
usa (`profiles/<nombre>.json`, `resume/<nombre>.md`, `companies.json`, `.env` y
`state/<nombre>/`). Una sola fuente de verdad, sin sincronizar nada.

Todo lo que toca disco vive acá, así `server.py` se ocupa sólo de HTTP.
"""

import json
import os
import re
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

from vacantia.config import PROFILES_DIR, load_profile, load_resume, profile_path
from vacantia.fechas import dias_desde, fecha_de
from vacantia.filters import passes_language
from vacantia.log import get_logger
from vacantia.models import Job
from vacantia.state import State

logger = get_logger()

ENV_FILE = Path(".env")
RESUME_DIR = Path("resume")
PLANTILLA_PERFIL = PROFILES_DIR / "example.json"
PLANTILLA_CV = RESUME_DIR / "EJEMPLO_CV.md"

#: Claves que la UI deja editar en el `.env`. El resto del archivo no se toca.
#:
#: El TELEGRAM_CHAT_ID NO está acá a propósito: es el único dato que no se
#: comparte. Dos personas que usan la misma computadora comparten la clave del
#: bot y las de las APIs, pero cada una tiene que recibir SUS ofertas en SU
#: Telegram, así que el chat_id va dentro del perfil (ver `chat_id_de`).
CLAVES_ENV = (
    "TELEGRAM_TOKEN",
    "GEMINI_API_KEY",
    "TINYFISH_API_KEY",
    "OPENROUTER_API_KEY",
)

#: Lo que se deja en el perfil cuando la persona no carga un chat propio: cae
#: al TELEGRAM_CHAT_ID del .env, que es como venía funcionando.
CHAT_ID_COMPARTIDO = "${TELEGRAM_CHAT_ID}"

NOMBRE_VALIDO = re.compile(r"^[a-z0-9_-]{2,32}$")


# --- perfiles ---------------------------------------------------------------

def perfiles() -> list[str]:
    """Los perfiles editables. `example` es la plantilla, no se lista."""
    if not PROFILES_DIR.exists():
        return []
    return sorted(p.stem for p in PROFILES_DIR.glob("*.json") if p.stem != "example")


def leer_perfil(nombre: str) -> dict:
    """El JSON tal cual está en disco.

    A propósito NO se usa `config.load_profile`: esa resuelve los `${VAR}` a su
    valor real, y guardar eso escribiría las claves de la API dentro del perfil,
    que se versiona en git.
    """
    ruta = profile_path(nombre)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el perfil '{nombre}'")
    return json.loads(ruta.read_text(encoding="utf-8"))


def guardar_perfil(nombre: str, data: dict) -> None:
    ruta = profile_path(nombre)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    _escribir_atomico(ruta, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    logger.info(f"[ui] Perfil guardado: {ruta}")


def _escribir_atomico(ruta: Path, texto: str) -> None:
    """Escribe a un temporal y reemplaza. Si se corta la luz a mitad de un
    guardado, el archivo viejo queda entero en vez de truncado."""
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    tmp.write_text(texto, encoding="utf-8")
    tmp.replace(ruta)


def crear_perfil(nombre: str) -> str:
    """Perfil nuevo en blanco a partir de la plantilla. Devuelve el nombre.

    No inventa datos de nadie: copia `profiles/example.json` con los
    placeholders puestos para que la persona los complete desde la UI.
    """
    nombre = (nombre or "").strip().lower().replace(" ", "_")
    if not NOMBRE_VALIDO.match(nombre):
        raise ValueError(
            "El nombre tiene que tener entre 2 y 32 letras, números, guiones o "
            "guiones bajos, sin espacios ni acentos (ej: maria, juan_pablo)."
        )
    if nombre == "example":
        raise ValueError("'example' es la plantilla: elegí otro nombre.")
    destino = profile_path(nombre)
    if destino.exists():
        raise ValueError(f"Ya existe un perfil llamado '{nombre}'.")
    if not PLANTILLA_PERFIL.exists():
        raise FileNotFoundError(f"Falta la plantilla {PLANTILLA_PERFIL}")

    data = json.loads(PLANTILLA_PERFIL.read_text(encoding="utf-8"))
    data.pop("_comentario", None)   # la nota es del molde, no del perfil nuevo
    data["name"] = nombre
    data["cv_path"] = f"resume/{nombre}.md"
    guardar_perfil(nombre, data)

    cv = RESUME_DIR / f"{nombre}.md"
    if not cv.exists():
        RESUME_DIR.mkdir(parents=True, exist_ok=True)
        if PLANTILLA_CV.exists():
            shutil.copyfile(PLANTILLA_CV, cv)
        else:
            cv.write_text("# PEGAR CV ACÁ\n", encoding="utf-8")
        logger.info(f"[ui] CV en blanco creado: {cv}")
    return nombre


# --- CV ---------------------------------------------------------------------

def ruta_cv(perfil: dict) -> Path:
    return Path(perfil.get("cv_path") or f"resume/{perfil.get('name', 'cv')}.md")


def leer_cv(perfil: dict) -> str:
    ruta = ruta_cv(perfil)
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


def guardar_cv(perfil: dict, texto: str) -> None:
    ruta = ruta_cv(perfil)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    _escribir_atomico(ruta, texto.replace("\r\n", "\n"))
    logger.info(f"[ui] CV guardado: {ruta} ({len(texto)} chars)")


# --- .env -------------------------------------------------------------------

def leer_env() -> dict[str, str]:
    if not ENV_FILE.exists():
        return {}
    valores = {}
    for linea in ENV_FILE.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        valores[clave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def guardar_env(cambios: dict[str, str]) -> list[str]:
    """Escribe sólo las claves que vienen con valor, respetando el resto.

    Un campo vacío en el formulario significa "no lo cambies", no "borralo":
    la UI muestra las claves enmascaradas, así que si vaciarlas borrara el
    valor, entrar a la pantalla y guardar sin tocar nada dejaría a la persona
    sin credenciales.
    """
    cambios = {k: v.strip() for k, v in cambios.items() if k in CLAVES_ENV and v.strip()}
    if not cambios:
        return []

    lineas = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    pendientes = dict(cambios)
    salida = []
    for linea in lineas:
        clave = linea.split("=", 1)[0].strip() if "=" in linea else ""
        if clave in pendientes and not linea.strip().startswith("#"):
            salida.append(f"{clave}={pendientes.pop(clave)}")
        else:
            salida.append(linea)
    for clave, valor in pendientes.items():
        salida.append(f"{clave}={valor}")

    _escribir_atomico(ENV_FILE, "\n".join(salida) + "\n")
    # Para que la corrida que se dispare desde esta misma sesión las vea.
    for clave, valor in cambios.items():
        os.environ[clave] = valor
    logger.info(f"[ui] .env actualizado: {', '.join(sorted(cambios))}")
    return sorted(cambios)


def enmascarar(valor: str) -> str:
    """'abc123def456' -> 'abc1…f456'. Para mostrar sin exponer la clave."""
    valor = (valor or "").strip()
    if not valor:
        return ""
    if len(valor) <= 8:
        return "•" * len(valor)
    return f"{valor[:4]}…{valor[-4:]}"


# --- empresas ---------------------------------------------------------------

def ruta_companies(perfil: dict) -> Path:
    fuente = _fuente(perfil, "careers")
    return Path((fuente or {}).get("companies_file") or "companies.json")


def leer_companies(perfil: dict) -> list[dict]:
    ruta = ruta_companies(perfil)
    if not ruta.exists():
        return []
    try:
        data = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning(f"[ui] {ruta} no es JSON válido — lo muestro vacío")
        return []
    return data if isinstance(data, list) else []


def companies_a_texto(companies: list[dict]) -> str:
    """Una empresa por línea: `Nombre | careers_url | dominio`."""
    return "\n".join(
        " | ".join(
            [c.get("name", ""), c.get("careers_url", ""), c.get("search_domain", "")]
        ).rstrip(" |")
        for c in companies
    )


def texto_a_companies(texto: str, previas: list[dict]) -> list[dict]:
    """Parsea el textarea conservando los campos que la UI no muestra.

    `use_search`, `location` y `region` no están en el formulario; si se
    reconstruyera la lista de cero se perderían (y con ellos el ahorro de las
    siete empresas que tienen la búsqueda apagada).
    """
    por_nombre = {c.get("name", "").strip().lower(): c for c in previas}
    salida = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        partes = [p.strip() for p in linea.split("|")]
        nombre = partes[0]
        if not nombre:
            continue
        entrada = dict(por_nombre.get(nombre.lower(), {}))
        entrada["name"] = nombre
        if len(partes) > 1 and partes[1]:
            entrada["careers_url"] = partes[1]
        if len(partes) > 2 and partes[2]:
            entrada["search_domain"] = partes[2]
        entrada.setdefault("careers_url", "")
        salida.append(entrada)
    return salida


def guardar_companies(perfil: dict, companies: list[dict]) -> None:
    ruta = ruta_companies(perfil)
    _escribir_atomico(ruta, json.dumps(companies, indent=2, ensure_ascii=False) + "\n")
    logger.info(f"[ui] {ruta} actualizado ({len(companies)} empresa(s))")


# --- fuentes dentro del perfil ---------------------------------------------

def _fuente(perfil: dict, tipo: str) -> dict | None:
    for entrada in perfil.get("sources", []) or []:
        if entrada.get("type") == tipo:
            return entrada
    return None


def fuente_o_crear(perfil: dict, tipo: str, defaults: dict | None = None) -> dict:
    """Devuelve el bloque de esa fuente en el perfil, creándolo si no está."""
    encontrada = _fuente(perfil, tipo)
    if encontrada is not None:
        return encontrada
    nueva = {"type": tipo, "enabled": True, **(defaults or {})}
    perfil.setdefault("sources", []).append(nueva)
    return nueva


# --- ofertas ----------------------------------------------------------------

#: Cuántas mostrar en la pestaña Trabajos. Con 3 corridas por día y ~25 ofertas
#: nuevas diarias, 300 son unas dos semanas de historial.
#: Cuántas ofertas por página. Con 267 en el historial, una sola página larga
#: no se puede recorrer: se scrollea sin llegar nunca al final.
POR_PAGINA = 20

#: Para ordenar: las que no tienen fecha van al fondo, no arriba de todo.
_SIN_FECHA = date.min


#: Antigüedad máxima en días de cada rango. None = sin límite.
#: Un aviso del mes pasado casi siempre está cubierto: se sigue pudiendo ver,
#: pero deja de ser lo primero que aparece.
RANGOS: dict[str, int | None] = {"hoy": 0, "7d": 7, "30d": 30, "todo": None}


def _entra_por_fecha(oferta: dict, desde: str, hoy=None) -> bool:
    tope = RANGOS.get(desde)
    if tope is None:
        return True
    momento, _ = fecha_de(oferta, hoy)
    dias = dias_desde(momento, hoy)
    # Sin fecha no se descarta: el aviso puede ser de hoy y no tenemos con qué
    # decir que no. Esconderlo sería peor que mostrarlo de más.
    return dias is None or dias <= tope


def _por_estado(historial: list[dict], ver: str) -> list[dict]:
    if ver == "aplicadas":
        return [h for h in historial if h.get("aplicado") is True]
    if ver == "descartadas":
        return [h for h in historial if h.get("aplicado") is False]
    if ver == "archivadas":
        return [h for h in historial if h.get("archivada")]
    if ver == "pendientes":
        # Las archivadas salen de acá: es el punto de archivarlas.
        return [h for h in historial
                if h.get("aplicado") is None and not h.get("archivada")]
    return historial


def ofertas(nombre_perfil: str, ver: str = "pendientes", desde: str = "todo",
            pagina: int = 1) -> tuple[list[dict], int, int]:
    """Una página de ofertas: (las de esta página, número de página, páginas).

    `ver`:   pendientes (sin marcar) | aplicadas | descartadas | todas.
    `desde`: hoy | 7d | 30d | todo, por antigüedad del aviso.

    En **Sin marcar** y **Todas** se ordena por puntaje, no por fecha. Ordenar por fecha ponía arriba las
    que acababan de entrar, y como el puntaje 0 lo sacan las que directamente no
    son para uno, la lista abría con lo peor: tres avisos de Lima puntuados 0
    antes que 29 ofertas de 80 para arriba. A igual puntaje manda la fecha del
    aviso, que ahí sí importa: entre dos que encajan igual, primero la más nueva.
    """
    historial = _por_estado(State(nombre_perfil).load_history(), ver)
    historial = [h for h in historial if _entra_por_fecha(h, desde)]
    if ver in ("aplicadas", "descartadas", "archivadas"):
        # Estas dos pestañas no son para elegir, son para revisar: "¿a quién le
        # mandé el CV?", "¿por qué había descartado ésta?". Lo último que hiciste
        # primero. Ordenarlas por puntaje, como la de pendientes, dejaba lo de
        # ayer mezclado con lo de hace tres semanas.
        historial.sort(
            key=lambda h: h.get("fecha_archivada") or h.get("fecha_feedback") or "",
            reverse=True,
        )
    else:
        historial.sort(
            key=lambda h: (
                h.get("score") if h.get("score") is not None else -1,
                fecha_de(h)[0] or _SIN_FECHA,
                h.get("found_at", ""),
            ),
            reverse=True,
        )

    paginas = max(1, -(-len(historial) // POR_PAGINA))   # división para arriba
    pagina = min(max(1, pagina), paginas)
    arranca = (pagina - 1) * POR_PAGINA
    return historial[arranca : arranca + POR_PAGINA], pagina, paginas


def contar_ofertas(nombre_perfil: str, desde: str = "todo") -> dict[str, int]:
    """Cuántas hay de cada estado, dentro del rango de fechas elegido."""
    historial = [h for h in State(nombre_perfil).load_history()
                 if _entra_por_fecha(h, desde)]
    return {
        "todas": len(historial),
        "pendientes": sum(1 for h in historial
                          if h.get("aplicado") is None and not h.get("archivada")),
        "aplicadas": sum(1 for h in historial if h.get("aplicado") is True),
        "descartadas": sum(1 for h in historial if h.get("aplicado") is False),
        "archivadas": sum(1 for h in historial if h.get("archivada")),
    }


def contar_por_fecha(nombre_perfil: str, ver: str = "pendientes") -> dict[str, int]:
    """Cuántas hay en cada rango, dentro del estado elegido.

    Los dos contadores se cruzan a propósito: el número de cada botón dice qué
    va a pasar si se lo aprieta, no cuántas hay en total.
    """
    historial = _por_estado(State(nombre_perfil).load_history(), ver)
    return {rango: sum(1 for h in historial if _entra_por_fecha(h, rango))
            for rango in RANGOS}


def pena_de_ingles(nombre_perfil: str, desde: str = "todo") -> dict:
    """Qué se perdió por no saber inglés: cuántas y cuánto puntuaba la mejor.

    Existe por pedido explícito, y el pedido incluía que incomode: ver sólo las
    ofertas en español da la impresión de que el mercado es así, cuando lo que
    se ve es el recorte que deja el filtro. El número adelante lo desarma.

    Se recalcula sobre el historial en vez de guardarse: el nivel de inglés del
    perfil se puede cambiar desde la pantalla, y el cartel tiene que responder a
    lo que dice el perfil hoy, no a lo que decía cuando corrió la búsqueda.
    """
    perfil = leer_perfil(nombre_perfil)
    cfg = ((perfil.get("filters") or {}).get("language")) or {}
    historial = [h for h in State(nombre_perfil).load_history()
                 if _entra_por_fecha(h, desde)]

    perdidas = [h for h in historial if not passes_language(Job.from_dict(h), cfg)[0]]
    if not perdidas:
        return {"cuantas": 0, "mejor": None, "mejor_titulo": ""}

    mejor = max(perdidas, key=lambda h: h.get("score") or 0)
    return {
        "cuantas": len(perdidas),
        "mejor": mejor.get("score"),
        "mejor_titulo": mejor.get("scored_title") or mejor.get("title") or "",
    }


def guardar_feedback(nombre_perfil: str, url: str, aplicado: bool, motivo: str) -> bool:
    return State(nombre_perfil).record_feedback(
        url, aplicado=aplicado, motivo_descarte=motivo,
        fecha_feedback=datetime.now(timezone.utc).isoformat(),
    )


def buscar_oferta(nombre_perfil: str, url: str) -> dict | None:
    """La oferta del historial con esa URL, o None."""
    clave = (url or "").split("?")[0].rstrip("/").lower()
    for entrada in State(nombre_perfil).load_history():
        if entrada.get("url", "").split("?")[0].rstrip("/").lower() == clave:
            return entrada
    return None


def como_job(oferta: dict) -> Job:
    return Job.from_dict(oferta)


def mensajes_con_llm(nombre_perfil: str, job: Job) -> tuple[dict[str, str], bool]:
    """Los dos mensajes escritos por el modelo. (textos, los escribió el modelo).

    Usa `load_profile` y no `leer_perfil` porque acá sí hacen falta los secretos
    resueltos: es el único lugar de la UI que llama a una API.
    """
    from vacantia import mensajes as mensajes_mod

    perfil = load_profile(nombre_perfil)
    cv = load_resume(perfil)
    textos, escritos = {}, []
    for tipo in mensajes_mod.TIPOS:
        texto, ok = mensajes_mod.generar(job, cv, perfil, tipo)
        textos[tipo] = texto
        escritos.append(ok)
    return textos, all(escritos)


# --- Telegram por persona ---------------------------------------------------

def _telegram(perfil: dict) -> dict:
    """El bloque del notificador de Telegram, creándolo si no está."""
    for entrada in perfil.get("notifiers") or []:
        if entrada.get("type") == "telegram":
            return entrada
    nuevo = {"type": "telegram", "enabled": True, "token": "${TELEGRAM_TOKEN}",
             "chat_id": CHAT_ID_COMPARTIDO}
    perfil.setdefault("notifiers", []).append(nuevo)
    return nuevo


def chat_id_de(perfil: dict) -> str:
    """El chat propio de esta persona, o "" si usa el compartido del .env."""
    valor = str(_telegram(perfil).get("chat_id") or "").strip()
    return "" if valor.startswith("${") else valor


def guardar_chat_id(perfil: dict, chat_id: str) -> None:
    """Vacío = volver al chat compartido del .env."""
    chat_id = (chat_id or "").strip()
    _telegram(perfil)["chat_id"] = chat_id or CHAT_ID_COMPARTIDO


def consejo_con_llm(nombre_perfil: str, job: Job) -> tuple[str, bool]:
    """El consejo escrito por el modelo. Necesita los secretos resueltos, así
    que va por `load_profile` y no por `leer_perfil`."""
    from vacantia import consejo as consejo_mod

    perfil = load_profile(nombre_perfil)
    return consejo_mod.consejo_con_llm(job, load_resume(perfil), perfil)


def marca_de_cambio(nombre_perfil: str) -> str:
    """Un valor que cambia cuando entran ofertas nuevas, y sólo entonces.

    Es la fecha de modificación del historial más su tamaño. Alcanza para que la
    pantalla se entere de que hubo una corrida sin leer el archivo entero cada
    veinte segundos: el historial son 207 ofertas y crece.
    """
    archivo = State(nombre_perfil).history_file
    try:
        st = archivo.stat()
    except OSError:
        return ""
    return f"{st.st_mtime_ns}-{st.st_size}"


def archivar(nombre_perfil: str, urls: list[str], archivada: bool = True) -> int:
    return State(nombre_perfil).archivar(urls, archivada)


def viejas_sin_marcar(nombre_perfil: str, dias: int) -> list[str]:
    """Las URLs sin marcar cuyo aviso tiene más de `dias`, para archivar de una.

    Las que no dicen cuándo se publicaron quedan afuera: no se sabe si están
    viejas, y archivar por las dudas es tirar una oferta que puede ser de ayer.
    """
    historial = _por_estado(State(nombre_perfil).load_history(), "pendientes")
    salida = []
    for h in historial:
        antiguedad = dias_desde(fecha_de(h)[0])
        if antiguedad is not None and antiguedad > dias:
            salida.append(h.get("url", ""))
    return [u for u in salida if u]
