"""Wrapper de LLM con fallback en cadena de modelos de OpenRouter.

Adaptado de autopilot-jobhunt/job_hunt/llm_utils.py. El import de `openai` es
perezoso para que el motor se pueda importar (y correr con scoring heurístico)
en una máquina sin las dependencias del proveedor instaladas.
"""

import json
import os
import subprocess
import time
from typing import Any, cast

from vacantia.log import get_logger

logger = get_logger()

# Timeout por request (segundos) para proveedores HTTP. Sin esto los SDK de
# openai/anthropic usan 600s por defecto, así que un solo modelo free-tier
# colgado congela la corrida 10 minutos. claude_cli tiene su propio timeout.
_LLM_REQUEST_TIMEOUT = 120.0


# Gemini expone un endpoint compatible con la API de OpenAI, así que se usa el
# mismo cliente y la misma cadena de fallback que OpenRouter — no hace falta el
# SDK de Google. https://ai.google.dev/gemini-api/docs/openai
_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def _key(config: dict, field: str, env_var: str) -> str:
    """Credencial ya resuelta, o del entorno como red — filtrando moldes.

    El `or os.getenv(...)` pelado dejaba pasar el molde sin completar que trae
    .env.example, y entonces el motor creía tener credencial y fallaba recién
    al llamar a la API en vez de avisar y caer a la heurística.
    """
    from vacantia.config import is_placeholder

    value = (config.get(field) or "").strip()
    if not value:
        value = (os.getenv(env_var) or "").strip()
    return "" if is_placeholder(value) else value


def has_llm_credentials(config: dict) -> bool:
    """¿Hay con qué llamar a un LLM? Si no, el scoring cae a la heurística."""
    provider = config.get("llm_provider") or "openrouter"
    if provider == "claude_cli":
        return True  # usa el login local de Claude Code, no necesita API key
    if provider == "anthropic":
        return bool(_key(config, "anthropic_api_key", "ANTHROPIC_API_KEY"))
    if provider == "gemini":
        return bool(_key(config, "gemini_api_key", "GEMINI_API_KEY"))
    return bool(_key(config, "openrouter_api_key", "OPENROUTER_API_KEY"))


def _make_openrouter_client(config: dict):
    from openai import OpenAI

    return OpenAI(
        api_key=config.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        timeout=_LLM_REQUEST_TIMEOUT,
    )


def _make_gemini_client(config: dict):
    from openai import OpenAI

    return OpenAI(
        api_key=config.get("gemini_api_key") or os.getenv("GEMINI_API_KEY"),
        base_url=_GEMINI_BASE_URL,
        timeout=_LLM_REQUEST_TIMEOUT,
    )


