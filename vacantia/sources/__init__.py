"""Registro de fuentes enchufables.

Para agregar una fuente nueva: implementá Source en un módulo de esta carpeta
y registrala en SOURCE_REGISTRY con su "type". El perfil la activa listándola
en su campo "sources".
"""

from vacantia.log import get_logger
from vacantia.sources.base import Source
from vacantia.sources.careers import CareersPagesSource
from vacantia.sources.dummy import DummySource
from vacantia.sources.getonbrd import GetOnBoardSource
from vacantia.sources.google_posts import GooglePostsSource
from vacantia.sources.indeed import IndeedSource
from vacantia.sources.linkedin_jobs import LinkedInJobsSource
from vacantia.sources.portales_ar import (
    BumeranSource,
    ComputrabajoSource,
    ZonajobsSource,
)
from vacantia.sources.rrhh_profiles import RRHHProfilesSource

logger = get_logger()

SOURCE_REGISTRY: dict[str, type[Source]] = {
    CareersPagesSource.name: CareersPagesSource,
    DummySource.name: DummySource,
    GooglePostsSource.name: GooglePostsSource,
    LinkedInJobsSource.name: LinkedInJobsSource,
    RRHHProfilesSource.name: RRHHProfilesSource,
    BumeranSource.name: BumeranSource,
    ZonajobsSource.name: ZonajobsSource,
    ComputrabajoSource.name: ComputrabajoSource,
    IndeedSource.name: IndeedSource,
    GetOnBoardSource.name: GetOnBoardSource,
}


def build_sources(profile: dict) -> list[Source]:
    """Instancia las fuentes activas del perfil. Ignora las desconocidas."""
    built: list[Source] = []
    for entry in profile.get("sources", []):
        if not entry.get("enabled", True):
            continue
        stype = entry.get("type")
        cls = SOURCE_REGISTRY.get(stype)
        if cls is None:
            logger.warning(f"Fuente desconocida en el perfil: '{stype}' — la salteo")
            continue
        built.append(cls(entry, profile))
    return built


__all__ = [
    "Source",
    "CareersPagesSource",
    "DummySource",
    "GooglePostsSource",
    "LinkedInJobsSource",
    "RRHHProfilesSource",
    "BumeranSource",
    "ZonajobsSource",
    "ComputrabajoSource",
    "IndeedSource",
    "GetOnBoardSource",
    "SOURCE_REGISTRY",
    "build_sources",
]
