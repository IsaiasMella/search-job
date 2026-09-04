"""Fuente: perfiles de reclutadores que uno decide seguir, por URL.

`google_posts` busca por palabra clave; esto vigila **personas**. Es lo que
pedía la spec original y no existía: para nichos chicos (QHSE en oil & gas, por
dar el caso concreto de la familia) suele rendir más seguir a las cinco
personas que publican siempre que buscar por keyword en todo LinkedIn.

Se le da una lista de URLs en el perfil:

```jsonc
{
  "type": "rrhh",
  "enabled": true,
  "profiles": [
    "https://www.linkedin.com/in/fulana-reclutadora/recent-activity/all/",
    "https://consultora.com.ar/busquedas-activas"
  ],
  "max_profiles": 12
}
```

Sirve cualquier página pública que liste publicaciones o búsquedas: el perfil
de actividad de alguien de RRHH, la página de una consultora, el blog de
empleos de una cámara. **No hay login ni scraping de LinkedIn**: se lee con
TinyFish, igual que `careers`.

De cada página salen tres cosas, en este orden:

1. Los links a publicaciones (`linkedin.com/posts/...`).
2. Los links que tienen pinta de aviso (`/jobs/`, ATS conocidos) — reusa la
   detección de `careers.py`.
3. Si no hay ni una cosa ni la otra, los **párrafos que anuncian una búsqueda**
   dentro del texto de la página. Cada párrafo es una oferta distinta, con la
   URL de la página más un hash del texto como identificador. Eso es lo que
   permite que una página cuya URL nunca cambia genere una oferta nueva cuando
   publica algo nuevo: el hash cambia y el dedupe del motor la deja pasar.
"""

import hashlib
import re
import time

from vacantia.config import resolve_secret
from vacantia.log import get_logger
from vacantia.models import Job
from vacantia.sources.base import Source
from vacantia.sources.careers import is_job_url
from vacantia.sources.google_posts import HIRING_TERMS_EN, HIRING_TERMS_ES

logger = get_logger()

#: Mismo ritmo que `careers`: 150 URLs/min es el límite del plan free.
_FETCH_DELAY = 0.4

#: Cuántos párrafos con pinta de búsqueda se levantan por página. Más que esto
#: y una página de consultora con 40 avisos viejos llena la corrida.
MAX_PARRAFOS = 8

#: Un párrafo más corto que esto no alcanza para puntuar nada.
MIN_LARGO_PARRAFO = 60

_POST_RE = re.compile(r"linkedin\.com/(posts|pulse)/", re.IGNORECASE)
_ADORNOS_RE = re.compile(r"^[#>*\-\s|]+|[\s|]+$")


def _terminos(profile: dict) -> list[str]:
    """Las señales de que un texto anuncia una búsqueda.

    Si el perfil tiene el inglés desactivado, los términos en inglés sólo
    traerían avisos que el filtro de idioma va a descartar igual.
    """
    idioma = (profile.get("filters") or {}).get("language") or {}
    if idioma.get("allow_english", True):
        return HIRING_TERMS_ES + HIRING_TERMS_EN
    return list(HIRING_TERMS_ES)


def nombre_desde_url(url: str) -> str:
    """'https://www.linkedin.com/in/ana-perez/recent-activity/' -> 'Ana Perez'.

    Es a quién hay que escribirle, así que vale la pena sacarlo prolijo. Para
    una página que no es un perfil, cae al dominio ('consultora.com.ar').
    """
    m = re.search(r"/in/([^/?#]+)", url)
    if m:
        slug = re.sub(r"-[0-9a-z]{6,}$", "", m.group(1))   # el sufijo de LinkedIn
        return " ".join(p.capitalize() for p in slug.replace("_", "-").split("-") if p)
    m = re.match(r"https?://(?:www\.)?([^/?#]+)", url)
    return m.group(1) if m else url


def parrafos_con_busqueda(texto: str, terminos: list[str]) -> list[str]:
    """Los párrafos del texto que anuncian una búsqueda, sin repetir."""
    if not texto:
        return []
    encontrados, vistos = [], set()
    for crudo in re.split(r"\n\s*\n|\r\n\s*\r\n", texto):
        parrafo = _ADORNOS_RE.sub("", " ".join(crudo.split()))
        if len(parrafo) < MIN_LARGO_PARRAFO:
            continue
        bajo = parrafo.lower()
        if not any(t in bajo for t in terminos):
            continue
        clave = bajo[:120]
        if clave in vistos:
            continue
        vistos.add(clave)
        encontrados.append(parrafo)
        if len(encontrados) >= MAX_PARRAFOS:
            break
    return encontrados


def _hash(texto: str) -> str:
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()[:10]


def es_perfil_de_linkedin(url: str) -> bool:
    """Un perfil de persona en LinkedIn (`/in/algo`), que es el caso que falla.

    Probado el 4/9/2026 con un perfil real: LinkedIn devuelve la página vacía
    tanto en `/in/fulano/` como en `/in/fulano/recent-activity/all/`, mientras
    que una página cualquiera de otro sitio devuelve el contenido completo. No
    es el patrón de URL ni el lector: LinkedIn no deja leer perfiles sin sesión.

    Los links a publicaciones sueltas (`/posts/...`) y las páginas de empresa
    (`/company/...`) no entran acá: esos se comportan distinto y no se probaron.
    """
    return bool(re.search(r"linkedin\.com/in/", str(url or ""), re.I))



