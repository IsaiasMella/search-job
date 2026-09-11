"""Fuente: Indeed Argentina.

Va en su propio módulo y no con los otros portales porque Indeed tiene tres
particularidades que no comparte con ninguno, y las tres se descubrieron
probando contra el sitio real el 9/9/2026:

**1. Cloudflare deja pasar el listado y no el aviso.** Pegarle desde Python
devuelve `403 Forbidden` con `server: cloudflare`; con TinyFish, la página de
resultados sí vuelve (7,7 KB, 35 links de aviso), pero `viewjob?jk=...` vuelve
**vacía**, 0 bytes. La página del aviso sólo se puede leer por el link de
redirección que el propio listado trae:

    https://ar.indeed.com/rc/clk?jk=<id>&bb=<token>   -> 2 a 3 KB, anda
    https://ar.indeed.com/viewjob?jk=<id>             -> 0 bytes

**2. Ese link lleva un token de sesión (`bb`) que cambia en cada corrida.** Si
se guardara como identidad del aviso, el mismo puesto entraría de nuevo tres
veces por día y el dedupe no lo agarraría nunca. Por eso el `bb` se usa **sólo
para bajar el detalle, dentro de la misma corrida**, y lo que se guarda en
`Job.url` es la dirección canónica `viewjob?jk=<id>`, que es estable y **abre
perfecto en el navegador de la persona** (verificado: la bloquea el scraper, no
el browser).

**3. El aviso no dice cuándo se publicó.** Ni el listado ni el detalle traen la
fecha en el Markdown. La ventana la aplica el propio Indeed con `fromage`, igual
que LinkedIn con `hours_old`: se pide sólo lo de los últimos N días y lo que
vuelve ya viene recortado. Por eso esta fuente no filtra por antigüedad después.

**Cuánto rinde, y por qué no rinde más** (todo medido el 9/9/2026):

* **La segunda página no existe sin cuenta**: ver `_SIN_PAGINACION`.
* Lo que sí trae más es **buscar por más términos**, porque cada búsqueda tiene
  su propia primera página: 1 término da 16 avisos, 6 términos dan 51 únicos.
  Por eso acá `max_queries` rinde mucho más que en los otros portales.
* Pero el cuello no está en el listado sino en el detalle: de los avisos que se
  encuentran **sólo se puede leer entre el 38% y el 50%**. Y no es
  rate-limiting: probado con lotes de 10, 5 y 3 con pausas crecientes, la tasa
  no se mueve (33%, 38%, 38%). Los que fallan son **siempre los mismos**, en dos
  rondas seguidas: es una propiedad del aviso, no de la request.
* Por eso traer 30 del listado en vez de 20 no sube los útiles, sólo el gasto de
  TinyFish, y el cupo del perfil está en 25.

**El techo de esta fuente son unos 11 avisos completos por corrida.**

Se evaluó y **se descartó** exprimir el listado, que trae empresa, ubicación y
un pedazo de la descripción en Markdown: los links vienen en una lista aparte,
sin el texto al lado, así que habría que emparejar cada bloque con su aviso por
posición. Basta que Indeed intercale un anuncio para que los títulos y las
empresas queden cruzados, y un aviso con la empresa equivocada es peor que un
aviso que no está.
"""

import re
import urllib.parse

from vacantia.log import get_logger
from vacantia.models import Job
from vacantia.sources.portales_ar import Portal, PortalSource

logger = get_logger()

#: Los valores que Indeed acepta en `fromage`. Cualquier otro lo ignora y
#: devuelve todo, que es justo lo que no queremos: se redondea al más chico que
#: cubra la ventana pedida, para no traer de más.
_VENTANAS = (1, 3, 7, 14)

#: **La segunda página de resultados no existe sin cuenta.** Pedir `&start=10`
#: devuelve 550 bytes que dicen, literal:
#:
#:     "Para ver más de una página de empleos, crea una cuenta o inicia sesión."
#:
#: No es Cloudflare ni un problema de scraping: es una decisión de producto de
#: Indeed, y no hay parámetro que la esquive. Se probaron `start`, `sort=date`,
#: la versión móvil y con `l=Argentina`: todas devuelven la misma primera página
#: de 16 avisos, o el cartel de login.
#:
#: **Lo que sí trae más es buscar por más términos**, porque cada búsqueda tiene
#: su propia primera página. Medido el 9/9/2026 con la misma ventana de 7 días:
#:
#:     1 término   -> 16 avisos
#:     6 términos  -> 51 avisos únicos
#:
#: Por eso acá `max_queries` rinde mucho más que en los otros portales, y por
#: eso `terminos()` rota los términos por día: en dos corridas se cubren seis
#: búsquedas sin pedir seis listados cada vez.
_SIN_PAGINACION = "crea una cuenta o inicia sesión"

