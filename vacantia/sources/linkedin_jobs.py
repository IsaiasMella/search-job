"""Fuente: LinkedIn Jobs vía la librería JobSpy.

A diferencia de `google_posts`, **esta fuente sí toca LinkedIn**: JobSpy scrapea
el buscador de empleos sin login. Consecuencias prácticas:

  - LinkedIn rate-limitea por IP. Sin login se corta cerca de la página 10, así
    que `results_wanted` alto no sirve de nada: pedí poco y filtrá por
    `hours_old` para traer sólo lo reciente.
  - Una búsqueda que falla no tumba la corrida: se loguea y se sigue con la
    siguiente. Es esperable que algunas se corten.
  - Si algún día necesitás volumen, el campo `proxies` del perfil se pasa tal
    cual a JobSpy.

Lo bueno: es la única fuente con datos **estructurados**. LinkedIn devuelve
`is_remote` y `location` como campos propios, no como texto a interpretar, así
que la modalidad y el país no dependen de que el LLM los deduzca bien. Se
completan acá y `scoring.py` respeta lo que ya viene cargado.
"""

import contextlib
import io
import logging
import sys
import time
from datetime import date

from vacantia.log import get_logger
from vacantia.models import Job
from vacantia.sources.base import Source

logger = get_logger()

DEFAULT_SEARCH_TERMS = [
    "AI Engineer",
    "Machine Learning Engineer",
    "Data Scientist",
    "MLOps Engineer",
    "LLM Engineer",
]

DEFAULT_LOCATIONS = ["Argentina"]

# Una semana. LinkedIn ordena por relevancia, no por fecha, así que sin esto
# vuelven avisos de hace meses mezclados con los de ayer.
DEFAULT_HOURS_OLD = 168

# Pausa entre búsquedas. No es un límite documentado como el de TinyFish: es
# scraping sin login, así que el criterio es no parecer un bot apurado.
DEFAULT_DELAY = 5.0


def _val(row, column: str) -> str:
    """Valor de la celda como string, o "" si es NaN/None.

    JobSpy deja media docena de columnas vacías según el aviso, y en pandas eso
    llega como NaN, que str() convierte en el texto "nan".
    """
    import pandas as pd

    if column not in row.index:
        return ""
    value = row[column]
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() in ("nan", "none", "nat") else text


#: Palabras que LinkedIn devuelve en el lugar del país y no son un país.
#: "Remote, LATAM" es lo más común: poner country="LATAM" haría que un filtro de
#: país=Argentina descarte una oferta remota que sí sirve.
_NO_ES_PAIS = {"latam", "latinoamerica", "america latina", "remote", "remoto",
               "worldwide", "global", "emea", "apac", "europe", "europa"}


def split_location(location: str) -> tuple[str, str, str]:
    """'Bahía Blanca, Buenos Aires, Argentina' -> ('Argentina', 'Bahía Blanca', 'Buenos Aires').

    Devuelve (país, ciudad, provincia). Tres detalles que importan:

    1. **La ciudad es el primer segmento, no todo lo que sobra.** LinkedIn
       manda "Londres, Catamarca, Argentina" —Londres es un pueblo de
       Catamarca— y dejar la ciudad como "Londres, Catamarca" hace que un
       filtro por ciudad se comporte de manera imprevisible. La provincia se
       guarda aparte, en `region`.
    2. **El país sólo se marca si es un país reconocible.** Si el último
       segmento es "LATAM" o "Remote", queda vacío: con el país vacío la oferta
       pasa el filtro y, si el aviso lo aclara, lo completa después el LLM.
    3. Un solo segmento se trata como ciudad, salvo que sea un país.
    """
    from vacantia.filters import COUNTRY_ALIASES, norm

    parts = [p.strip() for p in (location or "").split(",") if p.strip()]
    if not parts:
        return "", "", ""

    conocidos = {alias for nombres in COUNTRY_ALIASES.values() for alias in nombres}
    pais = ""
    if norm(parts[-1]) in conocidos:
        pais = parts[-1]
        parts = parts[:-1]
    elif norm(parts[-1]) in _NO_ES_PAIS:
        parts = parts[:-1]

    if not parts:
        return pais, "", ""
    ciudad = parts[0]
    provincia = ", ".join(parts[1:])
    return pais, ciudad, provincia


