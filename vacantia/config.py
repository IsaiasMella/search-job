"""Carga de perfiles. Cada persona es un JSON en profiles/<nombre>.json.

Regla de precedencia para secretos (misma idea que el .env + config.json de
autopilot-jobhunt, pero por perfil):

  1. Valor literal en el JSON del perfil, si no es un placeholder.
  2. "${NOMBRE_DE_VAR}" en el JSON → se lee esa variable de entorno.
  3. Vacío o placeholder → se lee la variable de entorno por defecto del campo.

Así el perfil se puede versionar sin secretos adentro, pero admite pegarlos
directo si a alguien le resulta más cómodo.
"""

import json
import os
import re
import unicodedata
from pathlib import Path

from vacantia.log import get_logger

logger = get_logger()

PROFILES_DIR = Path("profiles")

_ENV_REF_RE = re.compile(r"^\$\{?([A-Z0-9_]+)\}?$")


# Moldes que trae .env.example sin completar. Si no se reconocen, el motor cree
# que hay credencial y falla recién al llamar a la API, en vez de avisar que
# falta y seguir degradado. Van en inglés y en español porque el .env.example
# del repo está en español ("tu_openrouter_api_key_aca").
_PLACEHOLDER_MARKS = (
    "your_",
    "tu_",
    "pegala",
    "pegar",
    "_here",
    "_aca",
    "_aquí",
    "_aqui",
    "xxx",
    "<",
)


def is_placeholder(val: object) -> bool:
    if not isinstance(val, str) or not val.strip():
        return True
    v = val.strip().lower()
    return any(mark in v for mark in _PLACEHOLDER_MARKS)


def resolve_secret(value: object, env_var: str | None = None) -> str:
    """Devuelve el secreto ya resuelto, o "" si no hay ninguno usable."""
    if isinstance(value, str):
        m = _ENV_REF_RE.match(value.strip())
        if m:
            # El .env puede tener el molde sin completar: se filtra igual que un
            # literal, si no el motor cree que hay credencial y falla recién al
            # llamar a la API en vez de avisar que falta.
            env_val = (os.getenv(m.group(1)) or "").strip()
            return "" if is_placeholder(env_val) else env_val
        if not is_placeholder(value):
            return value.strip()
    if env_var:
        env_val = os.getenv(env_var, "")
        return "" if is_placeholder(env_val) else env_val.strip()
    return ""


def _load_dotenv() -> None:
    """Carga .env si python-dotenv está disponible; si no, parser mínimo."""
    env_path = Path(".env")
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=env_path, override=False)
        return
    except ImportError:
        pass
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def profile_path(name: str) -> Path:
    """Acepta 'isaias', 'isaias.json' o una ruta completa."""
    p = Path(name)
    if p.suffix == ".json" and p.exists():
        return p
    candidate = PROFILES_DIR / (name if name.endswith(".json") else f"{name}.json")
    return candidate


def available_profiles() -> list[str]:
    if not PROFILES_DIR.exists():
        return []
    return sorted(p.stem for p in PROFILES_DIR.glob("*.json"))


def load_profile(name: str) -> dict:
    _load_dotenv()

    path = profile_path(name)
    if not path.exists():
        found = available_profiles()
        raise FileNotFoundError(
            f"No existe el perfil '{name}' ({path}).\n"
            + (f"Perfiles disponibles: {', '.join(found)}" if found else
               "Copiá profiles/example.json a profiles/<tu_nombre>.json para empezar.")
        )

    profile = json.loads(path.read_text(encoding="utf-8"))
    profile.setdefault("name", path.stem)
    profile.setdefault("min_score", 60)
    profile.setdefault("top_n", 5)
    profile.setdefault("keywords", [])
    profile.setdefault("sources", [])
    profile.setdefault("notifiers", [])
    profile["llm"] = _build_llm_config(profile.get("llm", {}))
    profile["_path"] = str(path)
    logger.debug(f"Perfil cargado: {path}")
    return profile


def _build_llm_config(llm: dict) -> dict:
    """Traduce el bloque `llm` del perfil al dict que espera vacantia.llm."""
    return {
        "llm_provider": llm.get("provider") or os.getenv("LLM_PROVIDER") or "openrouter",
        "openrouter_api_key": resolve_secret(llm.get("openrouter_api_key"), "OPENROUTER_API_KEY"),
        "openrouter_model": llm.get("model") or os.getenv("OPENROUTER_MODEL")
        or "meta-llama/llama-3.3-70b-instruct:free",
        "openrouter_fallback_models": llm.get("fallback_models")
        or [m.strip() for m in (os.getenv("OPENROUTER_FALLBACK_MODELS") or "").split(",") if m.strip()],
        "anthropic_api_key": resolve_secret(llm.get("anthropic_api_key"), "ANTHROPIC_API_KEY"),
        "anthropic_model": llm.get("anthropic_model") or "claude-haiku-4-5-20251001",
        "claude_cli_model": llm.get("claude_cli_model") or os.getenv("CLAUDE_CLI_MODEL") or "",
        "gemini_api_key": resolve_secret(llm.get("gemini_api_key"), "GEMINI_API_KEY"),
        # Con provider="gemini", el campo "model" del perfil es el modelo de
        # Gemini. Se lee de ahí para que el perfil tenga una sola forma de
        # nombrar el modelo, sea cual sea el proveedor.
        "gemini_model": llm.get("model") or os.getenv("GEMINI_MODEL") or "gemini-3.5-flash-lite",
        "gemini_fallback_models": llm.get("fallback_models") or [],
    }