#: El id del aviso dentro de cualquiera de sus URLs.
_JK = re.compile(r"[?&]v?jk=([0-9a-f]{8,20})", re.IGNORECASE)

#: Lo que devuelve `title_from_url` sobre la URL canónica cuando no se pudo
#: leer el detalle. No es un título: es el nombre del endpoint.
_SIN_TITULO = "viewjob"

#: El encabezado del detalle en Markdown:
#:
#:     # AI Engineer
#:
#:     Darwin AI
#:
#:     4.0 de 5 estrellas
#:
#:     Buenos Aires, Buenos Aires
#:
#: La línea de estrellas es opcional y hay que saltearla: sin eso, la empresa
#: quedaba en "4.0 de 5 estrellas" en los avisos de empresas calificadas.
_ESTRELLAS = re.compile(r"^[\d.,]+\s+de\s+\d+\s+estrellas", re.IGNORECASE)


def _canonica(url: str) -> str:
    """`.../rc/clk?jk=abc&bb=<token>` -> `https://ar.indeed.com/viewjob?jk=abc`.

    Es la identidad del aviso: sin el token de sesión, que cambia en cada
    corrida, y sin los parámetros de tracking del listado.
    """
    m = _JK.search(url or "")
    if not m:
        return ""
    dominio = urllib.parse.urlparse(url).netloc or "ar.indeed.com"
    return f"https://{dominio}/viewjob?jk={m.group(1).lower()}"


def extraer_indeed(texto: str) -> dict:
    """Título, empresa y ciudad del detalle. {} si la maquetación cambió.

    **Hay dos maquetaciones**, y la segunda apareció probando: uno de cada
    quince avisos viene sin el encabezado y arranca directo en
    `## Información del empleo`, sin título ni empresa en ningún lado. De ésos
    se saca la ubicación igual, que es la única de las tres que sí está.
    """
    lineas = [l.strip() for l in (texto or "").splitlines()]
    datos: dict[str, str] = {}

    for i, linea in enumerate(lineas):
        if not linea.startswith("# ") or linea.startswith("## "):
            continue
        datos["title"] = linea[2:].strip()
        # Lo que sigue al título: empresa y después ubicación, salteando las
        # líneas vacías y la calificación con estrellas.
        siguientes = [l for l in lineas[i + 1 : i + 8]
                      if l and not _ESTRELLAS.match(l) and not l.startswith("#")]
        if siguientes:
            datos["company"] = siguientes[0]
        if len(siguientes) > 1:
            # "Buenos Aires, Buenos Aires" -> la ciudad es lo de antes de la coma.
            datos["city"] = siguientes[1].split(",")[0].strip()
        break

    if not datos.get("city"):
        for i, linea in enumerate(lineas):
            if linea.lower().startswith("## ubicación"):
                if valor := next((l for l in lineas[i + 1 : i + 5] if l), ""):
                    datos["city"] = valor.split(",")[0].strip()
                break
    return datos


