import logging
import os
import sys
from pathlib import Path


def get_logger(name: str = "vacantia") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # La consola muestra INFO por defecto; LOG_LEVEL=DEBUG saca el detalle
    # por URL / por oferta (el archivo vacantia.log siempre guarda DEBUG).
    console_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    # En Windows la consola suele venir en cp1252 y rompe los acentos y emojis.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(console_level)
    console.setFormatter(fmt)
    logger.addHandler(console)

    try:
        file_handler = logging.FileHandler(Path("vacantia.log"), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError:
        pass

    return logger
