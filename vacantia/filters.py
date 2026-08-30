"""Filtros de ubicación, modalidad e idioma, aplicados después del scoring.

**Regla transversal: lo que el aviso no dice, no filtra.** Si no aclara país,
ciudad, modalidad o idioma, la oferta pasa. Es preferible un falso positivo que
descartás leyendo dos líneas antes que perder una oferta buena porque quien la
publicó no completó un campo.

Los datos vienen de lo que el LLM extrae del aviso (`scoring.py`), no de
`companies.json`: ese archivo describe a la *empresa*. Globant publica ofertas
de Bologna y Pune bajo una entrada que dice "Buenos Aires, Argentina".

Sin LLM (scoring heurístico) no hay nada extraído, así que todo queda en "" y
estos filtros dejan pasar todo. Es deliberado: mejor no filtrar que filtrar mal.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from vacantia.log import get_logger
from vacantia.models import Job

logger = get_logger()

WORK_MODES = ("remote", "hybrid", "onsite")

# Orden CEFR. "Me piden inglés" empieza en B1 según el pedido del perfil.
CEFR_ORDER = ("a1", "a2", "b1", "b2", "c1", "c2")
DEFAULT_MAX_ENGLISH = "a2"  # todo lo que supere esto se considera "piden inglés"

# El LLM devuelve el país en español, pero conviene aguantar el nombre en
# inglés y las variantes más comunes por si se le escapa.
COUNTRY_ALIASES = {
    "argentina": {"argentina", "ar", "arg"},
    "espana": {"espana", "spain", "es", "esp"},
    "mexico": {"mexico", "mx", "mex"},
    "colombia": {"colombia", "co", "col"},
    "chile": {"chile", "cl", "chl"},
    "uruguay": {"uruguay", "uy", "ury"},
    "peru": {"peru", "pe", "per"},
    "brasil": {"brasil", "brazil", "br", "bra"},
    "estados unidos": {"estados unidos", "united states", "usa", "us", "eeuu"},
    "reino unido": {"reino unido", "united kingdom", "uk", "gb"},
    "alemania": {"alemania", "germany", "de", "deu"},
    "italia": {"italia", "italy", "it", "ita"},
    "francia": {"francia", "france", "fr", "fra"},
    "portugal": {"portugal", "pt", "prt"},
    "india": {"india", "in", "ind"},
}


# --- Red de seguridad determinista -----------------------------------------
# El LLM deja `english_level` vacio con frecuencia (en dos corridas sobre la
# misma oferta devolvio "C1" y luego ""). Esto no depende de el: busca en el
# texto del aviso una exigencia de ingles B1 o superior. "ingles basico" no
# dispara, porque A2 se considera aceptable.
#
# El texto se normaliza con norm() (minusculas, sin tildes) y se aplana a una
# sola linea, asi que los patrones no necesitan contemplar saltos ni acentos.
_ENG = "(?:ingles|english)"
_ALTO = ("(?:avanzado|advanced|fluido|fluent|nativo|native|proficient|"
         "proficiency|bilingue|bilingual|b1|b2|c1|c2|upper[ -]*intermediate|"
         "intermedio[ -]*alto|conversacional|conversational)")
_EXIGE = ("(?:requiere|required|require|necesario|excluyente|imprescindible|"
          "dominio|manejo|must)")

# El [^.]{0,N} acota la ventana a una misma oracion: evita que "espanol
# avanzado" en una frase se cruce con "ingles" de la siguiente.
_ENGLISH_REQ_RES = [
    re.compile(_ENG + "[^.]{0,60}" + _ALTO),
    re.compile(_ALTO + "[^.]{0,60}" + _ENG),
    re.compile(_EXIGE + "[^.]{0,40}" + _ENG),
    re.compile(_ENG + "[^.]{0,30}(?:required|mandatory|excluyente|is a must)"),
]


# Si dentro del fragmento aparece alguno de estos, la exigencia no es tal:
# "ingles basico, no excluyente" o "English is a plus" no piden ingles B1+.
_DESCARTA = re.compile(
    "(?:basico|basic|elemental|principiante|beginner|a1|a2"
    "|no excluyente|not required|no es excluyente|deseable|desirable"
    "|is a plus|nice to have|valorable|se valora|opcional|optional)"
)


def mentions_english_requirement(text: str) -> str:
    """Devuelve el fragmento que delata la exigencia de ingles, o ""."""
    if not text:
        return ""
    flat = " ".join(norm(text).split())
    for rx in _ENGLISH_REQ_RES:
        for m in rx.finditer(flat):
            # El desmentido suele caer fuera del fragmento que matchea
            # ("ingles avanzado deseable, no excluyente" matchea sólo las dos
            # primeras palabras), así que se evalúa la oración entera.
            ini = flat.rfind(".", 0, m.start()) + 1
            fin = flat.find(".", m.end())
            oracion = flat[ini : fin if fin != -1 else len(flat)]
            if _DESCARTA.search(oracion):
                continue
            return m.group(0)[:60]
    return ""


# --- Vacantes ya cubiertas -------------------------------------------------
# Un aviso cerrado sigue indexado y sigue llegando por las tres fuentes. No es
# ruido inocuo: se puntúa con el LLM (plata y cuota) y llega al Telegram como
# si fuera una oportunidad.
#
# Se busca en la URL, el título y la descripción, sobre el texto ya normalizado
# (minúsculas, sin tildes). En la URL los guiones se pasan a espacios, así
# ".../busqueda-cerrada/" también cae.
_CUBIERTA_RE = re.compile(
    # El relleno del medio es una lista corta y cerrada a propósito ("búsqueda
    # ya está cerrada", "posición ha sido cubierta"): dejar pasar cualquier
    # palabra haría que "búsqueda de un perfil senior cerrada" también matchee.
    r"(?:(?:vacante|puesto|posicion|busqueda|convocatoria|oferta|seleccion)\s+"
    r"(?:(?:ya|se|esta|fue|quedo|encuentra|ha|sido)\s+){0,3}"
    r"(?:cubiert[ao]|cerrad[ao]|finalizad[ao])"
    r"|ya (?:fue |esta )?cubiert[ao]"
    r"|no longer (?:accepting applications|available|open)"
    r"|(?:position|job|role|vacancy) (?:has been |is )?(?:filled|closed)"
    r"|applications (?:are )?closed)"
)


def filled_marker(job: Job) -> str:
    """El texto que delata que la vacante ya está cubierta, o "".

    Mira la URL, el título y la descripción — el aviso puede avisarlo en
    cualquiera de los tres.
    """
    url_texto = norm(job.url).replace("-", " ").replace("_", " ").replace("/", " ")
    for texto in (url_texto, norm(job.title), norm(job.description)):
        if not texto:
            continue
        m = _CUBIERTA_RE.search(" ".join(texto.split()))
        if m:
            return m.group(0)
    return ""


def drop_filled(jobs: list[Job]) -> tuple[list[Job], list[tuple[Job, str]]]:
    """Parte la lista en (sirven, ya cubiertas con su motivo).

    Se usa **antes** del scoring: puntuar una vacante cerrada es gastar una
    llamada al LLM para descartarla después.
    """
    kept, dropped = [], []
    for job in jobs:
        marca = filled_marker(job)
        (dropped.append((job, marca)) if marca else kept.append(job))
    if dropped:
        logger.info(f"Descartadas {len(dropped)} vacante(s) ya cubierta(s)")
        for job, marca in dropped:
            logger.debug(f"    cubierta ({marca!r}): {job.display_title[:45]} — {job.url}")
    return kept, dropped


def norm(text: str) -> str:
    """Minúsculas y sin tildes: 'Córdoba' y 'Cordoba' tienen que ser iguales."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text).strip().lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _as_list(value) -> list[str]:
    """Acepta 'Argentina', ['Argentina', 'España'] o vacío indistintamente."""
    if not value:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(v) for v in value if str(v).strip()]


