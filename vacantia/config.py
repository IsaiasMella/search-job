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
        "gemini_model": llm.get("model") or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash-lite",
        "gemini_fallback_models": llm.get("fallback_models") or [],
    }


def load_resume(profile: dict) -> str:
    cv_path = Path(profile.get("cv_path") or "resume/YOUR_CV.md")
    if not cv_path.exists():
        logger.warning(f"No encontré el CV en {cv_path} — el scoring va a andar a ciegas.")
        return ""
    text = cv_path.read_text(encoding="utf-8")
    logger.debug(f"CV cargado: {cv_path} ({len(text)} chars)")
    return text
