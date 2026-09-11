"""La pestaña "Mis datos": dibujar el formulario y volcarlo a los archivos.

Es lo que evita tener que editar `profiles/<nombre>.json` a mano. Escribe sobre
cuatro lugares distintos según el campo: el perfil, `resume/<nombre>.md`,
`companies.json` y `.env`.
"""

from vacantia.filters import home_cities
from vacantia.log import get_logger
from vacantia.ui import data
from vacantia.ui.render import avisos, esc

logger = get_logger()

MODALIDADES = (("remote", "Remoto"), ("hybrid", "Híbrido"), ("onsite", "Presencial"))
NIVELES = ("A1", "A2", "B1", "B2", "C1", "C2")

#: Fuentes que se pueden prender y apagar desde la UI. Agregar una fuente nueva
#: al sistema es agregar una línea acá.
# Qué página sirve. El perfil de LinkedIn ahora anda, pero por un rodeo: no se
# entra al perfil (LinkedIn no deja), se buscan sus posts en Google. Eso es
# invisible para quien carga la URL, y así tiene que quedar. Lo que se sigue
# equivocando cualquiera es la página de una consultora: no va la de inicio, va
# la que lista los puestos. El error es mudo, la fuente devuelve 0 y parece rota.
EJEMPLO_RRHH = """https://www.linkedin.com/in/nombre-apellido
https://consultora.com.ar/busquedas-activas"""

PISTA_RRHH = """<b>Qué página pegar</b>
<ul>
  <li><span class="bien">SÍ</span> <b>El perfil de LinkedIn de la persona</b>:
      <code>linkedin.com/in/nombre-apellido</code>. LinkedIn no deja leer los
      perfiles desde afuera, así que en vez de entrar se buscan sus publicaciones
      en Google y se leen ésas. Andá al perfil y copiá la dirección de la barra
      del navegador, sin más vueltas.</li>
  <li><span class="bien">SÍ</span> <b>La página de una consultora</b>, la que
      lista los puestos y no la de inicio. Suele llamarse
      <b>&#8220;Búsquedas activas&#8221;</b>, &#8220;Trabajá con nosotros&#8221;
      o &#8220;Empleos&#8221;.<br>
      <span class="bien">SÍ</span> <code>consultora.com.ar/busquedas-activas</code><br>
      <span class="mal">NO</span> <code>consultora.com.ar</code></li>
  <li>También sirve cualquier otra página pública que liste búsquedas: el blog de
      empleos de una cámara, una bolsa de trabajo de universidad.</li>
</ul>
<p>Una por línea. Y arriba tiene que estar tildado
<b>&#8220;Perfiles de reclutadores que sigo&#8221;</b>, si no no se usan.</p>
<p>Si el registro dice <code>0 publicación(es)</code> para una
consultora, casi siempre pegaste la página de entrada en vez de la que lista los
puestos.</p>"""


# (clave, etiqueta, nota). La nota se muestra abajo del tilde: es donde mira
# quien no programa, y hay cosas que no se pueden adivinar desde el nombre.
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


def _mas(texto: str) -> str:
    """Lo que no entra en tres líneas de ayuda.

    La ayuda gris explica la consecuencia de la elección y se lee una sola vez;
    cuando crece a seis renglones deja de leerse, se desparrama a lo ancho de la
    columna y encima empuja el campo de abajo fuera de pantalla. Lo que sobra
    pasa acá, a un desplegable que se abre sólo cuando hace falta.
    """
    if not texto:
        return ""
    return (f'<details class="como"><summary>Cómo funciona esto</summary>'
            f'<p class="ayuda">{esc(texto)}</p></details>')


def _campo(nombre, etiqueta, valor, tipo="text", ayuda="", mas="", **extra) -> str:
    attrs = " ".join(f'{k}="{esc(v)}"' for k, v in extra.items())
    return f"""<div class="campo">
  <label for="{nombre}">{esc(etiqueta)}</label>
  <input type="{tipo}" id="{nombre}" name="{nombre}" value="{esc(valor)}" {attrs}>
  {f'<p class="ayuda">{esc(ayuda)}</p>' if ayuda else ''}
  {_mas(mas)}
</div>"""


def _area(nombre, etiqueta, valor, filas=8, ayuda="", placeholder="", pista="") -> str:
    """`pista` va como HTML tal cual: es el recuadro amarillo, y lleva marcado.

    Se usa para lo que hay que recordar cada vez que se toca el campo, no para
    aclarar el campo una vez. La ayuda gris de abajo se lee la primera vez y
    después la vista la saltea.
    """
    ph = f' placeholder="{esc(placeholder)}"' if placeholder else ""
    return f"""<div class="campo ancho">
  <label for="{nombre}">{esc(etiqueta)}</label>
  <textarea id="{nombre}" name="{nombre}" rows="{filas}"{ph}>{esc(valor)}</textarea>
  {f'<p class="ayuda">{esc(ayuda)}</p>' if ayuda else ''}
  {f'<div class="pista">{pista}</div>' if pista else ''}
</div>"""


