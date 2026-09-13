"""Fuente: careers pages de empresas, leídas con TinyFish.

Adaptado del descubrimiento de autopilot-jobhunt/job_hunt/scanner.py
(discover_job_urls + fetch_job_details), envuelto como Source. Todo lo que sabe
de TinyFish vive en este archivo: si TinyFish deja de andar, se reemplaza esta
clase sin tocar el motor.
"""

import json
import re
import time
from pathlib import Path

from vacantia.config import terminos_de_busqueda
from vacantia.config import resolve_secret
from vacantia.log import get_logger
from vacantia.models import Job
from vacantia.sources.base import Source

logger = get_logger()

JOB_URL_RE = re.compile(
    r"/(job|jobs|opening|openings|position|positions|vacancy|vacancies|role|roles|apply)"
    r"/[a-zA-Z0-9_%@.-]{4,}",
    re.IGNORECASE,
)
ATS_JOB_RE = re.compile(
    r"(greenhouse\.io/.+/jobs/\d+"
    r"|lever\.co/[^/]+/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
    r"|myworkdayjobs\.com/[^?#]+"
    r"|smartrecruiters\.com/[^/]+/[A-Z0-9]+"
    r"|ashbyhq\.com/[^/]+/[a-f0-9-]{32,})",
    re.IGNORECASE,
)
ATS_LISTING_RE = re.compile(
    r"^https?://(jobs\.lever\.co|boards\.greenhouse\.io|apply\.workable\.com"
    r"|jobs\.smartrecruiters\.com)/[^/?#]+/?(\?.*)?$",
    re.IGNORECASE,
)

DEFAULT_SEARCH_SENIORITY = "senior OR staff OR principal OR lead"
DEFAULT_SEARCH_KEYWORDS = (
    '"data scientist" OR "ML engineer" OR "machine learning engineer" '
    'OR "AI engineer" OR MLOps OR "deep learning"'
)

# Ritmo de requests contra TinyFish.
#
# Límites del plan gratuito, según https://www.tinyfish.ai/pricing (agosto 2026):
#   Search : 30 requests / min  -> 2.0 s entre requests para tocar el techo
#   Fetch  : 150 urls    / min  -> 0.4 s por URL para tocar el techo
#
# Vamos al límite documentado, no por debajo: el plan permite ese ritmo y no
# hay motivo para regalar segundos. Lo que hace seguro ir al borde no es el
# margen sino el _Pacer, que se ensancha solo si comemos un 429 (ver penalize):
# el primer choque ajusta el ritmo para el resto de la corrida en vez de
# repetirse cada minuto. El SDK además reintenta solo (max_retries=2).
#
# Ambos son configurables por perfil con "search_delay" / "fetch_delay".
# Los valores anteriores (13 s y 2.5 s) venían heredados de autopilot-jobhunt
# sin explicación y eran ~6x más lentos de lo que el plan gratuito permite.
_FETCH_URL_DELAY = 0.4   # 150 urls/min — el límite exacto del plan free
_SEARCH_DELAY = 2.0      #  30 req/min  — el límite exacto del plan free


class _Pacer:
    """Espaciador de llamadas: asegura N segundos entre requests.

    La versión anterior dormía *después* de cada llamada, así que pagaba el
    delay entero aunque la request ya hubiera tardado 5s, y encima pagaba uno
    de más al terminar. Acá se duerme sólo lo que falta para completar el
    intervalo desde la request anterior, y nunca al final.
    """

    def __init__(self, label: str):
        self.label = label
        self._last = 0.0
        # Se ensancha solo ante un 429. Corremos pegados al límite documentado,
        # así que el margen no lo pone un número conservador sino esto.
        self.factor = 1.0

    def wait(self, interval: float) -> None:
        if self._last:
            remaining = interval * self.factor - (time.monotonic() - self._last)
            if remaining > 0:
                logger.debug(f"  [ritmo:{self.label}] espero {remaining:.1f}s")
                time.sleep(remaining)
        self._last = time.monotonic()

    def penalize(self) -> None:
        """Un 429 dice que el ritmo nominal no alcanzó — casi siempre porque el
        SDK metió reintentos propios que este pacer no ve. Ensanchamos para el
        resto de la corrida en vez de volver a chocar (y pagar 65s) cada minuto.
        """
        self.factor = min(self.factor * 1.5, 4.0)
        logger.warning(
            f"  [ritmo:{self.label}] 429 — ensancho el intervalo x{self.factor:.2f} "
            f"para el resto de la corrida"
        )


# Títulos de página que no identifican la oferta: son el <title> genérico del
# sitio de careers. Globant devolvía "Join now our Globant team | Globant
# Careers" para sus 10 ofertas distintas, y Accenture "Workday is currently
# unavailable." Cuando el <title> pinta así, preferimos el slug de la URL.
GENERIC_TITLE_RE = re.compile(
    r"(careers?$|carreras|jobs?$|vacancies|oportunidades|empleos?|sumate"
    r"|unavailable|not found|we are hiring|join (now )?our|trabaj[áa] con)",
    re.IGNORECASE,
)