def _country_matches(job_country: str, wanted: list[str]) -> bool:
    job_n = norm(job_country)
    if not job_n:
        return True  # el aviso no lo dice -> no filtra
    for w in wanted:
        w_n = norm(w)
        if job_n == w_n:
            return True
        # Alias en ambas direcciones: el perfil puede decir "España" y el
        # aviso "Spain", o al revés.
        for canonical, names in COUNTRY_ALIASES.items():
            if w_n in names and job_n in names:
                return True
    return False


def _city_matches(job_city: str, wanted: list[str]) -> bool:
    job_n = norm(job_city)
    if not job_n:
        return True  # el aviso no lo dice -> no filtra
    # Comparación por contención en ambos sentidos: el aviso puede decir
    # "Ciudad Autónoma de Buenos Aires" y el perfil "Buenos Aires".
    return any(
        job_n == (w_n := norm(w)) or w_n in job_n or job_n in w_n for w in wanted
    )


def passes_location(job: Job, cfg: dict) -> tuple[bool, str]:
    """país vacío -> cualquier lado. país -> todo el país. país+ciudad -> esa ciudad."""
    countries = _as_list(cfg.get("country"))
    cities = _as_list(cfg.get("city"))

    if not countries and not cities:
        return True, ""

    if countries and not _country_matches(job.country, countries):
        return False, f"país '{job.country}' fuera de {', '.join(countries)}"

    if cities and not _city_matches(job.city, cities):
        return False, f"ciudad '{job.city}' fuera de {', '.join(cities)}"

    return True, ""


