"""El HTML de la UI. Sin plantillas ni librerías: strings y f-strings.

El CSS son tokens semánticos con su juego oscuro, definidos una sola vez arriba.
Regla de formas: contenedores 10px, controles 8px, chips redondos. Un acento (el
azul). El verde y el rojo no decoran: significan "apliqué" y "descarté".
"""

from html import escape
from urllib.parse import quote

from vacantia.fechas import dias_desde, fecha_de

CSS = """
/* Tokens. Un solo juego de nombres semánticos, con su equivalente oscuro más
   abajo: nunca se escribe un color suelto en una regla, así el modo oscuro no
   se puede olvidar a la mitad.

   Escala de radios, con la regla escrita para no mezclar formas porque sí:
     contenedores 10px · controles 8px · chips y píldoras redondas.

   Un solo acento, el azul que ya tenía el proyecto. Verde y rojo NO son
   decoración: significan "apliqué" y "descarté", y no se usan para otra cosa. */
:root {
  color-scheme: light;
  --fondo:      #f4f6f8;
  --papel:      #ffffff;
  --papel-2:    #eef1f5;
  --borde:      #d5dae1;
  --borde-2:    #c2c9d2;
  --texto:      #14181d;
  --gris:       #5a636e;
  --acento:     #14509b;
  --acento-fte: #0f3f7d;
  --acento-luz: #e7eefa;
  --verde:      #1b7f3b;
  --verde-luz:  #e6f4ea;
  --rojo:       #b3261e;
  --rojo-luz:   #fdecea;
  --ambar:      #8a6100;
  --ambar-luz:  #fff8e1;
  --ambar-bde:  #e6cf7a;
  --sombra:     0 1px 2px rgb(20 24 29 / .05), 0 1px 3px rgb(20 24 29 / .06);
  --r-caja:     10px;
  --r-control:  8px;
}
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --fondo:      #11151a;
    --papel:      #181d24;
    --papel-2:    #212831;
    --borde:      #2c343e;
    --borde-2:    #3a444f;
    --texto:      #e6eaef;
    --gris:       #9aa4b1;
    --acento:     #6aa5f0;
    --acento-fte: #8dbcf7;
    --acento-luz: #16243a;
    --verde:      #5cc47f;
    --verde-luz:  #14291c;
    --rojo:       #f08b83;
    --rojo-luz:   #2e1614;
    --ambar:      #e3b64a;
    --ambar-luz:  #2a2313;
    --ambar-bde:  #5c4a1c;
    --sombra:     0 1px 2px rgb(0 0 0 / .3), 0 1px 3px rgb(0 0 0 / .25);
  }
}

* { box-sizing: border-box; }
body { font: 15px/1.5 system-ui, "Segoe UI", Roboto, Arial, sans-serif; margin: 0;
       color: var(--texto); background: var(--fondo);
       -webkit-text-size-adjust: 100%; }
a { color: var(--acento); }

/* Foco visible en todo lo que se puede tabular. Sin esto, quien navega con
   teclado no sabe dónde está parado. */
:where(a, button, input, select, textarea, [tabindex]):focus-visible {
  outline: 2px solid var(--acento); outline-offset: 2px; border-radius: 4px; }

.saltar { position: absolute; left: -9999px; top: 0; background: var(--acento);
          color: #fff; padding: 10px 14px; z-index: 10; border-radius: 0 0 8px 0; }
.saltar:focus { left: 0; }

/* --- cabecera --- */
header { background: var(--papel); border-bottom: 1px solid var(--borde);
         padding: 0 20px; position: sticky; top: 0; z-index: 5; }
.barra { display: flex; align-items: center; gap: 8px 18px; flex-wrap: wrap;
         max-width: 1100px; margin: 0 auto; min-height: 60px; }
.barra h1 { font-size: 15px; margin: 0; letter-spacing: .10em; font-weight: 700;
            color: var(--gris); }
nav { display: flex; gap: 4px; }
nav a { display: inline-block; padding: 8px 14px; border-radius: var(--r-control);
        text-decoration: none; color: var(--gris); font-weight: 500; }
nav a:hover { background: var(--papel-2); color: var(--texto); }
nav a.activa { background: var(--acento); color: #fff; }
.perfil-sel { margin-left: auto; display: flex; align-items: center; gap: 8px;
              font-size: 13px; color: var(--gris); }

main { max-width: 1100px; margin: 0 auto; padding: 24px 20px 64px; }
h2 { font-size: 17px; margin: 28px 0 12px; letter-spacing: -.01em; }
h2:first-child { margin-top: 0; }
h3 { letter-spacing: -.01em; }

.aviso { padding: 11px 14px; border-radius: var(--r-control); margin-bottom: 16px;
         border: 1px solid var(--borde); background: var(--papel);
         border-left: 4px solid var(--borde-2); }
.aviso.ok { border-color: var(--borde); border-left-color: var(--verde);
            background: var(--verde-luz); }
.aviso.error { border-color: var(--borde); border-left-color: var(--rojo);
               background: var(--rojo-luz); }

/* Instrucciones que hay que volver a leer cada vez que se usa el campo.
   Ámbar y con borde grueso a la izquierda: en una pantalla de formulario
   gris y blanca, es lo único que salta. */
.pista { background: var(--ambar-luz); border: 1px solid var(--ambar-bde);
         border-left: 4px solid var(--ambar); border-radius: var(--r-control);
         padding: 11px 14px; margin: 8px 0 0; font-size: 13px; line-height: 1.55; }
.pista b { display: block; margin-bottom: 4px; }
.pista li b, .pista p b { display: inline; margin: 0; }
.pista code { background: var(--papel); border: 1px solid var(--ambar-bde);
              border-radius: 4px; padding: 1px 5px; font-size: 12px;
              font-family: ui-monospace, Consolas, monospace; }
.pista ul { margin: 6px 0 0; padding-left: 18px; }
.pista li { margin: 5px 0; }
.pista .mal { color: var(--rojo); font-weight: 700; }
.pista .bien { color: var(--verde); font-weight: 700; }

/* --- ofertas --- */
.filtros { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
.filtros a { display: inline-block; padding: 7px 14px; border: 1px solid var(--borde);
             border-radius: 999px; background: var(--papel); text-decoration: none;
             color: var(--gris); font-size: 13px; font-weight: 500; }
.filtros a:hover { border-color: var(--borde-2); color: var(--texto); }
.filtros a.activa { background: var(--acento); color: #fff; border-color: var(--acento); }
.filtros .cuenta { font-variant-numeric: tabular-nums; opacity: .75; }
.filtros.fechas { align-items: center; margin-bottom: 20px; }
.filtros .rotulo { font-size: 12px; color: var(--gris); text-transform: uppercase;
                   letter-spacing: .06em; margin-right: 4px; }

/* El costo de no saber inglés. Se pidió que incomode, así que el número va
   grande y el cartel no se puede cerrar. */
.duele { display: flex; align-items: center; gap: 16px; margin: 0 0 18px;
         background: var(--ambar-luz); border: 1px solid var(--ambar-bde);
         border-left: 4px solid var(--ambar); border-radius: var(--r-caja);
         padding: 14px 18px; }
.duele .numero { font-size: 34px; font-weight: 800; line-height: 1;
                 color: var(--ambar); font-variant-numeric: tabular-nums; }
.duele .dice { font-size: 13.5px; line-height: 1.5; }
@media (max-width: 560px) { .duele { flex-direction: column; align-items: flex-start;
                                     gap: 8px; } }

.oferta { display: grid; grid-template-columns: 60px 1fr 260px; gap: 16px;
          background: var(--papel); border: 1px solid var(--borde);
          border-radius: var(--r-caja); padding: 16px; margin-bottom: 12px;
          align-items: start; box-shadow: var(--sombra); }
.puntaje { font-size: 21px; font-weight: 700; text-align: center;
           font-variant-numeric: tabular-nums; border-radius: var(--r-control);
           padding: 8px 0; background: var(--papel-2); color: var(--gris);
           line-height: 1.1; }
.puntaje .de { display: block; font-size: 10px; font-weight: 500; letter-spacing: .06em;
               text-transform: uppercase; opacity: .7; }
.puntaje.alto { background: var(--verde-luz); color: var(--verde); }
.oferta h3 { font-size: 16px; margin: 0 0 6px; line-height: 1.35; }
.oferta h3 a { text-decoration: none; color: var(--texto); }
.oferta h3 a:hover { color: var(--acento); text-decoration: underline; }
.meta { color: var(--gris); font-size: 13px; margin: 3px 0; }
.datos-meta { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 8px;
              list-style: none; padding: 0; }
.datos-meta li { font-size: 12px; color: var(--gris); background: var(--papel-2);
                 border-radius: 999px; padding: 3px 9px; }
.datos-meta li.fuente { font-variant-numeric: tabular-nums; }
.datos-meta li.cuando { font-variant-numeric: tabular-nums; cursor: help;
                        border: 1px solid var(--borde); }
.razon { font-size: 13.5px; margin: 8px 0 0; color: var(--texto); }
.enlaces { margin: 10px 0 0; display: flex; flex-wrap: wrap; gap: 14px; }

.acciones { display: flex; flex-direction: column; gap: 8px; }
.acciones .fila { display: flex; gap: 8px; }
.acciones .fila button { flex: 1; }
button { font: inherit; font-weight: 500; padding: 9px 14px;
         border-radius: var(--r-control); cursor: pointer; min-height: 40px;
         border: 1px solid var(--borde-2); background: var(--papel);
         color: var(--texto); transition: background .12s, border-color .12s,
         transform .06s; }
button:hover { border-color: var(--gris); }
button:active { transform: translateY(1px); }
button.verde { background: var(--verde); border-color: var(--verde); color: #fff; }
button.rojo  { background: var(--rojo);  border-color: var(--rojo);  color: #fff; }
@media (prefers-color-scheme: dark) {
  /* En oscuro el verde y el rojo son claros: el texto blanco no se leería. */
  button.verde, button.rojo { color: #10151a; font-weight: 700; }
}
button.verde:hover, button.rojo:hover { filter: brightness(1.08); }
.acciones input[type=text] { width: 100%; padding: 9px 10px; border: 1px solid var(--borde-2);
                             border-radius: var(--r-control); font: inherit; font-size: 13px;
                             background: var(--papel); color: var(--texto); }
.acciones input[type=text]::placeholder { color: var(--gris); opacity: .85; }
.acciones input.mal { border-color: var(--rojo); background: var(--rojo-luz); }
.error-motivo { display: none; font-size: 12.5px; color: var(--rojo); margin: 0; }
.error-motivo.visible { display: block; }
.marca { font-size: 13px; padding: 10px 12px; border-radius: var(--r-control);
         background: var(--papel-2); }
.marca.si { background: var(--verde-luz); color: var(--verde); font-weight: 600; }
.marca.no { background: var(--rojo-luz); color: var(--rojo); }
.marca small { color: var(--texto); font-weight: 400; }

/* --- formularios --- */
form.datos { background: var(--papel); border: 1px solid var(--borde);
             border-radius: var(--r-caja); padding: 20px; box-shadow: var(--sombra); }
form.datos h2 { border-top: 1px solid var(--borde); padding-top: 20px; }
form.datos h2:first-of-type { border-top: 0; padding-top: 0; }
.grilla { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
          gap: 16px 20px; }
.campo { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
.campo label { font-size: 13px; color: var(--gris); font-weight: 500; }
.campo input[type=text], .campo input[type=number], .campo input[type=password],
.campo select, textarea {
    padding: 9px 10px; border: 1px solid var(--borde-2);
    border-radius: var(--r-control); font: inherit; min-height: 40px;
    background: var(--papel); color: var(--texto); }
.campo input::placeholder, textarea::placeholder { color: var(--gris); opacity: .8; }
textarea { width: 100%; font-family: ui-monospace, Consolas, monospace;
           font-size: 13px; line-height: 1.55; resize: vertical; }
.ancho { grid-column: 1 / -1; }
.checks { display: flex; gap: 10px 20px; flex-wrap: wrap; align-items: flex-start; }
.checks label { font-size: 14px; display: flex; align-items: center; gap: 7px;
                min-height: 32px; cursor: pointer; }
.checks input[type=checkbox] { width: 17px; height: 17px; accent-color: var(--acento);
                               margin: 0; cursor: pointer; }
.tilde { display: flex; flex-direction: column; gap: 1px; }
.tilde .nota { font-size: 12px; color: var(--gris); max-width: 34ch;
               padding-left: 24px; line-height: 1.45; }
.ayuda { font-size: 12.5px; color: var(--gris); margin: 3px 0 0; line-height: 1.5; }

/* La barra de guardar se pega abajo: el formulario es largo y el botón
   quedaba fuera de pantalla, así que se guardaba a ciegas o no se guardaba. */
.guardar { position: sticky; bottom: 0; margin: 24px -20px -20px;
           padding: 14px 20px; background: var(--papel);
           border-top: 1px solid var(--borde);
           border-radius: 0 0 var(--r-caja) var(--r-caja); }
.guardar button { padding: 11px 24px; background: var(--acento);
                  border-color: var(--acento); color: #fff; font-size: 15px;
                  font-weight: 600; }
@media (prefers-color-scheme: dark) { .guardar button { color: #10151a; } }
.guardar button:hover { background: var(--acento-fte); border-color: var(--acento-fte); }

.herramientas { margin: 0 0 16px; display: flex; flex-wrap: wrap; gap: 10px; }
a.boton { display: inline-block; padding: 9px 16px; border-radius: var(--r-control);
          background: var(--acento); color: #fff; text-decoration: none;
          font-size: 14px; font-weight: 500; }
@media (prefers-color-scheme: dark) { a.boton { color: #10151a; } }
a.boton:hover { background: var(--acento-fte); }
a.chico { font-size: 13px; }
.terminos { display: flex; flex-wrap: wrap; gap: 7px; list-style: none;
            padding: 0; margin: 0 0 10px; }
.terminos li { background: var(--acento-luz); color: var(--acento-fte);
               border-radius: 999px; padding: 4px 11px; font-size: 13px;
               font-weight: 500; }
@media (prefers-color-scheme: dark) { .terminos li { color: var(--acento-fte); } }
pre.consejo { white-space: pre-wrap; font: inherit; margin: 0; line-height: 1.6; }
.mensaje textarea { min-height: 160px; }
.mensaje { background: var(--papel); border: 1px solid var(--borde);
           border-radius: var(--r-caja); padding: 16px; margin-bottom: 14px;
           box-shadow: var(--sombra); }
.mensaje h3 { margin-top: 0; }
.vacio { color: var(--gris); background: var(--papel);
         border: 1px dashed var(--borde-2); border-radius: var(--r-caja);
         padding: 40px 24px; text-align: center; line-height: 1.6; }
.vacio b { color: var(--texto); }
.vacio code { background: var(--papel-2); border-radius: 4px; padding: 2px 6px;
              font-family: ui-monospace, Consolas, monospace; font-size: 13px; }

@media (max-width: 860px) {
  .oferta { grid-template-columns: 52px 1fr; gap: 12px; }
  .acciones { grid-column: 1 / -1; }
  .acciones .fila button { min-height: 44px; }   /* dedo, no mouse */
}
@media (max-width: 560px) {
  main { padding: 16px 14px 56px; }
  .oferta { grid-template-columns: 1fr; padding: 14px; }
  .puntaje { width: 60px; }
  form.datos { padding: 16px; }
  .guardar { margin: 20px -16px -16px; padding: 12px 16px; }
  .guardar button { width: 100%; }
  .barra { min-height: 52px; }
  .perfil-sel { margin-left: 0; width: 100%; }
}

/* MOTION_INTENSITY 2: sólo hover y active. Aun así, quien pide menos
   movimiento no recibe ninguno. */
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
"""