def build_searches(profile: dict, config: dict) -> list[tuple[str, str]]:
    """Producto (término, ubicación), rotado por día si hay más que `max_searches`."""
    terms = config.get("search_terms") or profile.get("keywords") or DEFAULT_SEARCH_TERMS
    terms = [str(t).strip() for t in terms if str(t).strip()]
    locations = config.get("locations") or DEFAULT_LOCATIONS
    locations = [str(l).strip() for l in locations if str(l).strip()]
    if not terms or not locations:
        return []

    combos = [(t, loc) for loc in locations for t in terms]

    max_searches = int(config.get("max_searches", 4) or len(combos))
    if 0 < max_searches < len(combos):
        # Mismo criterio que google_posts: sin rotación, los últimos términos
        # no se consultarían nunca.
        offset = date.today().toordinal() % len(combos)
        combos = [combos[(offset + i) % len(combos)] for i in range(max_searches)]
    return combos


@contextlib.contextmanager
def _sin_stderr():
    """Nada de lo que pase acá adentro sale por stderr; va a `vacantia.log`.

    JobSpy le engancha un `StreamHandler(stderr)` a cada logger suyo y por ahí
    manda hasta los mensajes de éxito ("finished scraping", nivel INFO).
    **PowerShell pinta de rojo cualquier cosa que un programa escriba en
    stderr**, con su bloque de `NativeCommandError` y `CategoryInfo`: durante la
    instalación eso se lee como si el programa se hubiera roto, cuando la
    corrida está saliendo bien.

    Se hacen las dos cosas porque no alcanza con una:

    - A los loggers que ya existen se les cambian los handlers por los nuestros
      (consola por stdout y archivo).
    - Se reemplaza `sys.stderr` mientras dura la llamada, porque JobSpy crea un
      logger más recién al scrapear (`JobSpy:Linkedin`, distinto del
      `JobSpy:LinkedIn` que arma al importarse) y ése engancha su handler al
      stderr que encuentre en ese momento.

    No se pierde nada: lo capturado se escribe en el log como DEBUG.
    """
    guardados = {}
    for nombre in list(logging.root.manager.loggerDict):
        if nombre.lower().startswith("jobspy"):
            ajeno = logging.getLogger(nombre)
            guardados[nombre] = (ajeno.handlers, ajeno.propagate)
            ajeno.handlers = list(logger.handlers)
            ajeno.propagate = False

    capturado, original = io.StringIO(), sys.stderr
    sys.stderr = capturado
    try:
        yield
    finally:
        sys.stderr = original
        for nombre, (handlers, propagate) in guardados.items():
            ajeno = logging.getLogger(nombre)
            ajeno.handlers, ajeno.propagate = handlers, propagate
        for linea in capturado.getvalue().splitlines():
            if linea.strip():
                logger.debug(f"[linkedin] (jobspy) {linea.strip()}")


