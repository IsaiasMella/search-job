"""Las pestañas "Mi perfil" y "Configuración": dibujar cada formulario y volcarlo.

Es lo que evita tener que editar `profiles/<nombre>.json` a mano. Escribe sobre
cuatro lugares distintos según el campo: el perfil, `resume/<nombre>.md`,
`companies.json` y `.env`.

**Eran una sola pantalla y se partió en dos** por lo seguido que se toca cada
cosa. Mi perfil es lo que cambia mientras buscás: los CV, las palabras, dónde,
las empresas. Configuración es lo que se carga una vez y no se vuelve a mirar:
las claves, el Telegram, las fuentes, los topes. Juntos, lo de todos los días
quedaba enterrado entre claves que nadie tenía que tocar.

El JSON del perfil no cambió de forma: sólo cambió qué pantalla edita qué campo.
Y **cada pantalla guarda sólo sus campos**: ver `aplicar_datos`.

**Lo que se explica una vez va detrás del signo de pregunta**, no suelto abajo
del campo. Había un "Cómo funciona esto" debajo de cada campo con historia y un
recuadro de catorce renglones debajo de las URLs de reclutadores: la pantalla
se leía como un manual, y los campos, que son lo que se viene a tocar, quedaban
perdidos entre explicaciones.
"""

from vacantia.filters import home_cities
from vacantia.log import get_logger
from vacantia.ui import data
from vacantia.ui.render import _ayuda_al_lado, _rotulo_con_ayuda, _tilde_con_ayuda, avisos, esc

logger = get_logger()

MODALIDADES = (("remote", "Remoto"), ("hybrid", "Híbrido"), ("onsite", "Presencial"))
NIVELES = ("A1", "A2", "B1", "B2", "C1", "C2")

# Qué página sirve. El perfil de LinkedIn ahora anda, pero por un rodeo: no se
# entra al perfil (LinkedIn no deja), se buscan sus posts en Google. Eso es
# invisible para quien carga la URL, y así tiene que quedar. Lo que se sigue
# equivocando cualquiera es la página de una consultora: no va la de inicio, va
# la que lista los puestos. El error es mudo, la fuente devuelve 0 y parece rota.
EJEMPLO_RRHH = """https://www.linkedin.com/in/nombre-apellido
https://consultora.com.ar/busquedas-activas"""

#: Los tres ejemplos que se ven siempre, abajo del cuadro. Es lo que hay que
#: recordar cada vez que se pega una URL, y por eso no va escondido: dos que
#: sirven y el error de siempre, en una línea cada uno. Antes era un recuadro
#: con viñetas, SÍ y NO en colores y tres párrafos, que pesaba más que el campo.
#: "Sirve" va en neutro: el verde en este sistema es lo que ya hiciste. "No
#: sirve" sí va en rojo, porque es exactamente el valor equivocado.
EJEMPLOS_RRHH = """<ul class="ejemplos" aria-label="Qué página pegar">
  <li><span class="bien">Sirve</span><code>linkedin.com/in/nombre-apellido</code><span>el perfil de la persona</span></li>
  <li><span class="bien">Sirve</span><code>consultora.com.ar/busquedas-activas</code><span>la página que lista los puestos</span></li>
  <li><span class="mal">No sirve</span><code>consultora.com.ar</code><span>la página de inicio</span></li>
</ul>"""

#: El porqué de los ejemplos, detrás del signo de pregunta: se lee una vez.
AYUDA_RRHH = (
    "Una por línea. LinkedIn no deja leer los perfiles desde afuera: en vez de "
    "entrar, se buscan sus publicaciones en Google. De una consultora va la "
    "página que lista los puestos, que suele llamarse Búsquedas activas, "
    "Trabajá con nosotros o Empleos. Si el registro dice 0 publicación(es), casi "
    "siempre se pegó la página de inicio."
)


#: Fuentes que se pueden prender y apagar desde la UI. Agregar una fuente nueva
#: al sistema es agregar una línea acá.
#:
#: (clave, etiqueta, nota). La nota va en el signo de pregunta al lado del
#: tilde: hay cosas que no se pueden adivinar desde el nombre, pero abajo de
#: cada tilde descolocaban la lista entera.
FUENTES = (
    ("careers", "Páginas de empleo de las empresas que sigo", ""),
    ("google_posts", "Publicaciones de LinkedIn (vía buscador, no toca LinkedIn)", ""),
    ("linkedin", "LinkedIn Jobs", ""),
    ("rrhh", "Perfiles de reclutadores que sigo", ""),
    ("bumeran", "Bumeran", "Misma base de avisos que Zonajobs."),
    ("zonajobs", "Zonajobs",
     "Misma base de avisos que Bumeran: prendé uno de los dos, o vas a recibir "
     "todo duplicado."),
    ("computrabajo", "Computrabajo", ""),
    ("indeed", "Indeed", "Los avisos que no dicen la fecha entran igual: la "
                         "antigüedad se la pide el propio Indeed."),
    ("getonbrd", "Get on Board",
     "La única que no necesita ninguna clave: sigue trayendo aunque falten las "
     "credenciales. Es sobre todo chilena, así que se le piden los avisos que "
     "aplican a la Argentina, que casi siempre son remotos."),
)

