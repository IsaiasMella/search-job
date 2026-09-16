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
import subprocess
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from vacantia.config import (PROFILES_DIR, cvs_con_texto, cvs_del_perfil, id_de_cv,
                             load_profile, load_resumes, profile_path)
from vacantia.fechas import dias_desde, fecha_de
from vacantia.filters import passes_language
from vacantia.log import get_logger
from vacantia.models import Job
from vacantia.state import STATE_ROOT, State

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
    # Cada perfil con su propio archivo de empresas. La plantilla trae
    # `companies.json`, que es el de Isaías: copiado tal cual, el perfil nuevo
    # compartía ese archivo, y guardar su lista pisaba la del otro. Pasó el
    # 12/9/2026 con el perfil de papá y se perdieron las 10 empresas de Isaías.
    for fuente in data.get("sources") or []:
        if fuente.get("type") == "careers":
            fuente["companies_file"] = f"companies-{nombre}.json"
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


#: Cómo se llama la búsqueda programada de cada perfil. La registra
#: `scripts/instalar.ps1` con este mismo nombre.
TAREA_PROGRAMADA = "Vacantia - {}"


def borrar_perfil(nombre: str) -> str:
    """Borra un perfil con todo lo suyo. Devuelve qué pasó con su tarea programada.

    **Es definitivo**, y por eso la pantalla pide confirmación antes de llegar
    acá. Se va:

    * `profiles/<nombre>.json`. `example` nunca: es el molde de los nuevos.
    * Sus CV, salvo el archivo que lea otro perfil.
    * `companies-<nombre>.json`, salvo que lo use otro perfil. Un archivo con
      otro nombre, como el `companies.json` de antes de separar las listas, no
      se toca: aunque este perfil lo use, no es suyo.
    * `state/<nombre>/`: las ofertas guardadas, lo que marcaste, los favoritos.
    * Su búsqueda programada de Windows. Si no está o no se deja sacar, lo demás
      se borra igual y la pantalla lo avisa: una tarea huérfana falla sola al
      no encontrar el perfil, que es mucho menos grave que un perfil a medio
      borrar.

    Devuelve "sacada", "no-estaba" o "fallo".
    """
    if nombre == "example":
        raise ValueError("'example' es el molde de los perfiles nuevos: no se borra.")
    if nombre not in perfiles():
        raise ValueError(f"No existe el perfil '{nombre}'.")
    try:
        perfil = leer_perfil(nombre)
    except json.JSONDecodeError:
        perfil = {}             # roto, pero igual se tiene que poder borrar
    cvs = cvs_del_perfil(perfil) if perfil else []
    empresas = ruta_companies(perfil)
    empresas_compartidas = otros_perfiles_con_las_mismas_empresas(nombre, perfil)

    # Primero el estado, que es lo único que puede fallar a mitad de camino: un
    # archivo abierto por una búsqueda en curso. Si falla acá, el perfil sigue
    # entero y se puede volver a intentar.
    estado = STATE_ROOT / nombre
    if estado.is_dir():
        shutil.rmtree(estado)

    # El perfil antes que los CV: `_archivo_de_cv_en_uso` recorre todos los
    # perfiles, y con éste todavía en disco cada CV suyo figuraría en uso.
    profile_path(nombre).unlink()
    for cv in cvs:
        ruta = Path(cv["path"])
        if (ruta.is_file() and ruta.resolve() != PLANTILLA_CV.resolve()
                and not _archivo_de_cv_en_uso(ruta)):
            ruta.unlink()

    if (empresas.name == f"companies-{nombre}.json" and empresas.is_file()
            and not empresas_compartidas):
        empresas.unlink()

    logger.info(f"[ui] Perfil borrado: {nombre}")
    return _sacar_tarea_programada(nombre)


