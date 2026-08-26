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


def has_llm_credentials(config: dict) -> bool:
    """¿Hay con qué llamar a un LLM? Si no, el scoring cae a la heurística."""
    provider = config.get("llm_provider") or "openrouter"
    if provider == "claude_cli":
        return True  # usa el login local de Claude Code, no necesita API key
    if provider == "anthropic":
        return bool(config.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY"))
    return bool(config.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY"))


def _make_openrouter_client(config: dict):
    from openai import OpenAI

    return OpenAI(
        api_key=config.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
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
    return chat_with_fallback(_make_openrouter_client(config), config, messages, temperature, max_tokens)


def chat_with_fallback(
    llm,
    config: dict,
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    from openai import RateLimitError

    primary = config.get("openrouter_model", "meta-llama/llama-3.3-70b-instruct:free")
    fallbacks = config.get("openrouter_fallback_models", [])
    models = [primary] + [m for m in fallbacks if m != primary]

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

    raise RuntimeError("Fallaron todos los modelos. Revisá tu OPENROUTER_API_KEY y la cuota.")
