"""Interfaz Source: todo lo que trae ofertas implementa esto y nada más."""

from abc import ABC, abstractmethod

from vacantia.models import Job


class Source(ABC):
    #: Identificador que va en `Job.source` y en el campo "type" del perfil.
    name: str = "source"

    def __init__(self, config: dict, profile: dict):
        self.config = config      # el bloque de esta fuente dentro del perfil
        self.profile = profile    # el perfil completo (keywords, candidate, ...)

    def is_available(self) -> tuple[bool, str]:
        """(disponible, motivo). Si es False el motor la saltea sin fallar."""
        return True, ""

    @abstractmethod
    def fetch(self) -> list[Job]:
        """Devuelve ofertas normalizadas. No deduplica ni puntúa: eso es del motor."""
        raise NotImplementedError