def title_from_url(url: str) -> str:
    """Título de fallback desde el slug. Si el último segmento es puro número
    (.../job/senior-data-scientist/74905) usa el anterior, que es el que
    describe el puesto."""
    parts = [p for p in url.split("?")[0].rstrip("/").split("/") if p]
    for part in reversed(parts[-2:]):
        if part and not part.isdigit():
            slug = part.replace("-", " ").replace("_", " ").replace("%20", " ").strip()
            # .title() sobre camelCase lo arruina ("AIEngineerSr" -> "Aiengineersr"),
            # así que sólo se aplica cuando el slug tiene separadores de verdad.
            return slug.title() if " " in slug else part
    return parts[-1] if parts else url


def is_job_url(url: str) -> bool:
    return bool(JOB_URL_RE.search(url)) or bool(ATS_JOB_RE.search(url))


def is_ats_listing(url: str) -> bool:
    return bool(ATS_LISTING_RE.match(url))


def build_search_query(domain: str, profile: dict) -> str:
    cand = profile.get("candidate", {})
    seniority = cand.get("search_seniority") or DEFAULT_SEARCH_SENIORITY
    keywords = cand.get("search_keywords")
    if not keywords:
        profile_kw = terminos_de_busqueda(profile)
        keywords = (
            " OR ".join(f'"{k}"' for k in profile_kw) if profile_kw else DEFAULT_SEARCH_KEYWORDS
        )
    return f"site:{domain} ({seniority}) ({keywords})"