# Lo único que necesita JavaScript: que el motivo sea obligatorio al descartar.
# `required` no sirve porque el mismo formulario tiene un botón que no lo pide.
#
# El error se muestra al lado del campo, no con un alert(): el alert tapa la
# pantalla, hay que sacarlo antes de poder escribir, y no deja ver cuál de las
# ofertas lo pidió cuando hay veinte en la lista. El servidor lo valida igual
# (`_post_feedback`), así que esto es comodidad, no la garantía.
JS = """
function descartar(boton) {
  var form  = boton.closest('form');
  var campo = form.querySelector('input[name=motivo]');
  var error = form.querySelector('.error-motivo');
  if (!campo.value.trim()) {
    campo.classList.add('mal');
    campo.setAttribute('aria-invalid', 'true');
    if (error) error.classList.add('visible');
    campo.focus();
    return false;
  }
  campo.classList.remove('mal');
  campo.removeAttribute('aria-invalid');
  if (error) error.classList.remove('visible');
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
<title>{esc(titulo)} · vacantia</title>
<style>{CSS}</style><script>{JS}</script>
</head><body>
<a class="saltar" href="#contenido">Saltar al contenido</a>
<header><div class="barra">
  <h1>VACANTIA</h1>
  <nav>{link('trabajos', 'Trabajos', 'trabajos')}{link('datos', 'Mis datos', 'datos')}</nav>
  <form class="perfil-sel" method="get" action="/{esc(tab)}">
    <label for="perfil-sel">Perfil</label>
    <select id="perfil-sel" name="perfil" onchange="this.form.submit()">{opciones}</select>
    <noscript><button type="submit">Cambiar</button></noscript>
  </form>
</div></header>
<main id="contenido">{cuerpo}</main>
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

#: El otro eje: qué tan viejo es el aviso. Se cruza con FILTROS, no lo reemplaza.
RANGOS = (
    ("hoy", "Hoy"),
    ("7d", "Últimos 7 días"),
    ("30d", "Últimos 30 días"),
    ("todo", "Sin filtro"),
)


def _cuando(oferta: dict) -> tuple[str, str]:
    """(texto, título) del chip de fecha.

    Distingue "publicado" de "visto" a propósito. Casi la mitad de los avisos no
    dicen cuándo se publicaron y ahí se cae a la fecha en que lo encontramos,
    que puede ser mucho más nueva: un aviso de hace tres meses encontrado ayer
    parecería de ayer. Decir cuál de las dos es cuesta una palabra.
    """
    momento, publicada = fecha_de(oferta)
    if momento is None:
        return "sin fecha", "El aviso no dice cuándo se publicó."
    dias = dias_desde(momento) or 0
    if publicada:
        cuando = "publicado hoy" if dias <= 0 else f"publicado hace {dias} d"
        return cuando, f"El aviso dice que se publicó el {momento.isoformat()}."
    visto = "visto hoy" if dias <= 0 else f"visto hace {dias} d"
    return visto, ("El aviso no dice cuándo se publicó. Esta es la fecha en que "
                   f"lo encontramos ({momento.isoformat()}): el aviso puede ser "
                   "bastante más viejo.")


def _tarjeta(oferta: dict, perfil: str, ver: str, desde: str = "todo") -> str:
    score = oferta.get("score")
    clase = "puntaje alto" if isinstance(score, int) and score >= 70 else "puntaje"
    titulo = oferta.get("scored_title") or oferta.get("title") or "(sin título)"
    lugar = oferta.get("location_remote") or oferta.get("location") or ""
    url = oferta.get("url", "")

    # Cada dato en su propia etiqueta, en vez de una tira separada por puntos.
    # Con cuatro datos la tira quedaba "ACME · Remoto · linkedin · 2026-09-04",
    # que se lee como una sola frase larga y no deja distinguir qué es cada cosa.
    cuando, detalle_fecha = _cuando(oferta)
    etiquetas = "".join(
        f'<li class="{cls}">{esc(valor)}</li>'
        for valor, cls in (
            (oferta.get("company"), "empresa"),
            (lugar, "lugar"),
            (oferta.get("source"), "origen"),
        )
        if valor
    )
    etiquetas += (f'<li class="cuando" title="{esc(detalle_fecha)}">'
                  f'{esc(cuando)}</li>')

    aplicado = oferta.get("aplicado")
    if aplicado is True:
        acciones = '<div class="marca si">Aplicaste</div>'
    elif aplicado is False:
        motivo = esc(oferta.get("motivo_descarte") or "sin motivo")
        acciones = f'<div class="marca no">Descartada<br><small>{motivo}</small></div>'
    else:
        acciones = f"""<form class="acciones" method="post" action="/feedback">
      <input type="hidden" name="perfil" value="{esc(perfil)}">
      <input type="hidden" name="ver" value="{esc(ver)}">
      <input type="hidden" name="desde" value="{esc(desde)}">
      <input type="hidden" name="url" value="{esc(url)}">
      <div class="fila">
        <button class="verde" name="aplicado" value="si">Apliqué</button>
        <button class="rojo" name="aplicado" value="no"
                onclick="return descartar(this)">No apliqué</button>
      </div>
      <input type="text" name="motivo" placeholder="Por qué no apliqué (obligatorio)">
      <p class="error-motivo">Escribí el motivo. Es lo que hace que el sistema aprenda
      qué no mostrarte.</p>
    </form>"""

    razon = oferta.get("reason") or ""
    stack = oferta.get("stack") or ""
    enlace = quote(url, safe="")
    return f"""<article class="oferta">
  <div class="{clase}">{esc(score if score is not None else '?')}<span class="de">de 100</span></div>
  <div class="datos">
    <h3><a href="{esc(url)}" target="_blank" rel="noopener">{esc(titulo)}</a></h3>
    <ul class="datos-meta">{etiquetas}</ul>
    {f'<p class="meta">{esc(stack)}</p>' if stack else ''}
    {f'<p class="razon">{esc(razon)}</p>' if razon else ''}
    <p class="enlaces">
      <a class="chico" href="/mensajes?perfil={esc(perfil)}&url={enlace}">Mensaje para escribirle</a>
      <a class="chico" href="/consejo?perfil={esc(perfil)}&url={enlace}">Consejo para el CV</a>
    </p>
  </div>
  {acciones}
