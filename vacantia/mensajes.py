"""Moldes de mensaje para escribirle a un reclutador o a RRHH.

**Son borradores**: hay que ajustarlos contra la experiencia de quien los usa,
que es más fresca que la de quien los escribió.

Dos formatos, porque son dos situaciones distintas:

- **DM por LinkedIn**: máximo 4 líneas. Lo leen en el celular entre 200
  mensajes.
- **Mail a una consultora o a RRHH**: asunto + cuerpo corto + CV adjunto.

Lo que va entre `{llaves}` lo completa el LLM leyendo el aviso y el CV; sin
credenciales, el molde sale con los huecos a la vista para completar a mano —
que es mejor que no tener nada, y deja claro qué falta.

Sobre la carta de presentación formal de una carilla: en Argentina casi no se
usa, así que no hay molde. Lo que mueve la aguja es el mensaje corto.
"""

from vacantia.llm import chat_with_llm, has_llm_credentials
from vacantia.log import get_logger
from vacantia.models import Job

logger = get_logger()

MOLDE_DM = """Hola {nombre}, vi la búsqueda de {puesto}.
Trabajo con {area} hace {anios} años; lo último fue {logro}.
¿Te sirve que te pase el CV?"""

MOLDE_MAIL = """Asunto: {puesto} — {candidato}

Hola, escribo por la búsqueda de {puesto}.

{linea_experiencia}
{logro}

Adjunto el CV. Quedo a disposición.
{candidato}{telefono}"""

#: Las tres reglas que hacen que estos mensajes funcionen. Van al prompt tal
#: cual: son la parte que no se puede templatear.
REGLAS = """1. El logro lo elegís vos leyendo el aviso: tiene que ser el más cercano a lo
   que la búsqueda pide, con número si el CV tiene uno. Es lo único que
   distingue un mensaje genérico de uno escrito para esa búsqueda.
2. Cero adjetivos sobre uno mismo. "Proactivo", "apasionado", "orientado a
   resultados" son ruido: los pone todo el mundo y no dicen nada.
3. Nunca más de 4 líneas, y cerrar con una pregunta fácil de responder."""

TIPOS = {"dm": "DM por LinkedIn", "mail": "Mail a RRHH"}


def _telefono(perfil: dict) -> str:
    tel = (perfil.get("candidate") or {}).get("phone") or ""
    return f" — {tel}" if tel else ""


def molde(job: Job, perfil: dict, tipo: str = "dm") -> str:
    """El molde con lo que ya sabemos puesto, y el resto entre llaves.

    `job.company` en las fuentes `google_posts` y `rrhh` es la persona que
    publicó, que es justo a quien hay que escribirle.
    """
    cand = perfil.get("candidate") or {}
    datos = {
        "nombre": job.company or "{nombre}",
        "puesto": job.display_title or "{puesto}",
        "candidato": cand.get("name") or "{tu nombre}",
        "telefono": _telefono(perfil),
        "area": "{el área o la tecnología principal que pide el aviso}",
        "anios": "{X}",
        "logro": "{tu logro más cercano a lo que pide el aviso, con número si hay}",
        "linea_experiencia": "{una línea: años de experiencia + la habilidad central que pide el aviso}",
    }
    plantilla = MOLDE_MAIL if tipo == "mail" else MOLDE_DM
    return plantilla.format(**datos)


def _prompt(job: Job, cv: str, perfil: dict, tipo: str) -> str:
    formato = MOLDE_MAIL if tipo == "mail" else MOLDE_DM
    cand = perfil.get("candidate") or {}
    return f"""Escribí el mensaje con el que este candidato le escribe a quien publicó esta búsqueda.

FORMATO EXACTO A SEGUIR (reemplazá lo que está entre llaves, no agregues nada más):
{formato}

REGLAS:
{REGLAS}
4. Escribí en el mismo idioma del aviso.
5. No inventes experiencia que no esté en el CV. Si el CV no tiene un logro con
   número, usá el más concreto que haya.
6. Devolvé SÓLO el mensaje, sin comillas, sin preámbulo y sin firma extra.

CANDIDATO: {cand.get('name', '')} — {cand.get('profile', '')}
QUIEN PUBLICÓ: {job.company or 'no figura'}
PUESTO: {job.display_title}

AVISO:
{(job.description or '')[:2000]}

CV:
{(cv or '')[:2500]}"""


def generar(job: Job, cv: str, perfil: dict, tipo: str = "dm") -> tuple[str, bool]:
    """(texto, lo_escribió_el_LLM).

    Sin credenciales —o si la llamada falla— devuelve el molde con los huecos a
    la vista. Nunca levanta: es un botón de la UI, no puede tirar la pantalla.
    """
    if not has_llm_credentials(perfil.get("llm", {})):
        return molde(job, perfil, tipo), False
    try:
        texto = chat_with_llm(
            perfil["llm"],
            messages=[{"role": "user", "content": _prompt(job, cv, perfil, tipo)}],
            temperature=0.4,
            max_tokens=600,
        )
    except Exception as e:
        logger.warning(f"[mensajes] No pude generar el mensaje ({e}) — devuelvo el molde")
        return molde(job, perfil, tipo), False
    return (texto or "").strip() or molde(job, perfil, tipo), bool(texto)