class LinkedInJobsSource(Source):
    name = "linkedin"

    def __init__(self, config: dict, profile: dict):
        super().__init__(config, profile)
        self.is_remote = bool(config.get("is_remote", True))
        self.results_wanted = int(config.get("results_wanted", 25))
        self.hours_old = config.get("hours_old", DEFAULT_HOURS_OLD)
        self.fetch_description = bool(config.get("fetch_description", True))
        self.delay = float(config.get("delay_between_searches", DEFAULT_DELAY))
        self.proxies = config.get("proxies") or None
        self.job_type = config.get("job_type") or None

    # --- disponibilidad -------------------------------------------------

    def is_available(self) -> tuple[bool, str]:
        try:
            import jobspy  # noqa: F401
        except ImportError:
            return False, "falta el paquete 'python-jobspy' (ver README: necesita --no-deps)"
        if not build_searches(self.profile, self.config):
            return False, "el perfil no tiene search_terms ni locations"
        return True, ""

    # --- scraping -------------------------------------------------------

    def _scrape(self, term: str, location: str):
        from jobspy import scrape_jobs


        kwargs = {
            "site_name": ["linkedin"],
            "search_term": term,
            "location": location,
            "is_remote": self.is_remote,
            "results_wanted": self.results_wanted,
            "linkedin_fetch_description": self.fetch_description,
            "verbose": 0,
        }
        if self.hours_old:
            kwargs["hours_old"] = int(self.hours_old)
        if self.job_type:
            kwargs["job_type"] = self.job_type
        if self.proxies:
            kwargs["proxies"] = self.proxies
        with _sin_stderr():
            return scrape_jobs(**kwargs)

    def _to_job(self, row) -> Job | None:
        url = _val(row, "job_url")
        if not url:
            return None

        location = _val(row, "location")
        country, city, provincia = split_location(location)

        # is_remote viene como campo propio de LinkedIn: es dato, no deducción.
        # Ojo con el caso falso: que LinkedIn no lo marque como remoto NO
        # significa que sea presencial, así que ahí se deja vacío (y no filtra).
        remote_flag = _val(row, "is_remote").lower()
        work_mode = "remote" if remote_flag in ("true", "1", "yes") else ""

        description = _val(row, "description")
        # Contexto que LinkedIn da aparte y ayuda al scoring cuando el aviso es
        # escueto. Se antepone en vez de pisar la descripción.
        extras = [
            f"Nivel: {_val(row, 'job_level')}" if _val(row, "job_level") else "",
            f"Modalidad: {_val(row, 'job_type')}" if _val(row, "job_type") else "",
            f"Área: {_val(row, 'job_function')}" if _val(row, "job_function") else "",
            f"Industria: {_val(row, 'company_industry')}" if _val(row, "company_industry") else "",
        ]
        header = " | ".join(e for e in extras if e)
        if header:
            description = f"{header}\n\n{description}" if description else header

        return Job(
            url=url,
            title=_val(row, "title") or "(sin título)",
            company=_val(row, "company"),
            source=self.name,
            location=location,
            description=description[:3000],
            posted_at=_val(row, "date_posted"),
            country=country,
            city=city,
            region=provincia,
            work_mode=work_mode,
            raw={
                "id": _val(row, "id"),
                "company_url": _val(row, "company_url"),
                "job_url_direct": _val(row, "job_url_direct"),
            },
        )

    # --- interfaz Source ------------------------------------------------

    def fetch(self) -> list[Job]:
        searches = build_searches(self.profile, self.config)
        logger.info(
            f"[linkedin] {len(searches)} búsqueda(s) "
            f"(remoto={self.is_remote}, últimas {self.hours_old}h, "
            f"{self.results_wanted} por búsqueda)"
        )

        jobs: list[Job] = []
        seen: set[str] = set()
        for i, (term, location) in enumerate(searches, 1):
            if i > 1:
                time.sleep(self.delay)
            logger.info(f"[linkedin] [{i}/{len(searches)}] '{term}' en {location}...")
            try:
                df = self._scrape(term, location)
            except Exception as e:
                # Rate limit, cambio de HTML, timeout: se pierde esta búsqueda,
                # no la corrida.
                logger.error(f"[linkedin]   falló '{term}' en {location}: {e}")
                continue

            nuevos = 0
            for _, row in df.iterrows():
                job = self._to_job(row)
                if job is None:
                    continue
                key = job.key
                if key in seen:
                    continue
                seen.add(key)
                jobs.append(job)
                nuevos += 1
            logger.info(f"[linkedin]   {len(df)} resultado(s), {nuevos} nuevos")

        logger.info(f"[linkedin] {len(jobs)} oferta(s) en total")
        return jobs