</article>"""


# Cada filtro vacío significa algo distinto, y decir siempre "no hay ofertas"
# desperdicia el único momento en que la pantalla tiene toda la atención puesta.
VACIO = {
    "pendientes": ("No te queda ninguna sin mirar.",
                   "Cuando entren ofertas nuevas van a aparecer acá. "
                   "Si querés buscar ahora sin esperar el horario, "
                   "doble clic en <code>buscar_ahora.bat</code>."),
    "aplicadas": ("Todavía no marcaste ninguna como aplicada.",
                  "Cuando mandes un CV, tocá <b>Apliqué</b> en esa oferta."),
    "descartadas": ("Todavía no descartaste ninguna.",
                    "Cuando una no sirva, tocá <b>No apliqué</b> y escribí por qué. "
                    "Ese motivo es lo que después afina las búsquedas."),
    "todas": ("Todavía no hay ofertas guardadas.",
              "Doble clic en <code>buscar_ahora.bat</code> para correr la primera "
              "búsqueda. Tarda unos minutos."),
}


def _ingles(pena: dict) -> str:
    """El cartel de lo que cuesta no saber inglés.

    Va arriba de la lista y no se puede cerrar, por pedido: la idea es
    justamente que moleste. Sin esto, la lista filtrada da la impresión de que
    el mercado no pide inglés, cuando lo que se ve es el recorte del filtro.
    """
    cuantas = (pena or {}).get("cuantas") or 0
    if not cuantas:
        return ""
    mejor, titulo = pena.get("mejor"), pena.get("mejor_titulo") or ""
    detalle = ""
    if mejor is not None:
        detalle = (f' La mejor puntuaba <b>{esc(mejor)}</b>'
                   f'{f", <i>{esc(titulo)}</i>" if titulo else ""}.')
    return f"""<div class="duele">
  <span class="numero">{esc(cuantas)}</span>
  <span class="dice">ofertas que no podés tomar porque piden inglés.{detalle}
  <br>No están filtradas por gusto: es lo que hoy te queda afuera.</span>