#: Cómo se agrupan en la pantalla. Son dos clases de cosa distintas: los
#: portales traen lo que publica cualquiera, y lo que seguís depende de listas
#: que cargaste en Mi perfil. Una fuente nueva que no esté acá cae en portales.
GRUPOS_DE_FUENTES = (
    ("Portales de empleo", ("linkedin", "bumeran", "zonajobs", "computrabajo",
                            "indeed", "getonbrd")),
    ("Lo que seguís", ("careers", "rrhh", "google_posts")),
)


def _campo(nombre, etiqueta, valor, tipo="text", ayuda="", mas="", **extra) -> str:
    """Un campo con su rótulo. `mas` es la explicación larga: va en el signo de
    pregunta, y `ayuda` es la línea corta que se lee siempre."""
    attrs = " ".join(f'{k}="{esc(v)}"' for k, v in extra.items())
    rotulo = f'<label for="{nombre}">{esc(etiqueta)}</label>'
    if mas:
        rotulo = _rotulo_con_ayuda(rotulo, mas)
    return f"""<div class="campo">
  {rotulo}
  <input type="{tipo}" id="{nombre}" name="{nombre}" value="{esc(valor)}" {attrs}>
  {f'<p class="ayuda">{esc(ayuda)}</p>' if ayuda else ''}
</div>"""


def _area(nombre, etiqueta, valor, filas=8, ayuda="", placeholder="", mas="",
          debajo="") -> str:
    """`debajo` va como HTML tal cual, después de la ayuda: los ejemplos de qué
    pegar, o el aviso de que la fuente está apagada."""
    ph = f' placeholder="{esc(placeholder)}"' if placeholder else ""
    rotulo = f'<label for="{nombre}">{esc(etiqueta)}</label>'
    if mas:
        rotulo = _rotulo_con_ayuda(rotulo, mas)
    return f"""<div class="campo ancho">
  {rotulo}
  <textarea id="{nombre}" name="{nombre}" rows="{filas}"{ph}>{esc(valor)}</textarea>
  {f'<p class="ayuda">{esc(ayuda)}</p>' if ayuda else ''}
  {debajo}
</div>"""


def _check(nombre, etiqueta, marcado) -> str:
    return (f'<label><input type="checkbox" name="{nombre}" value="1"'
            f'{" checked" if marcado else ""}> {esc(etiqueta)}</label>')


def _lista(valor) -> str:
    if isinstance(valor, list):
        return ", ".join(str(v) for v in valor)
    return str(valor or "")


def _plural(n: int, uno: str, varios: str) -> str:
    return f"{n} {uno if n == 1 else varios}"


def _activa(perfil: dict, tipo: str) -> bool:
    return any(s.get("type") == tipo and s.get("enabled", True)
               for s in perfil.get("sources") or [])


def _fuente_apagada(nombre: str, perfil: dict, tipo: str) -> str:
    """La línea que avisa que lo cargado no se usa, sólo si de verdad no se usa.

    Antes el recordatorio de "tiene que estar tildado" se veía siempre, con la
    fuente prendida o no. Un aviso que está siempre deja de leerse, y justo el
    día que hace falta ya nadie lo mira.
    """
    if _activa(perfil, tipo):
        return ""
    etiqueta = dict((t, e) for t, e, _ in FUENTES)[tipo]
    return (f'<p class="ayuda apagada">No se usan hasta que prendas <b>{esc(etiqueta)}</b> '
            f'en <a href="/configuracion?perfil={esc(nombre)}">Configuración</a>.</p>')