class IndeedSource(PortalSource):
    """Indeed AR. Reusa la maquinaria de los portales; cambia lo de arriba."""

    name = "indeed"
    portal = Portal(
        name="indeed",
        etiqueta="Indeed",
        # `q` va urlencodeado y no en slug: Indeed busca por texto, no por ruta.
        search_url="https://ar.indeed.com/jobs?q={query}",
        location_url="https://ar.indeed.com/jobs?q={query}&l={location}",
        job_url_pattern=r"indeed\.com/(?:rc/clk|viewjob)\?.*?jk=",
    )
    extractor = staticmethod(extraer_indeed)

    def __init__(self, config: dict, profile: dict):
        super().__init__(config, profile)
        #: {url canónica: link con token} de esta corrida. El token vale para
        #: bajar el detalle ahora y no se guarda en ningún lado.
        self._con_token: dict[str, str] = {}
        #: Por fecha y no por "relevancia", que es el default de Indeed. Como
        #: sólo se puede leer la primera página, lo que entre en esa página es
        #: todo lo que vamos a ver: conviene que sea lo más nuevo. Y el mismo
        #: aviso rinde más cuanto antes se lo ve, porque tiene menos postulantes.
        self.orden = str(config.get("sort", "date") or "")

    def _fromage(self) -> int | None:
        """La ventana de días, redondeada a lo que Indeed acepta."""
        if self.max_age_days <= 0:
            return None
        return next((v for v in _VENTANAS if v >= self.max_age_days), _VENTANAS[-1])

    def url_de_busqueda(self, termino: str) -> str:
        """Como la de los portales, pero con el término urlencodeado y `fromage`.

        `PortalSource` arma la URL con `slug()` porque Bumeran y compañía ponen
        la búsqueda en la ruta. Acá va en el query string.
        """
        query = urllib.parse.quote_plus(str(termino).strip())
        if self.location and self.location_url:
            url = self.location_url.format(
                query=query, location=urllib.parse.quote_plus(self.location))
        else:
            url = self.search_url.format(query=query, location="")
        if (dias := self._fromage()) is not None:
            url += f"&fromage={dias}"
        if self.orden:
            url += f"&sort={self.orden}"
        return url

    def links_de_aviso(self, links: list[str], texto: str) -> list[str]:
        """Los avisos del listado, ya canónicos.

        No se puede usar el de `PortalSource`: ése corta el query string, y en
        Indeed el `jk` que va ahí **es** la identidad del aviso. Cortarlo dejaba
        todos los links en `https://ar.indeed.com/rc/clk`, o sea uno solo.
        """
        # Si algún día se intenta paginar de nuevo, que quede dicho en el log
        # por qué no vino nada, en vez de parecer que el portal se rompió.
        if _SIN_PAGINACION in (texto or "").lower():
            logger.info(f"[{self.name}] Indeed pide cuenta para pasar de la primera "
                        "página: se lee sólo la primera, por búsqueda")

        candidatos = list(links) + re.findall(r"https?://[^\s)\"'<>]+", texto or "")
        salida: list[str] = []
        for link in candidatos:
            if not self.job_re.search(link):
                continue
            canonica = _canonica(link)
            if not canonica or canonica in self._con_token:
                continue
            # El link con token sólo si lo trae; el listado a veces da la
            # canónica pelada, y ésa no se puede bajar.
            self._con_token[canonica] = link if "bb=" in link else ""
            salida.append(canonica)
        return salida

    def _detalle(self, jobs: list[Job]) -> None:
        """Baja el detalle por el link con token, y lo aplica al job canónico.

        `PortalSource._detalle` pide `job.url` directamente; acá eso devolvería
        0 bytes siempre.

        **Se reintenta lo que no volvió.** Medido contra el sitio real: de 10
        links pedidos en un lote, TinyFish devuelve 7, y de esos 7 ninguno viene
        vacío. O sea que lo que falta no es Cloudflare bloqueando, es el lote que
        vuelve incompleto; pidiéndolo de nuevo aparece.
        """
        pedibles = {j.url: self._con_token.get(j.url, "") for j in jobs}
        urls = [u for u in pedibles.values() if u]
        if not urls:
            logger.warning(f"[{self.name}] Ningún aviso trajo el link con token: "
                           "me quedo con lo del listado")
            return

        paginas = self._descargar(urls, con_links=False)
        # Un reintento, y uno solo. Medido dos veces: la primera ronda recupera
        # algunos, la segunda no recupera ninguno. Las que faltan después del
        # reintento son siempre las mismas, así que no es que el lote vuelva
        # incompleto: es Cloudflare que a esos avisos no los deja leer, y
        # pedirlos de nuevo sólo agrega segundos a la corrida.
        if faltan := [u for u in urls if not paginas.get(u, ("", []))[0]]:
            logger.info(f"[{self.name}] {len(faltan)} aviso(s) no volvieron: reintento")
            paginas.update(self._descargar(faltan, con_links=False))

        for job in jobs:
            texto, _ = paginas.get(pedibles.get(job.url, ""), ("", []))
            if not texto:
                continue
            job.description = texto[:3000]
            try:
                datos = extraer_indeed(texto)
            except Exception as e:      # un cambio de maquetación no tumba nada
                logger.debug(f"[{self.name}] No pude leer {job.url}: {e}")
                continue
            if titulo := datos.pop("title", ""):
                job.title = titulo
            for campo, valor in datos.items():
                if valor and not getattr(job, campo, ""):
                    setattr(job, campo, valor)

    def fetch(self) -> list[Job]:
        self._con_token.clear()
        jobs = super().fetch()

        # Los que se quedaron sin título de verdad no entran. Sin la página del
        # aviso lo único que hay es la URL canónica, y el título sale del slug:
        # queda en "viewjob", sin empresa y sin descripción. Eso no se puede ni
        # mostrar en una tarjeta, el modelo le pone 0 igual que a una oferta que
        # de verdad no sirve, y encima cuesta una llamada.
        #
        # Con el detalle apagado a mano no se filtra nada: ahí que no haya
        # título es lo esperado, no una falla.
        if not self.fetch_description:
            return jobs
        sirven = [j for j in jobs if j.description and j.title != _SIN_TITULO]
        if perdidos := len(jobs) - len(sirven):
            logger.info(f"[{self.name}] {perdidos} aviso(s) sin detalle, afuera: "
                        "sin la página del aviso no hay ni título ni empresa")

        # `PortalSource.fetch` filtra por antigüedad al final, y acá eso no tira
        # nada: Indeed no dice la fecha en ningún lado, y sin fecha `es_reciente`
        # deja pasar. La ventana ya la aplicó `fromage` del lado del portal.
        logger.info(f"[{self.name}] {len(sirven)} aviso(s) con detalle")
        return sirven
