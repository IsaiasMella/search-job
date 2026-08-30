"""Fuente: publicaciones de LinkedIn encontradas vía buscador.

**No toca LinkedIn.** Le pega a una search API con `site:linkedin.com/posts`,
así que no hay login, ni scraping de LinkedIn, ni riesgo de que te baneen la
cuenta. Lo único que se lee es lo que el buscador ya indexó.

Es la fuente de menor competencia: posts sueltos de gente de RRHH que publica
una búsqueda en su feed y no llega a ningún portal de empleo. La contra es la
latencia de indexación — un post de ayer puede no estar todavía. No es tiempo
real y no pretende serlo.

Proveedores de búsqueda soportados (campo `"provider"` en el perfil):

  tinyfish   (por defecto) Reusa TINYFISH_API_KEY, que ya está configurada para
             la fuente `careers`. Gratis, 30 req/min, sin tope mensual.
  google_cse Google Custom Search JSON API: 100 consultas/día gratis. Necesita
             GOOGLE_CSE_API_KEY y GOOGLE_CSE_ID, y que el motor esté configurado
             para "buscar en toda la web" (si no, sólo mira los sitios que le
             cargaste y no encuentra nada).
"""

import re
import time
from datetime import date

from vacantia.config import resolve_secret
from vacantia.log import get_logger
from vacantia.models import Job
from vacantia.sources.base import Source

logger = get_logger()

SITE = "site:linkedin.com/posts"

# Roles a rotar. Si el perfil no define "roles", se usan las keywords del perfil.
DEFAULT_ROLES = [
    "AI Engineer",
    "Machine Learning Engineer",
    "Data Scientist",
    "MLOps Engineer",
    "LLM Engineer",
    "GenAI Engineer",
]

# Señales de que el post es una búsqueda laboral y no una opinión del sector.
# Están separadas por idioma a propósito: el término de búsqueda es lo que más
# condiciona el idioma de los resultados. Buscar "hiring" trae posts en inglés,
# y si el perfil tiene el inglés desactivado esos 30 resultados se recolectan,
# se puntúan con el LLM y se descartan enteros. Conviene no pedirlos.
HIRING_TERMS_ES = [
    "vacante",
    "estamos buscando",
    "búsqueda activa",
    "se busca",
    "oportunidad laboral",
    "nos encontramos buscando",
    "buscamos",
]
HIRING_TERMS_EN = [
    "hiring",
    "we are hiring",
    "job opening",
    "open role",
]
DEFAULT_HIRING_TERMS = HIRING_TERMS_ES + HIRING_TERMS_EN

# Términos que se suman a toda query. Por defecto ninguno: el filtro de
# modalidad ya se encarga de la presencialidad, y forzar "remoto" acá dejaría
# afuera posts que no usan esa palabra exacta.
DEFAULT_EXTRA_TERMS: list[str] = []

_SEARCH_DELAY = 2.0  # mismo ritmo que careers.py: 30 req/min del plan free

# Títulos que no dicen nada del puesto: el buscador devuelve "Publicación de
# Fulano" o "Fulano's Post" cuando el post no tiene un encabezado propio.
_GENERIC_TITLE = re.compile(
    r"^\s*(publicaci[oó]n de |post de |publicación:)|[’']s post\s*$",
    re.IGNORECASE,
)

# "Lucia Carranza - Nueva vacante 100% remota" -> autor + título real
_AUTHOR_SPLIT = re.compile(
    r"^(?P<author>[^|\-–]{3,40}?)\s*[-–|]\s*(?P<rest>.+)$"
)


# --- Separar ofertas de posts de opinión ------------------------------------
# La query pide términos de búsqueda laboral, pero el buscador devuelve
# coincidencias flojas: charlas, cursos, felicitaciones y —lo más molesto—
# posts de gente que ESTÁ BUSCANDO trabajo, que usan exactamente el mismo
# vocabulario que quien ofrece uno. Cada uno de esos se puntúa con el LLM y se
# descarta después: cuesta cuota y ensucia el aviso.
def _plano(texto: str) -> str:
    """Minúsculas, sin tildes ni eñes y en una sola línea. Reusa `filters.norm`,
    que es la misma normalización que aplican los filtros."""
    from vacantia.filters import norm

    return " ".join(norm(texto).split())