def _selector_de_cv(cvs: list[dict], elegido: str) -> str:
    """El desplegable para cambiar de CV. Con un solo CV, sólo el campo escondido.

    Se ve un CV por vez porque con cinco o seis, uno abajo del otro con su texto
    entero, la pantalla era una columna interminable y no se encontraba nada.

    `cv_elegido` viaja con el formulario: así, después de guardar, agregar o
    borrar, la pantalla vuelve al CV que estabas mirando y no siempre al primero.
    El desplegable no tiene `name` a propósito, para no mandarse dos veces.
    """
    oculto = f'<input type="hidden" name="cv_elegido" value="{esc(elegido)}">'
    if len(cvs) < 2:
        return oculto
    opciones = "".join(
        f'<option value="{esc(cv["id"])}"{" selected" if cv["id"] == elegido else ""}>'
        f'{esc(cv["nombre"])}</option>'
        for cv in cvs
    )
    return f"""<div class="selector-de-cv">
  <label for="cv-elegido">Estás viendo el CV</label>
  <select id="cv-elegido" onchange="elegirCv(this.value)">{opciones}</select>
  <span class="cuantos">{len(cvs)} cargados</span>
  {oculto}
</div>"""


def _bloque_de_cv(cv: dict, cuantos: int, activo: bool = False) -> str:
    """Un CV: cómo se llama, qué buscar con él, y el texto.

    Los botones de agregar y borrar van **adentro del formulario grande** y no
    en uno propio, con `formaction`. Es a propósito: un formulario no puede ir
    adentro de otro, y si fueran aparte, apretar "Agregar otro CV" perdería todo
    lo que estabas escribiendo sin guardar. Así primero se guarda y después se
    agrega o se borra.

    **Borrar pide confirmación** y es definitivo: se va el CV y su texto. La
    confirmación se abre adentro del mismo bloque, con un `<details>`, en vez de
    un cartel del navegador: el cartel tapa la pantalla y no deja ver qué CV se
    está por borrar, que es justo lo que hay que mirar antes de confirmar.

    Con un solo CV no hay botón de borrar: tiene que quedar al menos uno.
    """
    prefijo = f"cv_{cv['id']}_"
    borrar = "" if cuantos < 2 else f"""<details class="borrar-cv">
    <summary>Borrar este CV</summary>
    <div class="cuerpo">
      <p>Se borra <b>{esc(cv['nombre'])}</b> con todo su texto, y no se puede recuperar.</p>
      <button class="peligro" type="submit" formaction="/cv-borrar" name="cv_borrar"
              value="{esc(cv['id'])}">Sí, borrar definitivamente</button>
      <button class="fantasma" type="button"
              onclick="this.closest('details').open = false">Cancelar</button>
    </div>
  </details>"""
    clase = "grilla cv activo" if activo else "grilla cv"
    return f"""<div class="{clase}" id="cv-{esc(cv['id'])}">
  {_campo(prefijo + "nombre", "Nombre de este CV", cv["nombre"], placeholder="Full Stack",
          ayuda="Es el que aparece en cada oferta: “Mandá tu CV Full Stack”.")}
  {_campo(prefijo + "palabras", "Qué buscar con este CV", _lista(cv["palabras_clave"]),
          placeholder="Full Stack, React, Next.js",
          ayuda="Separadas por coma. Se suman a las palabras clave en todos los portales.")}
  {_area(prefijo + "texto", "El CV", cv["texto"], 14,
         ayuda="Texto plano o Markdown. Cuanto más concreto, mejor puntúa.")}
  {borrar}
</div>"""


# --- Mi perfil: lo que se toca seguido --------------------------------------