def _check(nombre, etiqueta, marcado, nota="") -> str:
    tilde = (f'<label><input type="checkbox" name="{nombre}" value="1"'
             f'{" checked" if marcado else ""}> {esc(etiqueta)}</label>')
    if not nota:
        return tilde
    return f'<span class="tilde">{tilde}<span class="nota">{esc(nota)}</span></span>'


def _lista(valor) -> str:
    if isinstance(valor, list):
        return ", ".join(str(v) for v in valor)
    return str(valor or "")


def render(nombre: str, perfil: dict, mensajes: list[tuple[str, str]]) -> str:
    filtros = perfil.get("filters") or {}
    loc = filtros.get("location") or {}
    idioma = filtros.get("language") or {}
    modos = filtros.get("work_modes") or []
    if isinstance(modos, str):
        modos = [modos]
    cand = perfil.get("candidate") or {}
    env = data.leer_env()
    rrhh = data.fuente_o_crear(perfil, "rrhh") if _tiene(perfil, "rrhh") else {}
    activas = {s.get("type"): s.get("enabled", True) for s in perfil.get("sources") or []}
    rrhh_texto = "\n".join(rrhh.get("profiles") or [])
    # `city` y `home_city` significan lo mismo; el formulario muestra una sola.
    ciudades = ", ".join(home_cities(loc))

    claves = "".join(
        _campo(clave, clave, "", tipo="password",
               ayuda=(f"Cargada: {data.enmascarar(env.get(clave, ''))}"
                      if env.get(clave) else "Sin cargar"),
               placeholder="dejar vacío para no cambiarla", autocomplete="off")
        for clave in data.CLAVES_ENV
    )

    return f"""{avisos(mensajes)}
<h1>Mi perfil de {esc(nombre)}</h1>
<form class="datos" method="post" action="/datos">
<input type="hidden" name="perfil" value="{esc(nombre)}">

<h2>Qué busco</h2>
<div class="grilla">
  {_campo("keywords", "Palabras clave", _lista(perfil.get("keywords")),
          ayuda="Separadas por coma. Es lo que se busca en los portales.")}
  {_campo("excluir_titulos", "Puestos que NO quiero",
          _lista((filtros.get("excluir_titulos")) or []),
          placeholder="Data Steward, MLOps",
          ayuda="Separados por coma. Cada uno es una llamada al modelo que no se paga.",
          mas="Si el título del aviso dice alguno de éstos, el aviso se descarta "
              "antes de puntuarlo. Sólo mira el título: un aviso de AI Engineer "
              "puede nombrar 'machine learning' entre las tecnologías del equipo, "
              "y ése no se pierde.")}
  {_campo("min_score", "Puntaje mínimo para avisarme", perfil.get("min_score", 60),
          tipo="number", ayuda="0 a 100. 60 es un buen punto de partida.", min="0", max="100")}
  {_campo("top_n", "Cuántas ofertas por aviso", perfil.get("top_n", 5), tipo="number", min="1")}
  {_campo("max_new_per_run", "Máximo de ofertas nuevas por corrida",
          perfil.get("max_new_per_run", 30), tipo="number", min="1",
          ayuda="Protege el límite diario de la API. 30 está bien.")}
  {_campo("max_age_days", "No traerme avisos de más de (días)",
          filtros.get("max_age_days", 7), tipo="number", min="0", max="365",
          ayuda="Es la ventana que se ve al pie de la pantalla. 7 días anda bien.",
          mas="Se le pide a cada buscador y portal, así que los avisos viejos ni "
              "entran. Poné 7 para puestos con mucha competencia, donde a la "
              "semana ya está cubierto, y 30 o 45 para rubros donde una búsqueda "
              "queda abierta un mes. Con 0 no hay límite y vuelven a aparecer "
              "avisos de hace años. Un aviso que no dice cuándo se publicó entra "
              "igual: no se descarta por no saber.")}
</div>

<h2>Dónde</h2>
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
</div>

<h2>Idioma</h2>
<div class="grilla">
  <div class="campo">
    <label>Inglés</label>
    <div class="checks">
      {_check("allow_english", "Aceptar avisos en inglés", idioma.get("allow_english", True))}
    </div>
  </div>
  <div class="campo">
    <label for="max_english_level">Inglés que sí manejo</label>
    <select id="max_english_level" name="max_english_level">
      {"".join(f'<option{" selected" if n == str(idioma.get("max_english_level", "A2")).upper() else ""}>{n}</option>' for n in NIVELES)}
    </select>
    <p class="ayuda">Se descartan los avisos que pidan más que esto.</p>
  </div>
  <div class="campo">
    <label>Avisos</label>
    <div class="checks">
      {_check("notify_when_empty", "Avisarme aunque no haya ofertas",
              perfil.get("notify_when_empty", False))}
    </div>
    <p class="ayuda">Sirve para saber que el sistema sigue vivo.</p>
  </div>
</div>

<h2>Mi CV</h2>
<div class="grilla">
  {_area("cv", "Se le pasa entero al que puntúa las ofertas", data.leer_cv(perfil), 16,
         ayuda="Texto plano o Markdown. Cuanto más concreto, mejor puntúa.")}
</div>

<h2>De dónde traer ofertas</h2>
<div class="grilla">
  <div class="campo ancho">
    <div class="checks">
      {"".join(_check(f"fuente_{t}", etiqueta, activas.get(t, False), nota) for t, etiqueta, nota in FUENTES)}
    </div>
  </div>
  {_area("empresas", "Empresas que sigo", data.companies_a_texto(data.leer_companies(perfil)), 8,
         ayuda="Una por línea:  Nombre | https://empresa.com/careers | empresa.com")}
  {_area("rrhh", "Las URLs de esos reclutadores",
         rrhh_texto, 5,
         placeholder=EJEMPLO_RRHH, pista=PISTA_RRHH)}
</div>

<h2>Mi Telegram</h2>
<div class="grilla">
  {_campo("chat_id", "Mi chat de Telegram", data.chat_id_de(perfil),
          ayuda="Es tuyo, no de la computadora: cada persona recibe sólo lo suyo.",
          mas="Si en esta máquina busca trabajo más de una persona, cada una pone "
              "su chat acá. Vacío usa el chat compartido de la configuración.")}
</div>

<h2>Claves</h2>
<div class="grilla">{claves}</div>
<p class="ayuda">Estas sí se comparten entre todos los perfiles de esta computadora.
Se guardan en el archivo .env de esta carpeta, no en internet.</p>

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
</form>

<h2>Crear un perfil nuevo</h2>
<form class="datos" method="post" action="/perfil-nuevo">
  <div class="grilla">
    {_campo("nombre", "Nombre de la persona", "", placeholder="maria",
            ayuda="Sin espacios ni acentos. Se crea en blanco para que lo complete.")}
  </div>
  <div class="guardar"><button class="primario" type="submit">Crear perfil</button></div>
</form>"""


