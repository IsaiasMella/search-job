"""Modo consejo: qué reordenar del CV para este aviso, sin reescribirlo.

La distinción que ordena todo esto: **el CV que ya funciona no se toca.** Para quien pagó un curso y tiene evidencia de que su CV
anda, un CV generado por una máquina es un downgrade. Lo que sí sirve es que
alguien lea el aviso y le diga *qué reordenar* y *qué palabra le falta* para que
el filtro automático de la empresa (el ATS) no lo descarte antes de que un
humano lo lea. Es consejo, no generación: riesgo cero sobre lo que ya anda.

Dos capas, y la primera no necesita LLM:

1. **Palabras del aviso que no están en el CV.** Es tonto y es exactamente lo
   que hace un ATS: comparar texto contra texto. Sale gratis y ya dice bastante.
2. **El consejo escrito**, con el modelo leyendo el aviso y el CV. Agrega el
   orden (qué subir arriba de todo) y el criterio de qué NO tocar.
"""

import re
import unicodedata
from collections import Counter

from vacantia.llm import chat_with_llm, has_llm_credentials
from vacantia.log import get_logger
from vacantia.models import Job

logger = get_logger()

#: Palabras que aparecen en cualquier aviso y no dicen nada del puesto. No
#: pretende ser exhaustiva: sólo sacar el relleno más obvio para que la lista de
#: "te falta esto" no venga llena de "para", "with" y "equipo".
VACIAS = {
    # español
    "para", "con", "los", "las", "del", "que", "una", "uno", "por", "como",
    "sus", "nos", "este", "esta", "estos", "estas", "muy", "mas", "sobre",
    "entre", "desde", "hasta", "ser", "estar", "tener", "hacer", "puesto",
    "empresa", "trabajo", "equipo", "buscamos", "buscando", "vacante",
    "experiencia", "conocimiento", "conocimientos", "requisitos", "tareas",
    "funciones", "ofrecemos", "beneficios", "sueldo", "horario", "jornada",
    "anos", "ano", "nivel", "area", "sector", "perfil", "candidato", "persona",
    "somos", "sera", "seran", "deseable", "excluyente", "manejo", "capacidad",
    "actitud", "ganas", "parte", "todo", "todos", "cada", "otras", "otros",
    # inglés
    "the", "and", "for", "with", "you", "your", "our", "are", "will", "have",
    "this", "that", "from", "team", "work", "role", "job", "company", "about",
    "who", "what", "how", "were", "years", "year", "experience", "skills",
    "requirements", "responsibilities", "benefits", "position", "candidate",
    "strong", "good", "great", "help", "including", "such", "using", "well",
}

#: Una palabra suelta más corta que esto es ruido: buscar "IT" o "de" dentro de
#: un CV matchea cualquier cosa.
LARGO_MINIMO = 3

#: Dentro de un par sí valen las de dos letras, porque el par las desambigua:
#: "power bi", "ms project", "sap fi". Sueltas no significarían nada.
LARGO_MINIMO_EN_PAR = 2

_PALABRA_RE = re.compile(r"[a-z0-9+#.]+")