def render_datos(nombre: str, perfil: dict, mensajes: list[tuple[str, str]],
                 cv_elegido: str = "") -> str:
    filtros = perfil.get("filters") or {}
    loc = filtros.get("location") or {}
    idioma = filtros.get("language") or {}
    modos = filtros.get("work_modes") or []
    if isinstance(modos, str):
        modos = [modos]
    cand = perfil.get("candidate") or {}
    cvs = data.load_resumes(perfil)
    # El CV que se muestra. Si piden uno que no existe (lo acaban de borrar, o
    # la dirección es vieja), el primero.
    ids = [cv["id"] for cv in cvs]
    elegido = cv_elegido if cv_elegido in ids else ids[0]
    rrhh = data.fuente_o_crear(perfil, "rrhh") if _tiene(perfil, "rrhh") else {}
    rrhh_texto = "\n".join(rrhh.get("profiles") or [])
    # `city` y `home_city` significan lo mismo; el formulario muestra una sola.
    ciudades = ", ".join(home_cities(loc))
    nivel = str(idioma.get("max_english_level", "A2")).upper()

    return f"""{avisos(mensajes)}
<h1>Mi perfil de {esc(nombre)}</h1>
<form class="datos" method="post" action="/datos">
<input type="hidden" name="perfil" value="{esc(nombre)}">
<!-- El botón que aprieta Enter. Apretar Enter en un campo manda el formulario
     con el PRIMER botón de envío que haya, y ése era "Agregar otro CV": un Enter
     en cualquier campo agregaba un CV. Con el borrado habría sido peor. Éste va
     primero, no se ve, y hace lo mismo que "Guardar cambios". -->
<button type="submit" class="enviar-por-defecto" tabindex="-1" aria-hidden="true">Guardar cambios</button>

<h2 id="mis-cv">Mis CV</h2>
<p class="ayuda intro">Uno por cada clase de puesto a la que te postulás. Cada oferta te
dice con cuál mandarte, y cada CV suma sus propias búsquedas.</p>
{_selector_de_cv(cvs, elegido)}
<div class="mis-cv">
{"".join(_bloque_de_cv(cv, len(cvs), cv["id"] == elegido) for cv in cvs)}
</div>
<noscript><style>.mis-cv .grilla.cv:not(.activo) {{ display: grid; }}
.selector-de-cv {{ display: none; }}</style></noscript>
<div class="agregar-cv"><button class="boton-agregar" type="submit" formaction="/cv-nuevo">
  <span aria-hidden="true">+</span> Agregar otro CV</button></div>

<h2>Qué busco</h2>
<div class="grilla">
  {_campo("keywords", "Palabras clave", _lista(perfil.get("keywords")),
          ayuda="Separadas por coma. Es lo que se busca en los portales.")}
  {_campo("excluir_titulos", "Puestos que NO quiero",
          _lista((filtros.get("excluir_titulos")) or []),
          placeholder="Data Steward, MLOps",
          ayuda="Separados por coma. Se descartan sin pagar por puntuarlos.",
          mas="Si el título del aviso dice alguno de éstos, el aviso se descarta "
              "antes de puntuarlo. Sólo mira el título: un aviso de AI Engineer "
              "puede nombrar 'machine learning' entre las tecnologías del equipo, "
              "y ése no se pierde.")}
</div>

<h2>Dónde y en qué idioma</h2>
<div class="grilla">
  {_campo("pais", "País", _lista(loc.get("country")), placeholder="Argentina",
          ayuda="Vacío trae ofertas de todo el mundo.",
          mas="Con el país puesto, el remoto también tiene que ser de acá: un "
              "remoto publicado para España deja de entrar.")}
  {_campo("ciudad", "Ciudades a las que puedo ir en persona", ciudades,
          placeholder="Bahía Blanca, Punta Alta",
          ayuda="Separadas por coma. Sólo filtran presencial e híbrido.",
          mas="El remoto entra venga de la ciudad que venga, y un presencial en "
              "una de estas ciudades entra aunque hayas pedido sólo remoto.")}
  <div class="campo">
    <label>Modalidades que acepto</label>
    <div class="checks">
      {"".join(_check(f"modo_{clave}", etiqueta, clave in modos) for clave, etiqueta in MODALIDADES)}
    </div>
    <p class="ayuda">Ninguna marcada = todas.</p>
  </div>
  <div class="campo">
    <label for="max_english_level">Inglés que sí manejo</label>
    <select id="max_english_level" name="max_english_level">
      {"".join(f'<option{" selected" if n == nivel else ""}>{n}</option>' for n in NIVELES)}
    </select>
    <div class="checks">
      {_check("allow_english", "Aceptar avisos en inglés", idioma.get("allow_english", True))}
    </div>
    <p class="ayuda">Se descartan los avisos que pidan más nivel que éste.</p>
  </div>
</div>

<h2>Empresas y reclutadores que sigo</h2>
<div class="grilla">
  {_area("empresas", "Empresas que sigo", data.companies_a_texto(data.leer_companies(perfil)), 6,
         ayuda="Una por línea:  Nombre | https://empresa.com/careers | empresa.com",
         debajo=_fuente_apagada(nombre, perfil, "careers"))}
  {_area("rrhh", "Las URLs de esos reclutadores", rrhh_texto, 4,
         placeholder=EJEMPLO_RRHH, mas=AYUDA_RRHH,
         debajo=EJEMPLOS_RRHH + _fuente_apagada(nombre, perfil, "rrhh"))}
</div>

<h2>Datos personales</h2>
<div class="grilla">
  {_campo("cand_name", "Mi nombre", cand.get("name", ""))}
  {_campo("cand_headline", "Cómo me presento", cand.get("headline", ""),
          placeholder="AI Engineer",
          ayuda="Dos o tres palabras. Va tal cual en el mensaje al reclutador: "
                "“Mi nombre es Isaías, soy AI Engineer”.")}
  {_campo("cand_profile", "En una línea, qué hago", cand.get("profile", ""))}
  {_campo("cand_seeking", "Qué estoy buscando", cand.get("seeking", ""))}
  {_campo("cand_not_suitable", "Qué NO me sirve", cand.get("not_suitable", ""),
          ayuda="Se lo decimos al que puntúa para que no te traiga eso.")}
</div>

<div class="guardar"><button class="primario" type="submit">Guardar cambios</button></div>
</form>"""


