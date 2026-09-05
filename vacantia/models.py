"""Modelo normalizado de oferta. Toda fuente devuelve `Job`, nada más."""

import re
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

# Ruido que no distingue una oferta de otra y que cada fuente escribe distinto.
# "Data Scientist (Remote)" en LinkedIn y "data-scientist" en la careers page
# son la misma oferta.
_TITLE_NOISE = {
    "remoto", "remota", "remote", "hibrido", "hybrid", "presencial", "onsite",
    "hibrida", "home", "office", "full", "time", "part", "m", "f", "d", "h",
    "x", "eng", "ing",
}
# Sufijos societarios y de país: `careers` los toma de companies.json
# ("Globant Argentina") y LinkedIn del perfil de la empresa ("Globant").
_COMPANY_NOISE = {
    "sa", "s", "a", "srl", "sas", "sl", "inc", "llc", "ltd", "ltda", "gmbh",
    "corp", "co", "company", "group", "grupo", "holding", "technologies",
    "tech", "solutions", "argentina", "arg", "chile", "uruguay", "mexico",
    "colombia", "peru", "brasil", "brazil", "espana", "spain", "latam",
}

_PARENTESIS_RE = re.compile(r"[\(\[\{][^)\]\}]*[\)\]\}]")
_NO_ALFANUM_RE = re.compile(r"[^a-z0-9]+")


def _tokens(text: str, noise: set[str]) -> list[str]:
    """Minúsculas, sin tildes, sin puntuación y sin las palabras de relleno.

    Duplica a propósito la idea de `filters.norm()` en vez de importarla:
    `filters` importa este módulo y al revés sería un import circular.
    """
    if not text:
        return []
    plano = unicodedata.normalize("NFKD", str(text).lower())
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    plano = _PARENTESIS_RE.sub(" ", plano)
    return [t for t in _NO_ALFANUM_RE.sub(" ", plano).split() if t and t not in noise]


def normalize_title(title: str) -> str:
    """Título comparable entre fuentes. Los tokens se ordenan alfabéticamente:
    "Senior Data Scientist" y "Data Scientist Senior" son el mismo puesto."""
    return " ".join(sorted(set(_tokens(title, _TITLE_NOISE))))


def normalize_company(company: str) -> str:
    return " ".join(_tokens(company, _COMPANY_NOISE))


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

    # --- Feedback de la persona (lo escribe la pestaña Trabajos de la UI) ---
    # Es la materia prima del ciclo de aprendizaje: las descartadas con su
    # motivo van al prompt de scoring como ejemplos negativos, y las aplicadas
    # como positivos. Se guardan en job_history.json vía State.record_feedback.
    aplicado: bool | None = None   # True verde, False rojo, None todavía sin mirar
    motivo_descarte: str = ""      # por qué no sirve. Obligatorio cuando aplicado=False
    fecha_feedback: str = ""       # ISO-8601 UTC. "" = nunca se lo miró

    # Archivada: la publicación venció o ya la bajaron. **No es lo mismo que
    # descartada**, y por eso es un campo aparte y no un valor más de
    # `aplicado`. El motivo de un descarte dice algo del puesto y va al prompt
    # de scoring como ejemplo negativo; "el aviso ya no está" no dice nada de
    # si servía, y meterlo ahí le enseñaría al sistema una preferencia falsa.
    archivada: bool = False
    fecha_archivada: str = ""      # ISO-8601 UTC

    # --- Trazabilidad ---
    found_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def key(self) -> str:
        """Clave de quitar duplicados. La URL es el identificador estable entre corridas."""
        return self.url.split("?")[0].rstrip("/").lower()

    @property
    def dedupe_key(self) -> str:
        """Clave secundaria: empresa + título normalizado.

        La misma búsqueda llega por `careers` y por `linkedin` con URLs
        distintas, así que `key` no la detecta: se puntuaba dos veces y podía
        recibir dos veredictos opuestos.

        Devuelve "" cuando falta la empresa o el título, y ahí no se deduplica
        por esta vía: sin empresa, un "Data Scientist" de `google_posts` se
        comería al "Data Scientist" de cualquier otra.
        """
        empresa = normalize_company(self.company)
        titulo = normalize_title(self.title)
        return f"{empresa}|{titulo}" if empresa and titulo else ""

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