def _sacar_tarea_programada(nombre: str) -> str:
    """Saca la búsqueda programada de un perfil. "sacada", "no-estaba" o "fallo".

    Primero pregunta si está. Un perfil creado desde la pantalla no tiene tarea
    hasta que se vuelve a correr la instalación, y decirle "no pude sacarla" a
    quien nunca la tuvo lo manda a buscar un problema que no existe.

    `schtasks` viene con Windows. Las tareas se registran con el usuario común,
    así que sacarlas no pide permisos de administrador.
    """
    tarea = TAREA_PROGRAMADA.format(nombre)
    opciones = {"capture_output": True, "text": True, "errors": "replace", "timeout": 15,
                "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    try:
        consulta = subprocess.run(["schtasks", "/Query", "/TN", tarea], **opciones)
        if consulta.returncode != 0:
            logger.info(f"[ui] {tarea} no estaba programada")
            return "no-estaba"
        borrado = subprocess.run(["schtasks", "/Delete", "/TN", tarea, "/F"], **opciones)
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning(f"[ui] No pude sacar la tarea {tarea}: {e}")
        return "fallo"
    if borrado.returncode != 0:
        logger.warning(f"[ui] No pude sacar la tarea {tarea}: "
                       f"{(borrado.stderr or borrado.stdout or '').strip()}")
        return "fallo"
    logger.info(f"[ui] Tarea sacada: {tarea}")
    return "sacada"


# --- CV ---------------------------------------------------------------------

def ruta_cv(perfil: dict) -> Path:
    return Path(perfil.get("cv_path") or f"resume/{perfil.get('name', 'cv')}.md")


def leer_cv(perfil: dict) -> str:
    ruta = ruta_cv(perfil)
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


def fijar_cvs(perfil: dict, cvs: list[dict]) -> None:
    """Escribe la lista de CV en el perfil (en memoria; guardarlo es aparte).

    `cv_path` sigue apuntando al primero: lo leen el drafter y cualquier cosa
    vieja que todavía piense en un CV solo, y así no se entera del cambio.
    """
    perfil["cvs"] = [
        {"id": cv["id"], "nombre": cv["nombre"], "path": cv["path"],
         "palabras_clave": list(cv.get("palabras_clave") or [])}
        for cv in cvs
    ]
    perfil["cv_path"] = perfil["cvs"][0]["path"]


def agregar_cv(nombre_perfil: str) -> str:
    """Suma un CV vacío al perfil, para completarlo en la pantalla. Devuelve su id.

    Nace vacío a propósito y así no cuenta para nada (ver `config.cvs_con_texto`)
    hasta que tenga texto: agregarlo no cambia ninguna recomendación ni ningún
    puntaje. El archivo es `resume/<perfil>-<id>.md`; si ya existía uno con ese
    nombre, no se pisa.
    """
    perfil = leer_perfil(nombre_perfil)
    cvs = cvs_del_perfil(perfil)
    ids = {cv["id"] for cv in cvs}
    numero = len(cvs) + 1
    while id_de_cv(f"CV {numero}") in ids:
        numero += 1
    nombre_cv = f"CV {numero}"
    cv_id = id_de_cv(nombre_cv)

    ruta = RESUME_DIR / f"{nombre_perfil}-{cv_id}.md"
    if not ruta.exists():
        RESUME_DIR.mkdir(parents=True, exist_ok=True)
        ruta.write_text("", encoding="utf-8")

    fijar_cvs(perfil, cvs + [{"id": cv_id, "nombre": nombre_cv,
                             "path": ruta.as_posix(), "palabras_clave": []}])
    guardar_perfil(nombre_perfil, perfil)
    logger.info(f"[ui] CV agregado a {nombre_perfil}: {cv_id} ({ruta})")
    return cv_id


def borrar_cv(nombre_perfil: str, cv_id: str) -> str:
    """Borra un CV del perfil y su archivo. Devuelve su nombre, o "" si no se pudo.

    **Es definitivo**, y por eso la pantalla pide confirmación antes de llegar
    acá. No se puede borrar el último: el perfil tiene que quedar con uno.

    El archivo no se borra si lo lee otro CV, de éste o de otro perfil: pasa si
    alguien apunta dos CV al mismo texto a mano, y borrar uno no puede dejar al
    otro vacío. Las ofertas que recomendaban el CV borrado se vuelven a estimar
    solas.
    """
    perfil = leer_perfil(nombre_perfil)
    cvs = cvs_del_perfil(perfil)
    borrado = next((cv for cv in cvs if cv["id"] == cv_id), None)
    quedan = [cv for cv in cvs if cv["id"] != cv_id]
    if borrado is None or not quedan:
        return ""
    fijar_cvs(perfil, quedan)
    guardar_perfil(nombre_perfil, perfil)

    ruta = Path(borrado["path"])
    if ruta.exists() and not _archivo_de_cv_en_uso(ruta):
        ruta.unlink()
        logger.info(f"[ui] CV borrado de {nombre_perfil}: {cv_id} ({ruta})")
    else:
        logger.info(f"[ui] CV sacado de {nombre_perfil}: {cv_id} (el archivo lo usa otro CV)")
    return borrado["nombre"]


def _archivo_de_cv_en_uso(ruta: Path) -> bool:
    """¿Algún CV de algún perfil lee este archivo?"""
    objetivo = ruta.resolve()
    for nombre in perfiles():
        try:
            otro = leer_perfil(nombre)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        if any(Path(cv["path"]).resolve() == objetivo for cv in cvs_del_perfil(otro)):
            return True
    return False


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


def otros_perfiles_con_las_mismas_empresas(nombre_perfil: str, perfil: dict) -> list[str]:
    """Los demás perfiles que leen y escriben el mismo archivo de empresas."""
    propia = ruta_companies(perfil).resolve()
    otros = []
    for otro in perfiles():
        if otro == nombre_perfil:
            continue
        try:
            if ruta_companies(leer_perfil(otro)).resolve() == propia:
                otros.append(otro)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    return otros


def separar_companies(nombre_perfil: str, perfil: dict) -> list[str]:
    """Si otro perfil usa el mismo archivo de empresas, éste pasa a tener el suyo.

    Devuelve con quiénes lo compartía, o [] si no hizo falta separar. Cambia el
    perfil en memoria: guardarlo es de quien llama.

    **El que se va es el que guarda, y el otro no se toca.** Así, guardar la
    lista de un perfil nunca puede pisar la de otro, que es exactamente lo que
    pasó cuando compartían archivo: se guardó el perfil de papá y la lista de
    Isaías desapareció.
    """
    otros = otros_perfiles_con_las_mismas_empresas(nombre_perfil, perfil)
    if otros:
        # Si el bloque no existía, nace apagado: separar la lista no puede
        # prender una fuente. Prenderla es de Configuración.
        fuente_o_crear(perfil, "careers", {"enabled": False})["companies_file"] = (
            f"companies-{nombre_perfil}.json")
    return otros


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

#: Hasta cuántos días una oferta cuenta como "recién publicada" y sube arriba de
#: todo, por encima del puntaje.
#:
#: **Por qué existe.** Ordenar sólo por puntaje contesta "cuál encaja mejor con
#: mi CV", que no es la misma pregunta que "a cuál me conviene postularme
#: ahora": una de 92 puntos de hace seis días ya tiene cien postulantes y una de
#: 88 de esta mañana no tiene ninguno. Entre esas dos, la segunda.
#:
#: **Por qué 2 y no 1.** El buscador tarda en indexar: un post de ayer puede
#: aparecer recién pasado mañana. Con un día, lo verdaderamente nuevo se
#: perdería la banda por la demora del índice y no por su fecha.
#:
#: Una oferta **sin fecha no entra acá**: no sabemos que sea nueva y ponerla
#: arriba sería inventarlo. Se ordena por puntaje como siempre.
DIAS_RECIEN = 2

def es_recien_publicada(oferta: dict, min_score: int, hoy: date | None = None) -> bool:
    """¿Va en la banda de arriba? Recién publicada **y** que valga la pena.

    Dos condiciones, y las dos hacen falta:

    1. **Que el aviso diga que es de hace poco.** Se exige que la fecha sea de
       publicación y no la de cuándo lo vimos: `found_at` es de hoy para todo lo
       que entró en la corrida de hoy, y usarlo metería en "recién publicadas"
       un aviso de hace tres meses que encontramos esta mañana.

    2. **Que llegue al puntaje que la persona pidió** (`min_score` del perfil,
       el mismo número que decide si le avisamos por Telegram). Ésta es la
       lección ya aprendida que subir lo reciente reintroducía: las que puntúan
       0 son las que directamente no son para uno, y si entraron hoy quedaban
       arriba de todo — tres avisos de Lima en 0 antes que 29 ofertas de 80 para
       arriba. Ser de hoy no vuelve buena a una oferta mala; la frescura sólo
       ordena entre las que ya sirven.
    """
    if (oferta.get("score") or 0) < min_score:
        return False
    momento, es_de_publicacion = fecha_de(oferta, hoy)
    if not es_de_publicacion:
        return False
    dias = dias_desde(momento, hoy)
    return dias is not None and dias <= DIAS_RECIEN


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


# --- por qué no apliqué -----------------------------------------------------
#
# El campo era un texto libre y obligatorio, y con 60 descartes se vio en qué se
# convierte: 46 veces la misma frase escrita a mano ("Estaba en ingles, osea que
# necesito ingles para aplicar"), 4 veces "era presencial en Buenos Aires", y 6
# veces un guion, que es lo que se escribe cuando el motivo no se puede resumir
# y encima uno no quiere que el sistema saque conclusiones de ahí.
#
# El texto libre sigue estando —hay descartes que sólo se explican escribiendo—
# pero deja de ser el camino principal.

#: (clave, etiqueta, qué significa). El orden es el del desplegable.
#:
#: Los tres del medio se sumaron el 13/9/2026, cuando Métricas empezó a mostrar
#: lo escrito a mano: eran 16 descartes de Isaías tipeados de siete formas
#: ("No es una oferta laboral", "No era una oferta", "No rea mi puesto", "Me
#: pide tecnologias con las que no trabajo"...). Lo mismo que había pasado con
#: el inglés: si se repite, va a la lista.
MOTIVOS = (
    ("ingles", "Piden inglés",
     "Suma al contador de ofertas que se pierden por el idioma."),
    ("presencial", "Es presencial y no puedo ir",
     "El aviso exige estar en un lugar al que no vas."),
    ("no_es_oferta", "No es una oferta de trabajo",
     "Un posteo que habla de otra cosa y no busca a nadie."),
    ("no_mi_puesto", "No era mi puesto",
     "Es un trabajo de otra cosa, aunque haya coincidido con la búsqueda."),
    ("tecnologias", "Pide tecnologías con las que no trabajo",
     "El puesto es de lo tuyo, pero con otras herramientas."),
    ("especial", "Caso especial (que no aprenda de esto)",
     "Se guarda el descarte, pero no cuenta como preferencia tuya."),
)

#: Los dos caminos para descartar, y alcanza con cualquiera de los dos: elegir
#: uno de arriba, o escribirlo. **No hay una opción "Otro motivo" en la lista**,
#: y es a propósito: obligaba a abrir el desplegable, bajar hasta "Otro" y recién
#: ahí escribir, o sea tres pasos de más para el caso en que ya tenías la mano en
#: el teclado. El campo está siempre a la vista y es opcional.

#: Las que NO son una preferencia sobre el puesto y por lo tanto no tienen que
#: enseñarle nada al sistema el día que el scoring aprenda del feedback.
#:
#: "Piden inglés" y "es presencial" son restricciones tuyas que los filtros ya
#: aplican solos y mejor: meterlas al prompt como ejemplos negativos sería
#: enseñarle dos veces lo mismo, y por el lado impreciso. Y "razón especial" lo
#: pediste explícitamente.
#:
#: Los otros tres SÍ enseñan: "no era mi puesto" y "otras tecnologías" dicen
#: qué no te sirve, y "no es una oferta" es justo lo que el puntaje tendría que
#: aprender a mandar al cero.
MOTIVOS_QUE_NO_ENSENIAN = frozenset({"ingles", "presencial", "especial"})

_ETIQUETAS_MOTIVO = dict((clave, etiqueta) for clave, etiqueta, _ in MOTIVOS)

#: Para los descartes viejos, escritos a mano antes de que existiera el
#: desplegable. Sin esto, los 46 "estaba en ingles" que ya tenía Isaías no
#: sumarían al contador de inglés y el número arrancaría mintiendo.
#:
#: Los patrones de los motivos nuevos salen de las redacciones reales, errores
#: de tipeo incluidos ("No rea mi puesto"), y son angostos a propósito: "no es
#: una oferta" y no "no es", porque una frase mal clasificada desaparece de la
#: lista de lo escrito a mano y ya no hay forma de verla.
_MOTIVO_VIEJO = (
    ("ingles", re.compile(r"\bingl[eé]s\b|\bingles\b", re.I)),
    ("presencial", re.compile(r"\bpresencial\b|\bh[ií]brid", re.I)),
    ("no_es_oferta", re.compile(r"\bno\s+(?:es|era)\s+(?:una?\s+)?(?:oferta|empleo)\b",
                                re.I)),
    ("no_mi_puesto", re.compile(r"\bno\s+(?:es|era|rea)\s+mi\s+puesto\b", re.I)),
    ("tecnologias", re.compile(
        r"\bno\s+trabajo\s+con\s+(?:esas?\s+)?tecnolog"
        r"|\btecnolog[ií]as?\s+con\s+(?:las?\s+)?que\s+no\s+trabajo\b", re.I)),
    ("especial", re.compile(r"^[-–—\s]*$")),
)


def clave_de_motivo(oferta: dict) -> str:
    """Qué motivo tiene este descarte, sea del desplegable o escrito a mano.

    Devuelve "" para un texto libre que no encaja en ninguna categoría — que es
    exactamente el descarte valioso: el que dice algo del puesto y no de una
    restricción que los filtros ya conocen.
    """
    if clave := (oferta.get("motivo_clave") or "").strip():
        return clave if clave in _ETIQUETAS_MOTIVO else ""
    texto = (oferta.get("motivo_descarte") or "").strip()
    if not texto:
        return ""
    for clave, patron in _MOTIVO_VIEJO:
        if patron.search(texto):
            return clave
    return ""


#: Cómo se muestra un descarte sin motivo elegido ni escrito. El formulario ya
#: no deja guardarlo así, pero en el historial viejo los hay.
SIN_ESCRIBIR = "(no escribiste nada)"


def escritos_a_mano(descartadas) -> list[tuple[str, int]]:
    """Las frases de la barra "Escrito a mano", agrupadas y de más a menos.

    La barra sola decía cuántas y no qué eran. Isaías sospechaba que se estaban
    colando posteos de LinkedIn que no son ofertas, y eso no se podía confirmar
    sin leer lo que había escrito en cada descarte.

    Se agrupa ignorando mayúsculas, tildes, espacios de más y el punto final:
    "No es una oferta" y "no es una oferta." son la misma frase tipeada dos
    veces, y separadas ninguna parece repetirse. Más allá de eso no se
    interpreta nada: dos frases distintas que dicen lo mismo quedan en dos
    filas, porque adivinar sinónimos es la clase de cosa que termina contando mal.
    Cuando una idea se repite con varias redacciones, su lugar es el desplegable:
    así entraron "No es una oferta de trabajo" y los otros dos.

    Las que salieron del desplegable no van, aunque además tengan algo escrito:
    ya tienen su propia barra y acá se contarían dos veces. De cada frase se
    muestra la versión más reciente, y a igual cantidad va primero la última.
    """
    grupos: dict[str, list] = {}
    for h in sorted(descartadas, key=lambda h: h.get("fecha_feedback") or "",
                    reverse=True):
        if clave_de_motivo(h):
            continue
        texto = " ".join((h.get("motivo_descarte") or "").split())
        sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto.casefold())
                             if not unicodedata.combining(c))
        clave = sin_tildes.rstrip(" .,;:!?¡¿")
        if clave in grupos:
            grupos[clave][1] += 1
        else:
            grupos[clave] = [texto or SIN_ESCRIBIR, 1]
    return sorted(((t, n) for t, n in grupos.values()), key=lambda f: -f[1])


