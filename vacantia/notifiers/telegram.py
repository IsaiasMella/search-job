"""Notificador de Telegram. Adaptado de autopilot-jobhunt/job_hunt/notifier.py."""

from vacantia.config import resolve_secret
from vacantia.log import get_logger
from vacantia.models import Job
from vacantia.notifiers.base import Notifier

logger = get_logger()

TELEGRAM_MAX_CHARS = 4096


def send_telegram(bot_token: str, chat_id: str, message: str) -> bool:
    """Envía un mensaje HTML a un chat de Telegram. No levanta: devuelve bool."""
    import requests

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            logger.info("Telegram enviado.")
            return True
        logger.error(f"Telegram falló: HTTP {resp.status_code} — {resp.text[:200]}")
        return False
    except Exception as e:
        logger.error(f"Error de Telegram: {e}")
        return False


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_message(jobs: list[Job], header: str) -> str:
    lines = [f"<b>{_escape(header)}</b>", f"<i>{len(jobs)} coincidencia(s)</i>\n"]
    for i, job in enumerate(jobs, 1):
        score = job.score if job.score is not None else "?"
        lines.append(
            f"<b>#{i}</b> [{score}] {_escape(job.company or '?')} — "
            f"{_escape(job.display_title)}\n"
            f"📍 {_escape(job.display_location)}\n"
            + (f"🔧 {_escape(job.stack)}\n" if job.stack else "")
            + (f"✅ {_escape(job.reason)}\n" if job.reason else "")
            + f'<a href="{_escape(job.url)}">Ver oferta</a>\n'
        )
    return "\n".join(lines)


def _split_chunks(text: str, limit: int = TELEGRAM_MAX_CHARS) -> list[str]:
    """Parte por bloques de oferta para no cortar una etiqueta HTML al medio."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for block in text.split("\n\n"):
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) > limit and current:
            chunks.append(current)
            current = block
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


class TelegramNotifier(Notifier):
    name = "telegram"

    def __init__(self, config: dict, profile: dict):
        super().__init__(config, profile)
        self.token = resolve_secret(config.get("token"), config.get("token_env", "TELEGRAM_TOKEN"))
        self.chat_id = resolve_secret(
            config.get("chat_id"), config.get("chat_id_env", "TELEGRAM_CHAT_ID")
        )

    def is_available(self) -> tuple[bool, str]:
        if not self.token or not self.chat_id:
            return False, "faltan TELEGRAM_TOKEN y/o TELEGRAM_CHAT_ID"
        try:
            import requests  # noqa: F401
        except ImportError:
            return False, "falta el paquete 'requests' (pip install requests)"
        return True, ""

    def send(self, jobs: list[Job]) -> bool:
        header = self.config.get("header") or f"Vacantia — {self.profile.get('name', '')}".strip()
        if not jobs:
            return send_telegram(self.token, self.chat_id, f"<b>{_escape(header)}</b>\nSin novedades hoy.")

        ok = True
        for chunk in _split_chunks(format_message(jobs, header)):
            ok = send_telegram(self.token, self.chat_id, chunk) and ok
        return ok