# --- Configuración: lo que se toca una vez ----------------------------------

def _fila_de_fuente(nombre: str, perfil: dict, tipo: str, etiqueta: str, nota: str,
                    activas: dict) -> str:
    """Un renglón de la lista de fuentes: el tilde, su nota y, si depende de una
    lista de Mi perfil, cuánto hay cargado y el link para ir a cargarlo.

    Prender "Empresas que sigo" sin ninguna empresa cargada es una fuente que
    devuelve cero todos los días sin decir por qué. El número al lado lo dice
    antes de guardar.
    """
    campo = f"fuente_{tipo}"
    marcada = bool(activas.get(tipo, False))
    tilde = (_tilde_con_ayuda(campo, etiqueta, marcada, nota) if nota
             else _check(campo, etiqueta, marcada))
    dato = ""
    if tipo == "careers":
        cuantas = len(data.leer_companies(perfil))
        texto = _plural(cuantas, "empresa", "empresas") if cuantas else "ninguna cargada"
        dato = f'<a class="cargadas" href="/datos?perfil={esc(nombre)}#empresas">{texto}</a>'
    elif tipo == "rrhh":
        rrhh = data.fuente_o_crear(perfil, "rrhh") if _tiene(perfil, "rrhh") else {}
        cuantas = len(rrhh.get("profiles") or [])
        texto = _plural(cuantas, "URL", "URLs") if cuantas else "ninguna cargada"
        dato = f'<a class="cargadas" href="/datos?perfil={esc(nombre)}#rrhh">{texto}</a>'
    return f"<li>{tilde}{dato}</li>"


def _fuentes(nombre: str, perfil: dict) -> str:
    """De dónde traer ofertas: dos listas ordenadas, una por clase de fuente.

    Estaban sueltas en una fila que se acomodaba sola: cada tilde caía a una
    altura distinta según lo largo del nombre y de la nota, y no se leían como
    una lista ni se encontraba cuál estaba prendida.
    """
    activas = {s.get("type"): s.get("enabled", True) for s in perfil.get("sources") or []}
    por_tipo = {t: (e, n) for t, e, n in FUENTES}
    agrupadas = {t for _, tipos in GRUPOS_DE_FUENTES for t in tipos}
    sueltas = tuple(t for t in por_tipo if t not in agrupadas)

    grupos = []
    for i, (titulo, tipos) in enumerate(GRUPOS_DE_FUENTES):
        tipos = tipos + sueltas if i == 0 else tipos
        filas = "".join(_fila_de_fuente(nombre, perfil, t, *por_tipo[t], activas)
                        for t in tipos if t in por_tipo)
        grupos.append(f'<fieldset class="fuentes"><legend>{esc(titulo)}</legend>'
                      f'<ul>{filas}</ul></fieldset>')

    # Bumeran y Zonajobs son la misma base: con los dos prendidos llega todo
    # dos veces. La nota del signo de pregunta lo dice siempre; esto lo dice
    # sólo cuando pasa, que es cuando hay que leerlo.
    duplicadas = ""
    if activas.get("bumeran") and activas.get("zonajobs"):
        duplicadas = ('<p class="ayuda apagada">Bumeran y Zonajobs están prendidos '
                      'los dos: traen los mismos avisos y te van a llegar duplicados.</p>')
    return f'<div class="grupos-fuentes">{"".join(grupos)}</div>{duplicadas}'


