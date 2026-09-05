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


def _url_key(url: str) -> str:
    """Misma normalización que `Job.key`, para poder comparar contra el JSON
    del historial, donde hay dicts y no Jobs."""
    return (url or "").split("?")[0].rstrip("/").lower()


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

        history = self.load_history()
        existing = {h.get("url") for h in history}
        added = [d for d in payload if d["url"] not in existing]
        # Sólo se agregan las que no estaban: una oferta que vuelve a aparecer
        # no pisa a la que ya está, que puede tener el feedback cargado.
        history.extend(added)
        self._write_history(history)
        logger.debug(f"Estado guardado en {self.dir} (+{len(added)} al historial, {len(history)} total)")


    # --- Feedback de la persona --------------------------------------------
    # `job_history.json` es el archivo durable (last_run.json se pisa en cada
    # corrida con novedades), así que el feedback vive ahí. Esto es sólo el
    # guardado: quien lo escribe es la pestaña Trabajos de la UI, que todavía
    # no existe.

    def load_history(self) -> list[dict]:
        """El historial completo, tal como está en disco. [] si no hay o está roto."""
        if not self.history_file.exists():
            return []
        try:
            data = json.loads(self.history_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning(f"{self.history_file} corrupto — lo trato como vacío")
            return []
        return data if isinstance(data, list) else []

    def _write_history(self, history: list[dict]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.history_file.write_text(json.dumps(history, indent=2), encoding="utf-8")

    def record_feedback(
        self,
        url: str,
        aplicado: bool | None,
        motivo_descarte: str = "",
        fecha_feedback: str | None = None,
    ) -> bool:
        """Guarda el veredicto de la persona sobre una oferta.

        Devuelve False si esa URL no está en el historial, para que quien
        llame lo pueda avisar en vez de perder el dato en silencio.

        La fecha se estampa sola salvo que se pase una (sirve para importar
        feedback viejo). Se escribe también en last_run.json cuando la oferta
        está ahí, así lo que se muestre desde ese archivo no queda desfasado.
        """
        clave = _url_key(url)
        if aplicado is False and not motivo_descarte.strip():
            # No se rechaza: el motivo es una regla de la UI, no del estado. Pero
            # sin motivo esta oferta no le sirve al prompt como ejemplo negativo.
            logger.warning(f"Feedback sin motivo para {url} — no va a servir de ejemplo")

        cambios = {
            "aplicado": aplicado,
            "motivo_descarte": motivo_descarte.strip(),
            "fecha_feedback": fecha_feedback or datetime.now(timezone.utc).isoformat(),
        }

        history = self.load_history()
        tocadas = [h for h in history if _url_key(h.get("url", "")) == clave]
        for entrada in tocadas:
            entrada.update(cambios)
        if not tocadas:
            logger.warning(f"No encontré {url} en {self.history_file} — no guardo el feedback")
            return False
        self._write_history(history)

        # Espejo en last_run.json, si la oferta es de la última tanda.
        ultima = self._read_last_run()
        espejo = [h for h in ultima if _url_key(h.get("url", "")) == clave]
        if espejo:
            for entrada in espejo:
                entrada.update(cambios)
            self.last_run_file.write_text(json.dumps(ultima, indent=2), encoding="utf-8")

        logger.info(f"Feedback guardado: aplicado={aplicado} — {url}")
        return True

    def archivar(self, urls: list[str], archivada: bool = True) -> int:
        """Guarda (o saca) el archivado de varias ofertas. Devuelve cuántas tocó.

        **Archivar no es descartar.** Un descarte lleva un motivo que dice algo
        del puesto, y ése va al prompt de scoring como ejemplo negativo. "El
        aviso ya no está" no dice nada de si el puesto servía: mezclarlos le
        enseñaría al sistema una preferencia que nadie tuvo.

        Las archivadas **no vuelven a entrar** en las corridas siguientes, pero
        no porque se archiven: sus claves ya están en `seen_jobs.json` desde que
        se guardaron por primera vez, y el dedupe las saca antes de nada. Por eso
        archivar no las borra del historial y se puede deshacer.
        """
        claves = {_url_key(u) for u in urls if u}
        if not claves:
            return 0
        cambios = {
            "archivada": bool(archivada),
            "fecha_archivada": datetime.now(timezone.utc).isoformat() if archivada else "",
        }

        history = self.load_history()
        tocadas = [h for h in history if _url_key(h.get("url", "")) in claves]
        for entrada in tocadas:
            entrada.update(cambios)
        if tocadas:
            self._write_history(history)
            logger.info(f"{'Archivadas' if archivada else 'Desarchivadas'} "
                        f"{len(tocadas)} oferta(s)")
        return len(tocadas)

    def _read_last_run(self) -> list[dict]:
        if not self.last_run_file.exists():
            return []
        try:
            data = json.loads(self.last_run_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    def feedback_jobs(self, aplicado: bool | None = None, limit: int | None = None) -> list[Job]:
        """Las ofertas ya marcadas, de la más reciente a la más vieja.

        `aplicado=False` devuelve las descartadas (con su motivo), que es lo que
        va a alimentar el prompt de scoring como ejemplos negativos.
        """
        marcadas = [h for h in self.load_history() if h.get("fecha_feedback")]
        if aplicado is not None:
            marcadas = [h for h in marcadas if h.get("aplicado") is aplicado]
        marcadas.sort(key=lambda h: h.get("fecha_feedback", ""), reverse=True)
        jobs = [Job.from_dict(h) for h in marcadas]
        return jobs[:limit] if limit else jobs
