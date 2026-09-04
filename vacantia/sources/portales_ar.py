"""Fuentes: los portales de empleo argentinos — Bumeran, Zonajobs, Computrabajo.

Son los que importan para los rubros no técnicos de la familia (ventas,
gastronomía, marketing, QHSE): ahí no hay careers pages ni posts de LinkedIn,
hay portal.

⚠️ **VERIFICAR CONTRA EL SITIO REAL ANTES DE CONFIAR EN ESTO.** El código se
escribió sin poder probarlo contra las webs: las direcciones de búsqueda y los
patrones de URL de aviso son los que usan hoy esos portales según su estructura
conocida, pero cambian sin avisar. Por eso **todo lo frágil es configurable
desde el perfil**, sin tocar código:

```jsonc
{
  "type": "bumeran",
  "enabled": true,
  "search_url": "https://www.bumeran.com.ar/empleos-busqueda-{query}.html",
  "job_url_pattern": "/empleos/.+-\\\\d+\\\\.html",
  "location": "buenos-aires",
  "max_queries": 3,
  "results_wanted": 20
}
```

Si algún día el portal cambia el formato, se arregla pegando la dirección nueva
en `search_url` y el patrón nuevo en `job_url_pattern`. No hace falta releer
este archivo.

La lectura es con TinyFish, igual que `careers` y `rrhh`: una request por
búsqueda para la página de resultados, y después el detalle de los avisos en
tandas de 10. Sin credenciales de TinyFish la fuente se saltea sola.
"""

import re
import time
import unicodedata
from datetime import date

from vacantia.config import resolve_secret
from vacantia.log import get_logger
from vacantia.models import Job
from vacantia.sources.base import Source
from vacantia.sources.careers import title_from_url

logger = get_logger()

_FETCH_DELAY = 0.4      # 150 URLs/min, el límite del plan free de TinyFish


class Portal:
    """Lo que distingue a un portal de otro. Todo lo demás es común."""

    def __init__(self, name: str, etiqueta: str, search_url: str,
                 job_url_pattern: str, location_url: str = ""):
        self.name = name
        self.etiqueta = etiqueta
        self.search_url = search_url
        self.job_url_pattern = job_url_pattern
        #: Variante de la dirección de búsqueda cuando además se filtra por
        #: lugar. Vacía = el portal no lo soporta por URL y se ignora el lugar.
        self.location_url = location_url


PORTALES = {
    "bumeran": Portal(
        name="bumeran",
        etiqueta="Bumeran",
        search_url="https://www.bumeran.com.ar/empleos-busqueda-{query}.html",
        location_url="https://www.bumeran.com.ar/{location}/empleos-busqueda-{query}.html",
        job_url_pattern=r"bumeran\.com\.ar/empleos/.+?-\d+\.html",
    ),
    "zonajobs": Portal(
        name="zonajobs",
        etiqueta="Zonajobs",
        search_url="https://www.zonajobs.com.ar/empleos-busqueda-{query}.html",
        location_url="https://www.zonajobs.com.ar/{location}/empleos-busqueda-{query}.html",
        job_url_pattern=r"zonajobs\.com\.ar/empleos/.+?-\d+\.html",
    ),
    "computrabajo": Portal(
        name="computrabajo",
        etiqueta="Computrabajo",
        search_url="https://ar.computrabajo.com/trabajo-de-{query}",
        location_url="https://ar.computrabajo.com/trabajo-de-{query}-en-{location}",
        job_url_pattern=r"computrabajo\.com(?:\.ar)?/(?:ofertas-de-trabajo/)?[^\s\"']*"
                        r"(?:oferta-de-trabajo-de|/trabajo-de)[^\s\"']*",
    ),
}


def slug(texto: str) -> str:
    """'Analista de Datos' -> 'analista-de-datos'. Es como arman la URL los tres."""
    plano = unicodedata.normalize("NFKD", str(texto or "").strip().lower())
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", plano).strip("-")


