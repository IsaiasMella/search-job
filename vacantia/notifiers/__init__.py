"""Registro de notificadores enchufables.

Para agregar un canal nuevo: implementá Notifier en un módulo de esta carpeta
y registralo en NOTIFIER_REGISTRY. El perfil lo activa en su campo "notifiers".
"""

from vacantia.log import get_logger
from vacantia.notifiers.base import Notifier
from vacantia.notifiers.console import ConsoleNotifier
from vacantia.notifiers.telegram import TelegramNotifier

logger = get_logger()

NOTIFIER_REGISTRY: dict[str, type[Notifier]] = {
    TelegramNotifier.name: TelegramNotifier,
    ConsoleNotifier.name: ConsoleNotifier,
    # TODO(próximas fases): "email" -> EmailNotifier, "whatsapp" -> WhatsAppNotifier
}


def build_notifiers(profile: dict) -> list[Notifier]:
    """Instancia los notificadores activos del perfil. Ignora los desconocidos."""
    built: list[Notifier] = []
    for entry in profile.get("notifiers", []):
        if not entry.get("enabled", True):
            continue
        ntype = entry.get("type")
        cls = NOTIFIER_REGISTRY.get(ntype)
        if cls is None:
            logger.warning(f"Notificador desconocido en el perfil: '{ntype}' — lo salteo")
            continue
        built.append(cls(entry, profile))
    return built


__all__ = [
    "Notifier",
    "TelegramNotifier",
    "ConsoleNotifier",
    "NOTIFIER_REGISTRY",
    "build_notifiers",
]