def partes_del_motivo(oferta: dict) -> tuple[str, str]:
    """(etiqueta, escrito a mano). Cualquiera de los dos puede venir vacío.

    Los dos caminos se pueden combinar: elegir "Piden inglés" y además escribir
    algo. Cuando pasa, se muestran los dos, pero cada uno en su propio elemento:
    la tarjeta no une datos con puntos medios.
    """
    escrito = (oferta.get("motivo_descarte") or "").strip()
    clave = clave_de_motivo(oferta)
    if not clave:
        return "", escrito
    # El guion que venías escribiendo para el caso especial no dice nada solo,
    # así que no se repite al lado de la etiqueta.
    etiqueta = "caso especial" if clave == "especial" else _ETIQUETAS_MOTIVO[clave]
    return etiqueta, (escrito if len(escrito) > 3 else "")


def texto_del_motivo(oferta: dict) -> str:
    """El motivo en una sola línea de texto plano, para donde no hay marcado."""
    etiqueta, escrito = partes_del_motivo(oferta)
    if etiqueta and escrito:
        return f"{etiqueta} · {escrito}"
    return etiqueta or escrito or "sin motivo"


# --- lo que el filtro ya había rechazado ------------------------------------


def motivos_del_sistema(oferta: dict, filtros: dict) -> list[tuple[str, str]]:
    """**Todos** los filtros que la sacan, no el primero. [(clave, explicación)]

    Devolvía sólo el primero, y eso hacía mentir a la pantalla de auditoría. Una
    oferta puede caer por idioma **y** por lugar a la vez: medido sobre el
    historial de Isaías el 11/9/2026, 28 de 204. En ésas se mostraba el lugar y
    se callaba el idioma, así que si el lugar estaba mal atribuido la respuesta
    honesta era "mal descartada" — y la oferta volvía a la lista aunque el
    idioma la sacara con todo derecho.

    **El idioma va primero porque es el motivo más firme.** Es el idioma en que
    está escrito el aviso, que se puede verificar leyéndolo, y además tiene una
    red de seguridad determinista que busca la exigencia en el texto. El lugar
    sale de lo que el modelo extrajo, y ahí hay deducciones: el caso que
    disparó esto fue un aviso sin ninguna ubicación al que el modelo le puso
    "Estados Unidos", que es la sede de la empresa. El prompt lo prohíbe
    explícitamente y el modelo lo hizo igual.

    **Se calcula al leer, no se guarda.** Es a propósito: el nivel de inglés y
    las ciudades se cambian desde *Mi perfil*, y una oferta rechazada hoy por
    pedir B2 tiene que volver a aparecer sola el día que subas tu nivel. Un
    campo guardado congelaría la decisión que se tomó con la configuración de
    aquel día.

    El motor ya aplica estos mismos filtros para decidir a qué avisarte; lo que
    guarda en el historial es **todo lo puntuado**, incluso lo rechazado. Eso
    estaba bien para poder contar lo que se pierde por idioma, pero llenaba la
    lista de "Sin marcar" con avisos sobre los que el sistema ya había decidido:
    medido el 8/9/2026, 31 de 41.
    """
    from vacantia.filters import passes_place

    job = Job.from_dict(oferta)
    motivos = []
    ok, why = passes_language(job, filtros.get("language") or {})
    if not ok:
        motivos.append(("idioma", why))
    ok, why, _ = passes_place(job, filtros.get("location") or {},
                              filtros.get("work_modes"))
    if not ok:
        motivos.append(("lugar", why))
    return motivos