#: Si aparece alguno de estos, el post NO es una oferta por más que hable de
#: búsquedas. El primer grupo es gente buscando trabajo para sí misma; el
#: segundo, contenido que no es un aviso.
_NO_ES_OFERTA = re.compile(
    r"(?:busco trabajo|busco empleo|estoy buscando trabajo|estoy en busqueda laboral"
    r"|me quede sin trabajo|open to work|#openttowork|#opentowork|disponible para nuevas"
    r"|si sabes de alguna|si saben de alguna|si conocen alguna|quede sin trabajo"
    r"|agradezco difusion|agradeceria difusion|agradezco la difusion"
    r"|me sumo a la busqueda|alguien sabe de|avisenme si"
    r"|webinar|curso |cursos |capacitacion|masterclass|charla |workshop|meetup"
    r"|felicitaciones|felicito|aniversario|cumplimos \d+ anos|orgulloso de anunciar"
    r"|mi opinion|reflexion|hilo |tips para|consejos para|como hacer un cv"
    r"|encuesta|que opinan|te comparto mi experiencia)"
)


def parece_oferta(titulo: str, snippet: str, terminos: list[str]) -> tuple[bool, str]:
    """(es una oferta, motivo del descarte).

    Dos condiciones, en este orden:

    1. Tiene que **decir** que hay una búsqueda. Un post que ni menciona una
       vacante no es una oferta por más que el buscador lo haya traído.
    2. No tiene que ser de los que usan ese mismo vocabulario sin ofrecer nada:
       alguien buscando trabajo para sí mismo, un curso, una felicitación.
    """
    texto = _plano(f"{titulo} {snippet}")
    if not texto:
        return False, "sin texto"
    if not any(_plano(t) in texto for t in terminos):
        return False, "no menciona ninguna búsqueda"
    marca = _NO_ES_OFERTA.search(texto)
    if marca:
        return False, f"no es un aviso ({marca.group(0).strip()!r})"
    return True, ""


# --- De dónde es la oferta --------------------------------------------------
# El snippet rara vez dice el país, así que sin esto entra LATAM entero: el
# filtro de ubicación deja pasar todo lo que no lo aclara, que es lo correcto
# como regla general pero acá es casi el 100%.
#
# La salida sigue siendo "" cuando de verdad no hay señal: preferimos un falso
# positivo antes que inventar un país y descartar una oferta buena.
_CIUDADES_AR = {
    "buenos aires": "Argentina", "caba": "Argentina", "capital federal": "Argentina",
    "cordoba": "Argentina", "rosario": "Argentina", "mendoza": "Argentina",
    "la plata": "Argentina", "mar del plata": "Argentina", "bahia blanca": "Argentina",
    "tucuman": "Argentina", "salta": "Argentina", "neuquen": "Argentina",
    "santa fe": "Argentina", "quilmes": "Argentina", "vicente lopez": "Argentina",
}


def pais_del_post(titulo: str, snippet: str) -> str:
    """El país que el post nombra, o "" si no nombra ninguno."""
    from vacantia.filters import COUNTRY_ALIASES

    texto = _plano(f"{titulo} {snippet}")
    if not texto:
        return ""
    for canonico, alias in COUNTRY_ALIASES.items():
        # Sólo los nombres largos: "ar", "us" o "it" sueltos aparecen dentro de
        # cualquier palabra y darían falsos positivos todo el tiempo.
        for nombre in alias:
            if len(nombre) > 3 and _menciona(texto, nombre):
                return canonico.title()
    for ciudad, pais in _CIUDADES_AR.items():
        if _menciona(texto, ciudad):
            return pais
    return ""


def _menciona(texto: str, palabra: str) -> bool:
    """Palabra entera: "salta" no puede matchear dentro de "resaltar"."""
    return re.search(r"\b" + re.escape(palabra) + r"\b", texto) is not None


def _hiring_terms_for(profile: dict) -> list[str]:
    """Términos de búsqueda acordes al filtro de idioma del perfil.

    Si `filters.language.allow_english` es false, buscar en inglés es tirar
    cuota: todo lo que venga lo descarta después `filters.passes_language`.
    """
    language_cfg = (profile.get("filters") or {}).get("language") or {}
    if language_cfg.get("allow_english", True):
        return HIRING_TERMS_ES + HIRING_TERMS_EN
    return list(HIRING_TERMS_ES)


