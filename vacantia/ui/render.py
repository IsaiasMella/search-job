"""El HTML de la UI. Sin plantillas ni librerías: strings y f-strings.

El CSS es deliberadamente mínimo — lo justo para que se lea: una grilla para
que la oferta no quede apilada en una columna, y dos colores para los botones.
Que sea linda es otra etapa.
"""

from html import escape
from urllib.parse import quote

CSS = """
:root { --borde:#d0d0d0; --gris:#666; --fondo:#fafafa; --verde:#1b7f3b; --rojo:#b3261e; }
* { box-sizing: border-box; }
body { font: 15px/1.45 system-ui, "Segoe UI", Arial, sans-serif; margin: 0;
       color: #1a1a1a; background: var(--fondo); }
a { color: #14509b; }
header { background: #fff; border-bottom: 1px solid var(--borde); padding: 10px 20px; }
.barra { display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
         max-width: 1100px; margin: 0 auto; }
.barra h1 { font-size: 17px; margin: 0; letter-spacing: .5px; }
nav a { display: inline-block; padding: 6px 12px; border-radius: 4px;
        text-decoration: none; color: #333; }
nav a.activa { background: #14509b; color: #fff; }
main { max-width: 1100px; margin: 0 auto; padding: 20px; }
h2 { font-size: 18px; margin: 22px 0 10px; }
h2:first-child { margin-top: 0; }
.aviso { padding: 10px 14px; border-radius: 4px; margin-bottom: 16px;
         border: 1px solid var(--borde); background: #fff; }
.aviso.ok { border-color: var(--verde); background: #f0f8f2; }
.aviso.error { border-color: var(--rojo); background: #fdf2f1; }

/* --- ofertas --- */
.filtros { margin-bottom: 14px; }
.filtros a { display: inline-block; padding: 4px 10px; margin-right: 6px;
             border: 1px solid var(--borde); border-radius: 4px; background: #fff;
             text-decoration: none; color: #333; font-size: 13px; }
.filtros a.activa { background: #14509b; color: #fff; border-color: #14509b; }
.oferta { display: grid; grid-template-columns: 56px 1fr 250px; gap: 14px;
          background: #fff; border: 1px solid var(--borde); border-radius: 6px;
          padding: 12px 14px; margin-bottom: 10px; align-items: start; }
.puntaje { font-size: 20px; font-weight: 600; text-align: center;
           border-radius: 4px; padding: 6px 0; background: #eef2f7; }
.puntaje.alto { background: #e3f3e8; color: var(--verde); }
.oferta h3 { font-size: 15px; margin: 0 0 4px; }
.meta { color: var(--gris); font-size: 13px; margin: 2px 0; }
.razon { font-size: 13px; margin: 6px 0 0; }
.acciones { display: flex; flex-direction: column; gap: 6px; }
.acciones .fila { display: flex; gap: 6px; }
button { font: inherit; padding: 6px 10px; border-radius: 4px; cursor: pointer;
         border: 1px solid var(--borde); background: #fff; }
button.verde { background: var(--verde); border-color: var(--verde); color: #fff; }
button.rojo  { background: var(--rojo);  border-color: var(--rojo);  color: #fff; }
.acciones input[type=text] { width: 100%; padding: 5px; border: 1px solid var(--borde);
                             border-radius: 4px; font: inherit; font-size: 13px; }
.marca { font-size: 13px; padding: 6px; border-radius: 4px; background: #f2f2f2; }
.marca.si { background: #e3f3e8; color: var(--verde); }
.marca.no { background: #fdf2f1; color: var(--rojo); }

/* --- formularios --- */
form.datos { background: #fff; border: 1px solid var(--borde); border-radius: 6px;
             padding: 16px; }
.grilla { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
          gap: 12px 18px; }
.campo { display: flex; flex-direction: column; gap: 3px; }
.campo label { font-size: 13px; color: var(--gris); }
.campo input[type=text], .campo input[type=number], .campo input[type=password],
.campo select, textarea {
    padding: 6px; border: 1px solid var(--borde); border-radius: 4px; font: inherit; }
textarea { width: 100%; font-family: ui-monospace, Consolas, monospace; font-size: 13px; }
.ancho { grid-column: 1 / -1; }
.checks { display: flex; gap: 16px; flex-wrap: wrap; align-items: center; }
.checks label { font-size: 14px; }
.ayuda { font-size: 12px; color: var(--gris); margin: 3px 0 0; }
.guardar { margin-top: 18px; }
.guardar button { padding: 9px 20px; background: #14509b; border-color: #14509b;
                  color: #fff; font-size: 15px; }
.herramientas { margin: 0 0 14px; }
a.boton { display: inline-block; padding: 7px 14px; border-radius: 4px;
          background: #14509b; color: #fff; text-decoration: none; font-size: 14px; }
a.chico { font-size: 13px; }
.mensaje textarea { min-height: 150px; }
.mensaje { background: #fff; border: 1px solid var(--borde); border-radius: 6px;
           padding: 14px; margin-bottom: 14px; }
.vacio { color: var(--gris); background: #fff; border: 1px dashed var(--borde);
         border-radius: 6px; padding: 24px; text-align: center; }
@media (max-width: 760px) {
  .oferta { grid-template-columns: 46px 1fr; }
  .acciones { grid-column: 1 / -1; }
}
"""