</div>"""


def trabajos(perfil: str, ofertas: list[dict], conteo: dict, ver: str,
             mensajes: list[tuple[str, str]], desde: str = "todo",
             conteo_fecha: dict | None = None, pena: dict | None = None) -> str:
    def chips(opciones, activo, param, cuentas, otro_param, otro_valor):
        return "".join(
            f'<a href="/trabajos?perfil={esc(perfil)}&{otro_param}={esc(otro_valor)}'
            f'&{param}={clave}"{" class=activa" if clave == activo else ""}>{etiqueta} '
            f'<span class="cuenta">{(cuentas or {}).get(clave, 0)}</span></a>'
            for clave, etiqueta in opciones
        )

    # Cada botón conserva el valor del otro eje: cambiar de "Sin marcar" a
    # "Descarté" no tiene por qué devolverte a ver los avisos de hace un año.
    por_estado = chips(FILTROS, ver, "ver", conteo, "desde", desde)
    por_fecha = chips(RANGOS, desde, "desde", conteo_fecha, "ver", ver)

    if ofertas:
        listado = "".join(_tarjeta(o, perfil, ver, desde) for o in ofertas)
    elif desde != "todo":
        listado = (
            '<div class="vacio"><b>Ninguna en ese rango de fechas.</b><br>'
            'Probá con <b>Sin filtro</b> para ver también las más viejas.</div>'
        )
    else:
        titulo, detalle = VACIO.get(ver, VACIO["todas"])
        listado = f'<div class="vacio"><b>{titulo}</b><br>{detalle}</div>'

    return f"""{avisos(mensajes)}