class PortalSource(Source):
    """Base común. Cada portal es una subclase con su `portal` puesto."""

    portal: Portal | None = None
    extractor = None        # lo pone cada subclase; ver `extraer_navent`

    def __init__(self, config: dict, profile: dict):
        super().__init__(config, profile)
        base = self.portal
        self.search_url = config.get("search_url") or base.search_url
        self.location_url = config.get("location_url") or base.location_url
        self.job_re = re.compile(
            config.get("job_url_pattern") or base.job_url_pattern, re.IGNORECASE
        )
        self.location = slug(config.get("location") or "")
        self.results_wanted = int(config.get("results_wanted", 20))
        self.max_queries = int(config.get("max_queries", 3))
        self.fetch_description = bool(config.get("fetch_description", True))
        self.fetch_delay = float(config.get("fetch_delay", _FETCH_DELAY))
        self.api_key = resolve_secret(
            config.get("api_key"), config.get("api_key_env", "TINYFISH_API_KEY")
        )
        self._tf = None

    # --- qué buscar -----------------------------------------------------

    def terminos(self) -> list[str]:
        """Los términos de búsqueda, rotados por día como en las otras fuentes.

        Sin rotación, con `max_queries` chico los últimos términos del perfil no
        se consultarían nunca.
        """
        crudos = self.config.get("search_terms") or self.profile.get("keywords") or []
        terminos = [str(t).strip() for t in crudos if str(t).strip()]
        if not terminos or self.max_queries <= 0 or self.max_queries >= len(terminos):
            return terminos
        offset = date.today().toordinal() % len(terminos)
        return [terminos[(offset + i) % len(terminos)] for i in range(self.max_queries)]

    def url_de_busqueda(self, termino: str) -> str:
        if self.location and self.location_url:
            return self.location_url.format(query=slug(termino), location=self.location)
        return self.search_url.format(query=slug(termino), location=self.location)

    # --- disponibilidad -------------------------------------------------

    def is_available(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "falta TINYFISH_API_KEY"
        try:
            import tinyfish  # noqa: F401
        except ImportError:
            return False, "falta el paquete 'tinyfish' (pip install tinyfish)"
        if not self.terminos():
            return False, "el perfil no tiene keywords ni search_terms"
        return True, ""

    # --- red ------------------------------------------------------------

    def _descargar(self, urls: list[str], con_links: bool) -> dict[str, tuple[str, list[str]]]:
        """{url pedida: (texto, links)}. Único punto que sale a la red.

        Una URL que falla no tumba la corrida: se pierde esa búsqueda y sigue.
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
                resp = self._tf.fetch.get_contents(lote, format="markdown", links=con_links)
            except RateLimitError:
                logger.warning(f"[{self.name}] Rate-limited — espero 65s y sigo...")
                time.sleep(65)
                continue
            except Exception as e:
                logger.error(f"[{self.name}] Falló la descarga de {lote[:1]}: {e}")
                continue
            resultados = list(resp.results)
            pares = (zip(lote, resultados) if len(resultados) == len(lote)
                     else [(u, {r.url: r for r in resultados}.get(u)) for u in lote])
            for pedida, r in pares:
                if r is not None:
                    salida[pedida] = (getattr(r, "text", "") or "", list(r.links or []))
        return salida

    # --- armado ---------------------------------------------------------

    def links_de_aviso(self, links: list[str], texto: str) -> list[str]:
        """Los links de la página de resultados que son avisos.

        También se rastrea el texto en Markdown: si el portal arma los links por
        JavaScript, `links` puede venir vacío pero las direcciones aparecen
        igual dentro del texto.
        """
        candidatos = list(links)
        candidatos += re.findall(r"https?://[^\s)\"'<>]+", texto or "")
        vistos, salida = set(), []
        for link in candidatos:
            # El `#` se corta acá y no en `Job.key`: para estos portales el
            # fragmento es ruido —Computrabajo cuelga ahí la posición del aviso
            # en la lista (`#lc=ListOffers-Score4-3`), y el mismo aviso salía
            # dos veces— pero para la fuente `rrhh` es identidad: ahí la página
            # del reclutador es una sola URL y el hash es lo que separa una
            # publicación de otra.
            limpio = link.split("?")[0].split("#")[0].rstrip("/")
            if not self.job_re.search(limpio):
                continue
            clave = limpio.lower()
            if clave in vistos:
                continue
            vistos.add(clave)
            salida.append(limpio)
        return salida

    def _detalle(self, jobs: list[Job]) -> None:
        paginas = self._descargar([j.url for j in jobs], con_links=False)
        for job in jobs:
            texto, _ = paginas.get(job.url, ("", []))
            if not texto:
                continue
            job.description = texto[:3000]
            if self.extractor is None:
                continue
            try:
                datos = self.extractor(texto)
            except Exception as e:       # un cambio de maquetación no tumba la corrida
                logger.debug(f"[{self.name}] No pude leer los campos de {job.url}: {e}")
                continue
            # El título del listado sale del slug de la URL y trae pegado el
            # id del aviso ("...En Monserrat B4D6A5C1...9B61373E686DCF3405"),
            # así que dos publicaciones del mismo puesto nunca coincidían y el
            # dedupe por empresa+título no las juntaba. El <h1> es el título de
            # verdad, y por eso este sí pisa lo que había.
            if titulo := datos.pop("title", ""):
                job.title = titulo
            # El resto no: lo que vino del listado es más específico.
            for campo, valor in datos.items():
                if valor and not getattr(job, campo, ""):
                    setattr(job, campo, valor)

    # --- interfaz Source ------------------------------------------------

    def fetch(self) -> list[Job]:
        terminos = self.terminos()
        urls = [self.url_de_busqueda(t) for t in terminos]
        logger.info(f"[{self.name}] {len(urls)} búsqueda(s) en {self.portal.etiqueta}")

        paginas = self._descargar(urls, con_links=True)
        jobs: list[Job] = []
        vistos: set[str] = set()
        for termino, url in zip(terminos, urls):
            texto, links = paginas.get(url, ("", []))
            encontrados = self.links_de_aviso(links, texto)
            nuevos = 0
            for aviso in encontrados:
                if aviso.lower() in vistos or len(jobs) >= self.results_wanted:
                    continue
                vistos.add(aviso.lower())
                jobs.append(
                    Job(
                        url=aviso,
                        title=title_from_url(aviso),
                        company="",          # el portal no lo pone en el listado
                        source=self.name,
                        location=self.config.get("location") or "",
                        country=self.config.get("country") or "Argentina",
                        raw={"portal": self.portal.etiqueta, "busqueda": termino,
                             "listado": url},
                    )
                )
                nuevos += 1
            logger.info(f"[{self.name}]   '{termino}': {len(encontrados)} aviso(s), {nuevos} nuevos")

        if jobs and self.fetch_description:
            logger.info(f"[{self.name}] Bajando el detalle de {len(jobs)} aviso(s)...")
            self._detalle(jobs)
        logger.info(f"[{self.name}] {len(jobs)} aviso(s) en total")
        return jobs


# --- leer empresa, ciudad y modalidad de la página del aviso -------------
#
# `city` y `work_mode` los completa normalmente el scoring con el LLM
# (`scoring.py`), pero si el LLM falla quedan vacíos y entonces la regla de
# ubicación no filtra nada: así entró un presencial de Jujuy con el perfil
# puesto en Bahía Blanca. Sacarlos acá es gratis —la página de detalle ya se
# baja para la descripción— y deja el filtro en pie aunque el modelo se caiga.
#
# `company` no lo llena nadie más, y sin él `Job.dedupe_key` devuelve "" y el
# dedupe por empresa+título no corre. Es lo que dejaba pasar el mismo aviso por
# Bumeran y por Zonajobs, que comparten la base.

_MODOS = (
    ("remote", ("remoto", "remote", "teletrabajo", "home office")),
    ("hybrid", ("hibrido", "hybrid", "mixto", "semipresencial")),
    ("onsite", ("presencial", "on site", "on-site", "in situ")),
)


def _sin_tildes(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", str(texto or "").lower())
    return "".join(c for c in plano if not unicodedata.combining(c))


def _modo(texto: str, estricto: bool = False) -> str:
    """'remote' | 'hybrid' | 'onsite' | ''.

    Con `estricto`, devuelve "" si el texto nombra más de una modalidad. Es para
    texto libre, donde "el primero que aparece" se equivoca: un aviso de
    Computrabajo empezaba diciendo "remoto" y más abajo aclaraba "días
    presenciales (3)" —o sea híbrido— y lo dábamos por remoto, que es
    justamente el error que deja pasar un presencial disfrazado.

    Devolver "" no es perder información: `Job.work_mode` vacío significa "el
    aviso no lo dice" y no filtra, así que la duda queda para el LLM, que lee
    la frase entera en vez de buscar palabras sueltas.
    """
    plano = _sin_tildes(texto)
    posiciones = [
        (pos, modo)
        for modo, marcas in _MODOS
        for m in marcas
        if (pos := plano.find(m)) >= 0
    ]
    if not posiciones:
        return ""
    if estricto and len({modo for _, modo in posiciones}) > 1:
        return ""
    return min(posiciones)[1]


def _ciudad(lugar: str) -> str:
    """'Monserrat, Capital Federal' -> 'Monserrat'. El barrio es lo específico."""
    return (lugar or "").split(",")[0].strip()


def extraer_navent(texto: str) -> dict:
    """Bumeran y Zonajobs: misma plataforma, misma maquetación.

    Al pie de la página del aviso:

        * Híbrido
        ...
        Ubicación

        Capital Federal, Capital Federal
        ...
        Ver más avisos de la empresa

        Aliantec
    """
    datos: dict[str, str] = {}

    if m := re.search(r"^#\s+(.+?)\s*$", texto, re.M):
        datos["title"] = m.group(1)

    if m := re.search(r"^Ubicaci[oó]n\s*$\n+^(.+)$", texto, re.M | re.I):
        datos["city"] = _ciudad(m.group(1))

    if m := re.search(r"^Ver m[aá]s avisos de la empresa\s*$\n+^(.+)$", texto, re.M | re.I):
        datos["company"] = m.group(1).strip()

    # La modalidad es un bullet suelto, no una etiqueta con valor.
    if m := re.search(r"^\*\s*(Presencial|H[ií]brido|Remoto)\s*$", texto, re.M | re.I):
        datos["work_mode"] = _modo(m.group(1))

    return datos


def extraer_computrabajo(texto: str) -> dict:
    """Computrabajo: empresa y lugar van juntos, en la línea de abajo del título.

        # ML / AI Engineer // Proyectos Bancarios - Remoto para residentes...

        Kaizen Recursos Humanos - Monserrat, Capital Federal

    No publica la modalidad como campo aparte, así que sale del texto.
    """
    datos: dict[str, str] = {}

    cuerpo = [l.strip() for l in texto.splitlines() if l.strip()]
    if cuerpo and cuerpo[0].startswith("#"):
        datos["title"] = cuerpo[0].lstrip("# ").strip()
    if len(cuerpo) >= 2 and cuerpo[0].startswith("#") and " - " in cuerpo[1]:
        empresa, _, lugar = cuerpo[1].partition(" - ")
        datos["company"] = empresa.strip()
        datos["city"] = _ciudad(lugar)

    # Sin campo propio: lo dice el título o el cuerpo ("Zona y horario Laboral:
    # REMOTO"). Se mira sólo el principio para no comerse los avisos
    # relacionados que el portal lista al pie.
    if modo := _modo(texto[:2500], estricto=True):
        datos["work_mode"] = modo

    return datos


class BumeranSource(PortalSource):
    name = "bumeran"
    portal = PORTALES["bumeran"]
    extractor = staticmethod(extraer_navent)


class ZonajobsSource(PortalSource):
    name = "zonajobs"
    portal = PORTALES["zonajobs"]
    extractor = staticmethod(extraer_navent)


class ComputrabajoSource(PortalSource):
    name = "computrabajo"
    portal = PORTALES["computrabajo"]
    extractor = staticmethod(extraer_computrabajo)
