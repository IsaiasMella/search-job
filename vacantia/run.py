#!/usr/bin/env python3
"""Entry point de vacantia.

    python -m vacantia.run --profile isaias
    python -m vacantia.run --profile isaias --dry-run
    python -m vacantia.run --list-profiles
"""

import argparse
import sys

from vacantia.config import available_profiles, load_profile
from vacantia.log import get_logger

logger = get_logger()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m vacantia.run",
        description="Motor de búsqueda de trabajo: fuentes → quitar duplicados → scoring → notificación.",
    )
    parser.add_argument(
        "--profile", "-p", help="Nombre del perfil en profiles/ (ej: isaias)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Corre todo pero imprime por consola sin notificar ni tocar el estado.",
    )
    parser.add_argument(
        "--min-score", type=int, help="Pisa el min_score del perfil para esta corrida."
    )
    parser.add_argument(
        "--top-n", type=int, help="Pisa el top_n del perfil para esta corrida."
    )
    parser.add_argument(
        "--list-profiles", action="store_true", help="Lista los perfiles disponibles y sale."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_profiles:
        found = available_profiles()
        print("\n".join(found) if found else "No hay perfiles en profiles/")
        return 0

    if not args.profile:
        found = available_profiles()
        logger.error(
            "Falta --profile. "
            + (f"Disponibles: {', '.join(found)}" if found else "Creá uno en profiles/")
        )
        return 2

    try:
        profile = load_profile(args.profile)
    except FileNotFoundError as e:
        logger.error(str(e))
        return 2
    except ValueError as e:
        logger.error(f"El perfil no es JSON válido: {e}")
        return 2

    if args.min_score is not None:
        profile["min_score"] = args.min_score
    if args.top_n is not None:
        profile["top_n"] = args.top_n

    # Se importa acá y no arriba para que --list-profiles y los errores de
    # perfil no dependan de tener instaladas las dependencias del motor.
    from vacantia.engine import run

    try:
        result = run(profile, dry_run=args.dry_run)
    except KeyboardInterrupt:
        logger.warning("Interrumpido.")
        return 130

    if result.skipped:
        logger.info("Notas de esta corrida:")
        for note in result.skipped:
            logger.info(f"  - {note}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