def passes_work_mode(job: Job, cfg) -> tuple[bool, str]:
    """Lista de modalidades aceptadas. Vacía = todas. Sin dato en el aviso = pasa."""
    allowed = [norm(m) for m in _as_list(cfg)]
    if not allowed:
        return True, ""

    mode = norm(job.work_mode)
    if not mode or mode not in WORK_MODES:
        return True, ""  # el aviso no lo aclara -> pasa

    if mode not in allowed:
        return False, f"modalidad '{mode}' no está en {', '.join(allowed)}"
    return True, ""


def home_cities(cfg: dict) -> list[str]:
    """Las ciudades a las que la persona puede ir a trabajar en persona.

    Es una sola idea con dos nombres por historia: `city` es el campo de
    siempre y `home_city` el que se agregó después. Significan lo mismo y se
    acepta una lista — "Bahía Blanca, Punta Alta" para quien vive en el sur,
    "La Plata, Buenos Aires, CABA" para quien vive en el conurbano.

    **Sólo filtran presencial e híbrido.** Una oferta remota no se descarta por
    la ciudad: un remoto publicado desde Córdoba se trabaja igual desde Bahía
    Blanca.
    """
    return _as_list(cfg.get("city")) or _as_list(cfg.get("home_city"))


def passes_place(job: Job, location_cfg: dict, modes_cfg) -> tuple[bool, str, str]:
    """Ubicación y modalidad, evaluadas **juntas** — la regla de Bahía Blanca.

    El país y la ciudad no filtran lo mismo, y ahí está toda la regla:

      - **El país filtra siempre, también al remoto.** "Remoto" no quiere decir
        "desde cualquier parte del mundo": Argentina es enorme y muchísimas
        búsquedas remotas de Buenos Aires o Córdoba son para todo el país, que
        es justo lo que se busca. Al revés, un remoto de Colombia o México suele
        ser remoto *para Colombia o México* por temas legales de contratación, y
        traerlo es ruido puro. País vacío en el perfil = todo el mundo.
      - **La ciudad filtra sólo presencial e híbrido.** Un remoto publicado
        desde Córdoba se trabaja igual desde Bahía Blanca, así que descartarlo
        por ciudad sería perder una oferta buena. Ciudad vacía = cualquier lugar
        del país.
      - **Presencial o híbrido en las ciudades de uno entra aunque `work_modes`
        pida sólo remoto.** Es el caso que dio nombre a la regla: quien pone
        sólo remoto lo hace porque no se muda, no porque le moleste salir de su
        casa, y un presencial *en su ciudad* le sirve igual. Exige que el aviso
        *diga* la ciudad: si no la dice no se asume que sea la de uno, porque
        ahí el falso positivo sería sistemático.

    `location.remote_anywhere: true` vuelve al comportamiento viejo, donde el
    remoto ignora el país. Por defecto está apagado.

    Devuelve (pasa, motivo, etiqueta) — la etiqueta es "location" o "work_mode",
    para que FilterStats siga contando por dónde se cayó cada oferta.
    """
    mode = norm(job.work_mode)
    if mode not in WORK_MODES:
        mode = ""  # el aviso no lo aclara
    allowed = [norm(m) for m in _as_list(modes_cfg)]
    countries = _as_list(location_cfg.get("country"))
    ciudades = home_cities(location_cfg)

    def pais_ok() -> tuple[bool, str, str]:
        if countries and not _country_matches(job.country, countries):
            return False, f"país '{job.country}' fuera de {', '.join(countries)}", "location"
        return True, "", ""

    # 1) Remoto: filtra el país, no la ciudad.
    if mode == "remote":
        if allowed and "remote" not in allowed:
            return False, f"modalidad 'remote' no está en {', '.join(allowed)}", "work_mode"
        if location_cfg.get("remote_anywhere", False):
            return True, "", ""
        return pais_ok()

    # El país filtra en todos los casos, sea cual sea la modalidad.
    ok, why, etiqueta = pais_ok()
    if not ok:
        return False, why, etiqueta

    # 2) Presencial/híbrido en una de las ciudades de uno: entra aunque
    #    work_modes no lo liste. Es la excepción que da nombre a la regla.
    if mode in ("hybrid", "onsite") and job.city and ciudades:
        if _city_matches(job.city, ciudades):
            logger.debug(
                f"    regla de Bahía Blanca: '{job.display_title[:45]}' es {mode} "
                f"en {job.city} — pasa aunque work_modes pida {allowed or 'todas'}"
            )
            return True, "", ""

    ok, why = passes_work_mode(job, modes_cfg)
    if not ok:
        return False, why, "work_mode"

    # 3) La ciudad, sólo para lo que exige estar ahí. Si el aviso no dice de qué
    #    ciudad es, pasa: puede ser remoto sin aclararlo.
    if mode in ("hybrid", "onsite") and ciudades and job.city:
        if not _city_matches(job.city, ciudades):
            return False, f"ciudad '{job.city}' fuera de {', '.join(ciudades)}", "location"
    return True, "", ""