def _plano(texto: str) -> str:
    """Minúsculas y sin tildes. 'Análisis' y 'analisis' son la misma palabra."""
    nfkd = unicodedata.normalize("NFKD", (texto or "").lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _palabras(texto: str, minimo: int = LARGO_MINIMO) -> list[str]:
    return [
        limpia
        for p in _PALABRA_RE.findall(_plano(texto))
        if (limpia := p.strip(".")) and len(limpia) >= minimo and limpia not in VACIAS
    ]


def terminos_del_aviso(texto: str, limite: int = 40) -> list[str]:
    """Las palabras y pares de palabras que más se repiten en el aviso.

    Los pares importan: "power bi", "machine learning" o "seguridad e higiene"
    valen como término y por separado no dicen lo mismo.
    """
    # Dos pasadas: los pares se arman con las palabras cortas incluidas ("power
    # bi" se perdía porque "bi" tiene dos letras), las sueltas no.
    con_cortas = _palabras(texto, LARGO_MINIMO_EN_PAR)
    palabras = [p for p in con_cortas if len(p) >= LARGO_MINIMO]
    if not palabras:
        return []

    cuenta = Counter(palabras)
    pares = Counter(f"{a} {b}" for a, b in zip(con_cortas, con_cortas[1:]))
    # Un par que aparece dos veces pesa más que una palabra suelta que aparece
    # dos veces: es más específico.
    puntaje = {t: n for t, n in cuenta.items()}
    puntaje.update({t: n * 2 for t, n in pares.items() if n > 1})

    ordenados = sorted(puntaje.items(), key=lambda kv: (-kv[1], kv[0]))
    return [t for t, _ in ordenados[:limite]]


def faltan_en_el_cv(job: Job, cv: str, limite: int = 12) -> list[str]:
    """Términos del aviso que el CV no menciona. Es lo que mira un ATS.

    No dice "agregá esto": dice "esto no está". Si la persona no tiene esa
    experiencia, la respuesta correcta es no agregarla — mentir en el CV se
    descubre en la primera entrevista técnica.
    """
    texto = f"{job.display_title} {job.description}"
    cv_plano = _plano(cv)
    faltantes = []
    for termino in terminos_del_aviso(texto):
        if termino in cv_plano:
            continue
        # Un par cuyas dos palabras ya están sueltas en el CV no es un hueco
        # real: "machine learning" con "machine" y "learning" en el CV es
        # cuestión de redacción, no de experiencia.
        partes = termino.split()
        if len(partes) > 1 and all(p in cv_plano for p in partes):
            continue
        faltantes.append(termino)
        if len(faltantes) >= limite:
            break
    return faltantes


def cv_que_mejor_encaja(job: Job, cvs: list[dict]) -> str:
    """El id del CV al que le faltan menos términos del aviso. Sin llamar al modelo.

    Es la recomendación para las ofertas que se puntuaron antes de que el perfil
    tuviera varios CV, y el respaldo cuando el modelo no contesta cuál. Mira lo
    mismo que mira un ATS, qué palabras del aviso no aparecen en el CV, así que
    es tosca pero honesta: por eso la pantalla la marca como estimada.

    Empate, o aviso sin texto: gana el primero, que es el CV principal.
    """
    if not cvs:
        return ""
    mejor, menos = cvs[0]["id"], None
    for cv in cvs:
        # `limite` alto a propósito: con el tope de 12 de siempre, dos CV a los
        # que les faltan 15 y 30 términos empataban en 12.
        faltan = len(faltan_en_el_cv(job, cv.get("texto") or "", limite=40))
        if menos is None or faltan < menos:
            mejor, menos = cv["id"], faltan
    return mejor


PROMPT = """Sos alguien con experiencia en selección de personal mirando un aviso y un CV.

NO reescribas el CV. NO inventes experiencia. El CV que te paso funciona: la
tarea es decir qué mover y qué palabra falta para que el filtro automático de la
empresa (ATS) no lo descarte antes de que lo lea una persona.

Contestá en español, en tres bloques cortos y en texto plano:

QUÉ SUBIR
- 2 o 3 cosas que YA están en el CV y deberían quedar más arriba o más visibles
  para este aviso, diciendo por qué (qué pide el aviso que eso responde).

QUÉ PALABRA FALTA
- Términos del aviso que no aparecen en el CV Y que la persona claramente sabe
  hacer según el resto del CV, con la redacción exacta sugerida.
- Si el aviso pide algo que la persona NO tiene, decilo en una línea como riesgo,
  y NO sugieras agregarlo.

QUÉ NO TOCAR
- Una línea: qué parte del CV ya está bien para este aviso y conviene dejar como
  está.

Nunca más de 12 líneas en total. Sin adjetivos vacíos. Sin preámbulo.

AVISO ({empresa} — {puesto}):
{aviso}

CV:
{cv}"""


def consejo_con_llm(job: Job, cv: str, perfil: dict) -> tuple[str, bool]:
    """(texto del consejo, lo escribió el modelo).

    Nunca levanta: es un botón de la pantalla. Sin credenciales devuelve "" y la
    UI muestra sólo la lista de palabras faltantes, que ya sirve.
    """
    if not has_llm_credentials(perfil.get("llm", {})):
        return "", False
    prompt = PROMPT.format(
        empresa=job.company or "sin empresa",
        puesto=job.display_title,
        aviso=(job.description or "")[:3000],
        cv=(cv or "")[:3000],
    )
    try:
        texto = chat_with_llm(
            perfil["llm"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=900,
        )
    except Exception as e:
        logger.warning(f"[consejo] No pude generar el consejo ({e})")
        return "", False
    return (texto or "").strip(), bool(texto)