def render_configuracion(nombre: str, perfil: dict,
                         mensajes: list[tuple[str, str]]) -> str:
    """Telegram y avisos, búsqueda, claves. Y crear o borrar un perfil.

    **Un solo primario, "Guardar cambios".** "Crear perfil" era primario cuando
    vivía abajo de Mi perfil, y eran dos botones del mismo peso en la misma
    pantalla. Crear y borrar son mantenimiento: no son lo que venís a hacer acá.

    Crear y borrar van en formularios propios, fuera del grande. Al revés que
    "Agregar otro CV", ninguno de los dos necesita guardar antes lo que estaba
    escrito: el perfil nuevo es otro y el borrado desaparece.

    Las secciones siguen lo que la persona se pregunta, no dónde se guarda cada
    dato: "cómo me avisa" junta el chat con el puntaje y el tope por aviso, y
    "qué busca" junta las fuentes con la antigüedad y el tope por corrida.
    """
    filtros = perfil.get("filters") or {}
    env = data.leer_env()

    claves = "".join(
        _campo(clave, clave, "", tipo="password",
               ayuda=(f"Cargada: {data.enmascarar(env.get(clave, ''))}"
                      if env.get(clave) else "Sin cargar"),
               placeholder="dejar vacío para no cambiarla", autocomplete="off")
        for clave in data.CLAVES_ENV
    )

    return f"""{avisos(mensajes)}
<h1>Configuración de {esc(nombre)}</h1>
<form class="datos" method="post" action="/configuracion">
<input type="hidden" name="perfil" value="{esc(nombre)}">

<h2>Cómo me avisa</h2>
<div class="grilla">
  {_campo("chat_id", "Mi chat de Telegram", data.chat_id_de(perfil),
          ayuda="Vacío usa el chat compartido de esta computadora.",
          mas="Es tuyo, no de la computadora: cada persona recibe sólo lo suyo. Si "
              "en esta máquina busca trabajo más de una persona, cada una pone su "
              "chat acá.")}
  {_campo("min_score", "Puntaje mínimo para avisarme", perfil.get("min_score", 60),
          tipo="number", ayuda="0 a 100. 60 es un buen punto de partida.", min="0", max="100")}
  {_campo("top_n", "Cuántas ofertas por aviso", perfil.get("top_n", 5), tipo="number", min="1")}
  <div class="campo">
    <label>Sin ofertas nuevas</label>
    <div class="checks">
      {_check("notify_when_empty", "Avisarme aunque no haya ofertas",
              perfil.get("notify_when_empty", False))}
    </div>
    <p class="ayuda">Sirve para saber que el sistema sigue vivo.</p>
  </div>
</div>

<h2>Qué busca</h2>
{_fuentes(nombre, perfil)}
<div class="grilla">
  {_campo("max_age_days", "No traerme avisos de más de (días)",
          filtros.get("max_age_days", 7), tipo="number", min="0", max="365",
          ayuda="7 días anda bien. Con 0 no hay límite.",
          mas="Se le pide a cada buscador y portal, así que los avisos viejos ni "
              "entran. Poné 7 para puestos con mucha competencia, donde a la "
              "semana ya está cubierto, y 30 o 45 para rubros donde una búsqueda "
              "queda abierta un mes. Un aviso que no dice cuándo se publicó entra "
              "igual: no se descarta por no saber.")}
  {_campo("max_new_per_run", "Máximo de ofertas nuevas por corrida",
          perfil.get("max_new_per_run", 30), tipo="number", min="1",
          ayuda="Protege el límite diario de la API. 30 está bien.")}
</div>

<h2>Claves</h2>
<p class="ayuda intro">Se comparten entre todos los perfiles de esta computadora. Se
guardan en el archivo .env de esta carpeta, no en internet.</p>
<div class="grilla">{claves}</div>

<div class="guardar"><button class="primario" type="submit">Guardar cambios</button></div>
</form>

<h2>Perfiles de esta computadora</h2>
<section class="perfiles">
<form class="crear-perfil" method="post" action="/perfil-nuevo">
  <input type="hidden" name="perfil" value="{esc(nombre)}">
  <label for="nombre">Crear el perfil de otra persona</label>
  <div class="en-linea">
    <input type="text" id="nombre" name="nombre" value="" placeholder="maria" autocomplete="off">
    <button type="submit">Crear perfil</button>
  </div>
  <p class="ayuda">Sin espacios ni acentos. Nace en blanco, para que lo complete.</p>
</form>
{_borrar_perfil(nombre)}
</section>"""


def _borrar_perfil(nombre: str) -> str:
    """La confirmación de borrar el perfil: la misma que la de "Borrar este CV".

    Se abre en el lugar y no con un cartel del navegador, por lo mismo que la
    del CV: el nombre de quién se borra tiene que estar a la vista justo cuando
    se confirma. Usa las clases de aquella a propósito, para que las dos
    acciones destructivas de la app se vean y se aprieten igual.
    """
    return f"""<form class="borrar-perfil" method="post" action="/perfil-borrar">
  <input type="hidden" name="perfil" value="{esc(nombre)}">
  <details class="borrar-cv">
    <summary>Borrar el perfil de {esc(nombre)}</summary>
    <div class="cuerpo">
      <p>Se borra <b>{esc(nombre)}</b> con todo: CV, ofertas guardadas y lo que marcaste. No se puede recuperar.</p>
      <button class="peligro" type="submit" name="perfil_borrar"
              value="{esc(nombre)}">Sí, borrar definitivamente</button>
      <button class="fantasma" type="button"
              onclick="this.closest('details').open = false">Cancelar</button>
    </div>
  </details>
</form>"""