def build_queries(profile: dict, config: dict) -> list[str]:
    """Una query por rol. Se rotan entre corridas para cubrirlos todos.

    Si hay más roles que `max_queries`, arrancar siempre desde el primero haría
    que los últimos no se consultaran nunca. El offset por día del calendario
    los va rotando sin necesidad de guardar estado.
    """
    roles = config.get("roles") or profile.get("keywords") or DEFAULT_ROLES
    roles = [str(r).strip() for r in roles if str(r).strip()]
    if not roles:
        return []

    max_queries = int(config.get("max_queries", 6) or len(roles))
    if 0 < max_queries < len(roles):
        offset = date.today().toordinal() % len(roles)
        roles = [roles[(offset + i) % len(roles)] for i in range(max_queries)]

    hiring = config.get("hiring_terms") or _hiring_terms_for(profile)
    extra = config.get("extra_terms")
    if extra is None:
        extra = DEFAULT_EXTRA_TERMS

    hiring_clause = " OR ".join(f'"{t}"' for t in hiring)
    extra_clause = " ".join(f'"{t}"' for t in extra) if extra else ""

    queries = []
    for role in roles:
        query = f'{SITE} "{role}" ({hiring_clause})'
        if extra_clause:
            query = f"{query} {extra_clause}"
        queries.append(query)
    return queries


def clean_title(raw_title: str, snippet: str) -> tuple[str, str]:
    """Devuelve (título, autor). El título indexado suele ser inservible.

    El buscador trae "Publicación de Hector Sosa" o "Mayra Rueda's Post", que no
    dicen nada del puesto. En esos casos el contenido real está en el snippet.
    """
    title = " ".join((raw_title or "").split())
    author = ""

    match = _AUTHOR_SPLIT.match(title)
    if match and not _GENERIC_TITLE.search(title):
        candidate = match.group("author").strip()
        rest = match.group("rest").strip()
        # Sólo tratamos la primera parte como autor si parece un nombre propio
        # (dos o tres palabras, sin números) y queda algo de título después.
        if 1 < len(candidate.split()) <= 3 and not any(c.isdigit() for c in candidate):
            author, title = candidate, rest

    if not title or _GENERIC_TITLE.search(title):
        # El autor está en la parte que sobra al sacar el molde genérico:
        # "Publicación de Hector Sosa" (prefijo) o "Mayra Rueda's Post" (sufijo).
        if not author:
            resto = _GENERIC_TITLE.sub("", title).strip()
            # Sacamos emojis y adornos que LinkedIn mete en el nombre.
            resto = " ".join(w for w in resto.split() if any(c.isalpha() for c in w))
            if 0 < len(resto.split()) <= 4:
                author = resto
        snippet_head = " ".join((snippet or "").split())[:110]
        title = snippet_head or title or "Publicación de LinkedIn"

    return title.strip(), author.strip()