def render_sin_perfiles() -> str:
    """Instalación recién estrenada: todavía no hay ningún perfil.

    No se crea ninguno solo ni se inventan datos de nadie: se ofrece crear el
    primero, en blanco, para que la persona lo complete.
    """
    return f"""<h1>Bienvenido a vacantia</h1>
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


def aplicar(nombre: str, form: dict) -> list[tuple[str, str]]:
    """Guarda todo lo que vino del formulario. Devuelve los carteles a mostrar."""
    perfil = data.leer_perfil(nombre)
    mensajes: list[tuple[str, str]] = []

    perfil["keywords"] = _lista_desde(form.get("keywords", ""))
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
    loc = filtros.setdefault("location", {})
    loc["country"] = form.get("pais", "").strip()
    # Una sola ciudad se guarda como texto y varias como lista: los filtros
    # aceptan las dos formas. `home_city` era el nombre viejo de este mismo
    # campo y se borra, para que no queden dos valores peleándose.
    ciudades = _lista_desde(form.get("ciudad", ""))
    loc["city"] = ciudades[0] if len(ciudades) == 1 else ciudades
    loc.pop("home_city", None)
    filtros["work_modes"] = [c for c, _ in MODALIDADES if f"modo_{c}" in form]
    idioma = filtros.setdefault("language", {})
    idioma["allow_english"] = "allow_english" in form
    idioma["max_english_level"] = form.get("max_english_level", "A2").strip().upper()[:2]

    # Los puestos que la persona no hace. Se descartan antes del scoring, así
    # que cada término que se agrega acá es plata que no se gasta.
    filtros["excluir_titulos"] = _lista_desde(form.get("excluir_titulos", ""))

    cand = perfil.setdefault("candidate", {})
    for campo in ("name", "headline", "profile", "seeking", "not_suitable"):
        cand[campo] = form.get(f"cand_{campo}", "").strip()

    # Fuentes: prender/apagar sin perder la configuración que ya tenían.
    for tipo, _, _nota in FUENTES:
        bloque = data.fuente_o_crear(perfil, tipo)
        bloque["enabled"] = f"fuente_{tipo}" in form
    rrhh = data.fuente_o_crear(perfil, "rrhh")
    rrhh["profiles"] = [u.strip() for u in form.get("rrhh", "").splitlines() if u.strip()]

    if "chat_id" in form:
        data.guardar_chat_id(perfil, form.get("chat_id", ""))

    data.guardar_perfil(nombre, perfil)
    mensajes.append(("ok", "Datos guardados."))

    if "cv" in form:
        data.guardar_cv(perfil, form.get("cv", ""))

    if "empresas" in form:
        previas = data.leer_companies(perfil)
        nuevas = data.texto_a_companies(form.get("empresas", ""), previas)
        data.guardar_companies(perfil, nuevas)
        sin_url = [c["name"] for c in nuevas if not c.get("careers_url")]
        if sin_url:
            mensajes.append(
                ("error", "Estas empresas quedaron sin dirección y no se van a poder "
                          f"revisar: {', '.join(sin_url)}")
            )

    guardadas = data.guardar_env({k: form.get(k, "") for k in data.CLAVES_ENV})
    if guardadas:
        mensajes.append(("ok", f"Claves actualizadas: {', '.join(guardadas)}"))

    return mensajes