# Lo único que necesita JavaScript: que el motivo sea obligatorio al descartar.
# `required` no sirve porque el mismo formulario tiene un botón que no lo pide.
JS = """
function descartar(boton) {
  var campo = boton.closest('form').querySelector('input[name=motivo]');
  if (!campo.value.trim()) {
    alert('Escribí por qué no aplicaste. Ese texto es lo que hace que el sistema aprenda.');
    campo.focus();
    return false;
  }
  return true;
}
"""


def esc(texto) -> str:
    return escape(str(texto or ""), quote=True)


def pagina(titulo: str, cuerpo: str, perfil: str, perfiles: list[str], tab: str) -> str:
    opciones = "".join(
        f'<option value="{esc(p)}"{" selected" if p == perfil else ""}>{esc(p)}</option>'
        for p in perfiles
    )
    def link(destino, etiqueta, clave):
        activa = " class='activa'" if clave == tab else ""
        return f'<a href="/{destino}?perfil={esc(perfil)}"{activa}>{etiqueta}</a>'

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo)} — vacantia</title>
<style>{CSS}</style><script>{JS}</script>
</head><body>
<header><div class="barra">
  <h1>VACANTIA</h1>
  <nav>{link('trabajos', 'Trabajos', 'trabajos')}{link('datos', 'Mis datos', 'datos')}</nav>
  <form method="get" action="/{esc(tab)}" style="margin-left:auto">
    <label style="font-size:13px;color:var(--gris)">Perfil
      <select name="perfil" onchange="this.form.submit()">{opciones}</select>
    </label>
  </form>
</div></header>
<main>{cuerpo}</main>
</body></html>"""


def avisos(mensajes: list[tuple[str, str]]) -> str:
    """[(clase, texto)] -> los carteles de arriba de todo."""
    return "".join(f'<div class="aviso {esc(c)}">{esc(t)}</div>' for c, t in mensajes)


# --- pestaña Trabajos -------------------------------------------------------

FILTROS = (
    ("pendientes", "Sin marcar"),
    ("aplicadas", "Apliqué"),
    ("descartadas", "Descarté"),
    ("todas", "Todas"),
)


def _tarjeta(oferta: dict, perfil: str, ver: str) -> str:
    score = oferta.get("score")
    clase = "puntaje alto" if isinstance(score, int) and score >= 70 else "puntaje"
    titulo = oferta.get("scored_title") or oferta.get("title") or "(sin título)"
    lugar = oferta.get("location_remote") or oferta.get("location") or ""
    meta = " · ".join(
        x for x in (oferta.get("company"), lugar, oferta.get("source"),
                    (oferta.get("found_at") or "")[:10]) if x
    )
    url = oferta.get("url", "")

    aplicado = oferta.get("aplicado")
    if aplicado is True:
        acciones = '<div class="marca si">Aplicaste ✓</div>'
    elif aplicado is False:
        motivo = esc(oferta.get("motivo_descarte") or "sin motivo")
        acciones = f'<div class="marca no">Descartada<br><small>{motivo}</small></div>'
    else:
        acciones = f"""<form class="acciones" method="post" action="/feedback">
      <input type="hidden" name="perfil" value="{esc(perfil)}">
      <input type="hidden" name="ver" value="{esc(ver)}">
      <input type="hidden" name="url" value="{esc(url)}">
      <div class="fila">
        <button class="verde" name="aplicado" value="si">Apliqué</button>
        <button class="rojo" name="aplicado" value="no"
                onclick="return descartar(this)">No apliqué</button>
      </div>
      <input type="text" name="motivo" placeholder="Por qué no apliqué (obligatorio)">
    </form>"""

    razon = oferta.get("reason") or ""
    stack = oferta.get("stack") or ""
    mensajes_link = (f'<a class="chico" href="/mensajes?perfil={esc(perfil)}'
                     f'&url={quote(url, safe="")}">Mensaje para escribirle</a>')
    return f"""<article class="oferta">
  <div class="{clase}">{esc(score if score is not None else '?')}</div>
  <div class="datos">
    <h3><a href="{esc(url)}" target="_blank" rel="noopener">{esc(titulo)}</a></h3>
    <p class="meta">{esc(meta)}</p>
    {f'<p class="meta">{esc(stack)}</p>' if stack else ''}
    {f'<p class="razon">{esc(razon)}</p>' if razon else ''}
    <p class="meta">{mensajes_link}</p>
  </div>
  {acciones}