def motivo_del_sistema(oferta: dict, filtros: dict) -> tuple[str, str]:
    """El motivo más firme de los que la sacan, o ("", "") si no la saca ninguno.

    Para quien sólo necesita saber si el filtro la sacó. La pantalla de
    auditoría usa `motivos_del_sistema`, que los devuelve todos.
    """
    motivos = motivos_del_sistema(oferta, filtros)
    return motivos[0] if motivos else ("", "")


def filtros_del_perfil(nombre_perfil: str) -> dict:
    """Los filtros del perfil, o {} si no hay perfil.

    Tolerante a propósito: el historial se puede leer sin que exista el archivo
    del perfil (pasa en los tests y pasaría con un perfil borrado a mano), y ahí
    la respuesta correcta es "no hay filtros", no reventar la pantalla.
    """
    try:
        return leer_perfil(nombre_perfil).get("filters") or {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _lo_saco_el_sistema(oferta: dict, filtros: dict) -> bool:
    """¿El filtro automático la descartó, y todavía nadie lo revisó?

    Una marcada **mal descartada** deja de contar como sacada por el sistema:
    ése es el punto de marcarla, que vuelva a la fila para poder aplicar.
    """
    if oferta.get("revision_filtro") == "mal":
        return False
    return bool(motivo_del_sistema(oferta, filtros)[0])


def _sin_marcar(historial: list[dict], filtros: dict) -> list[dict]:
    """Las que de verdad esperan una decisión tuya.

    Quedan afuera las que el sistema ya descartó por idioma o por lugar: sobre
    ésas ya hay un veredicto y ponerlas en la fila es pedirte que hagas a mano
    el trabajo que el filtro hizo. Viven en **Filtradas**, se cuentan en
    Métricas, y vuelven solas si cambiás el filtro que las sacó.

    La excepción es la que revisaste y marcaste **mal descartada**: ésa vuelve
    acá aunque el filtro la siga sacando, porque el filtro se equivocó y la
    oferta sigue estando.
    """
    return [h for h in historial
            if h.get("aplicado") is None and not h.get("archivada")
            and not _lo_saco_el_sistema(h, filtros)]


#: De qué puntaje para arriba vale la pena revisar si el filtro acertó.
#:
#: Una de 20 mal descartada no cambia nada: aunque el filtro se haya equivocado,
#: esa oferta no te iba a servir igual. Las que importan son las que te habrían
#: llamado, y ahí abajo de 50 no hay ninguna. Revisar las 43 que puntúan menos
#: es gastar la atención en el tramo donde el error no tiene consecuencia.
PUNTAJE_PARA_REVISAR = 50

#: Cuántas hay que revisar para poder decir algo del filtro. Con 40 revisadas y
#: ningún error, el filtro acierta arriba del 90% y no hay nada que tocar; con
#: 4 o más errores hay un patrón que mirar. Menos que eso es anécdota.
META_REVISION = 40


def _vale_revisarla(oferta: dict) -> bool:
    """¿Puntúa lo suficiente como para que importe si el filtro se equivocó?"""
    score = oferta.get("score")
    return (score if score is not None else -1) >= PUNTAJE_PARA_REVISAR


def _saco_el_sistema_sin_revisar(historial: list[dict], filtros: dict) -> list[dict]:
    """Todo lo que sacó el filtro y nadie revisó, sin mirar el puntaje."""
    return [h for h in historial
            if h.get("aplicado") is None and not h.get("archivada")
            and not h.get("revision_filtro")
            and motivo_del_sistema(h, filtros)[0]]


def _filtradas(historial: list[dict], filtros: dict) -> list[dict]:
    """Las que descartó el sistema solo, todavía no revisaste, y vale revisar.

    Es la pestaña para auditar el filtro en la primera semana: se lee el aviso,
    se lo compara con el motivo que dio el sistema, y se contesta si acertó. Las
    ya revisadas salen de acá, para las dos respuestas: la lista se vacía a
    medida que se revisa y no hay que acordarse de dónde se quedó uno.

    Las que puntúan menos de `PUNTAJE_PARA_REVISAR` no entran: ver el porqué
    arriba de esa constante.
    """
    return [h for h in _saco_el_sistema_sin_revisar(historial, filtros)
            if _vale_revisarla(h)]


def _por_estado(historial: list[dict], ver: str, filtros: dict) -> list[dict]:
    if ver == "aplicadas":
        return [h for h in historial if h.get("aplicado") is True]
    if ver == "descartadas":
        return [h for h in historial if h.get("aplicado") is False]
    if ver == "archivadas":
        return [h for h in historial if h.get("archivada")]
    if ver == "filtradas":
        return _filtradas(historial, filtros)
    if ver == "pendientes":
        # Las archivadas salen de acá: es el punto de archivarlas.
        return _sin_marcar(historial, filtros)
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

    **Con una excepción arriba de todo**: las publicadas hace `DIAS_RECIEN` días
    o menos van primero, ordenadas entre ellas por puntaje. No es lo mismo "cuál
    encaja mejor" que "a cuál me conviene postularme ahora", y cuanto más
    reciente el aviso, menos gente se postuló. El puntaje que se muestra no se
    toca: significa qué tan bien encaja con el CV y mezclarle la fecha lo
    arruinaría. Lo único que cambia es el orden.
    """
    filtros = filtros_del_perfil(nombre_perfil)
    historial = _por_estado(State(nombre_perfil).load_history(), ver, filtros)
    historial = [h for h in historial if _entra_por_fecha(h, desde)]
    if ver in ("aplicadas", "archivadas"):
        # Estas dos pestañas no son para elegir, son para revisar: "¿a quién le
        # mandé el CV esta semana?", "¿qué archivé?". Lo último que hiciste
        # primero. Ordenarlas por puntaje dejaba lo de ayer mezclado con lo de
        # hace tres semanas.
        historial.sort(
            key=lambda h: h.get("fecha_archivada") or h.get("fecha_feedback") or "",
            reverse=True,
        )
    elif ver == "descartadas":
        # Descarté también es para revisar, pero la pregunta es otra: no es
        # "¿qué hice ayer?" sino **"¿me equivoqué al descartar algo bueno?"**, y
        # eso se contesta mirando primero las de más puntaje. Por fecha, una de
        # 90 quedaba quinta, abajo de dos de 0, y las que hay que auditar son
        # justamente las de arriba. A igual puntaje manda lo último que marcaste.
        historial.sort(
            key=lambda h: (h.get("score") if h.get("score") is not None else -1,
                           h.get("fecha_feedback") or ""),
            reverse=True,
        )
    elif ver == "filtradas":
        # Primero las de más puntaje: son las que más duele perder si el filtro
        # se equivocó, y son las que hay que mirar con más atención. Sin la
        # banda de recientes, que acá no ayuda: la pregunta no es "¿a cuál me
        # postulo?" sino "¿el filtro acertó?".
        #
        # El motivo que dio el sistema viaja pegado a cada oferta: es el dato
        # que hay que auditar, y calcularlo acá evita que la pantalla tenga que
        # volver a abrir el perfil por cada tarjeta.
        historial = [{**h, "_motivos_sistema": motivos_del_sistema(h, filtros)}
                     for h in historial]
        historial.sort(
            key=lambda h: (h.get("score") if h.get("score") is not None else -1,
                           h.get("found_at", "")),
            reverse=True,
        )
    else:
        # El puntaje que pidió la persona es el que decide qué entra a la banda
        # de recientes. Se lee una vez acá y viaja pegado a cada oferta en
        # `_recien`, para que la pantalla no tenga que volver a abrir el perfil
        # ni repetir la regla.
        try:
            min_score = int(leer_perfil(nombre_perfil).get("min_score", 60) or 0)
        except (FileNotFoundError, json.JSONDecodeError):
            min_score = 60
        historial = [{**h, "_recien": es_recien_publicada(h, min_score)}
                     for h in historial]
        historial.sort(
            key=lambda h: (
                h["_recien"],
                h.get("score") if h.get("score") is not None else -1,
                fecha_de(h)[0] or _SIN_FECHA,
                h.get("found_at", ""),
            ),
            reverse=True,
        )

    paginas = max(1, -(-len(historial) // POR_PAGINA))   # división para arriba
    pagina = min(max(1, pagina), paginas)
    arranca = (pagina - 1) * POR_PAGINA
    return (_con_cv_para_mandar(nombre_perfil, historial[arranca : arranca + POR_PAGINA]),
            pagina, paginas)


def _con_cv_para_mandar(nombre_perfil: str, ofertas: list[dict]) -> list[dict]:
    """Qué CV mandar a cada oferta de esta página. Viaja pegado en `_cv`.

    `_cv` es {id, nombre, estimado}. Así la tarjeta sólo tiene que dibujarlo:
    no necesita abrir el perfil ni saber cómo se llama cada CV, igual que con
    `_recien` y `_motivos_sistema`.

    Las que se puntuaron antes de que el perfil tuviera varios CV no traen
    recomendación del modelo. No se re-puntúan, que serían decenas de llamadas:
    se estima gratis por palabras con `consejo.cv_que_mejor_encaja`, y queda
    marcado como estimado para que la tarjeta lo diga. Lo mismo si recomendaba
    un CV que después se borró: dejarla sin nada sería tirar un dato que se
    puede calcular.

    **Sólo la página que se va a dibujar**, 20 como mucho, y **sólo con dos o
    más CV escritos**: con uno no hay nada que recomendar. No se guarda en el
    historial: se recalcula en cada carga, así si cambiás un CV la
    recomendación se acomoda sola.
    """
    try:
        perfil = leer_perfil(nombre_perfil)
    except (FileNotFoundError, json.JSONDecodeError):
        return ofertas
    if len(cvs_del_perfil(perfil)) < 2:
        return ofertas                  # ni siquiera se leen los archivos
    cvs = cvs_con_texto(perfil)
    if len(cvs) < 2:
        return ofertas

    from vacantia.consejo import cv_que_mejor_encaja

    por_id = {cv["id"]: cv for cv in cvs}
    salida = []
    for oferta in ofertas:
        elegido = oferta.get("cv_recomendado")
        estimado = elegido not in por_id
        if estimado:
            elegido = cv_que_mejor_encaja(Job.from_dict(oferta), cvs)
        salida.append({**oferta, "_cv": {"id": elegido,
                                         "nombre": por_id[elegido]["nombre"],
                                         "estimado": estimado}})
    return salida


def contar_ofertas(nombre_perfil: str, desde: str = "todo") -> dict[str, int]:
    """Cuántas hay de cada estado, dentro del rango de fechas elegido."""
    historial = [h for h in State(nombre_perfil).load_history()
                 if _entra_por_fecha(h, desde)]
    filtros = filtros_del_perfil(nombre_perfil)
    return {
        "todas": len(historial),
        # El mismo criterio que usa la lista: si el número dijera 41 y la lista
        # mostrara 10, el número estaría mintiendo.
        "pendientes": len(_sin_marcar(historial, filtros)),
        "aplicadas": sum(1 for h in historial if h.get("aplicado") is True),
        "descartadas": sum(1 for h in historial if h.get("aplicado") is False),
        "filtradas": len(_filtradas(historial, filtros)),
        "archivadas": sum(1 for h in historial if h.get("archivada")),
    }


def resumen_revision(nombre_perfil: str) -> dict[str, int]:
    """El marcador de la auditoría del filtro.

    {bien, mal, sin_revisar, meta, faltan, bajo_puntaje}.

    **Es acumulativo y no se resetea con el rango de fechas.** La pregunta que
    contesta es "en toda la semana, ¿cuántas veces acertó el filtro?", y con
    dos días de muestra un porcentaje sobre lo de hoy no dice nada. Por eso se
    cuenta contra el historial entero, no contra la página que se está viendo.
    """
    historial = State(nombre_perfil).load_history()
    filtros = filtros_del_perfil(nombre_perfil)
    revisiones = Counter(h.get("revision_filtro") for h in historial)
    bien = revisiones.get("bien", 0)
    mal = revisiones.get("mal", 0)
    # "Bien sacada, pero el motivo estaba mal". Cuenta como acierto del filtro
    # —la oferta no tenía que llegarte— y como error de la explicación, que es
    # otra cosa y se arregla en otro lado.
    motivo_errado = revisiones.get("motivo", 0)
    sin_revisar = _saco_el_sistema_sin_revisar(historial, filtros)
    return {
        "bien": bien + motivo_errado,
        "mal": mal,
        "motivo_errado": motivo_errado,
        "sin_revisar": sum(1 for h in sin_revisar if _vale_revisarla(h)),
        # Las que el filtro sacó y no se revisan porque puntúan poco. Se cuentan
        # aparte para poder decir por qué la lista está vacía en vez de dejar
        # pensando que se terminaron las ofertas.
        "bajo_puntaje": sum(1 for h in sin_revisar if not _vale_revisarla(h)),
        "meta": META_REVISION,
        "faltan": max(0, META_REVISION - (bien + motivo_errado + mal)),
    }


def revisar_filtro(nombre_perfil: str, url: str, revision: str) -> int:
    """Anota si el filtro acertó con esa oferta. Ver `State.revisar_filtro`."""
    return State(nombre_perfil).revisar_filtro([url], revision)


def contar_por_fecha(nombre_perfil: str, ver: str = "pendientes") -> dict[str, int]:
    """Cuántas hay en cada rango, dentro del estado elegido.

    Los dos contadores se cruzan a propósito: el número de cada botón dice qué
    va a pasar si se lo aprieta, no cuántas hay en total.
    """
    filtros = filtros_del_perfil(nombre_perfil)
    historial = _por_estado(State(nombre_perfil).load_history(), ver, filtros)
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
    cfg = filtros_del_perfil(nombre_perfil).get("language") or {}
    historial = [h for h in State(nombre_perfil).load_history()
                 if _entra_por_fecha(h, desde)]

    # Dos fuentes, y la segunda la pediste vos: lo que el filtro detecta solo,
    # más lo que marcaste a mano como "piden inglés". El LLM no siempre pone
    # `requires_english` —de tus 46 descartes por idioma, varios no lo tenían—
    # así que sin esto el número se quedaba corto justo donde vos ya sabías la
    # respuesta. Marcar una como "piden inglés" ahora hace subir el número.
    perdidas = [h for h in historial
                if not passes_language(Job.from_dict(h), cfg)[0]
                or clave_de_motivo(h) == "ingles"]
    if not perdidas:
        return {"cuantas": 0, "mejor": None, "mejor_titulo": ""}

    mejor = max(perdidas, key=lambda h: h.get("score") or 0)
    return {
        "cuantas": len(perdidas),
        "mejor": mejor.get("score"),
        "mejor_titulo": mejor.get("scored_title") or mejor.get("title") or "",
    }


def estadisticas(nombre_perfil: str, desde: str = "todo") -> dict:
    """Los números de la pestaña Estadísticas.

    Existe porque los contadores estaban repartidos en los botones de arriba, y
    ahí compiten con el único número que importa mientras uno trabaja: cuántas
    quedan por mirar. Los botones se quedan con ése; el resto vive acá.
    """
    historial = [h for h in State(nombre_perfil).load_history()
                 if _entra_por_fecha(h, desde)]
    filtros = filtros_del_perfil(nombre_perfil)

    # Se cuenta por CADA filtro que la saca, no por el primero: una oferta que
    # cae por idioma y por lugar aparece en las dos filas. Por eso las filas
    # suman más que `sistema_total`, que son ofertas distintas.
    sistema: Counter = Counter()
    sacadas = 0
    for h in historial:
        if h.get("aplicado") is None and not h.get("archivada"):
            claves = [c for c, _ in motivos_del_sistema(h, filtros)]
            sacadas += bool(claves)
            for clave in claves:
                sistema[clave] += 1

    descartadas = [h for h in historial if h.get("aplicado") is False]
    motivos: Counter = Counter()
    for h in descartadas:
        motivos[clave_de_motivo(h) or "otro"] += 1

    por_fuente: Counter = Counter(h.get("source") or "?" for h in historial)

    return {
        "total": len(historial),
        "sin_marcar": len(_sin_marcar(historial, filtros)),
        "aplicadas": sum(1 for h in historial if h.get("aplicado") is True),
        "descartadas": len(descartadas),
        "archivadas": sum(1 for h in historial if h.get("archivada")),
        "sistema": dict(sistema),
        "sistema_total": sacadas,
        "sistema_solapadas": sum(sistema.values()) - sacadas,
        "motivos": dict(motivos),
        "escritos": escritos_a_mano(descartadas),
        "por_fuente": dict(por_fuente.most_common()),
        "ingles": pena_de_ingles(nombre_perfil, desde),
        "max_age_days": filtros.get("max_age_days"),
    }


def guardar_feedback(nombre_perfil: str, url: str, aplicado: bool, motivo: str,
                     motivo_clave: str = "") -> bool:
    return State(nombre_perfil).record_feedback(
        url, aplicado=aplicado, motivo_descarte=motivo, motivo_clave=motivo_clave,
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


def cv_para_oferta(nombre_perfil: str, oferta: dict, perfil: dict | None = None) -> dict:
    """El CV con el que conviene postularse a esta oferta.

    {id, nombre, path, palabras_clave, texto, estimado}. El que recomendó el
    modelo si sigue existiendo y tiene texto; si no, el estimado por palabras;
    con un solo CV, ése. Es lo que usan Consejo y Mensajes: aconsejar sobre el
    CV de AI para una oferta de Full Stack sería aconsejar sobre el equivocado.

    `perfil` se pasa cuando quien llama ya lo tiene cargado, para no leerlo dos
    veces; puede venir con los secretos resueltos o no, los CV son iguales.
    """
    cvs = cvs_con_texto(perfil if perfil is not None else leer_perfil(nombre_perfil))
    if len(cvs) == 1:
        return {**cvs[0], "estimado": False}
    por_id = {cv["id"]: cv for cv in cvs}
    elegido = str(oferta.get("cv_recomendado") or "")
    if elegido in por_id:
        return {**por_id[elegido], "estimado": False}

    from vacantia.consejo import cv_que_mejor_encaja

    estimado = cv_que_mejor_encaja(Job.from_dict(oferta), cvs)
    return {**por_id[estimado], "estimado": True}


def mensajes_con_llm(nombre_perfil: str, job: Job) -> tuple[dict[str, str], bool]:
    """Los dos mensajes escritos por el modelo. (textos, los escribió el modelo).

    Usa `load_profile` y no `leer_perfil` porque acá sí hacen falta los secretos
    resueltos: es el único lugar de la UI que llama a una API.
    """
    from vacantia import mensajes as mensajes_mod

    perfil = load_profile(nombre_perfil)
    cv = cv_para_oferta(nombre_perfil, job.to_dict(), perfil)["texto"]
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
    cv = cv_para_oferta(nombre_perfil, job.to_dict(), perfil)["texto"]
    return consejo_mod.consejo_con_llm(job, cv, perfil)


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
    filtros = filtros_del_perfil(nombre_perfil)
    historial = _por_estado(State(nombre_perfil).load_history(), "pendientes", filtros)
    salida = []
    for h in historial:
        antiguedad = dias_desde(fecha_de(h)[0])
        if antiguedad is not None and antiguedad > dias:
            salida.append(h.get("url", ""))
    return [u for u in salida if u]


# --- el estado del sistema, para el pie de la barra lateral -----------------


def _hace_cuanto(momento: datetime) -> str:
    """"hoy 16:30", "ayer 23:59" o "el 3/9 a las 12:00".

    En lenguaje humano y relativo, como se lo diría una persona. Nada de
    "hace 2 min" ni de contadores que corran: es texto quieto que cambia
    cuando cambia el dato.
    """
    local = momento.astimezone()
    dias = (date.today() - local.date()).days
    hora = local.strftime("%H:%M")
    if dias <= 0:
        return f"hoy {hora}"
    if dias == 1:
        return f"ayer {hora}"
    return f"el {local.day}/{local.month} a las {hora}"


def _proxima_corrida(nombre_perfil: str) -> str:
    """El próximo horario de este perfil, como "hoy 23:59" o "mañana 12:00".

    Los horarios los reparte `agenda` para que dos personas de la misma casa no
    busquen al mismo tiempo, así que hay que preguntárselos a ella y no
    escribirlos acá.
    """
    from vacantia import agenda

    horarios = agenda.plan(perfiles()).get(nombre_perfil) or []
    if not horarios:
        return ""
    ahora = datetime.now().strftime("%H:%M")
    for hora in sorted(horarios):
        if hora > ahora:
            return f"hoy {hora}"
    return f"mañana {sorted(horarios)[0]}"


def estado_del_sistema(nombre_perfil: str) -> dict:
    """{ultima, proxima, ventana} para el pie de la barra lateral.

    Es la información que contesta "¿esto es todo lo que hay?", que es de donde
    sale la mayor parte de la ansiedad de buscar trabajo. Por eso tiene un lugar
    fijo en la pantalla y no un tooltip.
    """
    ultima = ""
    crudo = State(nombre_perfil).ultima_corrida
    if crudo:
        try:
            ultima = _hace_cuanto(datetime.fromisoformat(crudo))
        except ValueError:
            ultima = ""
    from vacantia.ui import corrida

    ventana = (filtros_del_perfil(nombre_perfil) or {}).get("max_age_days")
    return {"ultima": ultima,
            "proxima": _proxima_corrida(nombre_perfil),
            "ventana": ventana,
            # Para que el botón "Buscar ahora" del pie no deje arrancar dos
            # búsquedas encimadas: los límites del plan gratis son de la cuenta.
            "corriendo": corrida.esta_corriendo(),
            # En qué etapa va la búsqueda, para el cartel que se refresca solo.
            "paso": corrida.progreso(),
            # Cómo está el historial AHORA. La pantalla se lo guarda al abrir y
            # después compara contra esto para saber si entraron ofertas
            # mientras la persona miraba.
            "marca": marca_de_cambio(nombre_perfil),
            "pendientes": contar_ofertas(nombre_perfil).get("pendientes", 0)}


# --- cuántas apliqué, y cuándo ---------------------------------------------
#
# El número que contesta "¿estoy haciendo algo o no?". Es lo único de la app que
# mide el trabajo de la persona y no el del sistema, y por eso va grande y arriba
# de la lista: los otros contadores dicen cuántas ofertas hay, éste dice cuántas
# veces te postulaste.

#: Los períodos del selector, en días. `0` es "desde que empezaste".
PERIODOS = (
    ("7d", "Últimos 7 días", 7),
    ("14d", "Últimas 2 semanas", 14),
    ("30d", "Último mes", 30),
    ("60d", "Últimos 2 meses", 60),
    ("90d", "Últimos 3 meses", 90),
    ("todo", "Desde que empecé", 0),
)

PERIODO_POR_DEFECTO = "30d"


def _dia_local(marca) -> date | None:
    """El día local de una marca de tiempo guardada en UTC.

    Igual que en la tarjeta: hay que pasar a la hora de acá **antes** de quedarse
    con el día, porque entre las 21:00 y la medianoche el UTC ya es de mañana y
    una postulación de hoy contaría para el día siguiente.
    """
    crudo = str(marca or "").strip()
    if not crudo:
        return None
    try:
        momento = datetime.fromisoformat(crudo.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (momento.astimezone().date() if momento.tzinfo else momento.date())


def _dias_del_periodo(periodo: str) -> int:
    return dict((clave, dias) for clave, _, dias in PERIODOS).get(periodo, 30)


def aplicadas_en(nombre_perfil: str, periodo: str = PERIODO_POR_DEFECTO,
                 solo_de_la_lista: bool = False) -> dict:
    """Cuántas postulaciones en ese período, y cómo se repartieron en el tiempo.

    {cuantas, a_mano, periodo, etiqueta, reparto: [(etiqueta, cuantas)],
     unidad, desde}

    El `reparto` es lo que hace que el número signifique algo: 12 postulaciones
    en un mes puede ser tres semanas sin hacer nada y una a los tiros, y eso es
    exactamente lo que conviene ver.

    La `unidad` es "día" para el período de una semana y "semana" para los
    demás: con siete días, repartir por semana da una barra sola, que no compara
    con nada.

    Con `solo_de_la_lista` quedan afuera las que se contaron a mano desde un
    posteo de LinkedIn. Es lo que se muestra parado en la pestaña **Apliqué**:
    ahí la lista de abajo son las ofertas marcadas una por una, y un número de
    arriba más grande que la lista de abajo se lee como un error.
    """
    from vacantia.ui import linkedin_urls

    if periodo not in dict((c, e) for c, e, _ in PERIODOS):
        periodo = PERIODO_POR_DEFECTO
    dias = _dias_del_periodo(periodo)
    hoy = date.today()
    desde = hoy - timedelta(days=dias - 1) if dias else None

    fechas: list[date] = []
    for h in State(nombre_perfil).load_history():
        if h.get("aplicado") is not True:
            continue
        cuando = _dia_local(h.get("fecha_feedback"))
        if cuando is None or (desde is not None and cuando < desde):
            continue
        fechas.append(cuando)

    # Y las que se aplicaron desde un posteo de LinkedIn, que no pasaron por
    # ninguna oferta de la lista y por lo tanto no están en el historial. Se
    # cuentan aparte para poder decirlo en la pantalla: si el total sube y no
    # hay ninguna tarjeta marcada, hay que poder explicar de dónde salió.
    a_mano = 0
    for marca in linkedin_urls.postulaciones(nombre_perfil):
        cuando = _dia_local(marca)
        if cuando is None or (desde is not None and cuando < desde):
            continue
        a_mano += 1
        if not solo_de_la_lista:
            fechas.append(cuando)
    if solo_de_la_lista:
        a_mano = 0

    # **Una semana se reparte por día, no por semana.** Con el período de 7
    # días el reparto semanal daba una sola barra, y una sola barra no compara
    # nada: la pantalla mostraba el número grande y abajo un vacío. Por día son
    # siete barras y contestan lo que se pregunta en una semana, que es qué días
    # mandaste y cuáles se te fueron en blanco.
    #
    # De 14 días para arriba vuelve a ser por semana: catorce o noventa barras
    # diarias no se leen, y ahí la pregunta ya es otra, la del ritmo.
    if dias and dias <= 7:
        unidad, paso, cuantos = "día", 1, dias
    else:
        unidad, paso = "semana", 7
        # La ventana se corta en semanas cerradas para que las barras sean
        # comparables entre sí: la última siempre está incompleta, pero es la de
        # hoy y se entiende. Sin ventana, se muestran las últimas 12.
        cuantos = max(2, min(12, -(-dias // 7))) if dias else 12

    arranque = hoy - timedelta(days=cuantos * paso - 1)
    reparto = []
    for i in range(cuantos):
        inicio = arranque + timedelta(days=i * paso)
        fin = inicio + timedelta(days=paso - 1)
        cuantas = sum(1 for f in fechas if inicio <= f <= fin)
        reparto.append((f"{inicio.day}/{inicio.month}", cuantas))

    return {
        "cuantas": len(fechas),
        "a_mano": a_mano,
        "periodo": periodo,
        "etiqueta": dict((c, e) for c, e, _ in PERIODOS)[periodo],
        "reparto": reparto,
        "unidad": unidad,
        "desde": desde.isoformat() if desde else "",
    }


def descartadas_en(nombre_perfil: str, periodo: str = PERIODO_POR_DEFECTO) -> dict:
    """Por qué descartaste, en ese período. {cuantas, periodo, etiqueta, motivos}.

    Es el equivalente de `aplicadas_en` para la pestaña **Descarté**, y contesta
    otra pregunta: no cuántas descartaste sino **por qué**. El total solo no
    sirve para nada; lo que sirve es ver que de 78 descartes 46 fueron por
    inglés, porque eso es una perilla de Mi perfil esperando que la muevan.

    Por eso el reparto es por motivo y no por semana: el ritmo importa cuando
    mandás CVs, porque medís tu trabajo. Descartar no es trabajo que quieras
    sostener, y saber que descartaste parejo a lo largo del mes no te dice nada.

    `motivos` viene ordenado de mayor a menor y con las etiquetas ya en
    castellano, listo para el gráfico de barras.
    """
    if periodo not in dict((c, e) for c, e, _ in PERIODOS):
        periodo = PERIODO_POR_DEFECTO
    dias = _dias_del_periodo(periodo)
    desde = date.today() - timedelta(days=dias - 1) if dias else None

    motivos: Counter = Counter()
    for h in State(nombre_perfil).load_history():
        if h.get("aplicado") is not False:
            continue
        # Se filtra por cuándo LA DESCARTASTE, no por cuándo se publicó el
        # aviso: la pregunta es qué venís rechazando últimamente.
        cuando = _dia_local(h.get("fecha_feedback"))
        if desde is not None and (cuando is None or cuando < desde):
            continue
        motivos[clave_de_motivo(h) or "otro"] += 1

    etiquetas = {c: t for c, t, _ in MOTIVOS}
    # "Escrito a mano" y no "Otro": es el descarte que dice algo del puesto, que
    # es justamente el valioso, y llamarlo "otro" lo manda al cajón de sobras.
    etiquetas["otro"] = "Escrito a mano"
    filas = [(etiquetas.get(clave, clave), cuantas)
             for clave, cuantas in motivos.most_common()]

    return {
        "cuantas": sum(motivos.values()),
        "periodo": periodo,
        "etiqueta": dict((c, e) for c, e, _ in PERIODOS)[periodo],
        "motivos": filas,
        "desde": desde.isoformat() if desde else "",
    }


#: Cuántos días muestra el gráfico de Cómo viene funcionando. Dos semanas: con
#: una sola, un fin de semana tranquilo parece una rotura.
DIAS_DE_ENTRADAS = 14


def entradas_por_dia(nombre_perfil: str, dias: int = DIAS_DE_ENTRADAS) -> list[dict]:
    """Cuántas ofertas nuevas entraron cada día, de la más vieja a hoy.

    Es el gráfico de Cómo viene funcionando, y contesta la pregunta de esa
    sección mejor que la tabla de la última búsqueda: una búsqueda en cero puede
    ser un mal día, varios días seguidos en cero es que algo dejó de andar.

    **Sale del historial y no del registro.** El registro rota a mano y lo
    comparten todos los perfiles y los tests: el 13/9/2026 tenía una sola
    corrida real y media docena de corridas de juguete del perfil "test". El
    historial es por perfil, es el archivo durable, y `found_at` es exactamente
    cuándo entró cada oferta.

    Los días sin nada van igual, con valor cero: acá el cero es el dato.
    """
    hoy = date.today()
    arranque = hoy - timedelta(days=dias - 1)
    cuantas: Counter = Counter()
    for h in State(nombre_perfil).load_history():
        dia = _dia_local(h.get("found_at"))
        if dia is not None and arranque <= dia <= hoy:
            cuantas[dia] += 1
    return [{"etiqueta": f"{d.day}/{d.month}", "cuantas": cuantas[d]}
            for d in (arranque + timedelta(days=i) for i in range(dias))]


# --- qué te están pidiendo -------------------------------------------------
#
# La lista de habilidades sale del campo `stack`, que el modelo ya venía
# devolviendo por cada oferta cuando la puntúa. **No cuesta ninguna llamada
# extra**: ya le estamos pasando el aviso entero para que lo puntúe, y pedirle
# de paso qué piden son unos pocos tokens más de respuesta.
#
# Eso es también lo que la hace servir para cualquier oficio. No hay ninguna
# lista de tecnologías escrita en el código, que es lo que habría que mantener
# para siempre y aun así nunca cubriría marketing ni seguridad e higiene. El
# modelo lee el aviso y devuelve lo que ese aviso pide, sea LangChain, Google
# Analytics o la ISO 45001.

#: Con qué se corta un `stack` en habilidades sueltas. La barra está porque el
#: modelo agrupa alternativas ("AWS/Azure/GCP" es una sola entrada suya y son
#: tres cosas distintas para contar), y el punto y coma porque a veces cambia de
#: separador a mitad de la lista.
_CORTES = re.compile(r"[,;/|]| \+ |\band\b|\bo\b|\by\b", re.I)

#: Lo que no es una habilidad aunque venga en la lista. Son las muletillas con
#: las que el modelo rellena cuando el aviso no dice nada concreto: no nombran
#: nada que se pueda ir a aprender, que es para lo que sirve este gráfico.
_NO_ES_HABILIDAD = frozenset({
    "", "n/a", "na", "none", "null", "-", "?", "varios", "otros", "etc",
    "no especificado", "not specified", "unknown", "experiencia", "experience",
    "conocimientos", "skills", "habilidades", "tecnologias", "tecnologías",
})

#: Cuántas habilidades distintas se muestran. Con más, el gráfico deja de ser un
#: "qué me piden" y pasa a ser un inventario: la cola larga son las que
#: aparecieron una sola vez, y una sola vez no es una tendencia.
TOPE_HABILIDADES = 15


def _habilidades_de(texto: str) -> list[str]:
    """Un campo `stack` cortado en habilidades sueltas, sin normalizar todavía."""
    salida = []
    for parte in _CORTES.split(texto or ""):
        limpia = " ".join(parte.split()).strip(" .-•·")
        if limpia.lower() in _NO_ES_HABILIDAD:
            continue
        # Una "habilidad" de 40 caracteres es una frase que el modelo metió
        # donde iba un nombre; contarla ensucia el gráfico con una barra única.
        if 1 < len(limpia) <= 32:
            salida.append(limpia)
    return salida


def _mismo_nombre(conteo: Counter) -> dict[str, str]:
    """Qué escrituras distintas son en realidad la misma habilidad.

    Devuelve {como vino: nombre canónico}. Resuelve dos cosas y **sólo** dos, a
    propósito: mezclar de más es peor que no mezclar, porque inventa una
    tendencia que no existe.

    1. **Mayúsculas.** "python" y "Python" son la misma. Gana la escritura más
       frecuente, que es la que usa el mercado: así sale "PostgreSQL" y no
       "postgresql", sin tener una tabla de nombres propios.
    2. **Plurales, pero sólo cuando las dos formas aparecen de verdad.** "LLMs"
       se une a "LLM" porque en los avisos están las dos. "Kubernetes" y
       "Analytics" no se tocan, porque el singular no existe en ningún lado.
       Es lo que hace que esto ande igual en marketing o en seguridad e higiene
       sin saber nada del rubro: la regla la ponen los datos, no una lista.
    """
    # Paso 1: agrupar por minúsculas y quedarse con la escritura más usada.
    por_minuscula: dict[str, Counter] = {}
    for nombre, cuantas in conteo.items():
        por_minuscula.setdefault(nombre.lower(), Counter())[nombre] += cuantas
    canonico = {clave: variantes.most_common(1)[0][0]
                for clave, variantes in por_minuscula.items()}

    # Paso 2: el plural cae en el singular, si el singular existe en los datos.
    for clave in list(canonico):
        singular = clave[:-1] if clave.endswith("s") else ""
        if singular and singular in canonico:
            canonico[clave] = canonico[singular]

    return {nombre: canonico[nombre.lower()] for nombre in conteo}


def habilidades_pedidas(nombre_perfil: str, desde: str = "todo",
                        tope: int = TOPE_HABILIDADES) -> dict:
    """Qué piden los avisos que entraron. {cuantas, ofertas, filas, sin_datos}.

    `filas` es [(habilidad, en cuántas ofertas)] de mayor a menor, lista para el
    gráfico de barras. `sin_datos` son las ofertas que todavía no pasaron por el
    modelo y por lo tanto no tienen nada que aportar: se dice en pantalla, para
    que un número bajo no se lea como "nadie pide nada".

    Se cuenta **una vez por oferta**: si un aviso nombra Python cuatro veces,
    sigue siendo un solo trabajo que pide Python. Lo que contesta el gráfico es
    en cuántas búsquedas te lo van a pedir, no cuánto insisten.

    Son dos pasadas y tienen que ser dos: primero se ve qué nombres hay para
    poder unificarlos, y recién después se cuenta. Al revés, un aviso que dice
    "Python, python" cuenta dos.
    """
    historial = [h for h in State(nombre_perfil).load_history()
                 if _entra_por_fecha(h, desde)]

    # Primera pasada: qué nombres aparecen y con qué frecuencia. Es lo que
    # necesita `_mismo_nombre` para decidir cuál escritura gana y qué plurales
    # tienen singular de verdad.
    por_oferta: list[list[str]] = []
    crudo: Counter = Counter()
    for h in historial:
        habilidades = _habilidades_de(h.get("stack") or "")
        if not habilidades:
            continue
        por_oferta.append(habilidades)
        crudo.update(habilidades)

    canonico = _mismo_nombre(crudo)

    # Segunda pasada: recién ACÁ se cuenta, y se cuenta una vez por oferta.
    #
    # El orden importa y fue un bug: deduplicando antes de unificar los nombres,
    # un aviso que decía "Python, python" contaba dos, y uno que decía "LLM" y
    # "LLMs" también. Son un solo trabajo pidiendo una sola cosa. Unificar
    # primero y deduplicar después es lo que lo arregla de raíz.
    unidas: Counter = Counter()
    for habilidades in por_oferta:
        unidas.update({canonico[n] for n in habilidades})

    return {
        "filas": unidas.most_common(tope),
        "distintas": len(unidas),
        "ofertas": len(por_oferta),
        "sin_datos": len(historial) - len(por_oferta),
    }


#: Los tramos del histograma de puntajes. Son los que usa la persona para
#: decidir: 0 es "esto no es para vos", y de `min_score` para arriba es lo que
#: el sistema considera digno de avisar por Telegram.
TRAMOS_PUNTAJE = ((0, 0), (1, 19), (20, 39), (40, 59), (60, 79), (80, 100))


def distribucion_de_puntajes(nombre_perfil: str) -> list[dict]:
    """Cuántas ofertas hay en cada tramo de puntaje.

    Es el gráfico que contesta "¿el sistema me está trayendo cosas buenas?" sin
    tener que abrir la lista. Una montaña pegada al cero significa que las
    búsquedas están mal apuntadas; una repartida significa que el problema es
    otro.
    """
    historial = State(nombre_perfil).load_history()
    try:
        minimo = int(leer_perfil(nombre_perfil).get("min_score", 60) or 0)
    except (FileNotFoundError, json.JSONDecodeError):
        minimo = 60

    salida = []
    for desde_p, hasta_p in TRAMOS_PUNTAJE:
        cuantas = sum(1 for h in historial
                      if h.get("score") is not None
                      and desde_p <= h["score"] <= hasta_p)
        salida.append({
            "etiqueta": "0" if hasta_p == 0 else f"{desde_p} a {hasta_p}",
            "cuantas": cuantas,
            # De acá para arriba el sistema te avisa. Es el único tramo que
            # lleva color de estado, y lo lleva porque significa algo.
            "avisa": desde_p >= minimo,
        })
    return salida
