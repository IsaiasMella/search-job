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
  "max_profiles": 12,
  "max_age_days": 30
}
```

`max_age_days` es la ventana de tiempo de esa búsqueda: 30 días por defecto, y
más ancha que la de `google_posts` porque acá se sigue a alguien puntual, que
puede pasarse tres semanas sin publicar. `0` la apaga y vuelve a traer lo de
hace años.

**No hay login ni scraping de LinkedIn**: se lee con TinyFish, igual que
`careers`.

## El rodeo para seguir a una persona de LinkedIn

Un perfil (`linkedin.com/in/...`) **no se puede leer**: LinkedIn devuelve la
página vacía a quien no tiene sesión, y desde una IP común responde `HTTP 999`.
Verificado el 4/9/2026 contra un perfil real.

Pero sus **posts sueltos sí se leen**, y Google los tiene indexados. Entonces,
cuando la URL es un perfil, no se entra: se le pregunta al buscador cuáles son
sus publicaciones (`site:linkedin.com/posts "Nombre Apellido"`), se filtran por
el slug del perfil para no traer a un homónimo, y se leen esos posts. Cuesta una
búsqueda por persona y por corrida. Se apaga con `"buscar_posts": false`.

Para quien carga la URL no cambia nada: pega el perfil y funciona.

## Qué sale de cada página

Cuando la página **es un post**, el aviso es esa página: título de su primera
línea y el texto como descripción. No se siguen los links que contiene, porque
un post enlaza a otros posts del mismo autor y eso traía publicaciones de hace
cinco años como si fueran búsquedas abiertas.

Cuando es **cualquier otra página** (una consultora, el blog de empleos de una
cámara), salen tres cosas en este orden:

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
from vacantia.sources.google_posts import (
    HIRING_TERMS_EN,
    HIRING_TERMS_ES,
    MINUTOS_POR_DIA,
)

logger = get_logger()

#: Mismo ritmo que `careers`: 150 URLs/min es el límite del plan free.
_FETCH_DELAY = 0.4

#: Días hacia atrás al pedirle al buscador las publicaciones de una persona.
#: Sin esto traía posts de hace cinco años, que es el problema que el docstring
#: de arriba ya nombraba y quedaba a medio resolver: se cortaba el seguir links
#: dentro de un post, pero la búsqueda seguía sin mirar la fecha.
DEFAULT_MAX_AGE_DAYS = 30

#: Cuántos párrafos con pinta de búsqueda se levantan por página. Más que esto
#: y una página de consultora con 40 avisos viejos llena la corrida.
MAX_PARRAFOS = 8

#: Un párrafo más corto que esto no alcanza para puntuar nada.
MIN_LARGO_PARRAFO = 60

_POST_RE = re.compile(r"linkedin\.com/(posts|pulse)/", re.IGNORECASE)

#: La propia navegación de LinkedIn, que viene en cada página de post.
#:
#: Una página de post trae 226 links, y el único que `is_job_url()` acepta es
#: el botón "Empleos" del menú de arriba: `/jobs/search?trk=public_post_guest_
#: nav_menu_jobs`. Sin esto, cada post generaba un aviso falso que apuntaba al
#: buscador de LinkedIn, siempre el mismo, y duplicaba la lista.
_CHROME_RE = re.compile(
    r"trk=public_post_guest_nav|linkedin\.com/jobs/search/?(\?|$)"
    r"|linkedin\.com/(login|signup|feed|help|legal|company/linkedin)",
    re.IGNORECASE,
)
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


#: Cuánto hace que se publicó, tal como lo escribe LinkedIn: "1mo", "3y", "2w".
_ANTIGUEDAD_RE = re.compile(r"^\d+\s*(mo|y|w|d|h|min)$", re.IGNORECASE)


def limpiar_post(texto: str) -> str:
    """Deja el texto que escribió la persona, sin el encabezado de LinkedIn.

    Arriba de cada post viene siempre lo mismo, y no dice nada del aviso:

        # Renzo Bazan's Post      <- el título de la página
        Renzo Bazan               <- el nombre, repetido
        1mo                       <- cuándo lo publicó
        Edited
        ¡Súmate a nuestros proyectos de Gobierno de Datos!   <- acá empieza

    Estorba porque el título del aviso sale de la primera línea de verdad. Se
    descartan líneas sólo hasta la primera que parece contenido: una vez que
    empezó el texto no se saca nada más, así que un post que arranque distinto
    no pierde nada.
    """
    utiles: list[str] = []
    empezo = False
    for cruda in str(texto or "").splitlines():
        linea = cruda.strip()
        if not linea:
            continue
        if not empezo:
            if (linea.startswith("#") or _ANTIGUEDAD_RE.match(linea)
                    or linea.lower() == "edited" or len(linea) <= 40):
                continue
            empezo = True
        utiles.append(linea)
    return "\n".join(utiles).strip()


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