</article>"""


def trabajos(perfil: str, ofertas: list[dict], conteo: dict, ver: str,
             mensajes: list[tuple[str, str]]) -> str:
    filtros = "".join(
        f'<a href="/trabajos?perfil={esc(perfil)}&ver={clave}"'
        f'{" class=activa" if clave == ver else ""}>{etiqueta} ({conteo.get(clave, 0)})</a>'
        for clave, etiqueta in FILTROS
    )
    if ofertas:
        listado = "".join(_tarjeta(o, perfil, ver) for o in ofertas)
    else:
        listado = (
            '<div class="vacio">No hay ofertas para mostrar acá.<br>'
            "Si es la primera vez, corré una búsqueda con <b>buscar_ahora.bat</b>.</div>"
        )
    return f"""{avisos(mensajes)}
<h2>Trabajos</h2>
<p class="herramientas">
  <a class="boton" href="/cv.pdf?perfil={esc(perfil)}">Descargar CV en PDF</a>
</p>
<div class="filtros">{filtros}</div>
{listado}"""


# --- mensajes para el reclutador -------------------------------------------

def mensajes(perfil: str, oferta: dict, textos: dict[str, str], con_llm: bool,
             avisos_: list[tuple[str, str]]) -> str:
    """Los dos moldes, en cajas de texto para copiar y pegar."""
    titulo = oferta.get("scored_title") or oferta.get("title") or "(sin título)"
    url = oferta.get("url", "")
    cajas = "".join(
        f"""<div class="mensaje">
  <h3>{esc(etiqueta)}</h3>
  <textarea rows="8" onclick="this.select()">{esc(textos.get(clave, ''))}</textarea>
  <p class="ayuda">Clic adentro para seleccionar todo y copiar.</p>
</div>"""
        for clave, etiqueta in (("dm", "DM por LinkedIn"), ("mail", "Mail a RRHH"))
    )
    boton = "" if con_llm else f"""<form method="post" action="/mensajes">
  <input type="hidden" name="perfil" value="{esc(perfil)}">
  <input type="hidden" name="url" value="{esc(url)}">
  <button type="submit">Completar con IA leyendo el aviso y mi CV</button>
  <p class="ayuda">Usa una llamada al modelo. Sin esto, completá a mano lo que
  está entre llaves.</p>
</form>"""
    return f"""{avisos(avisos_)}
<h2>Mensaje para {esc(oferta.get('company') or 'quien publicó')}</h2>
<p class="meta">{esc(titulo)} — <a href="{esc(url)}" target="_blank" rel="noopener">ver el aviso</a></p>
<p class="herramientas"><a class="boton" href="/trabajos?perfil={esc(perfil)}">Volver a Trabajos</a></p>
{cajas}
{boton}
<p class="ayuda">Estos moldes son un borrador de la sección 10 de COSTOS.md:
máximo 4 líneas, cero adjetivos sobre uno mismo, y cerrar con una pregunta
fácil de responder.</p>"""
