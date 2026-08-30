"""El motor: fuentes → Job → quitar duplicados → scoring → filtro → notificación.

El motor no sabe nada de TinyFish ni de Telegram: sólo habla con las interfaces
Source y Notifier. Cambiar de fuente o de canal no toca este archivo.
"""

import time
from dataclasses import dataclass, field

from vacantia.config import load_resume
from vacantia.filters import apply_filters, drop_filled, english_pain_lines
from vacantia.log import get_logger
from vacantia.models import Job
from vacantia.notifiers import build_notifiers
from vacantia.notifiers.base import Notifier
from vacantia.notifiers.console import ConsoleNotifier
from vacantia.scoring import filter_by_min_score, score_jobs, triage
from vacantia.sources import build_sources
from vacantia.sources.base import Source
from vacantia.sources.dummy import DummySource
from vacantia.state import State

logger = get_logger()


def _cap(msg: str) -> str:
    """Mayúscula inicial sin tocar el resto (str.capitalize baja NOMBRES_ASI)."""
    return msg[:1].upper() + msg[1:]


@dataclass
class RunResult:
    fetched: int = 0
    new: int = 0
    filled: int = 0
    scored: int = 0
    filtered_out: int = 0
    english_dropped: int = 0
    deferred: int = 0
    matched: int = 0
    sources_used: list[str] = field(default_factory=list)
    notifiers_used: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    jobs: list[Job] = field(default_factory=list)
    seconds: float = 0.0


def _usable_sources(profile: dict, result: RunResult) -> list[Source]:
    """Fuentes activas y disponibles. Si no queda ninguna, cae a DummySource."""
    usable: list[Source] = []
    for source in build_sources(profile):
        ok, why = source.is_available()
        if ok:
            usable.append(source)
        else:
            msg = f"fuente '{source.name}' no disponible ({why})"
            logger.warning(_cap(msg))
            result.skipped.append(msg)

    if not usable:
        logger.warning("Ninguna fuente disponible — uso DummySource para probar el pipeline.")
        result.skipped.append("sin fuentes disponibles → fallback a DummySource")
        usable.append(DummySource({"type": "dummy"}, profile))
    return usable


def _usable_notifiers(profile: dict, result: RunResult) -> list[Notifier]:
    """Notificadores activos y disponibles. Si no queda ninguno, imprime por consola."""
    usable: list[Notifier] = []
    for notifier in build_notifiers(profile):
        ok, why = notifier.is_available()
        if ok:
            usable.append(notifier)
        else:
            msg = f"notificador '{notifier.name}' no disponible ({why})"
            logger.warning(_cap(msg))
            result.skipped.append(msg)

    if not usable:
        logger.warning("Ningún notificador disponible — imprimo por consola.")
        result.skipped.append("sin notificadores disponibles → fallback a consola")
        usable.append(ConsoleNotifier({"type": "console"}, profile))
    return usable


def collect(sources: list[Source], result: RunResult) -> list[Job]:
    """Corre todas las fuentes. Una fuente que explota no tumba la corrida."""
    jobs: list[Job] = []
    for source in sources:
        logger.info(f"--- Fuente: {source.name} ---")
        try:
            found = source.fetch()
        except Exception as e:
            msg = f"fuente '{source.name}' falló: {e}"
            logger.error(_cap(msg))
            result.skipped.append(msg)
            continue
        for job in found:
            job.source = job.source or source.name
        result.sources_used.append(source.name)
        jobs.extend(found)
        logger.info(f"--- {source.name}: {len(found)} oferta(s) ---")
    return jobs


def run(profile: dict, dry_run: bool = False) -> RunResult:
    t0 = time.time()
    result = RunResult()
    name = profile.get("name", "?")
    min_score = int(profile.get("min_score", 60))
    top_n = profile.get("top_n")

    logger.info(f"=== vacantia — perfil '{name}' ===")
    logger.info(f"min_score={min_score} | top_n={top_n or 'todos'}")

    resume = load_resume(profile)
    state = State(name)

    # 1) fuentes → Job
    jobs = collect(_usable_sources(profile, result), result)
    result.fetched = len(jobs)
    logger.info(f"Total recolectado: {len(jobs)} oferta(s)")

    # 2) quitar duplicados
    new_jobs = state.filter_new(jobs)

    # 2 bis) vacantes ya cubiertas. Va antes del scoring: puntuar una búsqueda
    #        cerrada es gastar una llamada al LLM para descartarla después.
    new_jobs, cubiertas = drop_filled(new_jobs)
    result.filled = len(cubiertas)
    result.new = len(new_jobs)

    # 3) triaje: si entraron muchas de golpe (cargaste empresas nuevas, cambiaste
    #    los search_terms), puntúa las más prometedoras y difiere el resto.
    to_score, deferred = triage(new_jobs, resume, profile)
    result.deferred = len(deferred)

    # 4) scoring contra el CV
    scored = score_jobs(to_score, resume, profile) if to_score else []
    result.scored = len(scored)

    # 5) filtros de ubicación / modalidad / idioma
    eligible, fstats = apply_filters(scored, profile)
    result.filtered_out = fstats.dropped
    result.english_dropped = fstats.english_count

    # Informe opcional: cuántas se cayeron por idioma y cuánto valía la mejor.
    # Va en la notificación a pedido del perfil — ver report.english_pain.
    notes: list[str] = []
    if (profile.get("report") or {}).get("english_pain", False):
        notes = english_pain_lines(fstats)

    # 6) filtro por min_score
    matches = filter_by_min_score(eligible, min_score, top_n)
    result.matched = len(matches)
    result.jobs = matches
    logger.info(f"{len(matches)} de {len(eligible)} pasaron el min_score de {min_score}")

    # 7) notificación
    if dry_run:
        logger.info("--dry-run: no notifico ni guardo estado.")
        ConsoleNotifier({"type": "console"}, profile).send(matches, notes)
        result.seconds = time.time() - t0
        return result

    notify_empty = bool(profile.get("notify_when_empty", False))
    if matches or notify_empty:
        for notifier in _usable_notifiers(profile, result):
            try:
                if notifier.send(matches, notes):
                    result.notifiers_used.append(notifier.name)
            except Exception as e:
                msg = f"notificador '{notifier.name}' falló: {e}"
                logger.error(_cap(msg))
                result.skipped.append(msg)
    else:
        logger.info("Sin coincidencias — no notifico (poné notify_when_empty=true para avisar igual).")

    # 8) estado: recién acá marcamos como vistas, para que un fallo previo
    #    no haga perder ofertas que nunca llegaron a avisarse.
    # Sólo lo que efectivamente se puntuó: las diferidas por el triaje tienen
    # que volver a aparecer en la próxima corrida.
    # Las ya cubiertas también: no cuestan nada, pero vuelven en cada corrida
    # mientras el buscador las tenga indexadas.
    state.mark_seen(to_score + [j for j, _ in cubiertas])
    state.save(scored)

    result.seconds = time.time() - t0
    logger.info(
        f"=== Listo en {result.seconds:.1f}s — {result.fetched} recolectadas, "
        f"{result.new} nuevas, {result.filled} ya cubiertas, {result.deferred} diferidas, "
        f"{result.filtered_out} filtradas, {result.matched} avisadas ==="
    )
    return result