def slug_de_perfil(url: str) -> str:
    """'linkedin.com/in/ana-perez-2472/recent-activity/' -> 'ana-perez-2472'.

    Es el identificador exacto de la persona, y sirve para quedarse sólo con
    SUS posts: buscando "Renzo Bazan" el buscador devuelve también los de otros
    dos Renzo Bazan, y el slug es lo único que los distingue sin equivocarse.
    """
    m = re.search(r"linkedin\.com/in/([^/?#]+)", str(url or ""), re.I)
    return m.group(1).lower() if m else ""


class RRHHProfilesSource(Source):
    name = "rrhh"
    #: Más ancho que el de `google_posts` a propósito: acá no se busca "lo que
    #: haya", se sigue a alguien puntual que puede pasarse tres semanas sin
    #: publicar. Lo pisa `filters.max_age_days` del perfil si está puesto.
    max_age_days_default = DEFAULT_MAX_AGE_DAYS

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
        # Un perfil de LinkedIn no se puede leer (ver `es_perfil_de_linkedin`),
        # así que se buscan sus publicaciones por el buscador. Cuesta una
        # búsqueda por persona y por corrida.
        self.buscar_posts = bool(config.get("buscar_posts", True))
        self.posts_por_persona = int(config.get("posts_por_persona", 8))
        self.language = str(config.get("language", "es"))
        #: {url del post: cuándo lo publicó, según el buscador}. Se llena en
        #: `posts_de` y se lee al armar la oferta: la página del post no dice
        #: la fecha por ningún lado, el que la sabe es el buscador.
        self._fechas: dict[str, str] = {}
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
                        terminos: list[str], duenio: str = "") -> list[Job]:
        # `duenio` es la URL que cargó la persona; `url` puede ser un post suyo
        # que encontramos por el buscador. El autor sale del dueño porque es a
        # quien hay que escribirle, no del post.
        duenio = duenio or url
        autor = nombre_desde_url(duenio)
        base = dict(company=autor, source=self.name,
                    # La fecha la sabe el buscador, no la página: un post de
                    # LinkedIn leído suelto no dice cuándo se publicó. Se anotó
                    # en `posts_de` y se recupera acá. Vacía si la página vino
                    # de una URL cargada a mano, que no pasa por el buscador.
                    posted_at=self._fechas.get(url, ""),
                    raw={"perfil_rrhh": duenio, "autor": autor, "pagina": url})

        # Cuando la página YA es un post, el aviso es esa página y no los links
        # que contiene. Un post enlaza a otros posts del mismo autor, así que
        # seguirlos traía publicaciones sueltas de hace cinco años ("gracias
        # equipo por el reconocimiento") como si fueran búsquedas abiertas.
        if _POST_RE.search(url):
            return self._job_del_post(url, texto, terminos, base)

        utiles = [l for l in dict.fromkeys(links) if not _CHROME_RE.search(l)]
        posts = [l for l in utiles if _POST_RE.search(l)][: self.max_links]
        avisos = [l for l in utiles
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


    def _job_del_post(self, url: str, texto: str, terminos: list[str],
                      base: dict) -> list[Job]:
        """El post como una sola oferta, con su primera línea de título.

        Sin esto todos los posts salían con el mismo título ("Publicación de
        Fulano") y, como la empresa también es la misma persona, el dedupe del
        motor por empresa+título los colapsaba a uno.

        Se descarta el post que no anuncia una búsqueda: la gente de RRHH
        también publica agradecimientos y fotos del equipo.
        """
        cuerpo = limpiar_post(texto)
        if not any(t in cuerpo.lower() for t in terminos):
            logger.debug(f"[rrhh]   no parece una búsqueda: {url}")
            return []

        titulo = next((l for l in cuerpo.splitlines() if len(l.strip()) > 15), "")
        return [Job(
            url=url,
            title=(titulo.strip() or f"Publicación de {base['company']}")[:90],
            description=cuerpo[:2000],
            **base,
        )]

    # --- seguir a una persona sin poder leer su perfil ------------------

    def _cliente(self):
        from tinyfish import TinyFish

        if self._tf is None:
            self._tf = TinyFish(api_key=self.api_key)
        return self._tf

    def posts_de(self, url_perfil: str) -> list[str]:
        """Las direcciones de los posts de esa persona, según el buscador.

        Es la vuelta al bloqueo: el **perfil** no se puede leer, pero los
        **posts sueltos** sí, y Google los tiene indexados. Entonces en vez de
        entrar al perfil se le pregunta al buscador cuáles son sus posts.

        La query lleva el nombre entre comillas y los resultados se filtran por
        el slug del perfil, que es el identificador exacto: buscar "Renzo Bazan"
        trae también a otros dos que se llaman igual.
        """
        from vacantia.sources.google_posts import buscar_en_tinyfish

        slug = slug_de_perfil(url_perfil)
        nombre = nombre_desde_url(url_perfil)
        if not slug or not nombre:
            return []

        query = f'site:linkedin.com/posts "{nombre}"'
        resultados = buscar_en_tinyfish(
            self._cliente(), query, self.language,
            self.posts_por_persona * 3, etiqueta=self.name,
            recency_minutes=self.max_age_days * MINUTOS_POR_DIA or None,
        )
        marca = f"/posts/{slug}_"
        propios, vistos = [], set()
        for r in resultados:
            limpia = (r.get("url") or "").split("?")[0]
            if marca not in limpia.lower() or limpia.lower() in vistos:
                continue
            vistos.add(limpia.lower())
            propios.append(limpia)
            if fecha := (r.get("date") or "").strip():
                self._fechas[limpia] = fecha
            if len(propios) >= self.posts_por_persona:
                break

        ajenos = len(resultados) - len(propios)
        logger.info(f"[rrhh]   {nombre}: {len(propios)} post(s) suyos"
                    f"{f', {ajenos} de otra persona descartado(s)' if ajenos > 0 else ''}")
        return propios

    # --- interfaz Source ------------------------------------------------

    def _paginas_a_leer(self) -> dict[str, str]:
        """{url a bajar: a quién pertenece}.

        Una página común se lee tal cual. Un perfil de LinkedIn no se puede
        leer, así que se reemplaza por las direcciones de sus publicaciones,
        que sí se pueden. Para quien carga las URLs es el mismo campo: pega el
        perfil y funciona, sin tener que saber nada de esto.
        """
        destinos: dict[str, str] = {}
        for url in self.urls:
            if not es_perfil_de_linkedin(url):
                destinos[url] = url
                continue
            if not self.buscar_posts:
                logger.warning(
                    f"[rrhh]   {url} es un perfil de LinkedIn y `buscar_posts` "
                    "está apagado: LinkedIn no deja leerlo, así que no va a traer nada."
                )
                continue
            for post in self.posts_de(url):
                destinos[post] = url          # el autor es la persona, no el post
        return destinos

    def fetch(self) -> list[Job]:
        logger.info(f"[rrhh] Revisando {len(self.urls)} perfil(es) de RRHH...")
        destinos = self._paginas_a_leer()
        if not destinos:
            logger.info("[rrhh] 0 publicación(es) en total")
            return []

        paginas = self._descargar(list(destinos))
        terminos = _terminos(self.profile)

        jobs: list[Job] = []
        por_persona: dict[str, int] = {}
        for url, duenio in destinos.items():
            texto, links = paginas.get(url, ("", []))
            if not texto and not links:
                logger.warning(f"[rrhh]   sin contenido en {url}")
                continue
            # El aviso se le atribuye a la persona que seguís, no a la URL del
            # post: es a quien le vas a escribir.
            nuevas = self._jobs_de_pagina(url, texto, links, terminos, duenio)
            jobs.extend(nuevas)
            por_persona[duenio] = por_persona.get(duenio, 0) + len(nuevas)

        for duenio, cuantas in por_persona.items():
            logger.info(f"[rrhh]   {cuantas} de {nombre_desde_url(duenio)}")
        logger.info(f"[rrhh] {len(jobs)} publicación(es) en total")
        return jobs