def _chat_with_anthropic(config: dict, messages: list[dict], temperature: float, max_tokens: int) -> str:
    try:
        import anthropic
    except ImportError:
        raise ImportError("Ejecutá: pip install anthropic")
    api_key = config.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")
    model = config.get("anthropic_model", "claude-haiku-4-5-20251001")
    logger.debug(f"LLM call → Anthropic / {model}")
    t0 = time.time()
    client = anthropic.Anthropic(api_key=api_key, timeout=_LLM_REQUEST_TIMEOUT)
    system = next((m["content"] for m in messages if m["role"] == "system"), None)
    user_msgs = [m for m in messages if m["role"] != "system"]
    kwargs: dict = {
        "model": model,
        "messages": user_msgs,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if system:
        kwargs["system"] = system
    r = client.messages.create(**kwargs)
    elapsed = time.time() - t0
    text = r.content[0].text
    logger.debug(
        f"LLM response: {len(text)} chars in {elapsed:.1f}s "
        f"(in={r.usage.input_tokens} out={r.usage.output_tokens} tokens)"
    )
    return text


def _chat_with_claude_cli(config: dict, messages: list[dict], temperature: float, max_tokens: int) -> str:
    model = config.get("claude_cli_model", "")
    logger.debug(f"LLM call → Claude CLI{' / ' + model if model else ''}")
    t0 = time.time()

    system = next((m["content"] for m in messages if m["role"] == "system"), None)
    user_msgs = [m for m in messages if m["role"] != "system"]
    prompt_text = "\n\n".join(f"{m['role'].upper()}:\n{m['content']}" for m in user_msgs)

    # --strict-mcp-config apaga todos los MCP servers en el subproceso
    cmd = [
        "claude", "--print", "--output-format", "json", "--tools", "",
        "--mcp-config", '{"mcpServers":{}}', "--strict-mcp-config",
        "--disable-slash-commands",
    ]
    if system:
        cmd += ["--system-prompt", system]
    if model:
        cmd += ["--model", model]

    try:
        result = subprocess.run(
            cmd, input=prompt_text, capture_output=True, text=True, timeout=300
        )
    except FileNotFoundError:
        raise RuntimeError(
            "No se encontró el binario 'claude' en el PATH.\n"
            "Instalá Claude Code desde https://claude.ai/code y corré 'claude auth login'."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("claude CLI timeout a los 300s.")

    if result.returncode != 0:
        raise RuntimeError(f"claude CLI salió con {result.returncode}: {result.stderr.strip()}")

    try:
        data = json.loads(result.stdout)
        if isinstance(data, dict):
            text = data.get("result")
            if text is None:
                raise KeyError("no hay campo 'result' en la salida")
        elif isinstance(data, list):
            result_event = next(
                (e for e in data if isinstance(e, dict) and e.get("type") == "result"), None
            )
            if result_event is None:
                raise KeyError("no hay evento 'result' en la salida")
            text = result_event["result"]
        else:
            raise TypeError(f"tipo de salida inesperado: {type(data)}")
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
        raise RuntimeError(f"salida inesperada de claude CLI ({e}): {result.stdout[:200]}")

    elapsed = time.time() - t0
    logger.debug(f"LLM response: {len(text)} chars in {elapsed:.1f}s via claude CLI")
    return text


def chat_with_llm(
    config: dict,
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    provider = config.get("llm_provider")
    if provider == "anthropic":
        return _chat_with_anthropic(config, messages, temperature, max_tokens)
    if provider == "claude_cli":
        return _chat_with_claude_cli(config, messages, temperature, max_tokens)

    if provider == "gemini":
        client = _make_gemini_client(config)
        primary = config.get("gemini_model") or "gemini-2.5-flash-lite"
        fallbacks = config.get("gemini_fallback_models") or []
    else:
        client = _make_openrouter_client(config)
        primary = config.get("openrouter_model") or "nvidia/nemotron-3-super-120b-a12b:free"
        fallbacks = config.get("openrouter_fallback_models") or []

    models = [primary] + [m for m in fallbacks if m != primary]
    return chat_with_fallback(client, models, messages, temperature, max_tokens)


def chat_with_fallback(
    llm,
    models: list[str],
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    """Prueba los modelos en orden hasta que uno responda.

    Sirve igual para OpenRouter y para Gemini: los dos hablan el protocolo de
    OpenAI. La cadena cubre dos casos distintos — que un modelo esté caído o
    saturado, y que lo retiren (Gemini 2.5 Flash-Lite se retira el 16/10/2026 y
    ahí el fallback entra solo, sin que haya que tocar nada).
    """
    from openai import RateLimitError

    if not models:
        raise RuntimeError("No hay modelos configurados para el proveedor.")

    for model_idx, model in enumerate(models):
        label = f"[model {model_idx + 1}/{len(models)}] {model}"
        for attempt in range(2):
            try:
                logger.debug(f"LLM call → {label} (intento {attempt + 1})")
                t0 = time.time()
                resp = llm.chat.completions.create(
                    model=model,
                    messages=cast("Any", messages),
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                elapsed = time.time() - t0
                # Un error del proveedor puede volver con HTTP 200 y `choices`
                # en null (visto con OpenRouter al agotarse la cuota diaria).
                # Sin este guardia explota con "'NoneType' object is not
                # subscriptable", que no dice nada de lo que realmente pasó.
                if not getattr(resp, "choices", None):
                    detalle = getattr(resp, "error", None) or "respuesta sin 'choices'"
                    raise RuntimeError(f"{model} no devolvió resultado: {detalle}")
                text = resp.choices[0].message.content or ""
                usage = resp.usage
                if usage:
                    logger.debug(
                        f"LLM response: {len(text)} chars in {elapsed:.1f}s "
                        f"(in={usage.prompt_tokens} out={usage.completion_tokens} tokens) via {model}"
                    )
                else:
                    logger.debug(f"LLM response: {len(text)} chars in {elapsed:.1f}s via {model}")
                return text
            except RateLimitError:
                if attempt == 0:
                    logger.warning(f"Rate-limit en {model} — reintentando en 3s...")
                    time.sleep(3)
                    continue
                logger.warning(f"Rate-limit en {model} (cuota agotada) — probando el siguiente...")
                break
            except Exception as e:
                logger.error(f"Error de LLM ({model}): {e}")
                break

    raise RuntimeError(
        f"Fallaron los {len(models)} modelos configurados ({', '.join(models)}). "
        "Revisá la API key del proveedor y su cuota diaria."
    )