class GooglePostsSource(Source):
    name = "google_posts"

    def __init__(self, config: dict, profile: dict):
        super().__init__(config, profile)
        self.provider = (config.get("provider") or "tinyfish").lower()
        self.language = config.get("language", "es")
        self.results_per_query = int(config.get("results_per_query", 10))
        self.search_delay = float(config.get("search_delay", _SEARCH_DELAY))
        #: Filtrar los posts que no son ofertas. Se puede apagar por si algún
        #: día el filtro resulta demasiado goloso.
        self.solo_ofertas = bool(config.get("solo_ofertas", True))
        #: Qué país asumir cuando el post no nombra ninguno. Vacío = no asumir
        #: nada, que es la regla general del proyecto ("lo que el aviso no dice,
        #: no filtra"). Ponerle "Argentina" acota a costa de perder ofertas
        #: remotas de la región que no aclaran de dónde son.
        self.default_country = str(config.get("default_country", "") or "")

        if self.provider == "google_cse":
            self.api_key = resolve_secret(
                config.get("api_key"), config.get("api_key_env", "GOOGLE_CSE_API_KEY")
            )
            self.cse_id = resolve_secret(
                config.get("cse_id"), config.get("cse_id_env", "GOOGLE_CSE_ID")
            )
        else:
            self.api_key = resolve_secret(
                config.get("api_key"), config.get("api_key_env", "TINYFISH_API_KEY")
            )
            self.cse_id = ""
        self._client_obj = None

    # --- disponibilidad -------------------------------------------------

    def is_available(self) -> tuple[bool, str]:
        if self.provider not in ("tinyfish", "google_cse"):
            return False, f"provider '{self.provider}' desconocido (usá tinyfish o google_cse)"
        if not self.api_key:
            var = "GOOGLE_CSE_API_KEY" if self.provider == "google_cse" else "TINYFISH_API_KEY"
            return False, f"falta {var}"
        if self.provider == "google_cse" and not self.cse_id:
            return False, "falta GOOGLE_CSE_ID"

        if self.provider == "tinyfish":
            try:
                import tinyfish  # noqa: F401
            except ImportError:
                return False, "falta el paquete 'tinyfish' (pip install tinyfish)"
        else:
            try:
                import requests  # noqa: F401
            except ImportError:
                return False, "falta el paquete 'requests' (pip install requests)"

        if not build_queries(self.profile, self.config):
            return False, "el perfil no tiene roles ni keywords para buscar"
        return True, ""

    # --- proveedores ----------------------------------------------------

    def _search_tinyfish(self, query: str) -> list[dict]:
        from tinyfish import RateLimitError, TinyFish

        if self._client_obj is None:
            self._client_obj = TinyFish(api_key=self.api_key)
        try:
            resp = self._client_obj.search.query(query, language=self.language)
        except RateLimitError:
            logger.warning("[google_posts] Rate-limited — espero 62s y sigo...")
            time.sleep(62)
            return []
        return [
            {
                "url": r.url,
                "title": r.title or "",
                "snippet": getattr(r, "snippet", "") or "",
                "date": getattr(r, "date", "") or "",
            }
            for r in resp.results[: self.results_per_query]
        ]

    def _search_google_cse(self, query: str) -> list[dict]:
        import requests

        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": self.api_key,
                "cx": self.cse_id,
                "q": query,
                "num": min(self.results_per_query, 10),  # el máximo que acepta
                "lr": f"lang_{self.language}",
            },
            timeout=30,
        )
        if resp.status_code == 429:
            logger.warning("[google_posts] Google CSE: cuota diaria agotada (100/día)")
            return []
        if resp.status_code != 200:
            logger.error(
                f"[google_posts] Google CSE HTTP {resp.status_code}: {resp.text[:200]}"
            )
            return []
        return [
            {
                "url": item.get("link", ""),
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "date": "",
            }
            for item in resp.json().get("items", [])
        ]

    def _search(self, query: str) -> list[dict]:
        try:
            if self.provider == "google_cse":
                return self._search_google_cse(query)
            return self._search_tinyfish(query)
        except Exception as e:
            logger.error(f"[google_posts] Falló la búsqueda: {e}")
            return []

    # --- interfaz Source ------------------------------------------------

    def fetch(self) -> list[Job]:
        queries = build_queries(self.profile, self.config)
        logger.info(f"[google_posts] {len(queries)} búsqueda(s) vía {self.provider}")

        hiring = self.config.get("hiring_terms") or _hiring_terms_for(self.profile)
        jobs: list[Job] = []
        seen: set[str] = set()
        descartados = 0
        for i, query in enumerate(queries, 1):
            if i > 1:
                time.sleep(self.search_delay)
            logger.debug(f"  [{i}/{len(queries)}] {query}")

            results = self._search(query)
            nuevos = 0
            for result in results:
                url = (result.get("url") or "").strip()
                # Sólo posts. La query ya lo pide, pero el buscador a veces
                # cuela perfiles (/in/) o páginas de empresa (/company/).
                if "/posts/" not in url:
                    continue
                key = url.split("?")[0].rstrip("/").lower()
                if key in seen:
                    continue
                seen.add(key)

                snippet = result.get("snippet", "")
                title, author = clean_title(result.get("title", ""), snippet)

                if self.solo_ofertas:
                    es_oferta, motivo = parece_oferta(
                        result.get("title", ""), snippet, hiring
                    )
                    if not es_oferta:
                        descartados += 1
                        logger.debug(f"    no es oferta ({motivo}): {title[:60]}")
                        continue

                jobs.append(
                    Job(
                        url=url,
                        title=title,
                        # No hay empresa: quien publica suele ser alguien de RRHH
                        # o el propio hiring manager. Guardamos el autor, que es
                        # a quien hay que escribirle.
                        company=author,
                        source=self.name,
                        description=snippet,
                        posted_at=result.get("date", ""),
                        # El snippet rara vez dice el país; cuando lo nombra, se
                        # aprovecha. Si no, queda "" (o lo que diga el perfil en
                        # default_country) y lo intenta después el LLM.
                        country=pais_del_post(title, snippet) or self.default_country,
                        raw={
                            "query": query,
                            "author": author,
                            "raw_title": result.get("title", ""),
                        },
                    )
                )
                nuevos += 1
            logger.info(
                f"[google_posts]   {len(results)} resultado(s), {nuevos} post(s) nuevos"
            )

        logger.info(
            f"[google_posts] {len(jobs)} publicación(es) en total"
            + (f", {descartados} descartada(s) por no ser ofertas" if descartados else "")
        )
        return jobs
