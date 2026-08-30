"""La pestaña "Mis datos": dibujar el formulario y volcarlo a los archivos.

Es lo que evita tener que editar `profiles/<nombre>.json` a mano. Escribe sobre
cuatro lugares distintos según el campo: el perfil, `resume/<nombre>.md`,
`companies.json` y `.env`.
"""

from vacantia.log import get_logger
from vacantia.ui import data
from vacantia.ui.render import avisos, esc

logger = get_logger()

MODALIDADES = (("remote", "Remoto"), ("hybrid", "Híbrido"), ("onsite", "Presencial"))
NIVELES = ("A1", "A2", "B1", "B2", "C1", "C2")

#: Fuentes que se pueden prender y apagar desde la UI. Agregar una fuente nueva
#: al sistema es agregar una línea acá.
FUENTES = (
    ("careers", "Páginas de empleo de las empresas que sigo"),
    ("google_posts", "Publicaciones de LinkedIn (vía buscador, no toca LinkedIn)"),
    ("linkedin", "LinkedIn Jobs"),
    ("rrhh", "Perfiles de reclutadores que sigo"),
    ("bumeran", "Bumeran"),
    ("zonajobs", "Zonajobs"),
    ("computrabajo", "Computrabajo"),
)


def _campo(nombre, etiqueta, valor, tipo="text", ayuda="", **extra) -> str:
    attrs = " ".join(f'{k}="{esc(v)}"' for k, v in extra.items())
    return f"""<div class="campo">
  <label for="{nombre}">{esc(etiqueta)}</label>
  <input type="{tipo}" id="{nombre}" name="{nombre}" value="{esc(valor)}" {attrs}>
  {f'<p class="ayuda">{esc(ayuda)}</p>' if ayuda else ''}
</div>"""


def _area(nombre, etiqueta, valor, filas=8, ayuda="") -> str:
    return f"""<div class="campo ancho">
  <label for="{nombre}">{esc(etiqueta)}</label>
  <textarea id="{nombre}" name="{nombre}" rows="{filas}">{esc(valor)}</textarea>
  {f'<p class="ayuda">{esc(ayuda)}</p>' if ayuda else ''}
</div>"""