class RRHHProfilesSource(Source):
    name = "rrhh"

    def __init__(self, config: dict, profile: dict):
        super().__init__(config, profile)
        self.api_key = resolve_secret(
            config.get("api_key"), config.get("api_key_env", "TINYFISH_API_KEY")
        )
        self.urls = [str(u).strip() for u in (config.get("profiles") or []) if str(u).strip()]
        max_profiles = config.get("max_profiles")
        if max_profiles:
            self.urls = self.urls[: int(max_profiles)]
        self.fetch_delay = float(config.get("fetch_delay", _FETCH_DELAY))
        self.max_links = int(config.get("max_links_per_profile", 15))
        self._tf = None

    # --- disponibilidad -------------------------------------------------

    def is_available(self) -> tuple[bool, str]:
        if not self.urls:
            return False, "no hay perfiles de RRHH cargados en el perfil"
        if not self.api_key:
            return False, "falta TINYFISH_API_KEY"
        try:
            import tinyfish  # noqa: F401
        except ImportError:
            return False, "falta el paquete 'tinyfish' (pip install tinyfish)"
        return True, ""

    # --- descarga -------------------------------------------------------

    def _descargar(self, urls: list[str]) -> dict[str, tuple[str, list[str]]]:
        """{url pedida: (texto, links)}. Es el único punto que toca la red.

        La clave es la URL *pedida* y no la devuelta: si el sitio redirige, no
        coinciden y la página se quedaría sin resultados (mismo cuidado que en
        careers.py).
        """
        from tinyfish import RateLimitError, TinyFish

        if self._tf is None:
            self._tf = TinyFish(api_key=self.api_key)

        salida: dict[str, tuple[str, list[str]]] = {}
        for i in range(0, len(urls), 10):
            lote = urls[i : i + 10]
            if i:
                time.sleep(self.fetch_delay * len(lote))
            try:
                resp = self._tf.fetch.get_contents(lote, format="markdown", links=True)
            except RateLimitError:
                logger.warning("[rrhh] Rate-limited — espero 65s y sigo con el resto...")
                time.sleep(65)
                continue
            except Exception as e:
                logger.error(f"[rrhh] Falló la descarga de {lote[:1]}: {e}")
                continue
            resultados = list(resp.results)
            if len(resultados) == len(lote):
                pares = zip(lote, resultados)
            else:                       # respuesta parcial: emparejamos por URL
                por_url = {r.url: r for r in resultados}
                pares = [(u, por_url.get(u)) for u in lote]
            for pedida, r in pares:
                if r is not None:
                    salida[pedida] = (getattr(r, "text", "") or "", list(r.links or []))
        return salida

    # --- armado de ofertas ----------------------------------------------

    def _jobs_de_pagina(self, url: str, texto: str, links: list[str],
                        terminos: list[str]) -> list[Job]:
        autor = nombre_desde_url(url)
        base = dict(company=autor, source=self.name,
                    raw={"perfil_rrhh": url, "autor": autor})

        posts = [l for l in dict.fromkeys(links) if _POST_RE.search(l)][: self.max_links]
        avisos = [l for l in dict.fromkeys(links)
                  if is_job_url(l) and l not in posts][: self.max_links]

        jobs = [
            Job(url=link, title=f"Publicación de {autor}", description=texto[:1200], **base)
            for link in posts
        ]
        jobs += [
            Job(url=link, title=f"Búsqueda publicada por {autor}",
                description=texto[:1200], **base)
            for link in avisos
        ]
        if jobs:
            return jobs

        # Ni posts ni links de aviso: la página misma es el aviso. Cada párrafo
        # que anuncia una búsqueda va como una oferta, identificada por el hash
        # de su texto para que una publicación nueva no se confunda con la vieja.
        for parrafo in parrafos_con_busqueda(texto, terminos):
            jobs.append(
                Job(
                    url=f"{url}#{_hash(parrafo)}",
                    title=parrafo[:90],
                    description=parrafo[:2000],
                    **base,
                )
            )
        return jobs


    # --- interfaz Source ------------------------------------------------

    def fetch(self) -> list[Job]:
        logger.info(f"[rrhh] Revisando {len(self.urls)} perfil(es) de RRHH...")
        paginas = self._descargar(self.urls)
        terminos = _terminos(self.profile)

        jobs: list[Job] = []
        for url in self.urls:
            texto, links = paginas.get(url, ("", []))
            if not texto and not links:
                logger.warning(f"[rrhh]   sin contenido en {url}")
                if es_perfil_de_linkedin(url):
                    logger.warning(
                        "[rrhh]   LinkedIn no deja leer los perfiles desde afuera: "
                        "devuelve la página vacía, con o sin /recent-activity/all/. "
                        "No es tu URL ni un error del programa. Para seguir a esta "
                        "persona, usá la página de su consultora, que sí se puede "
                        "leer. Verificado el 4/9/2026."
                    )
                continue
            nuevas = self._jobs_de_pagina(url, texto, links, terminos)
            jobs.extend(nuevas)
            logger.info(f"[rrhh]   {len(nuevas)} de {nombre_desde_url(url)}")

        logger.info(f"[rrhh] {len(jobs)} publicación(es) en total")
        return jobs
