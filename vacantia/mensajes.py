"""Los mensajes para escribirle a quien publicó una búsqueda.

Están calcados de los que Isaías usa de verdad y con los que lo contactaron.
**No son una plantilla que se rellena con `str.format`**: la parte que importa
es la lista de requisitos, y ésa cambia con cada aviso porque hay que cruzar lo
que la búsqueda pide contra lo que el CV dice. Eso lo escribe el modelo.

Dos formatos, porque son dos situaciones distintas:

- **DM por LinkedIn**: se lee en el celular. Va con la lista de tildes, que es
  lo que hace que se entienda de un vistazo que el candidato encaja.
- **Mail**: lleva asunto y da por hecho que el CV va adjunto.

Lo que el modelo NO decide, porque lo sabe mejor el código:

- **El saludo del cierre** sale del día de la semana (ver `cierre_del_dia`). Un
  modelo no sabe qué día es hoy y lo inventa.
- **El nombre y el rol del candidato** salen del perfil.
- **El nombre de quien publicó** sale del aviso.

Sin credenciales del modelo, el mensaje sale igual con los huecos marcados. Es
peor, pero deja claro qué falta y no se rompe nada.
"""

from datetime import date

from vacantia.llm import chat_with_llm, has_llm_credentials
from vacantia.log import get_logger
from vacantia.models import Job

logger = get_logger()

#: Cómo se cierra según el día. Es lo que Isaías escribe a mano: el lunes se
#: desea el comienzo, a mitad de semana el transcurso, y jueves y viernes ya es
#: el tramo final. Un modelo no sabe en qué día está, así que esto no se
#: delega: se calcula acá y se le pasa hecho.
CIERRE_POR_DIA = {
    0: "buen comienzo de semana",
    1: "buen transcurso de semana",
    2: "buen transcurso de semana",
    3: "buen último sprint de la semana",
    4: "buen último sprint de la semana",
    5: "buen fin de semana",
    6: "buen fin de semana",
}


def cierre_del_dia(hoy: date | None = None) -> str:
    """'buen comienzo de semana' | 'buen transcurso...' | 'buen último sprint...'"""
    return CIERRE_POR_DIA[(hoy or date.today()).weekday()]


MOLDE_DM = """Hola {nombre}!!

Mi nombre es {candidato}, soy {rol}.

Vi la publicación de la búsqueda para {puesto} y me interesó un montón, me \
gustaría acercarte mi CV y comentarte que cumplo con los requisitos:

{requisitos}

Además de algunas tecnologías más que están especificadas en el CV.

En caso de tener alguna consulta no dudes en hacérmela llegar, yo encantado de \
responder.

Desde ya muchísimas gracias por tu tiempo y {cierre} 😁!!"""

MOLDE_MAIL = """Asunto: {puesto} - {candidato}

¡Hola {nombre}!

Mi nombre es {candidato}, soy {rol}.

Mientras buscaba en LinkedIn, me encontré con tu publicación de una vacante y \
sé que puedo ser un buen candidato para el puesto.

Manejo {tecnologias} y otras tecnologías que podrás ver en mi CV adjunto. \
Estoy seguro de que estas habilidades pueden ser un gran aporte para el equipo.

¿Por qué deberías considerarme?
Además de cumplir con la mayoría de los requisitos que mencionás, siempre estoy \
dispuesto a aprender y adaptarme a nuevos desafíos.

Agradezco de antemano tu tiempo y consideración.

Espero podamos hablar pronto y que tengas {cierre} {nombre}!"""

#: Lo que hace que estos mensajes funcionen, sacado de los que ya sirvieron.
#: Va al prompt tal cual: es la parte que no se puede templatear.
REGLAS = """1. Los requisitos con tilde son el corazón del mensaje. Cada uno tiene que ser
   algo que el AVISO pide Y que el CV respalda. Entre 3 y 6, en el orden en que
   el aviso los nombra, escritos cortos y en primera persona del presente
   ("Trabajo con Python", "Manejo de LangChain para orquestar los modelos").
   Cada línea arranca con el caracter ✔️ y nada más. Ni guiones, ni viñetas,
   ni números: el tilde verde es lo que hace que se lea de un vistazo.
2. **Prohibido listar algo que el CV no diga.** No es un problema de honestidad
   nada más: se cae en la primera entrevista y quema el contacto. Si el aviso
   pide seis cosas y el CV cubre tres, van tres.
3. Cero adjetivos sobre uno mismo. "Proactivo", "apasionado", "orientado a
   resultados" son ruido: los pone todo el mundo y no dicen nada.
4. El nombre de pila solo, sin apellido: "Hola Jazmín", no "Hola Jazmín Pérez".
   Si el aviso no dice quién publicó, va "Hola!" sin nombre.
5. El puesto va corto y limpio, como lo diría una persona: "Machine Learning
   Engineer Sr", "Analista de Datos". El título que viene guardado suele traer
   pegada media publicación ("Buscamos Desarrollador/a ML si tenés +5 años
   de...") y así no se puede usar: sacalo del aviso y recortalo.
6. No cambiar el tono ni la estructura del molde. Está probado."""

