"""El HTML de la UI. Sin plantillas ni librerías: strings y f-strings.

La hoja de estilos vive en `estilos.py` y es la implementación de `DESIGN.md`.
Acá sólo se arma el marcado, y hay tres reglas que mandan sobre cualquier otra
consideración cuando se toca una pantalla:

1. **Una decisión por vez.** En pantalla está la acción que la persona vino a
   hacer. Los controles secundarios aparecen cuando se necesitan, no antes. En
   la tarjeta de oferta eso es una regla dura: **más de dos controles visibles
   por oferta es un error de diseño.**
2. **Nunca mostrar lo que la persona se pierde antes de lo que puede hacer.**
   Los recuentos de ofertas inalcanzables son información legítima y viven en
   Métricas, con la explicación y con el link a la sección donde se arregla.
   Arriba de la lista de trabajos no va ningún recuento de pérdidas.
3. **El estado del sistema es siempre visible.** Cuándo buscó, cuándo vuelve a
   buscar, qué ventana de días cubre. Tiene lugar fijo al pie de la barra
   lateral, en castellano llano, y es texto estático: cambia cuando cambia el
   dato, no solo.
"""

from datetime import date, datetime  # noqa: F401  (date, para la anotación)
from html import escape
from urllib.parse import quote, urlencode

from vacantia.fechas import dias_desde, fecha_de, parse_posted
from vacantia.ui.estilos import CSS  # noqa: F401  (lo importan los tests y `pagina`)

#: Cómo se abre el aviso en el portal. **`noreferrer` no es cosmético ni está
#: por privacidad: sin él, Computrabajo se rompe.**
#:
#: Sin `noreferrer` el navegador le cuenta al portal que venís de
#: `http://127.0.0.1:8756`, y Computrabajo guarda esa dirección en una cookie
#: propia (`extrfr`, de *external referrer*). A partir de ahí, **todos** los
#: pedidos de ese navegador al sitio llevan una URL a localhost adentro de una
#: cookie, que es la firma clásica de un ataque SSRF, y el firewall que tiene
#: delante contesta `403 Forbidden` en el sitio entero hasta que se borre la
#: cookie. No es un aviso el que falla: es uno que rompe todos los siguientes.
#:
#: Verificado el 7/9/2026 pegándole a un aviso con la cookie armada a mano:
#:
#:     extrfr=http://127.0.0.1:8756/trabajos       -> 403
#:     extrfr=http://localhost:8756/trabajos       -> 403
#:     extrfr=http%3A%2F%2F127.0.0.1%3A8756%2F...  -> 403  (tampoco zafa escapada)
#:     extrfr=https://ejemplo.com/x                -> 200  (un referrer normal no molesta)
#:     extrfr=127.0.0.1:8756/trabajos              -> 200  (sin el esquema no dispara)
#:     sin la cookie                               -> 200
#:
#: `noreferrer` implica `noopener`, así que reemplazarlo no pierde nada.
ABRIR_EL_AVISO = 'target="_blank" rel="noreferrer"'

# --- iconos -----------------------------------------------------------------
#
# Lucide, dibujados a mano acá adentro: son cuatro trazos y bajar una librería
# entera para eso sería pedirle a la red algo que la app no necesita. Todos con
# el mismo grosor de línea, que es lo que hace que se vean de la misma familia.