def _english_level_rank(level: str) -> int:
    """-1 si no pide inglés o no se sabe; si no, la posición en CEFR_ORDER."""
    lvl = norm(level)[:2]
    return CEFR_ORDER.index(lvl) if lvl in CEFR_ORDER else -1


def passes_language(job: Job, cfg: dict) -> tuple[bool, str]:
    """allow_english=True deja pasar español e inglés.

    allow_english=False deja pasar sólo avisos en español, y además descarta
    los que piden inglés B1 o superior: si el aviso está en español pero exige
    inglés B2, en los hechos te están pidiendo inglés.
    """
    if cfg.get("allow_english", True):
        return True, ""

    # Capa 1 — el idioma del aviso. Si está escrito en inglés, en los hechos
    # te van a pedir inglés.
    lang = norm(job.posting_language)[:2]
    if lang and lang != "es":
        return False, f"aviso en '{lang}' y el inglés está desactivado"

    # Capa 2 — el juicio directo del LLM, que sí contesta aunque el aviso sea
    # vago (a diferencia de english_level, que deja vacío).
    if job.requires_english is True:
        return False, "el LLM juzga que el puesto exige inglés"

    # Capa 3 — el nivel CEFR, cuando lo extrajo.
    max_rank = _english_level_rank(cfg.get("max_english_level", DEFAULT_MAX_ENGLISH))
    if _english_level_rank(job.english_level) > max_rank:
        return False, f"pide inglés {job.english_level.upper()}"

    # Capa 4 — red determinista sobre el texto, por si las tres anteriores
    # fallaron. No depende del LLM.
    if cfg.get("scan_description", True):
        hit = mentions_english_requirement(job.description)
        if hit:
            return False, f"la descripción pide inglés ({hit!r})"

    return True, ""


