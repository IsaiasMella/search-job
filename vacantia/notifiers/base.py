"""Interfaz Notifier: todo canal de salida implementa esto y nada más."""

from abc import ABC, abstractmethod

from vacantia.models import Job


class Notifier(ABC):
    #: Identificador que va en el campo "type" del perfil.
    name: str = "notifier"

    def __init__(self, config: dict, profile: dict):
        self.config = config      # el bloque de este notificador en el perfil
        self.profile = profile    # el perfil completo

    def is_available(self) -> tuple[bool, str]:
        """(disponible, motivo). Si es False el motor lo saltea sin fallar."""
        return True, ""

    @abstractmethod
    def send(self, jobs: list[Job], notes: list[str] | None = None) -> bool:
        """Entrega las ofertas ya filtradas. Devuelve True si salió bien."""
        raise NotImplementedError
