"""Interfaz Source: todo lo que trae ofertas implementa esto y nada más."""

from abc import ABC, abstractmethod

from vacantia.models import Job


class Source(ABC):
    #: Identificador que va en `Job.source` y en el campo "type" del perfil.
    name: str = "source"

    #: Cuántos días para atrás busca esta fuente si nadie dice otra cosa.
    #: `0` = sin ventana. Cada fuente lo pisa según lo que sabe de sí misma:
    #: `rrhh` usa 30 porque sigue a una persona puntual que puede pasarse tres
    #: semanas sin publicar, y no "lo que haya".
    max_age_days_default: int = 7

    def __init__(self, config: dict, profile: dict):
        self.config = config      # el bloque de esta fuente dentro del perfil
        self.profile = profile    # el perfil completo (keywords, candidate, ...)
        self.max_age_days = self._resolver_antiguedad()

    def _resolver_antiguedad(self) -> int:
        """Los días de antigüedad que acepta esta fuente, en orden de prioridad.

        La perilla que importa es **una sola y es de la persona**, no de cada
        fuente: para un AI Engineer una búsqueda de hace 7 días ya está cubierta
        de postulantes, y para un supervisor de seguridad e higiene en el campo
        una de hace un mes sigue viva. Es la misma diferencia entre dos perfiles
        de esta misma casa, y tenerla repartida en seis bloques de fuente
        garantizaba que quedaran desincronizados.

        Por eso:

        1. `max_age_days` en el bloque de la fuente, si está. Es el escape para
           el caso puntual, no lo que se espera que se toque.
        2. `filters.max_age_days` del perfil: **ésta es la que se configura**,
           una vez, desde *Mis datos*.
        3. El default de la fuente.

        `0` en cualquiera de los dos primeros apaga la ventana a propósito, y
        por eso se chequea contra `None` y no por verdadero/falso: `0` es un
        valor válido, no "no configurado".
        """
        propio = self.config.get("max_age_days")
        if propio is not None:
            return max(0, int(propio))
        del_perfil = (self.profile.get("filters") or {}).get("max_age_days")
        if del_perfil is not None:
            return max(0, int(del_perfil))
        return self.max_age_days_default

    def is_available(self) -> tuple[bool, str]:
        """(disponible, motivo). Si es False el motor la saltea sin fallar."""
        return True, ""

    @abstractmethod
    def fetch(self) -> list[Job]:
        """Devuelve ofertas normalizadas. No deduplica ni puntúa: eso es del motor."""
        raise NotImplementedError