@dataclass
class FilterStats:
    """Qué se descartó y por qué. Lo consume el informe de la notificación."""

    kept: int = 0
    dropped: int = 0
    by_reason: Counter = field(default_factory=Counter)
    #: Descartadas por el filtro de idioma, ya puntuadas. Sirve para mostrar
    #: cuánto valía lo que te perdiste por no saber inglés.
    english_dropped: list[Job] = field(default_factory=list)

    @property
    def english_count(self) -> int:
        return len(self.english_dropped)

    @property
    def english_best(self) -> Job | None:
        """La mejor puntuada de las que se cayeron por idioma."""
        return max(self.english_dropped, key=lambda j: j.score or 0, default=None)


def english_pain_lines(stats: FilterStats, limit: int = 3) -> list[str]:
    """Resumen en texto plano de lo que costó no saber inglés.

    Existe por pedido explícito: ver sólo las ofertas en español da la impresión
    de que el mercado es así, cuando en realidad lo que se ve es el recorte que
    deja el filtro. Esto pone el número adelante.
    """
    if not stats.english_dropped:
        return []

    total = stats.english_count
    lines = [f"{total} oferta(s) descartadas por estar en inglés o pedir inglés."]

    mejores = sorted(stats.english_dropped, key=lambda j: j.score or 0, reverse=True)
    best = mejores[0]
    if best.score is not None:
        lines.append(f"La mejor de esas puntuaba {best.score}.")

    for job in mejores[:limit]:
        if (job.score or 0) <= 0:
            continue
        lines.append(f"  [{job.score}] {job.display_title[:60]}")
    return lines


def apply_filters(jobs: list[Job], profile: dict) -> tuple[list[Job], FilterStats]:
    """Aplica los tres filtros. Devuelve (las que pasan, estadísticas)."""
    stats = FilterStats()
    cfg = profile.get("filters") or {}
    if not cfg:
        stats.kept = len(jobs)
        return jobs, stats

    location_cfg = cfg.get("location") or {}
    modes_cfg = cfg.get("work_modes")
    language_cfg = cfg.get("language") or {}

    kept: list[Job] = []
    dropped: list[tuple[Job, str]] = []
    for job in jobs:
        # Ubicación y modalidad van juntas (regla de Bahía Blanca), el idioma
        # aparte. `passes_place` ya devuelve con qué etiqueta contar el descarte.
        ok, why, etiqueta = passes_place(job, location_cfg, modes_cfg)
        if not ok:
            dropped.append((job, why))
            stats.by_reason[etiqueta] += 1
            continue

        ok, why = passes_language(job, language_cfg)
        if not ok:
            dropped.append((job, why))
            stats.by_reason["language"] += 1
            stats.english_dropped.append(job)
            continue

        kept.append(job)

    stats.kept, stats.dropped = len(kept), len(dropped)
    if dropped:
        logger.info(f"Filtros: {len(kept)} pasaron, {len(dropped)} descartadas")
        for job, why in dropped:
            logger.debug(f"    descartada: {job.display_title[:45]} — {why}")
    return kept, stats