# --- los CV del perfil --------------------------------------------------------
#
# Una persona puede postularse con más de un perfil profesional: AI Engineer y
# Full Stack, o dos variantes de QHSE. Por eso el perfil tiene una lista `cvs`,
# y cada uno trae su nombre, su archivo y sus propias palabras de búsqueda.
#
# **Un perfil viejo, con sólo `cv_path`, sigue andando igual**: se lo lee como un
# único CV llamado "principal". Nada se migra en disco; la lista se arma al leer.

def id_de_cv(nombre: str) -> str:
    """El identificador estable de un CV, sacado de su nombre.

    Minúsculas, sin tildes y con guiones: "Full Stack" -> "full-stack". Es lo
    que se guarda en cada oferta, así que no puede depender de cómo se escribe
    el nombre que se muestra.
    """
    plano = unicodedata.normalize("NFKD", str(nombre or "")).encode("ascii", "ignore")
    return re.sub(r"[^a-z0-9]+", "-", plano.decode().lower()).strip("-") or "cv"


def cvs_del_perfil(profile: dict) -> list[dict]:
    """Los CV del perfil, sin leer los archivos: [{id, nombre, path, palabras_clave}].

    Siempre devuelve al menos uno. Un perfil sin `cvs` (o con la lista vacía o
    rota) se lee como un único CV con el `cv_path` de siempre.
    """
    salida, vistos = [], set()
    for crudo in profile.get("cvs") or []:
        if not isinstance(crudo, dict) or not str(crudo.get("path") or "").strip():
            continue
        nombre = str(crudo.get("nombre") or "").strip() or "CV"
        cv_id = id_de_cv(crudo.get("id") or nombre)
        if cv_id in vistos:
            continue
        vistos.add(cv_id)
        palabras = crudo.get("palabras_clave") or []
        salida.append({
            "id": cv_id,
            "nombre": nombre,
            "path": str(crudo["path"]).strip(),
            "palabras_clave": [str(p).strip() for p in palabras if str(p).strip()],
        })
    if salida:
        return salida

    nombre = str((profile.get("candidate") or {}).get("headline") or "").strip()
    return [{
        "id": "principal",
        "nombre": nombre or "Principal",
        "path": profile.get("cv_path") or "resume/YOUR_CV.md",
        "palabras_clave": [],
    }]


def load_resumes(profile: dict) -> list[dict]:
    """Los CV del perfil con su texto: [{id, nombre, path, palabras_clave, texto}].

    Un CV cuyo archivo no está vuelve con texto vacío y un aviso en el registro:
    que falte uno no tiene que dejar sin puntuar contra los demás.
    """
    salida = []
    for cv in cvs_del_perfil(profile):
        ruta = Path(cv["path"])
        if not ruta.exists():
            logger.warning(f"No encontré el CV '{cv['nombre']}' en {ruta} — "
                           "el scoring va a andar a ciegas con ése.")
            texto = ""
        else:
            texto = ruta.read_text(encoding="utf-8")
            logger.debug(f"CV cargado: {cv['nombre']} {ruta} ({len(texto)} chars)")
        salida.append({**cv, "texto": texto})
    return salida


def cvs_con_texto(profile: dict) -> list[dict]:
    """Los CV que tienen algo escrito. Si ninguno tiene, el primero igual.

    "Agregar otro CV" crea uno vacío para que la persona lo complete. Mientras
    está vacío no puede contar como opción: el perfil pasaría a tener "varios
    CV", y todas las tarjetas mostrarían una recomendación contra un CV que
    no dice nada.
    """
    cvs = load_resumes(profile)
    return [cv for cv in cvs if cv["texto"].strip()] or cvs[:1]


def load_resume(profile: dict) -> str:
    """El texto del primer CV. Para quien todavía trabaja con uno solo."""
    return load_resumes(profile)[0]["texto"]


def terminos_de_busqueda(profile: dict, propios=None) -> list[str]:
    """Qué buscar en los portales: los términos de la fuente, más los de cada CV.

    `propios` son los `search_terms` (o `roles`) de la fuente. Si no tiene, se
    usan las palabras clave del perfil. **A eso se le suman siempre las
    palabras clave de todos los CV**, y es la razón de que exista este helper:
    las fuentes con términos propios ignoraban `profile.keywords`, así que
    cargar un CV de Full Stack no hacía salir a buscar ni una sola oferta de
    Full Stack.

    Sin duplicados y sin distinguir mayúsculas, respetando el orden: primero lo
    de la fuente, después lo de cada CV. Las fuentes ya rotan los términos por
    día con un tope por corrida, así que sumar términos reparte la cobertura
    entre días y no multiplica los pedidos.
    """
    base = propios if propios else (profile.get("keywords") or [])
    candidatos = list(base)
    for cv in cvs_del_perfil(profile):
        candidatos.extend(cv["palabras_clave"])

    salida, vistos = [], set()
    for termino in candidatos:
        limpio = str(termino).strip()
        if limpio and limpio.lower() not in vistos:
            vistos.add(limpio.lower())
            salida.append(limpio)
    return salida