def _check(nombre, etiqueta, marcado) -> str:
    return (f'<label><input type="checkbox" name="{nombre}" value="1"'
            f'{" checked" if marcado else ""}> {esc(etiqueta)}</label>')


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

    claves = "".join(
        _campo(clave, clave, "", tipo="password",
               ayuda=(f"Cargada: {data.enmascarar(env.get(clave, ''))}"
                      if env.get(clave) else "Sin cargar"),
               placeholder="dejar vacío para no cambiarla", autocomplete="off")
        for clave in data.CLAVES_ENV
    )

    return f"""{avisos(mensajes)}
<h2>Mis datos — {esc(nombre)}</h2>
<form class="datos" method="post" action="/datos">
<input type="hidden" name="perfil" value="{esc(nombre)}">

<h2>Qué busco</h2>
<div class="grilla">
  {_campo("keywords", "Palabras clave", _lista(perfil.get("keywords")),
          ayuda="Separadas por coma. Es lo que se busca en los portales.")}
  {_campo("min_score", "Puntaje mínimo para avisarme", perfil.get("min_score", 60),
          tipo="number", ayuda="0 a 100. 60 es un buen punto de partida.", min="0", max="100")}
  {_campo("top_n", "Cuántas ofertas por aviso", perfil.get("top_n", 5), tipo="number", min="1")}
  {_campo("max_new_per_run", "Máximo de ofertas nuevas por corrida",
          perfil.get("max_new_per_run", 30), tipo="number", min="1",
          ayuda="Protege el límite diario de la API. 30 está bien.")}
</div>

<h2>Dónde</h2>
<div class="grilla">
  {_campo("pais", "País", _lista(loc.get("country")),
          ayuda="Vacío = cualquier país.")}
  {_campo("ciudad", "Sólo esta ciudad", _lista(loc.get("city")),
          ayuda="Vacío = cualquier ciudad del país.")}
  {_campo("home_city", "Ciudad donde vivo", _lista(loc.get("home_city")),
          ayuda="Un presencial acá entra aunque sólo pidas remoto.")}
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
      {"".join(_check(f"fuente_{t}", etiqueta, activas.get(t, False)) for t, etiqueta in FUENTES)}
    </div>
  </div>
  {_area("empresas", "Empresas que sigo", data.companies_a_texto(data.leer_companies(perfil)), 8,
         ayuda="Una por línea:  Nombre | https://empresa.com/careers | empresa.com")}
  {_area("rrhh", "Perfiles de reclutadores que sigo",
         rrhh_texto, 5,
         ayuda="Una URL por línea (perfil de LinkedIn, página de la consultora...).")}
</div>

<h2>Claves</h2>
<div class="grilla">{claves}</div>
<p class="ayuda">Se guardan en el archivo .env de esta carpeta, no en internet.</p>

<h2>Datos personales</h2>
<div class="grilla">
  {_campo("cand_name", "Mi nombre", cand.get("name", ""))}
  {_campo("cand_profile", "En una línea, qué hago", cand.get("profile", ""))}
  {_campo("cand_seeking", "Qué estoy buscando", cand.get("seeking", ""))}
  {_campo("cand_not_suitable", "Qué NO me sirve", cand.get("not_suitable", ""),
          ayuda="Se lo decimos al que puntúa para que no te traiga eso.")}
</div>

<div class="guardar"><button type="submit">Guardar cambios</button></div>
</form>

<h2>Crear un perfil nuevo</h2>
<form class="datos" method="post" action="/perfil-nuevo">
  <div class="grilla">
    {_campo("nombre", "Nombre de la persona", "",
            ayuda="Sin espacios ni acentos: maria, juan_pablo. Se crea en blanco para que lo complete.")}
  </div>
  <div class="guardar"><button type="submit">Crear perfil</button></div>
</form>"""


def render_sin_perfiles() -> str:
    """Instalación recién estrenada: todavía no hay ningún perfil.

    No se crea ninguno solo ni se inventan datos de nadie: se ofrece crear el
    primero, en blanco, para que la persona lo complete.
    """
    return f"""<h2>Bienvenido a vacantia</h2>
<div class="vacio">Todavía no hay ningún perfil cargado.<br>
Creá el primero con el nombre de la persona que va a buscar trabajo.</div>
<form class="datos" method="post" action="/perfil-nuevo">
  <div class="grilla">
    {_campo("nombre", "Nombre de la persona", "",
            ayuda="Sin espacios ni acentos: maria, juan_pablo.")}
  </div>
  <div class="guardar"><button type="submit">Crear perfil</button></div>
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
    loc = filtros.setdefault("location", {})
    loc["country"] = form.get("pais", "").strip()
    loc["city"] = form.get("ciudad", "").strip()
    loc["home_city"] = form.get("home_city", "").strip()
    filtros["work_modes"] = [c for c, _ in MODALIDADES if f"modo_{c}" in form]
    idioma = filtros.setdefault("language", {})
    idioma["allow_english"] = "allow_english" in form
    idioma["max_english_level"] = form.get("max_english_level", "A2").strip().upper()[:2]

    cand = perfil.setdefault("candidate", {})
    for campo in ("name", "profile", "seeking", "not_suitable"):
        cand[campo] = form.get(f"cand_{campo}", "").strip()

    # Fuentes: prender/apagar sin perder la configuración que ya tenían.
    for tipo, _ in FUENTES:
        bloque = data.fuente_o_crear(perfil, tipo)
        bloque["enabled"] = f"fuente_{tipo}" in form
    rrhh = data.fuente_o_crear(perfil, "rrhh")
    rrhh["profiles"] = [u.strip() for u in form.get("rrhh", "").splitlines() if u.strip()]

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
