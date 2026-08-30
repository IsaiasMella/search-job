"""Estado por perfil: qué ofertas ya vimos, para no avisar dos veces.

Adaptado del manejo de state/ de autopilot-jobhunt, pero namespaceado por
perfil: cada persona tiene su propio state/<perfil>/ y no se pisan entre sí.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from vacantia.log import get_logger
from vacantia.models import Job

logger = get_logger()

STATE_ROOT = Path("state")


def _richness(job: Job) -> tuple:
    """Cuánto sabe de la oferta esta copia. Ante dos iguales, gana la mayor.

    Primero los campos estructurados (modalidad y país deciden los filtros y
    sólo LinkedIn los trae como dato, no como deducción del LLM), después el
    largo de la descripción, que es lo que ve el scoring.
    """
    return (
        bool(job.work_mode) + bool(job.country),
        len(job.description or ""),
    )


class State:
    def __init__(self, profile_name: str, root: Path | None = None):
        self.dir = (root or STATE_ROOT) / profile_name
        self.seen_file = self.dir / "seen_jobs.json"
        self.last_run_file = self.dir / "last_run.json"
        self.history_file = self.dir / "job_history.json"
        self._data = self._load()

    def _load(self) -> dict:
        if self.seen_file.exists():
            try:
                return json.loads(self.seen_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning(f"{self.seen_file} corrupto — arranco de cero")
        return {"seen_keys": [], "seen_alt_keys": [], "last_run": None}

    @property
    def seen_keys(self) -> set[str]:
        return set(self._data.get("seen_keys", []))

    @property
    def seen_alt_keys(self) -> set[str]:
        """Claves (empresa + título) ya vistas. Ausente en estados viejos."""
        return set(self._data.get("seen_alt_keys", []))

    def filter_new(self, jobs: list[Job]) -> list[Job]:
        """Saca las ya vistas y las duplicadas, por URL y por (empresa + título).

        La URL sola no alcanza: la misma búsqueda llega por `careers` y por
        `linkedin` con URLs distintas, se puntúa dos veces (dos llamadas al
        LLM) y puede recibir dos veredictos opuestos, así que quien la lee ve
        la misma oferta dos veces con puntajes que no coinciden.

        Cuando dos copias caen en el mismo lote se queda **la más completa**
        (ver `_richness`), no la primera: LinkedIn trae modalidad y país como
        campos propios y una descripción entera, y la copia de `careers` suele
        ser sólo un título sacado del slug de la URL.
        """
        seen, seen_alt = self.seen_keys, self.seen_alt_keys
        new: list[Job] = []
        batch_keys: set[str] = set()
        por_alt: dict[str, int] = {}   # clave secundaria -> índice en `new`
        dup_url = dup_alt = 0

        for job in jobs:
            if job.key in seen or job.key in batch_keys:
                dup_url += 1
                continue

            alt = job.dedupe_key
            if alt and alt in seen_alt:
                dup_alt += 1
                logger.debug(f"    duplicada de otra corrida ({alt}): {job.url}")
                continue

            if alt and alt in por_alt:
                dup_alt += 1
                i = por_alt[alt]
                previa = new[i]
                if _richness(job) > _richness(previa):
                    logger.debug(
                        f"    duplicada entre fuentes ({alt}): me quedo con la de "
                        f"'{job.source}' y descarto la de '{previa.source}'"
                    )
                    new[i] = job
                else:
                    logger.debug(
                        f"    duplicada entre fuentes ({alt}): descarto la de "
                        f"'{job.source}', ya la tengo por '{previa.source}'"
                    )
                batch_keys.add(job.key)
                continue

            batch_keys.add(job.key)
            if alt:
                por_alt[alt] = len(new)
            new.append(job)

        logger.info(
            f"Dedupe: {len(new)} nuevas de {len(jobs)} — {dup_url} por URL repetida, "
            f"{dup_alt} por empresa+título ({len(seen)} vistas históricas)"
        )
        return new

    def mark_seen(self, jobs: list[Job]) -> None:
        self._data["seen_keys"] = sorted(self.seen_keys | {j.key for j in jobs})
        # También la clave secundaria: si no, la copia de la otra fuente vuelve
        # a entrar en la próxima corrida con su URL distinta.
        self._data["seen_alt_keys"] = sorted(
            self.seen_alt_keys | {a for j in jobs if (a := j.dedupe_key)}
        )

    def save(self, all_jobs: list[Job]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self._data["last_run"] = datetime.now(timezone.utc).isoformat()
        self.seen_file.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

        payload = [j.to_dict() for j in all_jobs]
        # Una corrida sin novedades NO pisa last_run.json: es lo que lee el
        # drafter, y perderlo dejaría sin poder redactar sobre la última tanda.
        if payload:
            self.last_run_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        else:
            logger.debug("Sin ofertas nuevas — conservo el last_run.json anterior")

        history: list[dict] = []
        if self.history_file.exists():
            try:
                history = json.loads(self.history_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                history = []
        existing = {h.get("url") for h in history}
        added = [d for d in payload if d["url"] not in existing]
        history.extend(added)
        self.history_file.write_text(json.dumps(history, indent=2), encoding="utf-8")
        logger.debug(f"Estado guardado en {self.dir} (+{len(added)} al historial, {len(history)} total)")
