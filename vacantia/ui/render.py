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
from urllib.parse import quote

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

// El menú de tres puntos se cierra al tocar afuera. Sin esto quedan tres menús
// abiertos tapando la lista y hay que cerrarlos de a uno.
function cerrarMenus(salvo) {
  document.querySelectorAll('details.menu[open]').forEach(function (m) {
    if (m !== salvo) { m.removeAttribute('open'); }
  });
}

document.addEventListener('DOMContentLoaded', function () {
  volverAlScroll();
  // Para los envíos que sí pasan por 'submit': archivar, y marcar cuando la
  // animación está apagada por prefers-reduced-motion.
  document.querySelectorAll('form.acciones').forEach(function (form) {
    form.addEventListener('submit', recordarScroll);
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
    "archivadas": ("No archivaste ninguna todavía.",
                   "Archivar es para los avisos que ya no están o quedaron viejos. "
                   "No es lo mismo que descartar: no le enseña nada al sistema "
                   "sobre tus gustos, sólo los saca de la lista.", False),
    "todas": ("Todavía no hay ofertas guardadas.",
              "Buscá ahora para correr la primera búsqueda. Tarda unos minutos y "
              "podés seguir usando la pantalla mientras tanto.", True),
}


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
             viejas: dict | None = None, corriendo: bool = False) -> str:
    """La lista.

    Arriba no va ningún recuento de lo que se pierde: cuántas ofertas quedan
    afuera por el inglés es información legítima, pero vive en Métricas, con la
    explicación y con el link a donde se cambia el nivel declarado.
    """
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
        vigilante = f"""<div class="novedades" id="novedades" role="status">
  <span id="novedades-texto">Entraron ofertas nuevas</span>
  <button type="button" onclick="location.reload()">Ver las nuevas</button>
</div>
<script>vigilarNovedades({esc(perfil)!r}, {esc(marca)!r}, {pendientes});</script>"""

    return f"""{avisos(mensajes)}
{vigilante}
<h1>Trabajos</h1>
<div class="filtros">{por_estado}</div>
{_encabezado(ver, conteo, por_fecha)}
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
PESTANIAS_LINKEDIN = (
    ("jobs", "Jobs"),
    ("publicaciones", "Publicaciones"),
)


def linkedin(perfil: str, tab: str, mensajes: list[tuple[str, str]]) -> str:
    """Las direcciones de búsqueda de LinkedIn, en dos pestañas.

    Las pestañas son navegación adentro de la sección, no un filtro, y por eso
    van arriba del contenido y no adentro de una tarjeta. Para filtrar están las
    píldoras de la lista de trabajos.
    """
    if tab not in dict(PESTANIAS_LINKEDIN):
        tab = PESTANIAS_LINKEDIN[0][0]

    botones = "".join(
        f'<a class="pestania{" activa" if clave == tab else ""}" '
        f'href="/linkedin?perfil={esc(perfil)}&tab={esc(clave)}"'
        f'{" aria-current=page" if clave == tab else ""}>{esc(etiqueta)}</a>'
        for clave, etiqueta in PESTANIAS_LINKEDIN
    )

    if tab == "jobs":
        cuerpo = """<div class="vacio"><b>Todavía no hay ninguna dirección armada.</b>
Acá va a aparecer la dirección de búsqueda de LinkedIn Jobs para tu perfil, con
las palabras clave, la ubicación y la modalidad que cargaste, y el filtro de
publicadas hoy puesto. La vas a poder ver entera antes de usarla y copiarla de
un toque.</div>"""
    else:
        cuerpo = """<div class="vacio"><b>Todavía no hay ninguna dirección armada.</b>
Acá va a aparecer la dirección para buscar publicaciones de LinkedIn, que es por
donde salen los avisos que nadie subió al portal: los que un reclutador escribe
como posteo y se pierden apenas bajan del muro.</div>"""

    return f"""{avisos(mensajes)}
<h1>LinkedIn URLs</h1>
<p class="sub">El buscador trae lo que se publicó hace uno a tres días. Lo de hoy
todavía no lo indexó nadie, y estas direcciones son las que lo muestran.</p>
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
                 salud: dict | None = None) -> str:
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
    return f"""{avisos(mensajes)}
<h1>Métricas</h1>
<div class="tarjetas">{tarjetas}</div>

<h2>Lo que descartó el sistema, sin preguntarte</h2>
<p class="explica">Son las que no llegan a <b>Sin marcar</b> porque ya hay un
veredicto: no las borra nadie y vuelven solas si cambiás el filtro que las sacó.
Antes aparecían en la lista y había que descartarlas a mano una por una.</p>
{_tabla(("Motivo", "Ofertas"), sistema_filas)}
{_cuesta_el_ingles(perfil, ingles)}

<h2>Por qué descartaste vos</h2>
{_tabla(("Motivo", "Ofertas"), motivos_filas)}

<h2>De dónde vienen</h2>
{_tabla(("Portal", "Ofertas"), list((e.get("por_fuente") or {}).items()))}
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
