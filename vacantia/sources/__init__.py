"""Registro de fuentes enchufables.

Para agregar una fuente nueva: implementá Source en un módulo de esta carpeta
y registrala en SOURCE_REGISTRY con su "type". El perfil la activa listándola
en su campo "sources".
"""

from vacantia.log import get_logger
from vacantia.sources.base import Source
from vacantia.sources.careers import CareersPagesSource
from vacantia.sources.dummy import DummySource

logger = get_logger()

SOURCE_REGISTRY: dict[str, type[Source]] = {
    CareersPagesSource.name: CareersPagesSource,
    DummySource.name: DummySource,
    # TODO(fase 2): "google_posts" -> GooglePostsSource
    #   Publicaciones de empleo vía búsqueda de Google (Google Jobs / posts).
    #   Va en sources/google_posts.py, misma interfaz Source.fetch() -> list[Job].
    # TODO(fase 3): "linkedin" -> LinkedInJobsSource
    #   Ofertas de LinkedIn usando la librería JobSpy (pip install python-jobspy).
    #   Va en sources/linkedin.py, misma interfaz Source.fetch() -> list[Job].
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


__all__ = ["Source", "CareersPagesSource", "DummySource", "SOURCE_REGISTRY", "build_sources"]