def render_sin_perfiles(mensajes: list[tuple[str, str]] | None = None) -> str:
    """Instalación recién estrenada, o se borró el último perfil.

    No se crea ninguno solo ni se inventan datos de nadie: se ofrece crear el
    primero, en blanco, para que la persona lo complete.

    Muestra los carteles porque se llega acá de dos maneras en las que hay algo
    que decir: después de borrar el último perfil, y con un nombre inválido.
    """
    return f"""{avisos(mensajes or [])}
<h1>Bienvenido a vacantia</h1>
<div class="vacio"><b>Todavía no hay ningún perfil cargado.</b>
Creá el primero con el nombre de la persona que va a buscar trabajo. Después vas
a poder cargarle el CV, las palabras clave y de qué portales traer ofertas.</div>
<form class="datos" method="post" action="/perfil-nuevo">
  <div class="grilla">
    {_campo("nombre", "Nombre de la persona", "", placeholder="maria",
            ayuda="Sin espacios ni acentos.")}
  </div>
  <div class="guardar"><button class="primario" type="submit">Crear perfil</button></div>
</form>"""


def _tiene(perfil: dict, tipo: str) -> bool:
    return any(s.get("type") == tipo for s in perfil.get("sources") or [])


# --- volcado del formulario a los archivos ---------------------------------

def _entero(form, clave, default):
    try:
        return int(str(form.get(clave, "")).strip())
    except (TypeError, ValueError):
        return default


def _lista_desde(texto: str) -> list[str]:
    return [t.strip() for t in (texto or "").replace("\n", ",").split(",") if t.strip()]


def aplicar_datos(nombre: str, form: dict) -> list[tuple[str, str]]:
    """Guarda lo que vino de Mi perfil. Devuelve los carteles a mostrar.

    **Toca sólo los campos de Mi perfil.** Un tilde que no se marcó no viaja en
    el formulario: el navegador no manda nada. Por eso un tilde ausente se lee
    como apagado, y eso sólo es cierto en la pantalla que lo dibuja. Cuando todo
    era una sola pantalla daba igual; partida en dos, guardar Mi perfil leyendo
    las fuentes como ausentes las habría apagado todas sin que nadie tocara nada.

    Los tildes de esta pantalla (modalidades e inglés) sí se leen así. Los campos
    de texto, en cambio, se cambian sólo si vinieron: un pedido que no los trae
    no los vacía.
    """
    perfil = data.leer_perfil(nombre)
    mensajes: list[tuple[str, str]] = []

    if "keywords" in form:
        perfil["keywords"] = _lista_desde(form.get("keywords", ""))

    filtros = perfil.setdefault("filters", {})
    loc = filtros.setdefault("location", {})
    if "pais" in form:
        loc["country"] = form.get("pais", "").strip()
    if "ciudad" in form:
        # Una sola ciudad se guarda como texto y varias como lista: los filtros
        # aceptan las dos formas. `home_city` era el nombre viejo de este mismo
        # campo y se borra, para que no queden dos valores peleándose.
        ciudades = _lista_desde(form.get("ciudad", ""))
        loc["city"] = ciudades[0] if len(ciudades) == 1 else ciudades
        loc.pop("home_city", None)
    filtros["work_modes"] = [c for c, _ in MODALIDADES if f"modo_{c}" in form]
    idioma = filtros.setdefault("language", {})
    idioma["allow_english"] = "allow_english" in form
    if "max_english_level" in form:
        idioma["max_english_level"] = form.get("max_english_level", "A2").strip().upper()[:2]

    # Los puestos que la persona no hace. Se descartan antes del scoring, así
    # que cada término que se agrega acá es plata que no se gasta.
    if "excluir_titulos" in form:
        filtros["excluir_titulos"] = _lista_desde(form.get("excluir_titulos", ""))

    cand = perfil.setdefault("candidate", {})
    for campo in ("name", "headline", "profile", "seeking", "not_suitable"):
        if f"cand_{campo}" in form:
            cand[campo] = form.get(f"cand_{campo}", "").strip()

    if "rrhh" in form:
        urls = [u.strip() for u in form.get("rrhh", "").splitlines() if u.strip()]
        # Si la fuente no existía, se crea **apagada**: prenderla es de
        # Configuración. Antes el bloque lo creaba el repaso de los tildes de
        # fuentes, que estaba en esta misma pantalla; ahora pegar una URL acá
        # prendería una fuente que la persona nunca tildó.
        if urls or _tiene(perfil, "rrhh"):
            data.fuente_o_crear(perfil, "rrhh", {"enabled": False})["profiles"] = urls

    # Los CV. La lista sale del perfil, que es donde están los ids; del formulario
    # sólo se toma lo que se puede editar. Un CV que no vino en el formulario
    # queda como estaba.
    cvs = data.cvs_del_perfil(perfil)
    textos: dict[str, str] = {}
    for cv in cvs:
        prefijo = f"cv_{cv['id']}_"
        if f"{prefijo}nombre" in form:
            cv["nombre"] = form.get(f"{prefijo}nombre", "").strip() or cv["nombre"]
        if f"{prefijo}palabras" in form:
            cv["palabras_clave"] = _lista_desde(form.get(f"{prefijo}palabras", ""))
        if f"{prefijo}texto" in form:
            textos[cv["path"]] = form.get(f"{prefijo}texto", "")
    # El formulario de antes mandaba un solo campo `cv`. Si llega, va al primero.
    if "cv" in form and cvs[0]["path"] not in textos:
        textos[cvs[0]["path"]] = form.get("cv", "")
    data.fijar_cvs(perfil, cvs)

    data.guardar_perfil(nombre, perfil)
    mensajes.append(("ok", "Datos guardados."))

    for ruta, texto in textos.items():
        data.guardar_cv({"cv_path": ruta}, texto)

    if "empresas" in form:
        previas = data.leer_companies(perfil)
        nuevas = data.texto_a_companies(form.get("empresas", ""), previas)
        # Antes de guardar: si otro perfil usa el mismo archivo, éste pasa a
        # tener el suyo. Las `previas` se leyeron antes a propósito, del archivo
        # compartido, para no perder los campos que la pantalla no muestra.
        otros = data.separar_companies(nombre, perfil)
        if otros:
            data.guardar_perfil(nombre, perfil)
            mensajes.append((
                "ok", f"Tus empresas ahora se guardan aparte de las de "
                      f"{', '.join(otros)}: compartían la misma lista y guardar "
                      f"una pisaba la otra."))
        data.guardar_companies(perfil, nuevas)
        sin_url = [c["name"] for c in nuevas if not c.get("careers_url")]
        if sin_url:
            mensajes.append(
                ("error", "Estas empresas quedaron sin dirección y no se van a poder "
                          f"revisar: {', '.join(sin_url)}")
            )

    return mensajes


