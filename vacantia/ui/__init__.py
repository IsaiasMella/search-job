"""La pantalla local: Trabajos, LinkedIn URLs, Métricas, Mi perfil y Configuración.

    python -m vacantia.ui

No sale a internet: sirve HTML desde la propia máquina y lee/escribe los
archivos que el motor ya usa.
"""

from vacantia.ui.server import PUERTO, main, serve

__all__ = ["serve", "main", "PUERTO"]