class CareersPagesSource(Source):
    name = "careers"

    def __init__(self, config: dict, profile: dict):
        super().__init__(config, profile)
        self.api_key = resolve_secret(
            config.get("api_key"), config.get("api_key_env", "TINYFISH_API_KEY")
        )
        self.companies_file = Path(config.get("companies_file", "companies.json"))
        self.max_companies = config.get("max_companies")
        self.use_search = config.get("use_search", True)
        self.fetch_delay = float(config.get("fetch_delay", _FETCH_URL_DELAY))
        self.search_delay = float(config.get("search_delay", _SEARCH_DELAY))
        self._fetch_pacer = _Pacer("fetch")
        self._search_pacer = _Pacer("search")
        self._tf = None

    # --- disponibilidad -------------------------------------------------

    def is_available(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "falta TINYFISH_API_KEY"
        try:
            import tinyfish  # noqa: F401
        except ImportError:
            return False, "falta el paquete 'tinyfish' (pip install tinyfish)"
        if not self.companies_file.exists():
            return False, f"no existe {self.companies_file}"
        if not self._load_companies():
            return False, f"{self.companies_file} no tiene empresas cargadas"
        return True, ""

    def _load_companies(self) -> list[dict]:
        """Lee companies.json y descarta la entrada-molde de ejemplo."""
        try:
            data = json.loads(self.companies_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"No pude leer {self.companies_file}: {e}")
            return []
        companies = [
            c
            for c in data
            if c.get("careers_url")
            and not str(c.get("name", "")).upper().startswith("EJEMPLO")
        ]
        if self.max_companies:
            companies = companies[: int(self.max_companies)]
        return companies

    # --- TinyFish -------------------------------------------------------

    def _client(self):
        if self._tf is None:
            from tinyfish import TinyFish

            self._tf = TinyFish(api_key=self.api_key)
            logger.debug("Cliente TinyFish inicializado")
        return self._tf

    def _fetch_with_ratelimit(self, urls: list[str], **kwargs):
        from tinyfish import RateLimitError

        tf = self._client()
        for _ in range(2):
            try:
                self._fetch_pacer.wait(len(urls) * self.fetch_delay)
                return tf.fetch.get_contents(urls, **kwargs)
            except RateLimitError:
                self._fetch_pacer.penalize()
                logger.warning("Fetch rate-limited — espero 65s y reintento...")
                time.sleep(65)
            except Exception as e:
                logger.error(f"Error de fetch para {urls[:1]}: {e}")
                return None
        return None

    def _fetch_links(self, urls: list[str]) -> dict[str, list[str]]:
        """{url_pedida: links}, en tandas de 10 (el máximo que acepta la API).

        La clave es la URL *pedida*, no la devuelta: si el sitio redirige,
        `r.url` no coincide con lo que pedimos y la empresa se quedaba sin links.
        """
        result: dict[str, list[str]] = {}
        for i in range(0, len(urls), 10):
            batch = urls[i : i + 10]
            resp = self._fetch_with_ratelimit(batch, format="markdown", links=True)
            if not resp:
                continue
            results = list(resp.results)
            if len(results) == len(batch):
                for requested, r in zip(batch, results):
                    result[requested] = r.links or []
            else:  # respuesta parcial: caemos a la URL devuelta
                for r in results:
                    result[r.url] = r.links or []
        return result

    # --- descubrimiento -------------------------------------------------

    def _discover_from_careers_pages(self, companies: list[dict]) -> dict[str, set[str]]:
        """Fase 1: todas las careers pages juntas, de a 10 por request.

        Antes era una request por empresa (10 round-trips para 10 empresas).
        """
        by_company: dict[str, set[str]] = {c.get("name", "?"): set() for c in companies}

        logger.info(f"[careers] Leyendo {len(companies)} careers page(s)...")
        links_by_url = self._fetch_links([c["careers_url"] for c in companies])

        ats_owner: dict[str, str] = {}  # url del listado ATS -> empresa que lo trajo
        for company in companies:
            cname = company.get("name", "?")
            links = links_by_url.get(company["careers_url"], [])
            direct = {link for link in links if is_job_url(link)}
            ats = {link for link in links if is_ats_listing(link)}
            by_company[cname].update(direct)
            for link in sorted(ats)[:5]:
                ats_owner.setdefault(link, cname)
            logger.debug(
                f"  [{cname}] Careers page: {len(direct)} links directos, "
                f"{len(ats)} listados ATS"
            )

        if ats_owner:
            logger.info(f"[careers] Expandiendo {len(ats_owner)} listado(s) ATS...")
            for page_url, page_links in self._fetch_links(list(ats_owner)).items():
                cname = ats_owner.get(page_url)
                if cname:
                    by_company[cname].update(l for l in page_links if is_job_url(l))

        return by_company

    def _discover_from_search(
        self, companies: list[dict], by_company: dict[str, set[str]]
    ) -> None:
        """Fase 2: una búsqueda por dominio. La API no batchea search, así que
        esto es serial y es lo que domina el tiempo total. Una empresa puede
        apagarla con "use_search": false en su entrada de companies.json."""
        targets = [
            c for c in companies if c.get("search_domain") and c.get("use_search", True)
        ]
        if not targets:
            return
        logger.info(f"[careers] Buscando en {len(targets)} dominio(s)...")
        for company in targets:
            cname = company.get("name", "?")
            try:
                by_company[cname].update(
                    self._search_domain(cname, company["search_domain"])
                )
            except Exception as e:
                logger.error(f"[careers] Falló la búsqueda de {cname}: {e}")

    def _search_domain(self, name: str, domain: str) -> set[str]:
        from tinyfish import RateLimitError

        found: set[str] = set()
        query = build_search_query(domain, self.profile)
        logger.debug(f"  [{name}] Query: {query}")
        for _ in range(2):
            try:
                self._search_pacer.wait(self.search_delay)
                resp = self._client().search.query(query, language="en")
                found.update(r.url for r in resp.results if is_job_url(r.url))
                logger.debug(
                    f"  [{name}] Search: {len(resp.results)} resultados, "
                    f"{len(found)} con pinta de oferta"
                )
                break
            except RateLimitError:
                self._search_pacer.penalize()
                logger.warning(f"  [{name}] Search rate-limited — espero 60s...")
                time.sleep(62)
            except Exception as e:
                logger.error(f"  [{name}] Error de search: {e}")
                break
        return found

    def _fetch_details(self, jobs: list[Job]) -> list[Job]:
        for i in range(0, len(jobs), 10):
            batch = jobs[i : i + 10]
            resp = self._fetch_with_ratelimit([j.url for j in batch], format="markdown")
            if not resp:
                continue
            results = list(resp.results)
            if len(results) == len(batch):
                pairs = list(zip(batch, results))
            else:  # respuesta parcial: emparejamos por URL como se pueda
                fetched = {r.url: r for r in results}
                pairs = [(j, fetched.get(j.url)) for j in batch]
            for job, r in pairs:
                if not (r and r.text):
                    continue
                job.description = r.text[:3000]
                if r.title and not GENERIC_TITLE_RE.search(r.title):
                    job.title = r.title
                logger.debug(f"    '{job.title}' — {len(r.text)} chars")
        return jobs

    # --- interfaz Source ------------------------------------------------

    def fetch(self) -> list[Job]:
        companies = self._load_companies()
        logger.info(f"[careers] {len(companies)} empresa(s) a revisar")

        by_company = self._discover_from_careers_pages(companies)
        if self.use_search:
            self._discover_from_search(companies, by_company)

        jobs: list[Job] = []
        for company in companies:
            cname = company.get("name", "?")
            urls = by_company.get(cname, set())
            if not urls:
                logger.info(f"[careers]   sin ofertas en {cname}")
                continue
            jobs.extend(
                Job(
                    url=u,
                    title=title_from_url(u),
                    company=cname,
                    source=self.name,
                    location=company.get("location", ""),
                    region=company.get("region", ""),
                    raw={"careers_url": company.get("careers_url")},
                )
                for u in sorted(urls)
            )
            logger.info(f"[careers]   {len(urls)} URL(s) de oferta en {cname}")

        if jobs:
            logger.info(f"[careers] Bajando el detalle de {len(jobs)} oferta(s)...")
            self._fetch_details(jobs)
        return jobs
