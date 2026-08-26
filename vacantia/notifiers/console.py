"""Notificador de consola: el fallback cuando no hay credenciales de ningún canal."""

from vacantia.log import get_logger
from vacantia.models import Job
from vacantia.notifiers.base import Notifier

logger = get_logger()


class ConsoleNotifier(Notifier):
    name = "console"

    def send(self, jobs: list[Job], notes: list[str] | None = None) -> bool:
        if not jobs:
            print("\nSin coincidencias nuevas esta corrida.\n")
            _print_notes(notes)
            return True

        width = 72
        print("\n" + "=" * width)
        print(f"  VACANTIA — {len(jobs)} coincidencia(s)")
        print("=" * width)
        for i, job in enumerate(jobs, 1):
            print(f"\n#{i}  [{job.score if job.score is not None else '?'}] {job.display_title}")
            print(f"    Empresa : {job.company or '?'}")
            print(f"    Lugar   : {job.display_location}")
            if job.stack:
                print(f"    Stack   : {job.stack}")
            if job.reason:
                print(f"    Por qué : {job.reason}")
            print(f"    Fuente  : {job.source}")
            print(f"    URL     : {job.url}")
        print("\n" + "=" * width)
        _print_notes(notes)
        print()
        return True


def _print_notes(notes: list[str] | None) -> None:
    if not notes:
        return
    print()
    for line in notes:
        print(f"  {line}")
