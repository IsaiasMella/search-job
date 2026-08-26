"""Modelo normalizado de oferta. Toda fuente devuelve `Job`, nada más."""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class Job:
    # --- Identidad / origen ---
    url: str
    title: str
    company: str = ""
    source: str = ""

    # --- Datos crudos de la fuente ---
    location: str = ""
    region: str = ""
    description: str = ""
    posted_at: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    # --- Campos que completa el scoring (vacíos hasta que corre) ---
    score: int | None = None
    scored_title: str = ""
    stack: str = ""
    location_remote: str = ""
    reason: str = ""
    worth_applying: bool | None = None

    # --- Campos extraídos del aviso, para los filtros (ver filters.py) ---
    # Ojo: `location`/`region` vienen de companies.json y describen a la
    # *empresa*, no al puesto. Globant publica ofertas de Bologna y Pune bajo
    # una entrada que dice "Buenos Aires". Estos campos salen del aviso mismo.
    # "" siempre significa "el aviso no lo dice" y nunca filtra.
    country: str = ""
    city: str = ""
    work_mode: str = ""      # remote | hybrid | onsite | ""
    posting_language: str = ""   # es | en | otro código ISO | ""
    english_level: str = ""      # A1..C2 o "" si no pide inglés / no lo dice
    # Pregunta directa al LLM: ¿puede hacer este trabajo alguien que NO sabe
    # inglés? Es más confiable que deducirlo de english_level, que el modelo
    # deja vacío con frecuencia. None = no se sabe.
    requires_english: bool | None = None

    # --- Trazabilidad ---
    found_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def key(self) -> str:
        """Clave de quitar duplicados. La URL es el identificador estable entre corridas."""
        return self.url.split("?")[0].rstrip("/").lower()

    @property
    def display_title(self) -> str:
        return self.scored_title or self.title

    @property
    def display_location(self) -> str:
        return self.location_remote or self.location or "?"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})