TIPOS = {"dm": "DM por LinkedIn", "mail": "Mail a RRHH"}


def _rol(perfil: dict) -> str:
    """Cómo se presenta el candidato: "soy AI Engineer".

    Es un campo aparte del "en una línea, qué hago" porque no es lo mismo: ahí
    la gente escribe un párrafo con el stack entero, y en el mensaje tiene que
    entrar en media frase. Si no está cargado se recorta el otro, que sale
    torcido pero no rompe la frase.
    """
    cand = perfil.get("candidate") or {}
    if titulo := (cand.get("headline") or "").strip():
        return titulo
    linea = (cand.get("profile") or "").strip()
    return linea.split(".")[0].split(",")[0].strip()[:45]


def _nombre_de_pila(quien: str) -> str:
    """'Jazmín Pérez' -> 'Jazmín'. En un DM el apellido suena a formulario."""
    return (quien or "").strip().split(" ")[0]


def molde(job: Job, perfil: dict, tipo: str = "dm", hoy: date | None = None) -> str:
    """El mensaje con lo que ya sabemos puesto, y el resto entre llaves.

    Es lo que se muestra antes de apretar el botón de completar con el modelo, y
    lo que queda si el modelo no está disponible. Los huecos van a la vista a
    propósito: es más honesto que un mensaje genérico disfrazado de escrito a
    mano, y se ve de un golpe qué hay que completar.

    `job.company` en las fuentes `google_posts` y `rrhh` es la persona que
    publicó, que es justo a quien hay que escribirle.
    """
    cand = perfil.get("candidate") or {}
    datos = {
        "nombre": _nombre_de_pila(job.company) or "{nombre de quien publicó}",
        "puesto": job.display_title or "{el puesto del aviso}",
        "candidato": cand.get("name") or "{tu nombre}",
        "rol": _rol(perfil) or "{cómo te presentás: AI Engineer, Analista...}",
        "cierre": cierre_del_dia(hoy),
        "requisitos": ("✔️ {un requisito del aviso que tu CV respalde}\n"
                       "✔️ {otro}\n"
                       "✔️ {otro más, entre 3 y 6 en total}"),
        "tecnologias": "{las tecnologías del aviso que sí manejás, separadas por coma}",
    }
    plantilla = MOLDE_MAIL if tipo == "mail" else MOLDE_DM
    return plantilla.format(**datos)


def _prompt(job: Job, cv: str, perfil: dict, tipo: str, hoy: date | None = None) -> str:
    formato = MOLDE_MAIL if tipo == "mail" else MOLDE_DM
    cand = perfil.get("candidate") or {}
    return f"""Escribí el mensaje con el que este candidato le escribe a quien publicó esta búsqueda.

FORMATO EXACTO. Copialo tal cual y reemplazá SÓLO lo que está entre llaves:
{formato}

REGLAS:
{REGLAS}
7. Escribí en el mismo idioma del aviso.
8. Devolvé SÓLO el mensaje, sin comillas, sin preámbulo y sin explicaciones.

DATOS QUE YA ESTÁN RESUELTOS, no los cambies:
- nombre (quien publicó): {_nombre_de_pila(job.company) or 'no figura, usá "Hola!" sin nombre'}
- candidato: {cand.get('name', '')}
- rol: {_rol(perfil)}
- cierre: {cierre_del_dia(hoy)}

EL PUESTO lo sacás vos del aviso, corto y limpio (regla 5). Como referencia, el
título que quedó guardado es: {job.display_title}

AVISO:
{(job.description or '')[:2000]}

CV DEL CANDIDATO (de acá salen los requisitos con tilde, y de ningún otro lado):
{(cv or '')[:3000]}"""


def generar(job: Job, cv: str, perfil: dict, tipo: str = "dm",
            hoy: date | None = None) -> tuple[str, bool]:
    """(texto, lo_escribió_el_modelo).

    Sin credenciales, o si la llamada falla, devuelve el molde con los huecos a
    la vista. Nunca levanta: es un botón de la pantalla, no puede tirarla.
    """
    if not has_llm_credentials(perfil.get("llm", {})):
        return molde(job, perfil, tipo, hoy), False
    try:
        texto = chat_with_llm(
            perfil["llm"],
            messages=[{"role": "user", "content": _prompt(job, cv, perfil, tipo, hoy)}],
            temperature=0.4,
            max_tokens=900,
        )
    except Exception as e:
        logger.warning(f"[mensajes] No pude generar el mensaje ({e}) — devuelvo el molde")
        return molde(job, perfil, tipo, hoy), False
    return (texto or "").strip() or molde(job, perfil, tipo, hoy), bool(texto)