<h2>Trabajos</h2>
{_ingles(pena)}
<div class="filtros">{por_estado}</div>
<div class="filtros fechas">
  <span class="rotulo">Antigüedad del aviso</span>{por_fecha}
</div>
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
<p class="meta">{esc(titulo)} · <a href="{esc(url)}" target="_blank" rel="noopener">ver el aviso</a></p>
<p class="herramientas"><a class="boton" href="/trabajos?perfil={esc(perfil)}">Volver a Trabajos</a></p>
{cajas}
{boton}
<p class="ayuda">Estos moldes son un borrador: máximo 4 líneas, cero adjetivos
sobre uno mismo, y cerrar con una pregunta fácil de responder.</p>"""


# --- consejo sobre el CV ----------------------------------------------------

def consejo(perfil: str, oferta: dict, faltantes: list[str], texto: str,
            con_llm: bool, avisos_: list[tuple[str, str]]) -> str:
    """Qué reordenar del CV para este aviso. No lo reescribe."""
    titulo = oferta.get("scored_title") or oferta.get("title") or "(sin título)"
    url = oferta.get("url", "")

    if faltantes:
        lista = "".join(f"<li>{esc(t)}</li>" for t in faltantes)
        huecos = f"""<ul class="terminos">{lista}</ul>
<p class="ayuda">Están en el aviso y no en tu CV. <b>No las agregues si no las
hacés</b>: se nota en la primera entrevista. Sí valen las que sabés hacer y
escribiste con otra palabra.</p>"""
    else:
        huecos = ('<p class="ayuda">Tu CV ya menciona todos los términos '
                  'importantes del aviso.</p>')

    if texto:
        cuerpo = f'<div class="mensaje"><pre class="consejo">{esc(texto)}</pre></div>'
    else:
        cuerpo = f"""<form method="post" action="/consejo">
  <input type="hidden" name="perfil" value="{esc(perfil)}">
  <input type="hidden" name="url" value="{esc(url)}">
  <button type="submit">Leer el aviso y decirme qué reordenar</button>
  <p class="ayuda">Usa una llamada al modelo. No reescribe el CV: dice qué subir
  y qué palabra falta.</p>
</form>"""

    return f"""{avisos(avisos_)}
<h2>Consejo para tu CV</h2>
<p class="meta">{esc(titulo)} · {esc(oferta.get('company') or 'sin empresa')}<br>
<a href="{esc(url)}" target="_blank" rel="noopener">ver el aviso</a></p>
<p class="herramientas"><a class="boton" href="/trabajos?perfil={esc(perfil)}">Volver a Trabajos</a></p>

<h2>Palabras del aviso que no están en tu CV</h2>
<div class="mensaje">{huecos}</div>

<h2>Qué mover</h2>
{cuerpo}
<p class="ayuda">Tu CV no se toca: esto es para que lo edites vos con criterio.</p>"""
