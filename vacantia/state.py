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
        return {"seen_keys": [], "last_run": None}

    @property
    def seen_keys(self) -> set[str]:
        return set(self._data.get("seen_keys", []))

    def filter_new(self, jobs: list[Job]) -> list[Job]:
        """Saca las ya vistas en corridas anteriores y las duplicadas dentro del lote."""
        seen = self.seen_keys
        new: list[Job] = []
        batch_keys: set[str] = set()
        for job in jobs:
            if job.key in seen or job.key in batch_keys:
                continue
            batch_keys.add(job.key)
            new.append(job)
        logger.info(f"Dedupe: {len(new)} nuevas de {len(jobs)} ({len(seen)} vistas históricas)")
        return new

    def mark_seen(self, jobs: list[Job]) -> None:
        self._data["seen_keys"] = sorted(self.seen_keys | {j.key for j in jobs})

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