def aplicar_configuracion(nombre: str, form: dict) -> list[tuple[str, str]]:
    """Guarda lo que vino de Configuración. Devuelve los carteles a mostrar.

    **Toca sólo los campos de Configuración**, por lo mismo que `aplicar_datos`:
    guardar acá no puede vaciar las palabras clave ni el CV, que ni siquiera
    están en el formulario. Los tildes de esta pantalla (fuentes y "avisarme
    aunque no haya ofertas") se leen como apagados si no vinieron.
    """
    perfil = data.leer_perfil(nombre)
    mensajes: list[tuple[str, str]] = []

    perfil["min_score"] = max(0, min(100, _entero(form, "min_score", perfil.get("min_score", 60))))
    perfil["top_n"] = max(1, _entero(form, "top_n", perfil.get("top_n", 5)))
    perfil["max_new_per_run"] = max(1, _entero(form, "max_new_per_run",
                                               perfil.get("max_new_per_run", 30)))
    perfil["notify_when_empty"] = "notify_when_empty" in form

    filtros = perfil.setdefault("filters", {})
    # La antigüedad máxima que acepta esta persona. Es una sola para todas las
    # fuentes a propósito: lo que sirve depende del rubro, no del portal. Un AI
    # Engineer necesita 7 días —a la semana la búsqueda ya está cubierta— y un
    # supervisor de seguridad e higiene en el campo se banca 45. Cada fuente la
    # hereda desde `Source._resolver_antiguedad`.
    filtros["max_age_days"] = max(0, min(365, _entero(
        form, "max_age_days", filtros.get("max_age_days", 7))))

    # Fuentes: prender/apagar sin perder la configuración que ya tenían.
    for tipo, _, _nota in FUENTES:
        bloque = data.fuente_o_crear(perfil, tipo)
        bloque["enabled"] = f"fuente_{tipo}" in form

    if "chat_id" in form:
        data.guardar_chat_id(perfil, form.get("chat_id", ""))

    data.guardar_perfil(nombre, perfil)
    mensajes.append(("ok", "Configuración guardada."))

    guardadas = data.guardar_env({k: form.get(k, "") for k in data.CLAVES_ENV})
    if guardadas:
        mensajes.append(("ok", f"Claves actualizadas: {', '.join(guardadas)}"))

    return mensajes