def _icono(trazos: str) -> str:
    return (f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{trazos}</svg>')


ICONOS = {
    "trabajos": _icono('<rect width="20" height="14" x="2" y="7" rx="2"/>'
                       '<path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>'),
    "linkedin": _icono('<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.8 1.7"/>'
                       '<path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.8-1.7"/>'),
    "estadisticas": _icono('<path d="M3 3v18h18"/><path d="M18 17V9"/>'
                           '<path d="M13 17V5"/><path d="M8 17v-3"/>'),
    "datos": _icono('<circle cx="12" cy="8" r="4.5"/><path d="M20 21a8 8 0 0 0-16 0"/>'),
    "filtradas": _icono('<path d="M3 5h18l-7 8v6l-4 2v-8Z"/>'),
    "mas": _icono('<circle cx="5" cy="12" r=".6"/><circle cx="12" cy="12" r=".6"/>'
                  '<circle cx="19" cy="12" r=".6"/>'),
}

# Lo único que necesita JavaScript: que el motivo sea obligatorio al descartar,
# volver al mismo lugar de la lista después de marcar, y avisar si entraron
# ofertas con la pantalla abierta. Todo lo demás anda sin JavaScript: el bloque
# de motivo y el menú de tres puntos son `<details>`, que se abren solos.
#
# El error se muestra al lado del campo, no con un alert(): el alert tapa la
# pantalla, hay que sacarlo antes de poder escribir, y no deja ver cuál de las
# ofertas lo pidió cuando hay veinte en la lista. El servidor lo valida igual
# (`_post_feedback`), así que esto es comodidad, no la garantía.
JS = """
function marcarBien(form) {
  var campo = form.querySelector('input[name=motivo]');
  var error = form.querySelector('.error-motivo');
  var select = form.querySelector('select[name=motivo_clave]');
  [campo, select].forEach(function (el) {
    if (!el) { return; }
    el.classList.remove('mal');
    el.removeAttribute('aria-invalid');
  });
  if (error) { error.classList.remove('visible'); }
}

// Alcanza con CUALQUIERA de los dos: elegir un motivo de la lista, o
// escribirlo. No hay opción "Otro motivo" en el desplegable a propósito —
// obligaba a abrirlo, bajar hasta "Otro" y recién ahí escribir, tres pasos de
// más justo cuando ya tenías la mano en el teclado.
function descartar(boton) {
  var form   = boton.closest('form');
  var select = form.querySelector('select[name=motivo_clave]');
  var campo  = form.querySelector('input[name=motivo]');
  var error  = form.querySelector('.error-motivo');
  if ((select && select.value) || (campo && campo.value.trim())) {
    marcarBien(form);
    return true;
  }
  var flojo = select || campo;
  flojo.classList.add('mal');
  flojo.setAttribute('aria-invalid', 'true');
  if (error) { error.classList.add('visible'); }
  flojo.focus();
  return false;
}

// Volver al mismo lugar de la lista después de marcar una oferta.
//
// Marcar es un POST que redirige a un GET (si no, recargar reenviaría el
// formulario), y el navegador abre esa página nueva arriba de todo. Con 40
// ofertas eso significa que después de marcar la número 30 hay que volver a
// bajar hasta ahí. Se guarda dónde estabas justo antes de enviar y se vuelve
// al llegar; la clave se consume una sola vez, así un F5 posterior no te
// mueve.
var CLAVE_SCROLL = 'vacantia:scroll';

function recordarScroll() {
  try { sessionStorage.setItem(CLAVE_SCROLL, String(window.scrollY)); } catch (e) {}
}

function volverAlScroll() {
  var y;
  try {
    y = sessionStorage.getItem(CLAVE_SCROLL);
    sessionStorage.removeItem(CLAVE_SCROLL);
  } catch (e) { return; }
  if (y === null) { return; }
  // 'instant' y no 'smooth': ya estabas ahí, no es un viaje.
  window.scrollTo({ top: parseInt(y, 10) || 0, behavior: 'instant' });
}

// Lo mismo, pero para la columna del constructor de LinkedIn.
//
// Ahí la página entera no scrollea: scrollea cada columna por dentro. Armar la
// búsqueda es un GET, o sea una recarga, y la columna vuelve arriba: si venías
// eligiendo abajo de todo, cada intento te devolvía al principio del
// formulario. Se guarda dónde estabas y se vuelve, igual que en la lista.
var CLAVE_TALLER = 'vacantia:taller';

function elLado() { return document.querySelector('.taller > .controles'); }

function recordarTaller() {
  var col = elLado();
  if (!col) { return; }
  try { sessionStorage.setItem(CLAVE_TALLER, String(col.scrollTop)); } catch (e) {}
}

function volverAlTaller() {
  var col = elLado(), y;
  if (!col) { return; }
  try {
    y = sessionStorage.getItem(CLAVE_TALLER);
    sessionStorage.removeItem(CLAVE_TALLER);
  } catch (e) { return; }
  if (y === null) { return; }
  col.scrollTop = parseInt(y, 10) || 0;
}

// El menú de tres puntos se cierra al tocar afuera. Sin esto quedan tres menús
// abiertos tapando la lista y hay que cerrarlos de a uno.
function cerrarMenus(salvo) {
  document.querySelectorAll('details.menu[open]').forEach(function (m) {
    if (m !== salvo) { m.removeAttribute('open'); }
  });
}

// Una columna que scrollea recorta lo que se le sale, y el menú de la última
// guardada se abre justo contra el borde de abajo. Al abrirlo se lo trae a la
// vista; 'nearest' mueve lo mínimo, así que si ya entraba no mueve nada.
function menuALaVista(menu) {
  var panel = menu.querySelector('.panel');
  if (panel && panel.scrollIntoView) {
    panel.scrollIntoView({ block: 'nearest', behavior: 'instant' });
  }
}

document.addEventListener('DOMContentLoaded', function () {
  volverAlScroll();
  volverAlTaller();
  // Para los envíos que sí pasan por 'submit': archivar, y marcar cuando la
  // animación está apagada por prefers-reduced-motion.
  document.querySelectorAll('form.acciones').forEach(function (form) {
    form.addEventListener('submit', recordarScroll);
  });
  document.querySelectorAll('form.armador').forEach(function (form) {
    form.addEventListener('submit', recordarTaller);
  });
  document.querySelectorAll('details.menu').forEach(function (m) {
    m.addEventListener('toggle', function () { if (m.open) { menuALaVista(m); } });
  });
  document.addEventListener('click', function (ev) {
    var dentro = ev.target.closest ? ev.target.closest('details.menu') : null;
    cerrarMenus(dentro);
  });
});

// Marcar una oferta: se la ve irse antes de que la página se recargue.
//
// El servidor sigue haciendo todo el trabajo; esto es sólo para que se note
// CUÁL se fue. Con dos ofertas de 90 pegadas, la página vuelve y la lista se
// ve igual: no hay forma de saber a cuál le diste.
//
// Sin JavaScript el botón envía el formulario como siempre, y quien pidió
// menos movimiento tampoco espera la animación.
function marcar(boton, esDescarte) {
  if (esDescarte && !descartar(boton)) { return false; }
  var tarjeta = boton.closest('.oferta');
  var quieto = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!tarjeta || quieto) { return true; }

  // `form.submit()` no manda el botón apretado, así que se agrega a mano:
  // sin esto el servidor no sabría si fue "apliqué" o "no apliqué".
  var form = boton.closest('form');
  var oculto = document.createElement('input');
  oculto.type = 'hidden';
  oculto.name = boton.name;
  oculto.value = boton.value;
  form.appendChild(oculto);

  tarjeta.classList.add('yendose');
  // OJO: `form.submit()` NO dispara el evento 'submit', así que el listener de
  // más abajo no alcanza y hay que guardar la posición a mano. Es exactamente
  // lo que hacía que después de marcar volvieras arriba de todo.
  recordarScroll();
  setTimeout(function () { form.submit(); }, 220);
  return false;
}

// Copiar la URL armada al portapapeles, y avisar que se copió.
//
// Es el único caso de toast de la app, y está porque el resultado NO se ve: el
// portapapeles es invisible. Guardar un favorito no lleva toast, porque el
// favorito aparece en la lista y avisar lo que ya se ve es ruido.
//
// Sin `navigator.clipboard` (pasa si la página no es segura) se cae a
// seleccionar el texto, que deja el Ctrl+C a un paso.
function copiar(boton, url) {
  var listo = function () { avisar('Link copiado'); };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(listo, function () { seleccionar(boton); });
  } else {
    seleccionar(boton);
  }
  return false;
}

function seleccionar(boton) {
  var bloque = boton.closest('section, li');
  var texto = bloque && bloque.querySelector('.url-generada');
  if (!texto) { return; }
  var rango = document.createRange();
  rango.selectNodeContents(texto);
  var sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(rango);
  avisar('Seleccionada: apretá Ctrl+C');
}

// El toast: 4 segundos, abajo a la derecha, uno solo a la vez. El anterior se
// reemplaza en vez de apilarse, que es lo que convierte un aviso en un estorbo.
var TOAST_TIMER = null;

function avisar(texto) {
  var toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = 'toast';
    toast.setAttribute('role', 'status');
    document.body.appendChild(toast);
  }
  toast.textContent = texto;
  toast.classList.add('visible');
  if (TOAST_TIMER) { clearTimeout(TOAST_TIMER); }
  TOAST_TIMER = setTimeout(function () { toast.classList.remove('visible'); }, 4000);
}

// Avisa cuando entraron ofertas mientras la pantalla estaba abierta, para no
// tener que apretar F5. Le pregunta al servidor cada 20 segundos si el archivo
// del historial cambió; es una request local y no lee el archivo entero.
//
// NO recarga sola a propósito: si alguien está escribiendo el motivo de un
// descarte, una recarga se lo borra. Avisa, y decide la persona. El cartel es
// texto quieto: no parpadea, no pulsa y no cuenta nada hacia atrás.
function vigilarNovedades(perfil, marca, pendientesAlAbrir) {
  var cartel = document.getElementById('novedades');
  if (!cartel) { return; }
  setInterval(function () {
    fetch('/novedades?perfil=' + encodeURIComponent(perfil))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.marca || d.marca === marca) { return; }
        // La diferencia contra lo que habia al abrir, no el total: "entraron
        // 211 ofertas" cuando entraron 3 es peor que no decir nada.
        var nuevas = d.pendientes - pendientesAlAbrir;
        var texto = document.getElementById('novedades-texto');
        if (texto) {
          texto.textContent = nuevas > 0
            ? ('Entraron ' + nuevas + (nuevas === 1 ? ' oferta nueva' : ' ofertas nuevas'))
            : 'La lista cambió';
        }
        cartel.classList.add('visible');
      })
      .catch(function () { /* la ventana negra se cerro: se reintenta solo */ });
  }, 20000);
}
"""


def esc(texto) -> str:
    """Escapa para HTML. Sólo `None` se convierte en vacío.

    Ojo con `texto or ""`, que fue el bug: el cero es falsy, así que una oferta
    puntuada 0 salía con la caja del puntaje en blanco. Y justo el 0 es el
    puntaje que más importa mostrar, porque es el que dice "esto no es para vos".
    """
    return escape("" if texto is None else str(texto), quote=True)


# --- el shell ---------------------------------------------------------------

#: (ruta, etiqueta, clave). El sidebar agrupa por lo que la persona hace, no por
#: lo que la sección es: primero buscar, después revisar y configurar.
SECCIONES_BUSCAR = (
    ("trabajos", "Trabajos", "trabajos"),
    ("linkedin", "LinkedIn URLs", "linkedin"),
)
SECCIONES_RESTO = (
    ("estadisticas", "Métricas", "estadisticas"),
    ("datos", "Mi perfil", "datos"),
)


def _boton_buscar(perfil: str, corriendo: bool, primario: bool = False) -> str:
    """El botón que arranca una búsqueda sin esperar el horario.

    Antes esto era un archivo `.bat` que había que ir a buscar al Explorador, y
    la pantalla te lo nombraba por su nombre de archivo. Si hay que ejecutar
    algo, es un botón con nombre humano.

    Al pie de la barra lateral va en secundario: la acción de esa pantalla es
    aplicar a una oferta, y dos primarios enfrentados obligan a decidir antes de
    leer. En un estado vacío no hay ninguna oferta que aplicar, así que ahí sí
    es el primario.
    """
    if corriendo:
        return ('<button type="button" disabled>Buscando ofertas</button>')
    clase = "primario" if primario else ""
    return f"""<form method="post" action="/buscar">
  <input type="hidden" name="perfil" value="{esc(perfil)}">
  <button class="{clase}" type="submit">Buscar ahora</button>
</form>"""


def _estado_del_sistema(perfil: str, estado: dict | None) -> str:
    """El pie fijo de la barra lateral.

    Cuándo buscó, cuándo vuelve, qué ventana cubre, y el botón para buscar ya.
    Es la respuesta a "¿esto es todo lo que hay?", que es de donde sale la mayor
    parte de la ansiedad de buscar trabajo, y por eso tiene un lugar fijo y no
    un tooltip. El botón va acá y no arriba porque es la acción sobre este dato:
    la salida de "la última búsqueda fue hace seis horas".

    El punto medio se reserva para esta línea y no se usa en ninguna otra.
    """
    if not estado:
        return ""
    ultima = estado.get("ultima") or "todavía no buscó"
    proxima = estado.get("proxima") or ""
    ventana = estado.get("ventana")
    linea = f"Última búsqueda: {esc(ultima)}"
    if proxima:
        linea += f" &middot; Próxima: {esc(proxima)}"
    if ventana:
        cubre = (f"<p>Trae avisos de los últimos <span class='valor'>{esc(ventana)}</span> "
                 f"días.</p>")
    else:
        cubre = "<p>Trae avisos sin límite de antigüedad.</p>"
    return (f'<div class="estado"><p>{linea}</p>{cubre}'
            f'{_boton_buscar(perfil, bool(estado.get("corriendo")))}</div>')


def pagina(titulo: str, cuerpo: str, perfil: str, perfiles: list[str], tab: str,
           estado: dict | None = None) -> str:
    """El shell: barra lateral a la izquierda, una sola columna a la derecha."""
    opciones = "".join(
        f'<option value="{esc(p)}"{" selected" if p == perfil else ""}>{esc(p)}</option>'
        for p in perfiles
    )

    def link(destino, etiqueta, clave):
        activa = " activa" if clave == tab else ""
        ahi = ' aria-current="page"' if clave == tab else ""
        return (f'<a class="nav-item{activa}" href="/{destino}?perfil={esc(perfil)}"{ahi}>'
                f'{ICONOS[clave]}<span class="etiqueta">{etiqueta}</span></a>')

    buscar = "".join(link(*s) for s in SECCIONES_BUSCAR)
    resto = "".join(link(*s) for s in SECCIONES_RESTO)

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Las ofertas de trabajo de varios portales, en una sola lista y con un puntaje de ajuste.">
<title>{esc(titulo)} · vacantia</title>
<style>{CSS}</style><script>{JS}</script>
</head><body class="app">
<a class="saltar" href="#contenido">Saltar al contenido</a>
<aside class="lateral">
  <a href="/trabajos?perfil={esc(perfil)}" class="marca-app">
    <span class="sello" aria-hidden="true">V</span><span class="nombre">VACANTIA</span>
  </a>
  <form class="perfil-sel" method="get" action="/{esc(tab)}">
    <label for="perfil-sel">Perfil</label>
    <select id="perfil-sel" name="perfil" onchange="this.form.submit()">{opciones}</select>
    <noscript><button type="submit">Cambiar de perfil</button></noscript>
  </form>
  <p class="grupo">Buscar</p>
  <nav aria-label="Buscar">{buscar}</nav>
  <hr class="separador">
  <nav aria-label="Revisar y configurar">{resto}</nav>
  {_estado_del_sistema(perfil, estado)}
</aside>
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
    ("filtradas", "Filtradas"),
    ("archivadas", "Archivadas"),
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


def _en_hora_local(guardada) -> "date | None":
    """El día local de una marca de tiempo guardada en UTC.

    Si no trae hora, o no se entiende, cae en `parse_posted`, que ya sabe leer
    todos los formatos que aparecen en el historial.
    """
    crudo = str(guardada or "").strip()
    if not crudo:
        return None
    try:
        momento = datetime.fromisoformat(crudo.replace("Z", "+00:00"))
    except ValueError:
        return parse_posted(crudo[:10])
    if momento.tzinfo is None:      # una fecha sola, sin hora ni zona
        return momento.date()
    return momento.astimezone().date()


def _cuando_marcada(oferta: dict) -> tuple[str, str]:
    """(texto, título) de cuándo se marcó. Vacío si no hay fecha guardada.

    La fecha se guarda en UTC y hay que pasarla a la hora de acá **antes** de
    quedarse con el día. Cortando los primeros diez caracteres del texto, todo
    lo que marcabas entre las 21:00 y la medianoche quedaba con la fecha de
    mañana en UTC, y al día siguiente la tarjeta decía "Aplicaste hoy" a algo de
    ayer. Son tres horas por día, justo las que más se usa la pantalla.
    """
    momento = _en_hora_local(oferta.get("fecha_feedback"))
    if momento is None:
        return "", ""
    dias = dias_desde(momento) or 0
    cuando = ("hoy" if dias <= 0 else "ayer" if dias == 1 else f"hace {dias} días")
    return cuando, f"El {momento.isoformat()}"


def _select_de_motivos() -> str:
    """El desplegable de por qué no apliqué.

    Con 60 descartes se vio en qué se convierte un campo de texto obligatorio:
    46 veces la misma frase escrita a mano. Los cuatro motivos salen de lo que
    de verdad se escribió, no de lo que uno imagina que se va a escribir.

    Al lado queda el campo de texto, **opcional**: con cualquiera de los dos
    alcanza para descartar. No hay una opción "Otro motivo" en la lista a
    propósito — obligaba a abrir el desplegable, bajar hasta "Otro" y recién ahí
    escribir, tres pasos de más justo en el caso en que ya tenías la mano en el
    teclado.
    """
    from vacantia.ui.data import MOTIVOS

    opciones = "".join(
        f'<option value="{esc(clave)}" title="{esc(ayuda)}">{esc(etiqueta)}</option>'
        for clave, etiqueta, ayuda in MOTIVOS
    )
    return (f'<select name="motivo_clave" aria-label="Motivo del descarte">'
            f'<option value="">Por qué no apliqué…</option>{opciones}</select>')


def _cabecera_de_tarjeta(oferta: dict) -> str:
    """Puntaje, título y etiquetas: lo que se lee de un vistazo."""
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

    return f"""  <div class="{clase}">{esc(score if score is not None else '?')}<span class="de">de 100</span></div>
  <div class="datos">
    <h3><a href="{esc(url)}" {ABRIR_EL_AVISO}>{esc(titulo)}</a></h3>
    <ul class="datos-meta">{etiquetas}</ul>"""


def _ocultos(perfil: str, ver: str, desde: str, pagina: int, url: str) -> str:
    return (f'<input type="hidden" name="perfil" value="{esc(perfil)}">'
            f'<input type="hidden" name="ver" value="{esc(ver)}">'
            f'<input type="hidden" name="desde" value="{esc(desde)}">'
            f'<input type="hidden" name="p" value="{pagina}">'
            f'<input type="hidden" name="url" value="{esc(url)}">')


def _tarjeta_filtrada(oferta: dict, perfil: str, desde: str, pagina: int,
                      cabecera: str) -> str:
    """Una oferta que descartó el sistema solo, para auditar si acertó.

    Lo que se lee acá es distinto de lo que se lee en Sin marcar. En Sin marcar
    la pregunta es "¿me postulo?"; acá es "¿el filtro acertó?", y para
    contestarla hacen falta dos cosas juntas: **el motivo que dio el sistema** y
    **el aviso**, para poder ir a mirarlo. Por eso el motivo va arriba de todo y
    con su explicación completa, y no escondido en un tooltip.

    Dos botones, y los dos sacan la oferta de esta lista: se revisa una vez y no
    vuelve a aparecer, así la pila baja y no hay que acordarse dónde se quedó
    uno. El primario es "Bien descartada" porque es la respuesta que se va a dar
    la mayoría de las veces; "Mal descartada" es la que encuentra el error, y
    además de anotarlo devuelve la oferta a Sin marcar.
    """
    url = oferta.get("url", "")
    razon = oferta.get("reason") or ""
    clave, explica = oferta.get("_motivo_sistema") or ("", "")
    etiqueta = _MOTIVOS_SISTEMA.get(clave, "El sistema la descartó")
    return f"""<article class="oferta filtrada">
{cabecera}
    <p class="por-que"><b>{esc(etiqueta)}</b>
    {f'<span class="detalle">{esc(explica)}</span>' if explica else ''}</p>
    {f'<p class="razon">{esc(razon)}</p>' if razon else ''}
    <form class="acciones" method="post" action="/revisar-filtro">
      {_ocultos(perfil, "filtradas", desde, pagina, url)}
      <button class="primario" name="revision" value="bien"
              onclick="return marcar(this, false)">Bien descartada</button>
      <button name="revision" value="mal"
              onclick="return marcar(this, false)">Mal descartada</button>
      <span class="ayuda">Si estuvo mal, vuelve a Sin marcar para que puedas aplicar.</span>
    </form>
  </div>
</article>"""


def _tarjeta(oferta: dict, perfil: str, ver: str, desde: str = "todo",
             pagina: int = 1) -> str:
    """Una oferta.

    Es el componente central de la app y el que más disciplina necesita. Por
    defecto se ven **dos controles y nada más**: "Apliqué" en primario y "No
    apliqué" en secundario. El bloque de motivo se despliega adentro de la misma
    tarjeta recién cuando se marca "No apliqué"; "Ya no está" y los links
    auxiliares viven en el menú de tres puntos de la esquina.

    Una vez marcada, la tarjeta pierde el vidrio esmerilado y baja a superficie
    plana: así se distingue de un vistazo lo que queda por hacer de lo que ya
    está hecho.
    """
    url = oferta.get("url", "")
    aplicado = oferta.get("aplicado")
    marcada, detalle_marca = _cuando_marcada(oferta)
    cabecera = _cabecera_de_tarjeta(oferta)

    if oferta.get("archivada") and aplicado is None:
        cuando_arch, det = _cuando_marcada({"fecha_feedback": oferta.get("fecha_archivada")})
        etiqueta = f"Archivada {cuando_arch}" if cuando_arch else "Archivada"
        return f"""<article class="oferta marcada">
{cabecera}
    <form class="acciones" method="post" action="/archivar">
      {_ocultos(perfil, ver, desde, pagina, url)}
      <span class="marca" title="{esc(det)}">{esc(etiqueta)}</span>
      <button class="fantasma" name="archivar" value="0">Devolver a la lista</button>
    </form>
  </div>
</article>"""

    if aplicado is True:
        etiqueta = f"Aplicaste {marcada}" if marcada else "Aplicaste"
        return f"""<article class="oferta marcada">
{cabecera}
    <p class="marca si" title="{esc(detalle_marca)}">{esc(etiqueta)}</p>
  </div>
</article>"""

    if aplicado is False:
        from vacantia.ui.data import partes_del_motivo
        etiqueta = f"Descartada {marcada}" if marcada else "Descartada"
        # El motivo de la lista y el escrito a mano van en elementos separados:
        # unirlos con un punto medio los convierte en una sola frase larga, y
        # el punto medio está reservado para la línea de estado del sistema.
        de_la_lista, escrito = partes_del_motivo(oferta)
        motivo = ""
        if de_la_lista:
            motivo += f'<span class="motivo-elegido">{esc(de_la_lista)}</span>'
        if escrito:
            motivo += f'<span class="motivo-escrito">{esc(escrito)}</span>'
        return f"""<article class="oferta marcada">
{cabecera}
    <p class="marca" title="{esc(detalle_marca)}">{esc(etiqueta)}</p>
    <p class="marca-motivo">{motivo or "sin motivo"}</p>
  </div>
</article>"""

    if ver == "filtradas":
        return _tarjeta_filtrada(oferta, perfil, desde, pagina, cabecera)

    razon = oferta.get("reason") or ""
    stack = oferta.get("stack") or ""
    enlace = quote(url, safe="")
    return f"""<article class="oferta">
{cabecera}
    {f'<p class="stack">{esc(stack)}</p>' if stack else ''}
    {f'<p class="razon">{esc(razon)}</p>' if razon else ''}
    <form class="acciones" method="post" action="/feedback">
      {_ocultos(perfil, ver, desde, pagina, url)}
      <button class="primario" name="aplicado" value="si"
              onclick="return marcar(this, false)">Apliqué</button>
      <details class="motivo">
        <summary>No apliqué</summary>
        <div class="cuerpo">
          {_select_de_motivos()}
          <input type="text" name="motivo" placeholder="...o escribí otro motivo">
          <p class="error-motivo">Elegí uno de la lista o escribí el motivo. Con
          cualquiera de los dos alcanza.</p>
          <button name="aplicado" value="no"
                  onclick="return marcar(this, true)">Descartar la oferta</button>
        </div>
      </details>
      <details class="menu">
        <summary title="Más opciones" aria-label="Más opciones">{ICONOS['mas']}</summary>
        <div class="panel">
          <a href="/mensajes?perfil={esc(perfil)}&url={enlace}">Mensaje para escribirle</a>
          <a href="/consejo?perfil={esc(perfil)}&url={enlace}">Consejo para el CV</a>
          <button class="fantasma" name="archivar" value="1"
                  formaction="/archivar" formnovalidate>Ya no está</button>
          <p class="nota">Archivar saca el aviso de la lista sin enseñarle nada al
          sistema sobre lo que te gusta. Se puede devolver.</p>
        </div>
      </details>
    </form>
  </div>
</article>"""


# Cada filtro vacío significa algo distinto, y decir siempre "no hay ofertas"
# desperdicia el único momento en que la pantalla tiene toda la atención puesta.
#
# El tercer elemento dice si ese vacío se arregla buscando. Cuando sí, la
# pantalla ofrece el botón en vez de nombrar un archivo que hay que ir a abrir
# al Explorador.
VACIO = {
    "pendientes": ("No te queda ninguna sin mirar.",
                   "Cuando entren ofertas nuevas van a aparecer acá. "
                   "Si no querés esperar al próximo horario, buscá ahora.", True),
    "aplicadas": ("Todavía no marcaste ninguna como aplicada.",
                  "Cuando mandes un CV, tocá <b>Apliqué</b> en esa oferta.", False),
    "descartadas": ("Todavía no descartaste ninguna.",
                    "Cuando una no sirva, tocá <b>No apliqué</b> y escribí por qué. "
                    "Ese motivo es lo que después afina las búsquedas.", False),
    "filtradas": ("No queda ninguna sin revisar.",
                  "Acá caen las que el sistema descarta solo, por idioma o por "
                  "lugar, para que puedas contestar si acertó. Las revisaste a "
                  "todas: cuando entren ofertas nuevas van a aparecer las que "
                  "el filtro saque.", False),
    "archivadas": ("No archivaste ninguna todavía.",
                   "Archivar es para los avisos que ya no están o quedaron viejos. "
                   "No es lo mismo que descartar: no le enseña nada al sistema "
                   "sobre tus gustos, sólo los saca de la lista.", False),
    "todas": ("Todavía no hay ofertas guardadas.",
              "Buscá ahora para correr la primera búsqueda. Tarda unos minutos y "
              "podés seguir usando la pantalla mientras tanto.", True),
}


def _postulaciones(perfil: str, ver: str, desde: str, aplicadas: dict | None) -> str:
    """"Apliqué a N trabajos", grande y en verde, arriba de la lista.

    Es lo único de la app que mide el trabajo de **la persona** y no el del
    sistema: los otros contadores dicen cuántas ofertas hay, éste dice cuántas
    veces te postulaste. Por eso es lo más grande de la pantalla y por eso es lo
    único que usa `text-hero`.

    Va sólo en **Sin marcar**, que es la pantalla que se abre por defecto. En
    las otras pestañas la persona está revisando algo puntual y el contador
    sería un cartel de fondo; en Filtradas ya está el marcador de la auditoría,
    y dos marcadores en la misma pantalla no se leen, compiten.

    El verde no decora: en este sistema significa lo que ya hiciste, igual que
    en la tarjeta de una oferta aplicada. Y va con la palabra al lado, nunca
    sólo el color.
    """
    from vacantia.ui.data import PERIODOS
    from vacantia.ui.graficos import columnas

    if ver != "pendientes" or not aplicadas:
        return ""

    cuantas = aplicadas.get("cuantas", 0)
    opciones = "".join(
        f'<option value="{esc(clave)}"'
        f'{" selected" if clave == aplicadas.get("periodo") else ""}>{esc(etiqueta)}</option>'
        for clave, etiqueta, _ in PERIODOS
    )
    selector = f"""<form class="periodo" method="get" action="/trabajos">
  <input type="hidden" name="perfil" value="{esc(perfil)}">
  <input type="hidden" name="ver" value="{esc(ver)}">
  <input type="hidden" name="desde" value="{esc(desde)}">
  <label for="cuando-apliq">Período</label>
  <select id="cuando-apliq" name="apliq" onchange="this.form.submit()">{opciones}</select>
  <noscript><button>Ver el período</button></noscript>
</form>"""

    if not cuantas:
        cuerpo = ('<p class="vacio-corto">Todavía no marcaste ninguna en este '
                  'período. Cuando mandes un CV, tocá <b>Apliqué</b> en esa '
                  'oferta y el número empieza a subir.</p>')
    else:
        # El reparto por semana es lo que hace que el total signifique algo: 12
        # postulaciones en un mes puede ser tres semanas sin hacer nada y una a
        # los tiros, y eso no se ve en el total.
        semanas = [{"etiqueta": e, "cuantas": n}
                   for e, n in aplicadas.get("por_semana") or []]
        cuerpo = (f'<div class="semanas">{columnas(semanas, "postulaciones")}</div>'
                  if len(semanas) > 1 else "")

    trabajo = "trabajo" if cuantas == 1 else "trabajos"
    # De dónde salió el número, cuando parte no salió de esta lista. Sin esto,
    # el total sube sin que se haya marcado ninguna tarjeta y no hay forma de
    # entender por qué.
    a_mano = aplicadas.get("a_mano") or 0
    cuando = esc(aplicadas.get("etiqueta", ""))
    if a_mano:
        cuando += f" · {a_mano} desde un posteo de LinkedIn"
    return f"""<section class="postulaciones" aria-label="Postulaciones">
  <p class="cuenta"><span class="numero">{cuantas}</span>
     <span class="que">{trabajo} a los que apliqué</span>
     <span class="cuando">{cuando}</span></p>
  {selector}
  {cuerpo}
</section>"""


def _marcador_del_filtro(ver: str, revision: dict | None) -> str:
    """Cuántas veces acertó el filtro y cuántas se equivocó, de un vistazo.

    Va arriba de la lista de Filtradas y en ningún otro lado. No es un recuento
    de lo que se pierde, que ésos viven en Métricas: es el resultado del trabajo
    que la persona está haciendo en esta misma pantalla, y sin verlo revisar
    veinte avisos es tirarlos a un pozo.

    **Es acumulativo**: cuenta toda la semana de prueba, no la página abierta.
    Con dos días de muestra un porcentaje sobre lo de hoy no dice nada.
    """
    if ver != "filtradas" or not revision:
        return ""
    bien, mal = revision.get("bien", 0), revision.get("mal", 0)
    if not bien and not mal:
        return f"""<div class="callout marcador">
  <p>Acá se revisa si el sistema descartó bien. A medida que contestes, van a
  aparecer los dos contadores y vas a poder ver si el filtro está afinado.</p>
  <p class="ayuda">Con {revision.get('meta', 0)} revisadas ya se puede decir algo.</p>
</div>"""
    revisadas = bien + mal
    faltan = revision.get("faltan", 0)
    meta = revision.get("meta", 0)
    if faltan:
        # El progreso hacia la meta, y no un porcentaje de aciertos: con 19
        # revisadas un "100% de aciertos" suena a veredicto y todavía no lo es.
        cierre = (f"Sobre {revisadas} revisadas. Con {meta} ya se puede decir si el "
                  f"filtro anda: te faltan {faltan}.")
    else:
        cierre = (f"Sobre {revisadas} revisadas, y con {meta} alcanza para saberlo. "
                  "Ya tenés la muestra.")
    return f"""<div class="callout marcador">
  <p class="cuenta"><span class="valor">{bien}</span> bien descartadas
     <span class="valor">{mal}</span> mal descartadas</p>
  <p class="ayuda">{esc(cierre)} Las que marcaste mal volvieron a Sin marcar.</p>
</div>"""


def _filtradas_vacia(perfil: str, corriendo: bool, revision: dict | None) -> str:
    """No queda nada para revisar. Por qué, que no es lo mismo en los dos casos.

    O revisaste todo lo que había, o lo que queda puntúa tan poco que no vale la
    pena mirarlo: si el filtro se equivocó con una de 20, esa oferta no te iba a
    servir igual. Decir cuántas quedaron abajo del corte evita que la pantalla
    vacía se lea como "se terminaron las ofertas".
    """
    from vacantia.ui.data import PUNTAJE_PARA_REVISAR

    bajo = (revision or {}).get("bajo_puntaje", 0)
    if bajo:
        detalle = (
            f"Revisaste todas las que valía la pena mirar. Quedan {bajo} que el "
            f"filtro sacó y puntúan menos de {PUNTAJE_PARA_REVISAR}: aunque se "
            "haya equivocado con alguna, no te iban a servir. Cuando entre una "
            f"de {PUNTAJE_PARA_REVISAR} para arriba va a aparecer acá."
        )
    else:
        detalle = (
            "Acá caen las que el sistema descarta solo, por idioma o por lugar, "
            f"de {PUNTAJE_PARA_REVISAR} puntos para arriba. Cuando entren "
            "ofertas nuevas van a aparecer las que el filtro saque."
        )
    return (f'<div class="vacio"><b>No queda ninguna por revisar.</b>{detalle}'
            f'<div class="salida">{_boton_buscar(perfil, corriendo, primario=True)}</div>'
            f'</div>')


def _desplegable_de_fecha(perfil: str, ver: str, desde: str, cuentas: dict) -> str:
    """La antigüedad como desplegable y no como cuatro botones.

    Eran cuatro chips que ocupaban una fila entera para algo que se toca una vez
    por semana, compitiendo por atención con lo que sí importa mientras uno
    trabaja: cuántas quedan por mirar. Un desplegable dice lo mismo en un renglón.

    Sin JavaScript sigue funcionando: es un `<form method=get>` con su botón,
    que el `onchange` sólo adelanta.
    """
    opciones = "".join(
        f'<option value="{esc(clave)}"{" selected" if clave == desde else ""}>'
        f'{esc(etiqueta)} ({(cuentas or {}).get(clave, 0)})</option>'
        for clave, etiqueta in RANGOS
    )
    return f"""<form class="filtro-fecha" method="get" action="/trabajos">
  <input type="hidden" name="perfil" value="{esc(perfil)}">
  <input type="hidden" name="ver" value="{esc(ver)}">
  <label for="desde">Antigüedad del aviso</label>
  <select id="desde" name="desde" onchange="this.form.submit()">{opciones}</select>
  <noscript><button>Filtrar por antigüedad</button></noscript>
</form>"""


def _encabezado(ver: str, conteo: dict, filtro_fecha: str) -> str:
    """El número grande a la izquierda y el filtro de fecha a la derecha.

    El número es el único dato que importa mientras uno revisa: cuántas faltan.
    Estaba adentro de un chip, del mismo tamaño que los otros cuatro contadores,
    compitiendo con "Archivadas 83" — que no es una tarea, es un archivo.
    """
    cuantas = int((conteo or {}).get(ver, 0))
    # Sólo en "Sin marcar" el número es una tarea pendiente. En las otras
    # pestañas es un archivo, y no merece el tamaño.
    if ver != "pendientes":
        return f'<div class="encabezado"><div></div>{filtro_fecha}</div>'
    return f"""<div class="encabezado">
  <p class="cuantas"><span class="numero">{cuantas}</span>
     <span class="que">sin mirar</span></p>
  {filtro_fecha}
</div>"""


def _con_banda_de_recientes(ofertas: list[dict], perfil: str, ver: str,
                            desde: str, pagina: int) -> str:
    """Las tarjetas, con un rótulo que separa lo recién publicado del resto.

    `data.ofertas` ya las ordenó con las recientes arriba; acá sólo se dibuja
    dónde termina ese grupo. Se hace en dos rótulos y no en un color de tarjeta
    porque lo que hay que contestar es "¿hasta dónde miro hoy?", y una línea que
    cruza la lista lo dice mejor que un borde en cada una.

    Si no hay ninguna reciente, o si son todas, no se dibuja nada: un rótulo que
    encabeza la lista entera no separa nada y sólo ocupa lugar.
    """
    from vacantia.ui.data import DIAS_RECIEN

    tarjetas = [_tarjeta(o, perfil, ver, desde, pagina) for o in ofertas]
    cuantas = sum(1 for o in ofertas if o.get("_recien"))
    if not 0 < cuantas < len(ofertas):
        return "".join(tarjetas)

    def rotulo(texto: str, cuenta: str, detalle: str) -> str:
        numero = f'<span class="cuenta">{cuenta}</span>' if cuenta else ""
        return (f'<h3 class="banda"><span>{texto}</span>{numero}'
                f'<span class="detalle">{detalle}</span></h3>')

    dias = "de hoy o ayer" if DIAS_RECIEN <= 2 else f"de los últimos {DIAS_RECIEN} días"
    return (
        rotulo("Recién publicadas", str(cuantas),
               f"Avisos {dias}. Son a los que menos gente se postuló todavía.")
        + "".join(tarjetas[:cuantas])
        + rotulo("El resto", "", "Ordenadas por puntaje, como siempre.")
        + "".join(tarjetas[cuantas:])
    )


def _paginas(perfil: str, ver: str, desde: str, pagina: int, paginas: int,
             total: int) -> str:
    """La barra de abajo. No se dibuja si todo entra en una página."""
    if paginas <= 1:
        return ""

    def link(destino: int, etiqueta: str) -> str:
        if not 1 <= destino <= paginas:
            return f'<span class="quieto">{etiqueta}</span>'
        return (f'<a href="/trabajos?perfil={esc(perfil)}&ver={esc(ver)}'
                f'&desde={esc(desde)}&p={destino}">{etiqueta}</a>')

    return f"""<nav class="paginas" aria-label="Páginas">
  {link(pagina - 1, "Anteriores")}
  {link(pagina + 1, "Siguientes")}
  <span class="donde">Página {pagina} de {paginas}</span>
  <span class="donde">{total} ofertas</span>
</nav>"""


def _archivar_viejas(perfil: str, ver: str, desde: str, cuantas: dict) -> str:
    """El botón para encajonar de una todas las que quedaron viejas.

    Un aviso de hace tres semanas casi siempre está cubierto, y con 43 en esa
    situación archivarlas de a una es trabajo al pedo. Sólo aparece si hay algo
    que archivar, y dice cuántas son antes de apretar. Todo en fantasma: es
    mantenimiento y no compite con la acción de la pantalla.
    """
    if ver != "pendientes" or not cuantas:
        return ""
    opciones = "".join(
        f'<button class="fantasma" name="dias" value="{dias}">Más de {dias} días ({n})</button>'
        for dias, n in sorted(cuantas.items()) if n
    )
    if not opciones:
        return ""
    return f"""<form class="encajonar" method="post" action="/archivar-viejas">
  <input type="hidden" name="perfil" value="{esc(perfil)}">
  <input type="hidden" name="desde" value="{esc(desde)}">
  <span>Archivar los avisos viejos:</span>{opciones}
  <span class="ayuda">Los saca de la lista sin enseñarle nada al sistema sobre
  lo que te gusta. Se pueden devolver.</span>
</form>"""


def trabajos(perfil: str, ofertas: list[dict], conteo: dict, ver: str,
             mensajes: list[tuple[str, str]], desde: str = "todo",
             conteo_fecha: dict | None = None,
             marca: str = "", pagina: int = 1, paginas: int = 1,
             viejas: dict | None = None, corriendo: bool = False,
             revision: dict | None = None, aplicadas: dict | None = None) -> str:
    """La lista.

    Arriba no va ningún recuento de lo que se pierde: cuántas ofertas quedan
    afuera por el inglés es información legítima, pero vive en Métricas, con la
    explicación y con el link a donde se cambia el nivel declarado.
    """
    def chips(opciones, activo, param, cuentas, otro_param, otro_valor):
        salida = []
        for clave, etiqueta in opciones:
            # "Filtradas" se pinta distinto del resto: no es una pestaña más
            # donde mirar lo que ya hiciste, es la tarea de revisar si el filtro
            # automático acierta, y hay que poder encontrarla de un vistazo. Va
            # en el azul de "estado del sistema", con su ícono, y no en el
            # índigo de acción: una píldora rellena del color de acción se
            # confunde con un botón. Rojo tampoco: no es un error.
            clases = " ".join(c for c in (
                "activa" if clave == activo else "",
                "revisar" if clave == "filtradas" else "",
            ) if c)
            icono = ICONOS["filtradas"] if clave == "filtradas" else ""
            salida.append(
                f'<a href="/trabajos?perfil={esc(perfil)}&{otro_param}={esc(otro_valor)}'
                f'&{param}={clave}"{f" class=\'{clases}\'" if clases else ""}>'
                f'{icono}{etiqueta} '
                f'<span class="cuenta">{(cuentas or {}).get(clave, 0)}</span></a>'
            )
        return "".join(salida)

    # Cada botón conserva el valor del otro eje: cambiar de "Sin marcar" a
    # "Descarté" no tiene por qué devolverte a ver los avisos de hace un año.
    por_estado = chips(FILTROS, ver, "ver", conteo, "desde", desde)
    por_fecha = _desplegable_de_fecha(perfil, ver, desde, conteo_fecha)

    if ofertas:
        listado = (_con_banda_de_recientes(ofertas, perfil, ver, desde, pagina)
                   + _paginas(perfil, ver, desde, pagina, paginas,
                              int((conteo or {}).get(ver, 0))))
    elif desde != "todo":
        listado = (
            '<div class="vacio"><b>Ninguna en ese rango de fechas.</b>'
            'Probá con <b>Sin filtro</b> para ver también las más viejas.</div>'
        )
    elif ver == "filtradas":
        listado = _filtradas_vacia(perfil, corriendo, revision)
    else:
        titulo, detalle, se_arregla_buscando = VACIO.get(ver, VACIO["todas"])
        salida = (f'<div class="salida">{_boton_buscar(perfil, corriendo, primario=True)}</div>'
                  if se_arregla_buscando else "")
        listado = f'<div class="vacio"><b>{titulo}</b>{detalle}{salida}</div>'

    # El vigilante avisa si entran ofertas con la pantalla abierta. `marca` es
    # cómo estaba el historial al servir esta página: si cambia, hubo corrida.
    vigilante = ""
    if marca:
        pendientes = int((conteo or {}).get("pendientes", 0))
        vigilante = f"""<div class="toast novedades" id="novedades" role="status">
  <span id="novedades-texto">Entraron ofertas nuevas</span>
  <button type="button" onclick="location.reload()">Ver las nuevas</button>
</div>
<script>vigilarNovedades({esc(perfil)!r}, {esc(marca)!r}, {pendientes});</script>"""

    return f"""{avisos(mensajes)}
{vigilante}
<h1>Trabajos</h1>
{_postulaciones(perfil, ver, desde, aplicadas)}
<div class="filtros">{por_estado}</div>
{_encabezado(ver, conteo, por_fecha)}
{_marcador_del_filtro(ver, revision)}
{_archivar_viejas(perfil, ver, desde, viejas or {})}
{listado}"""


# --- pestaña LinkedIn URLs --------------------------------------------------
#
# El scraper trae lo publicado hace uno a tres días; los avisos de hoy no los
# indexó todavía ningún buscador y por eso no aparecen en Trabajos. Esta sección
# es la otra mitad: armar la dirección de búsqueda de LinkedIn que los muestra.
#
# Todavía no genera nada: por ahora es el lugar, con sus dos pestañas y lo que
# va en cada una escrito, para que se pueda ver dónde va a caer cada cosa.

#: (clave, etiqueta). La primera es la que se abre por defecto.
#:
#: Publicaciones va primero porque es la que resuelve el agujero real: los
#: avisos que se publican como posteo del feed y nunca llegan a la pestaña Jobs.
#: Jobs ya está cubierto por el scraper.
PESTANIAS_LINKEDIN = (
    ("publicaciones", "Publicaciones"),
    ("jobs", "Jobs"),
)


def _tildes(nombre: str, opciones, marcadas, columnas: bool = True) -> str:
    """Una fila de tildes. `marcadas` es el conjunto de los que vienen puestos."""
    puestas = {str(m).lower() for m in (marcadas or [])}
    tildes = "".join(
        f'<label><input type="checkbox" name="{esc(nombre)}" value="{esc(o)}"'
        f'{" checked" if str(o).lower() in puestas else ""}> {esc(o)}</label>'
        for o in opciones
    )
    return f'<div class="checks{" en-columnas" if columnas else ""}">{tildes}</div>'


def _desplegable(nombre: str, opciones, elegida: str, etiqueta: str) -> str:
    ops = "".join(
        f'<option value="{esc(c)}"{" selected" if c == elegida else ""}>{esc(e)}</option>'
        for c, e, *_ in opciones
    )
    return f"""<div class="campo">
  <label for="{esc(nombre)}">{esc(etiqueta)}</label>
  <select id="{esc(nombre)}" name="{esc(nombre)}">{ops}</select>
</div>"""


#: Los campos del constructor que hay que reponer al volver de un POST. El
#: orden es el de la pantalla, para que la dirección de la barra se lea igual
#: que el formulario.
_CAMPOS_DEL_ARMADOR = ("puestos", "lugares", "idioma", "sin_junior",
                       "cuando", "orden", "de_quien")


def _volver_al_armador(perfil: str, elegido: dict) -> str:
    """La query que devuelve esta misma pantalla, con lo mismo elegido.

    Los botones del contador son un POST: sin esto, anotar una postulación
    recargaría la pantalla en blanco y se perdería la búsqueda recién armada,
    que es justo lo que la persona está por usar.
    """
    partes: list[tuple[str, str]] = [("perfil", perfil), ("tab", "publicaciones")]
    partes += [("puesto", str(p)) for p in elegido.get("puestos") or []]
    partes += [("lugar", str(l)) for l in elegido.get("lugares") or []]
    partes.append(("idioma", str(elegido.get("idioma") or "es")))
    if elegido.get("sin_junior"):
        partes.append(("sin_junior", "1"))
    for clave, porde in (("cuando", "24h"), ("orden", "recientes"),
                         ("de_quien", "todos")):
        partes.append((clave, str(elegido.get(clave) or porde)))
    return urlencode(partes)


def _ayuda_al_lado(texto: str) -> str:
    """El signo de pregunta que muestra la explicación al pasarle por encima.

    Para lo que hace falta una vez y estorba siempre. El texto largo suelto en
    la pantalla compite con el control que importa; escondido detrás de un
    ícono, está cuando se busca y no antes.

    **No es sólo hover.** Se abre también con el foco del teclado, porque quien
    tabula no pasa el mouse por ningún lado, y el texto está en el DOM desde el
    principio para que un lector de pantalla lo lea como nota del rótulo.
    """
    return (f'<span class="ayuda-al-lado" tabindex="0" role="note">'
            f'<span class="signo" aria-hidden="true">?</span>'
            f'<span class="globo">{esc(texto)}</span></span>')


def _apliques(perfil: str, sin_confirmar: int, confirmadas: int,
              volver: str) -> str:
    """El anotador de lo que aplicaste desde un posteo de LinkedIn.

    Va acá y no en Trabajos porque acá es donde pasa: abrís la búsqueda, ves un
    posteo, escribís, y volvés. Marcarlo en otra pantalla sería acordarse
    después, y lo que no se marca en el momento no se marca nunca.

    Estas postulaciones no tienen ninguna oferta detrás: no entraron por el
    scraper y no están en el historial. Por eso hay que contarlas a mano, y por
    eso **suman al contador grande de Trabajos**: es el mismo trabajo.

    **Son dos pasos y no uno.** El más y el menos mueven un anotador que todavía
    no cuenta para nada; *Confirmar* lo pasa al contador de Trabajos y lo deja en
    cero. Un solo número que sube y nunca vuelve a cero no se puede confirmar:
    no habría forma de saber si lo que ves es lo de esta tanda o lo de toda la
    semana, ni de corregir un toque de más una hora después.

    **La forma es la de un stepper**, una sola pieza con los dos botones y el
    número adentro, y no tres cajas sueltas: tres cajas iguales no dicen que se
    tocan juntas ni cuál es el número y cuáles los botones.

    El verde es sólo del número y de *Confirmar*: en este sistema el verde
    significa lo que ya hiciste, y el más y el menos todavía no son nada. Y va
    con la palabra al lado, nunca sólo el color.

    La explicación larga vive adentro del signo de pregunta. Estaba suelta abajo
    del anotador, tres renglones de texto chico al pie de la barra, y competía
    con el único control de la pantalla que importa, que es *Armar la búsqueda*.
    """
    # A dónde volver viaja en la dirección del POST y no en un campo escondido:
    # el constructor es un GET, y un campo escondido más se colaría en la query
    # de "Armar la búsqueda" y crecería sobre sí mismo en cada armado.
    paso = ('type="submit" formmethod="post" '
            f'formaction="/linkedin-apliques?volver={quote(volver)}"')
    vacio = " disabled" if not sin_confirmar else ""
    ya = (f"Ya sumaste {confirmadas}." if confirmadas
          else "Todavía no sumaste ninguna.")
    return f"""<div class="apliques">
  <p class="rotulo">Apliqué desde acá{_ayuda_al_lado(
      "Contá acá lo que vayas mandando desde un posteo y confirmá al terminar. "
      "Recién ahí suman al contador de Trabajos, y el anotador vuelve a cero. "
      "Lo que no confirmes sigue esperándote cuando volvés. " + ya)}</p>
  <div class="pasos">
    <span class="stepper">
      <button class="paso" {paso} name="menos" value="1"
              aria-label="Sacar una del anotador"{vacio}>&#8722;</button>
      <b class="numero">{sin_confirmar}</b>
      <button class="paso" {paso} name="suma" value="1"
              aria-label="Sumar una al anotador">+</button>
    </span>
    <button class="confirmar" {paso} name="confirmar" value="1"{vacio}>Confirmar</button>
  </div>
</div>"""


def _constructor(perfil: str, elegido: dict, puestos: list[str],
                 apliques: dict | None = None) -> str:
    """El formulario que arma la búsqueda.

    Es un `<form method="get">` y no JavaScript, como el filtro de antigüedad y
    el selector de perfil. Eso trae algo gratis: lo que elegiste queda en la
    dirección de esta misma pantalla, así que volver acá con el botón de atrás
    te devuelve el constructor como lo dejaste.
    """
    from vacantia.ui.linkedin_urls import (
        CUANDO, DE_QUIEN, EXCLUIR, GATILLOS_EN, GATILLOS_ES, LUGARES, ORDEN,
    )

    idioma = elegido.get("idioma", "es")
    gatillos = "".join(
        f'<label><input type="radio" name="idioma" value="{esc(c)}"'
        f'{" checked" if c == idioma else ""}> {esc(e)}</label>'
        for c, e in (("es", "En español"), ("en", "En inglés"), ("ambos", "Los dos"))
    )

    return f"""<form class="datos armador" method="get" action="/linkedin">
<input type="hidden" name="perfil" value="{esc(perfil)}">
<input type="hidden" name="tab" value="publicaciones">

<h2>Qué buscar</h2>
<div class="grilla">
  <div class="campo ancho">
    <label>Puestos</label>
    {_tildes("puesto", puestos, elegido.get("puestos"))}
    <p class="ayuda">Se buscan todos juntos: alcanza con que el posteo diga uno.
    Salen de <b>Palabras clave</b>, en
    <a href="/datos?perfil={esc(perfil)}">Mi perfil</a>: lo que agregues o saques
    ahí aparece o desaparece de acá.</p>
  </div>
  <div class="campo ancho">
    <label>Cómo lo escribe quien contrata</label>
    <div class="checks">{gatillos}</div>
    <p class="ayuda">Es lo que separa un posteo que habla del tema de uno que
    ofrece trabajo: {esc(GATILLOS_ES[0])}, {esc(GATILLOS_ES[1])}, {esc(GATILLOS_EN[0])}.</p>
  </div>
  <div class="campo">
    <label>Dónde</label>
    {_tildes("lugar", LUGARES, elegido.get("lugares"), columnas=False)}
  </div>
  <div class="campo">
    <label>Qué dejar afuera</label>
    <div class="checks">
      <label><input type="checkbox" name="sin_junior" value="1"
      {" checked" if elegido.get("sin_junior") else ""}> Puestos junior</label>
    </div>
    <p class="ayuda">Saca {esc(", ".join(EXCLUIR))}.</p>
  </div>
</div>

<h2>Cómo mostrarlo</h2>
<div class="grilla">
  {_desplegable("cuando", CUANDO, elegido.get("cuando", "24h"), "Publicado hace")}
  {_desplegable("orden", ORDEN, elegido.get("orden", "recientes"), "Ordenar por")}
  {_desplegable("de_quien", DE_QUIEN, elegido.get("de_quien", "todos"), "Publicado por")}
</div>

<div class="guardar">
  <button class="primario" type="submit">Armar la búsqueda</button>
  {_apliques(perfil, (apliques or {}).get("pendientes", 0),
              (apliques or {}).get("confirmadas", 0),
              _volver_al_armador(perfil, elegido))}
</div>
</form>"""


def _bloque_de_url(perfil: str, url: str, nombre: str, ya_guardada: bool) -> str:
    """La dirección armada, entera y a la vista.

    **Nunca escondida detrás de un botón.** La persona tiene que poder leerla
    antes de usarla: es un texto largo con comillas y paréntesis que LinkedIn a
    veces interpreta distinto, y si algo sale raro lo primero que se mira es
    esto.

    La acción principal es abrirla, no copiarla: no vino a llevarse un texto,
    vino a ver los posteos.
    """
    guardar = "" if ya_guardada else f"""<form class="guardar-favorito" method="post" action="/linkedin-favorito">
  <input type="hidden" name="perfil" value="{esc(perfil)}">
  <input type="hidden" name="url" value="{esc(url)}">
  <label for="nombre-fav">Nombre</label>
  <input type="text" id="nombre-fav" name="nombre" value="{esc(nombre)}">
  <button type="submit">Guardar en favoritos</button>
</form>"""
    ya = ('<p class="ayuda">Esta búsqueda ya está en tus favoritos.</p>'
          if ya_guardada else "")

    return f"""<section class="armada" aria-label="La búsqueda armada">
  <h2>Tu búsqueda</h2>
  <p class="url-generada">{esc(url)}</p>
  <p class="herramientas">
    <a class="boton primario" href="{esc(url)}" {ABRIR_EL_AVISO}>Abrir en LinkedIn</a>
    <button type="button" onclick="copiar(this, {esc(url)!r})">Copiar link</button>
  </p>
  {guardar}{ya}
  <p class="ayuda">Al abrirla, LinkedIn cae directo en la pestaña Publicaciones
  con los filtros puestos. Si algún día deja de filtrar, rehacé los filtros a
  mano en LinkedIn y pegá acá la dirección nueva.</p>
</section>"""


def _aviso_de_recorte(entraron: dict | None, pedidos: dict | None) -> str:
    """Cuando el texto no entra, se recorta. Hay que decirlo.

    LinkedIn no avisa que la búsqueda es muy larga: aplica los filtros, muestra
    "No se han encontrado resultados" y te deja creyendo que no hay vacantes.
    Medido: con seis frases devuelve cero, con cuatro trae posteos de hace un
    minuto. Así que se recorta, pero callarlo sería peor que el problema: la
    persona creería que está buscando "vacante" y en realidad no.
    """
    entraron, pedidos = entraron or {}, pedidos or {}
    faltan = []
    if (n := pedidos.get("gatillos", 0) - entraron.get("gatillos", 0)) > 0:
        faltan.append(f"{n} " + ("frase de las que dijiste que usan"
                                 if n == 1 else "frases de las que dijiste que usan"))
    if (n := pedidos.get("excluir", 0) - entraron.get("excluir", 0)) > 0:
        faltan.append(f"{n} " + ("palabra de las que querías dejar afuera"
                                 if n == 1 else "palabras de las que querías dejar afuera"))
    if not faltan:
        return ""
    return f"""<div class="callout atencion">
  <p>Quedaron afuera {" y ".join(faltan)}: con más, LinkedIn devuelve cero
  resultados y no avisa por qué.</p>
  <p class="ayuda">Se conservaron las que más rinden. Si querés las otras, armá
  una segunda búsqueda y guardala aparte: dos búsquedas cortas traen más que una
  larga que no trae nada.</p>
</div>"""


def _todavia_sin_armar() -> str:
    """El lugar de la dirección, mientras no haya ninguna.

    La columna de la derecha existe siempre, así que el hueco se nombra en vez
    de dejarlo en blanco: al entrar por primera vez, esto dice de dónde va a
    salir lo que va a aparecer acá.
    """
    return """<section class="armada" aria-label="La búsqueda armada">
  <h2>Tu búsqueda</h2>
  <div class="vacio"><b>Todavía no armaste ninguna.</b>
  Elegí a la izquierda qué buscar y apretá el botón de abajo de todo, «Armar la
  búsqueda». La dirección aparece acá, entera y a la vista, para que puedas
  leerla antes de abrirla.</div>
</section>"""


def _favoritos(perfil: str, guardados: list[dict]) -> str:
    """Las búsquedas que ya sabés que sirven, para no rearmarlas cada vez."""
    if not guardados:
        return """<h2>Tus búsquedas guardadas</h2>
<div class="vacio"><b>Todavía no guardaste ninguna.</b>
Cuando armes una búsqueda que te traiga posteos que sirven, guardala acá y la
volvés a abrir de un toque. La idea es tener cuatro o cinco y revisarlas dos
veces por día: los posteos buenos duran horas.</div>"""

    filas = []
    for f in guardados:
        cuando = _en_hora_local(f.get("guardada"))
        dias = dias_desde(cuando) if cuando else None
        desde = ("hoy" if dias == 0 else "ayer" if dias == 1
                 else f"hace {dias} días" if dias else "")
        filas.append(f"""<li class="favorito">
  <div class="datos">
    <h3>{esc(f.get("nombre"))}</h3>
    {f'<p class="cuando">Guardada {esc(desde)}</p>' if desde else ''}
    <p class="url-generada chica">{esc(f.get("url"))}</p>
  </div>
  <div class="acciones">
    <a class="boton primario" href="{esc(f.get("url"))}" {ABRIR_EL_AVISO}>Abrir</a>
    <details class="menu">
      <summary title="Más opciones" aria-label="Más opciones">{ICONOS['mas']}</summary>
      <div class="panel">
        <button type="button" onclick="copiar(this, {esc(f.get("url"))!r})">Copiar link</button>
        <form method="post" action="/linkedin-favorito">
          <input type="hidden" name="perfil" value="{esc(perfil)}">
          <input type="hidden" name="url" value="{esc(f.get("url"))}">
          <button class="fantasma" name="borrar" value="1">Sacar de favoritos</button>
        </form>
      </div>
    </details>
  </div>
</li>""")
    return f"""<h2>Tus búsquedas guardadas</h2>
<ul class="favoritos">{"".join(filas)}</ul>"""


def linkedin(perfil: str, tab: str, mensajes: list[tuple[str, str]],
             elegido: dict | None = None, url: str = "",
             guardados: list[dict] | None = None,
             puestos: list[str] | None = None,
             apliques: dict | None = None) -> str:
    """Las direcciones de búsqueda de LinkedIn, en dos pestañas.

    Las pestañas son navegación adentro de la sección, no un filtro, y por eso
    van arriba del contenido y no adentro de una tarjeta. Para filtrar están las
    píldoras de la lista de trabajos.
    """
    from vacantia.ui.linkedin_urls import nombre_sugerido

    from vacantia.ui.linkedin_urls import PUESTOS_SUGERIDOS

    if tab not in dict(PESTANIAS_LINKEDIN):
        tab = PESTANIAS_LINKEDIN[0][0]
    elegido = elegido or {}
    guardados = guardados or []
    puestos = puestos or list(PUESTOS_SUGERIDOS)

    botones = "".join(
        f'<a class="pestania{" activa" if clave == tab else ""}" '
        f'href="/linkedin?perfil={esc(perfil)}&tab={esc(clave)}"'
        f'{" aria-current=page" if clave == tab else ""}>{esc(etiqueta)}</a>'
        for clave, etiqueta in PESTANIAS_LINKEDIN
    )

    if tab == "jobs":
        cuerpo = """<div class="vacio"><b>Todavía no hay ninguna dirección armada.</b>
Acá va a aparecer la dirección de búsqueda de LinkedIn Jobs para tu perfil, con
las palabras clave, la ubicación y la modalidad que cargaste. Por ahora la
pestaña que resuelve el agujero es la otra: Jobs ya lo cubre el buscador
automático.</div>"""
    else:
        ya = any(f.get("url") == url for f in guardados)
        nombre = nombre_sugerido(elegido.get("puestos"), elegido.get("cuando", "24h"),
                                 elegido.get("idioma") == "en")
        # Dos columnas: a la izquierda lo que elegís, a la derecha lo que sale.
        # Antes iba todo en una sola columna larga y la dirección aparecía abajo
        # de todo, fuera de pantalla; encima el formulario es GET, así que al
        # armarla la página se recargaba y el navegador la abría arriba. Así, el
        # resultado nace al lado de los controles y nada se mueve.
        cuerpo = f"""<div class="taller">
<div class="lado controles">{_constructor(perfil, elegido, puestos or [], apliques)}</div>
<div class="lado resultado">{_aviso_de_recorte(elegido.get("entraron"),
                                                elegido.get("pedidos"))}\
{_bloque_de_url(perfil, url, nombre, ya) if url else _todavia_sin_armar()}\
{_favoritos(perfil, guardados)}</div>
</div>"""

    return f"""{avisos(mensajes)}
<h1>LinkedIn URLs</h1>
<p class="sub">Muchas vacantes se publican como un posteo del muro y nunca llegan
a la pestaña de empleos. El buscador las indexa uno a tres días tarde, cuando ya
se llenaron de postulantes. Estas direcciones las muestran apenas se publican.</p>
<nav class="pestanias" aria-label="Tipo de búsqueda">{botones}</nav>
{cuerpo}"""


# --- pestaña Métricas -------------------------------------------------------


def _dato(numero, que: str, destacado: bool = False) -> str:
    clase = "dato destacado" if destacado else "dato"
    return (f'<div class="{clase}"><span class="numero">{esc(numero)}</span>'
            f'<span class="que">{esc(que)}</span></div>')


def _tabla(encabezados: tuple[str, str], filas: list[tuple[str, int]]) -> str:
    if not filas:
        return '<p class="explica">Todavía no hay ninguna.</p>'
    izq, der = encabezados
    cuerpo = "".join(f'<tr><td>{esc(k)}</td><td class="n">{v}</td></tr>'
                     for k, v in filas)
    return (f'<table class="numeros"><thead><tr><th>{esc(izq)}</th>'
            f'<th class="n">{esc(der)}</th></tr></thead>'
            f'<tbody>{cuerpo}</tbody></table>')


#: Cómo se lee cada motivo del sistema en la pantalla.
_MOTIVOS_SISTEMA = {
    "idioma": "Piden un inglés más alto que el tuyo",
    "lugar": "El lugar o la modalidad no te sirven",
}


def _desglose(encabezados: tuple[str, str], filas: list[tuple[str, int]]) -> str:
    """Un desglose, como gráfico o como tabla según cuántas filas tenga.

    El gráfico se gana el lugar cuando hay varias magnitudes que comparar de un
    vistazo. Con dos filas no hay comparación, hay dos números, y para dos
    números la tabla ocupa menos y se lee más rápido. El corte está en
    `graficos.MINIMO_PARA_GRAFICAR`.

    **La tabla no desaparece nunca**: cuando hay gráfico va debajo, plegada.
    Un gráfico no da el valor exacto ni se puede copiar, y a veces lo que se
    quiere es justamente el número.
    """
    from vacantia.ui.graficos import barras, vale_un_grafico

    tabla = _tabla(encabezados, filas)
    if not vale_un_grafico(filas):
        return tabla
    return f"""{barras(filas, encabezados[1].lower())}
<details class="como"><summary>Ver los números</summary>{tabla}</details>"""


def _grafico_de_puntajes(tramos: list[dict] | None) -> str:
    """El histograma de puntajes. La forma de la lista, de un vistazo.

    Va en columnas y no en barras horizontales porque el eje tiene un orden
    propio: de 0 a 100. Ordenarlo por tamaño, como hace `barras`, destruiría lo
    único que este gráfico tiene para decir.
    """
    from vacantia.ui.graficos import columnas

    if not tramos or not any(t.get("cuantas") for t in tramos):
        return ('<p class="explica">Todavía no hay ofertas puntuadas.</p>')
    datos = [{"etiqueta": t["etiqueta"], "cuantas": t["cuantas"],
              "destacada": t.get("avisa")} for t in tramos]
    return f"""{columnas(datos)}
<p class="pie-grafico"><span class="marca-color" aria-hidden="true"></span>
De este puntaje para arriba el sistema te avisa por Telegram. Se cambia en Mi
perfil, en <i>Puntaje mínimo para avisarme</i>.</p>"""


def _cuesta_el_ingles(perfil: str, ingles: dict) -> str:
    """Cuántas ofertas quedan afuera por el inglés, y cómo se cambia eso.

    Éste es el lugar del dato: acá se vino a mirar números, y el número viene
    con la salida al lado. Arriba de la lista de trabajos no va, porque ahí la
    persona vino a aplicar y lo primero que leería sería lo que se pierde.
    """
    cuantas = (ingles or {}).get("cuantas") or 0
    if not cuantas:
        return ""
    mejor, titulo = ingles.get("mejor"), ingles.get("mejor_titulo") or ""
    detalle = ""
    if mejor is not None:
        detalle = f" La mejor puntuaba {mejor} de 100"
        detalle += f": {titulo}." if titulo else "."
    return f"""<div class="callout atencion">
  <p><b>{esc(cuantas)} ofertas</b> piden un inglés más alto que el que declaraste.
  {esc(detalle)}</p>
  <p>Ese número sube cada vez que marcás una oferta como <i>Piden inglés</i>, y
  baja solo si subís tu nivel declarado.</p>
  <a class="salida" href="/datos?perfil={esc(perfil)}">Cambiar mi nivel de inglés</a>
</div>"""


def _como_viene_funcionando(perfil: str, salud: dict | None) -> str:
    """El "¿esto anda?" que antes había que abrir en una ventana negra aparte.

    Es lo mismo que mostraba la pantalla de estado: si está programado, cuándo
    corrió, qué encontró, si avisó por Telegram y qué se quejó. La diferencia es
    que ahora está adentro de la app, en castellano y sin nombres de archivo.

    Los avisos del registro van adentro de un desplegable: son texto de máquina,
    interesan cuando algo falla y no tienen por qué ocupar la pantalla el resto
    del tiempo.
    """
    if not salud:
        return ""

    if salud.get("corriendo"):
        ahora = ("<p>Hay una búsqueda en curso. Cuando entren ofertas nuevas te "
                 "avisa la pantalla de Trabajos.</p>")
    else:
        ahora = f'<p class="acciones-sueltas">{_boton_buscar(perfil, False)}</p>'

    tareas = salud.get("programada")
    if tareas is None:
        programado = ('<p class="explica">No puedo consultar las búsquedas '
                      'automáticas en este sistema. Las de esta pantalla '
                      'funcionan igual.</p>')
    elif not tareas:
        programado = ('<p class="explica">No está programado para buscar solo. '
                      'Volvé a correr la instalación para activarlo.</p>')
    else:
        filas = "".join(
            f'<tr><td>{esc(t["nombre"])}</td><td>{esc(t["estado"])}</td>'
            f'<td class="fecha">{esc(t["proxima"])}</td></tr>' for t in tareas
        )
        programado = (
            '<table class="numeros"><thead><tr><th>Búsqueda automática</th>'
            '<th>Estado</th><th class="fecha">Próxima</th></tr></thead>'
            f'<tbody>{filas}</tbody></table>'
        )

    encontro = ""
    if salud.get("encontro"):
        cuando = salud.get("cuando") or ""
        duracion = salud.get("duracion") or ""
        pie = f"La última terminó {cuando}" if cuando else "En la última búsqueda"
        if duracion:
            pie += f", en {duracion}"
        encontro = (f'<p class="explica">{esc(pie)}.</p>'
                    + _tabla(("En la última búsqueda", "Ofertas"), salud["encontro"]))

    telegram = salud.get("telegram")
    aviso = (f'<p class="explica">Último aviso por Telegram: {esc(telegram)}.</p>'
             if telegram else
             '<p class="explica">Todavía no se envió ningún aviso por Telegram. '
             'Puede ser normal si no hubo ofertas que pasen el puntaje mínimo.</p>')

    problemas = ""
    if salud.get("problemas"):
        lineas = "".join(f"<li>{esc(p)}</li>" for p in salud["problemas"])
        problemas = f"""<details class="como">
  <summary>Ver los últimos avisos del registro</summary>
  <ul class="registro">{lineas}</ul>
  <p class="ayuda">Son las quejas que el sistema decidió no considerar graves.
  Si siempre aparece la misma, algo hay que mirar.</p>
</details>"""

    return f"""<h2>Cómo viene funcionando</h2>
{programado}
{encontro}
{aviso}
{problemas}
{ahora}"""


def estadisticas(perfil: str, e: dict, desde: str, mensajes,
                 salud: dict | None = None,
                 puntajes: list[dict] | None = None) -> str:
    """Los números que antes vivían apretados en los botones de arriba.

    Se separó porque compiten: mientras uno revisa ofertas, el único número que
    importa es cuántas faltan. "Archivadas 83" no es una tarea, es un archivo, y
    ocupaba el mismo espacio.
    """
    ingles = e.get("ingles") or {}
    sistema = e.get("sistema") or {}

    tarjetas = (
        _dato(e["sin_marcar"], "sin mirar", destacado=True)
        + _dato(e["aplicadas"], "aplicaste")
        + _dato(e["descartadas"], "descartaste")
        + _dato(e["archivadas"], "archivadas")
        + _dato(e["total"], "en total")
    )

    motivos_filas = []
    from vacantia.ui.data import MOTIVOS
    etiquetas = {c: t for c, t, _ in MOTIVOS}
    for clave, cuantas in sorted((e.get("motivos") or {}).items(),
                                 key=lambda kv: -kv[1]):
        motivos_filas.append((etiquetas.get(clave, "Escrito a mano"), cuantas))

    sistema_filas = [(_MOTIVOS_SISTEMA.get(k, k), v)
                     for k, v in sorted(sistema.items(), key=lambda kv: -kv[1])]

    ventana = e.get("max_age_days")
    fuentes = list((e.get("por_fuente") or {}).items())
    return f"""{avisos(mensajes)}
<h1>Métricas</h1>
<div class="tarjetas">{tarjetas}</div>

<h2>Qué tan bien te encajan las ofertas que entran</h2>
<p class="explica">Cuántas hay en cada tramo de puntaje, sobre todo lo que se
buscó alguna vez. Una montaña pegada al cero significa que las búsquedas están
mal apuntadas; una repartida significa que el problema es otro.</p>
{_grafico_de_puntajes(puntajes)}

<h2>Lo que descartó el sistema, sin preguntarte</h2>
<p class="explica">Son las que no llegan a <b>Sin marcar</b> porque ya hay un
veredicto: no las borra nadie y vuelven solas si cambiás el filtro que las sacó.
Antes aparecían en la lista y había que descartarlas a mano una por una.</p>
{_desglose(("Motivo", "Ofertas"), sistema_filas)}
{_cuesta_el_ingles(perfil, ingles)}

<h2>Por qué descartaste vos</h2>
{_desglose(("Motivo", "Ofertas"), motivos_filas)}

<h2>De dónde vienen</h2>
{_desglose(("Portal", "Ofertas"), fuentes)}
<p class="explica">Ventana de búsqueda: los últimos
{esc(ventana if ventana is not None else "?")} días. Se cambia en Mi perfil.</p>

{_como_viene_funcionando(perfil, salud)}"""


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
  <button class="primario" type="submit">Completar con IA leyendo el aviso y mi CV</button>
  <p class="ayuda">Usa una llamada al modelo. Sin esto, completá a mano lo que
  está entre llaves.</p>
</form>"""
    return f"""{avisos(avisos_)}
<h1>Mensaje para {esc(oferta.get('company') or 'quien publicó')}</h1>
<p class="sub"><span class="dato-linea">{esc(titulo)}</span>
<a href="{esc(url)}" {ABRIR_EL_AVISO}>Ver el aviso en el portal</a></p>
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
  <button class="primario" type="submit">Leer el aviso y decirme qué reordenar</button>
  <p class="ayuda">Usa una llamada al modelo. No reescribe el CV: dice qué subir
  y qué palabra falta.</p>
</form>"""

    return f"""{avisos(avisos_)}
<h1>Consejo para tu CV</h1>
<p class="sub"><span class="dato-linea">{esc(titulo)}</span>
<span class="dato-linea">{esc(oferta.get('company') or 'sin empresa')}</span>
<a href="{esc(url)}" {ABRIR_EL_AVISO}>Ver el aviso en el portal</a></p>
<p class="herramientas"><a class="boton" href="/trabajos?perfil={esc(perfil)}">Volver a Trabajos</a></p>

<h2>Palabras del aviso que no están en tu CV</h2>
<div class="mensaje">{huecos}</div>

<h2>Qué mover</h2>
{cuerpo}
<p class="ayuda">Tu CV no se toca: esto es para que lo edites vos con criterio.</p>"""
