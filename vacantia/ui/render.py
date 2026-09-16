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
from pathlib import Path
from urllib.parse import quote, urlencode

from vacantia.fechas import dias_desde, fecha_de, parse_posted

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
    "configuracion": _icono('<path d="M20 7h-9"/><path d="M14 17H5"/>'
                            '<circle cx="17" cy="17" r="3"/><circle cx="7" cy="7" r="3"/>'),
    "filtradas": _icono('<path d="M3 5h18l-7 8v6l-4 2v-8Z"/>'),
    "mas": _icono('<circle cx="5" cy="12" r=".6"/><circle cx="12" cy="12" r=".6"/>'
                  '<circle cx="19" cy="12" r=".6"/>'),
    # El anillo del panel de "Buscando trabajo". Es un círculo entero más un
    # arco encima: el CSS gira sólo el arco, así que aun con el movimiento
    # apagado queda un anillo completo y no un gajo suelto que parece un error
    # de dibujo.
    "buscando": _icono('<circle class="aro" cx="12" cy="12" r="9"/>'
                       '<path class="arco" d="M21 12a9 9 0 0 0-9-9"/>'),
    # El tilde de un tramo cumplido. Sin círculo alrededor: al lado del punto
    # de los tramos que faltan, el tilde solo ya dice "éste pasó".
    "tilde-tramo": _icono('<path d="M4 12.5 9 17.5 20 6.5"/>'),
}

#: **El JavaScript de la pantalla vive en `static/app.js`, no acá**, y htmx en
#: `static/htmx.min.js`. Se sirven como archivos aparte, igual que el CSS y por
#: la misma razón: adentro de un string de Python no hay resaltado de sintaxis,
#: ni autocompletado, ni linter que te avise que te comiste un paréntesis.
#:
#: Se leen de disco en cada pedido, así que editás el archivo, apretás F5 y lo
#: ves. No hay que reiniciar el servidor.
ESTATICOS = Path(__file__).parent / "static"


def estatico(nombre: str) -> str:
    """Un archivo de `static/`, tal cual está en disco.

    Binario y decodificado a mano: `read_text()` en Windows traduce los finales
    de línea, y el contenido tiene que salir byte por byte como se escribió.
    """
    return (ESTATICOS / nombre).read_bytes().decode("utf-8")


def __getattr__(nombre: str):
    """`render.JS` y `render.CSS` siguen andando, leyendo el archivo de ahora.

    Son los nombres que existían cuando el código estaba adentro de strings de
    Python. Los usan los tests, y al leer en el momento un test mira lo que hay
    en disco y no lo que había cuando se importó el módulo.
    """
    if nombre == "JS":
        return estatico("app.js")
    if nombre == "CSS":
        from vacantia.ui import estilos

        return estilos.hoja()
    raise AttributeError(f"module {__name__!r} no tiene {nombre!r}")


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
#: Configuración va sola, al pie, abajo de Buscar ahora. Es lo que se carga una
#: vez y no se vuelve a mirar: arriba, al lado de lo que se usa todos los días,
#: competía por la vista sin merecerlo.
SECCION_AL_PIE = ("configuracion", "Configuración", "configuracion")


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


#: Cada cuánto le pregunta la pantalla al servidor cómo viene la búsqueda.
#:
#: Dos valores y no uno: mientras busca, el cartel cambia de etapa y dos
#: segundos es lo que hace que se sienta vivo; quieto, lo único que puede pasar
#: es que arranque la corrida programada, y preguntar cada dos segundos por eso
#: es tirar 1800 pedidos por hora a la basura.
#:
#: **El intervalo viaja en el fragmento, no en el JavaScript.** Cada respuesta
#: trae el suyo, así que el ritmo se acelera solo al arrancar la búsqueda y se
#: afloja solo al terminar, sin una línea de código nuestro.
LATIDO_BUSCANDO = "2s"
LATIDO_QUIETO = "15s"


def _cuanto_hace(segundos: int) -> str:
    """Los segundos que lleva la búsqueda, dichos como los diría una persona.

    Redondea a minutos enteros arriba del minuto: el segundero corriendo al lado
    de una barra que no avanza es lo que hace que cinco minutos se sientan
    veinte. Lo que el número tiene que contestar es "¿esto arrancó recién o hace
    un rato?", y para eso "3 minutos" alcanza.
    """
    if segundos < 60:
        return "recién arrancó"
    minutos = segundos // 60
    return "hace 1 minuto" if minutos == 1 else f"hace {minutos} minutos"


def _tramos(etapa: str) -> str:
    """La fila de tramos del panel: cuáles ya pasaron, en cuál está, cuáles no.

    Sale de `corrida.ETAPAS`, que es el orden del pipeline del motor, y **no de
    una lista escrita acá**: si mañana el motor gana o pierde una etapa, se toca
    en un solo lado y el panel la dibuja sola.
    """
    from vacantia.ui.corrida import ETAPAS

    orden = [clave for clave, _ in ETAPAS]
    # `arranque` es antes del primer tramo (-1) y `cierre` después del último.
    if etapa == "cierre":
        actual = len(orden)
    elif etapa in orden:
        actual = orden.index(etapa)
    else:
        actual = -1

    piezas = []
    for i, (clave, nombre) in enumerate(ETAPAS):
        if i < actual:
            estado, marca_ = "hecho", ICONOS["tilde-tramo"]
        elif i == actual:
            estado, marca_ = "activo", '<span class="punto" aria-hidden="true"></span>'
        else:
            estado, marca_ = "pendiente", '<span class="punto" aria-hidden="true"></span>'
        piezas.append(f'<li class="{estado}">{marca_}<span>{esc(nombre)}</span></li>')
    return f'<ol class="tramos">{"".join(piezas)}</ol>'


def _barra(paso: dict) -> str:
    """La barra del panel. Se llena de verdad sólo durante el puntaje.

    En las demás etapas no se sabe cuánto falta -- no se sabe cuántas fuentes
    van a contestar ni cuántas ofertas van a entrar -- así que la barra va sin
    porcentaje: dice "esto sigue andando", que es lo único cierto. Un porcentaje
    inventado que se clava en 40% durante dos minutos es peor que no tener
    ninguno.
    """
    total, hechas = int(paso.get("total") or 0), int(paso.get("hechas") or 0)
    if not total:
        return ('<div class="barra indefinida" role="progressbar"'
                ' aria-label="Buscando"><span></span></div>')
    porcentaje = min(100, round(hechas * 100 / total))
    return (f'<div class="barra" role="progressbar" aria-valuemin="0"'
            f' aria-valuemax="{total}" aria-valuenow="{hechas}"'
            f' aria-label="Ofertas puntuadas">'
            f'<span style="width: {porcentaje}%"></span></div>')


def panel_de_busqueda(paso: dict, oob: bool = False) -> str:
    """El panel grande de "Buscando trabajo", arriba del contenido.

    El cartel del pie de la barra lateral dice lo mismo en dos renglones de
    texto chico, y ese es justamente el problema que vino a resolver esto: al
    costado del campo visual y en cuerpo 12, arrancar una búsqueda y que no
    pasara nada visible se sentía igual que apretar un botón roto. El panel es
    lo que contesta "¿está haciendo algo?" de un vistazo y desde lejos.

    Los dos siguen existiendo y no es redundancia: el panel es el estado de
    *esta* búsqueda mientras dura, y el cartel del pie es el botón que la
    arranca y el lugar fijo donde vive el estado del sistema.

    **Vuelve siempre el contenedor, incluso vacío.** Es el único elemento de la
    pantalla que tiene que poder *desaparecer* solo cuando la búsqueda termina,
    y para que el reemplazo lo alcance el contenedor tiene que estar ahí. Si
    volviera `""` como el aviso de novedades, el panel quedaría clavado hasta
    que alguien recargue.

    Con `oob`, vuelve marcado para pisar al panel que ya está en la página
    aunque el pedido lo haya hecho el cartel de la barra lateral, que es otro
    elemento: así un solo pedido cada dos segundos actualiza los dos.

    **El `role="status"` lo lleva el cartel del pie y no éste.** Los dos dicen
    la misma oración y los dos se reemplazan cada dos segundos: con la etiqueta
    puesta en los dos, un lector de pantalla canta "Puntuando contra tu CV" dos
    veces cada dos segundos durante toda la búsqueda.
    """
    fuera = ' hx-swap-oob="true"' if oob else ""
    abre = f'<div class="buscando" id="buscando"{fuera}>'
    if not paso.get("corriendo"):
        return f"{abre}</div>"

    # El segundo renglón: durante el puntaje, cuántas lleva de cuántas, que es
    # el único momento en que se sabe el total de verdad. Fuera de ahí, de qué
    # perfil se trata, que con `--all` va cambiando y es lo que explica por qué
    # la búsqueda tarda el triple que de costumbre.
    if paso.get("total"):
        detalle = f'{paso["hechas"]} de {paso["total"]}'
    elif paso.get("perfil"):
        detalle = f'Perfil {paso["perfil"]}'
    else:
        detalle = ""

    return f"""{abre}
  <div class="cabecera">
    {ICONOS["buscando"]}
    <h2>Buscando trabajo</h2>
    <span class="hace">{esc(_cuanto_hace(int(paso.get("segundos") or 0)))}</span>
  </div>
  <p class="que">{esc(paso.get("paso", ""))}</p>
  <div class="avance">{_barra(paso)}<span class="detalle">{esc(detalle)}</span></div>
  {_tramos(paso.get("etapa", ""))}
  <p class="tranquilo">Seguí usando la pantalla: cuando entren ofertas nuevas, te avisa acá.</p>
</div>"""


def corrida_estado(perfil: str, paso: dict, marca: str, pendientes: int,
                   nuevas: int = 0, cambio: bool = False,
                   con_panel: bool = True) -> str:
    """El cartel del pie de la barra lateral: el botón, o en qué anda la búsqueda.

    Es el único pedazo de la pantalla que se actualiza solo. Se pide cada tantos
    segundos y se reemplaza entero; como el fragmento que vuelve trae de nuevo
    sus propios atributos, el ciclo se mantiene sin que nadie lo programe.

    `marca` y `pendientes` son **cómo estaba el historial cuando se abrió la
    página**, no ahora. Viajan en la dirección del pedido y vuelven iguales en
    cada respuesta, así que la comparación siempre es contra el momento en que
    la persona empezó a mirar. Sin eso, el aviso de "entraron 3 ofertas" se
    reiniciaría solo cada dos segundos y no diría nada.

    Cuando la corrida terminó y entraron ofertas, además del cartel vuelve el
    aviso de novedades marcado para reemplazar al de la página. **No recarga
    sola a propósito**: si alguien está escribiendo el motivo de un descarte,
    una recarga se lo borra. Avisa, y decide la persona.

    Con la misma respuesta viaja el panel grande de arriba del contenido. Es un
    solo pedido cada dos segundos que actualiza los tres lugares: el cartel del
    pie, el panel de arriba y el aviso de novedades. `con_panel=False` es para
    el armado inicial de la página, donde el panel lo pone `pagina()` en su
    lugar y mandarlo dos veces dejaría dos elementos con el mismo id.
    """
    destino = (f"/corrida?{urlencode({'perfil': perfil, 'marca': marca, 'pend': pendientes})}")
    latido = LATIDO_BUSCANDO if paso.get("corriendo") else LATIDO_QUIETO
    abre = (f'<div class="corrida" id="corrida" hx-get="{esc(destino)}" '
            f'hx-trigger="every {latido}" hx-swap="outerHTML">')

    if paso.get("corriendo"):
        # Dos renglones: qué está haciendo, y cuánto lleva de eso cuando el
        # total se sabe de verdad. Durante el puntaje se sabe; durante las
        # fuentes no, y un porcentaje inventado es peor que no poner ninguno.
        segunda = ""
        if paso.get("total"):
            segunda = f'{paso["hechas"]} de {paso["total"]}'
        elif paso.get("perfil"):
            segunda = f'Perfil {paso["perfil"]}'
        detalle = f'<p class="detalle">{esc(segunda)}</p>' if segunda else ""
        return (f'{abre}<p class="que" role="status">{esc(paso.get("paso", ""))}</p>'
                f'{detalle}</div>{panel_de_busqueda(paso, oob=True) if con_panel else ""}')

    boton = f"""<form method="post" action="/buscar" hx-post="/buscar"
      hx-target="#corrida" hx-swap="outerHTML">
  <input type="hidden" name="perfil" value="{esc(perfil)}">
  <input type="hidden" name="marca" value="{esc(marca)}">
  <input type="hidden" name="pend" value="{esc(pendientes)}">
  <button type="submit">Buscar ahora</button>
</form>"""
    # Sin corrida, el panel vuelve vacío igual: es lo que lo hace desaparecer
    # de la pantalla en el mismo pedido en que la búsqueda termina.
    panel = panel_de_busqueda(paso, oob=True) if con_panel else ""
    return f"{abre}{boton}</div>{panel}{_aviso_novedades(nuevas, cambio)}"


def _aviso_novedades(cuantas: int, cambio: bool) -> str:
    """El cartel de "entraron ofertas", listo para pisar al que está en la página.

    `hx-swap-oob` es lo que le permite a una respuesta tocar un elemento que no
    es el que la pidió: el cartel de la corrida vive en la barra lateral y el
    aviso abajo a la derecha, y los dos se actualizan con el mismo pedido.

    Vuelve vacío cuando no hay nada que avisar. Ojo: vacío de verdad, no el
    cartel escondido. Si volviera escondido, pisaría al que la persona está
    mirando y el aviso desaparecería solo a los dos segundos.

    **Que el historial cambie y que haya ofertas nuevas no son lo mismo.** Una
    corrida puede traer veinte avisos y que los veinte se caigan por filtro, o
    la persona puede estar marcando desde otra pestaña. En esos casos el número
    no sube pero la lista que está mirando ya no es la que hay, y eso también
    hay que decirlo.
    """
    if not cambio:
        return ""
    if cuantas <= 0:
        # El botón también cambia: "Ver las nuevas" abajo de "La lista cambió"
        # promete ofertas que a lo mejor no hay.
        que, hacer = "La lista cambió", "Actualizar"
    else:
        que = (f"Entraron {cuantas} ofertas nuevas" if cuantas != 1
               else "Entró 1 oferta nueva")
        hacer = "Ver las nuevas"
    return f"""
<div class="toast novedades visible" id="novedades" role="status" hx-swap-oob="true">
  <span>{esc(que)}</span>
  <button type="button" onclick="location.reload()">{esc(hacer)}</button>
</div>"""


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
    # El cartel de la corrida va adentro del estado del sistema porque es el
    # mismo dato: "la última búsqueda fue hace seis horas" y "está buscando
    # ahora" se leen juntos o no se leen.
    cartel = corrida_estado(perfil, estado.get("paso") or {},
                            estado.get("marca") or "",
                            int(estado.get("pendientes") or 0),
                            con_panel=False)
    return f'<div class="estado"><p>{linea}</p>{cubre}{cartel}</div>' 


def pagina(titulo: str, cuerpo: str, perfil: str, perfiles: list[str], tab: str,
           estado: dict | None = None) -> str:
    """El shell: barra lateral a la izquierda, una sola columna a la derecha.

    Arriba del contenido va el panel de "Buscando trabajo", que arranca vacío si
    no hay ninguna búsqueda en curso. Vacío ocupa cero y no se ve; existe
    siempre porque es el lugar donde el cartel del pie lo va a ir a pisar cuando
    la búsqueda arranque, y para pisarlo tiene que estar.

    Va acá y no adentro de cada pantalla: la búsqueda se puede arrancar desde
    cualquiera, y quedarse mirando Métricas mientras corre es exactamente el
    momento en el que hace falta ver que está corriendo."""
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
<link rel="stylesheet" href="/estilos.css">
<script src="/htmx.min.js" defer></script>
<script src="/app.js" defer></script>
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
  <nav class="al-pie" aria-label="Configuración">{link(*SECCION_AL_PIE)}</nav>
</aside>
<main id="contenido">{panel_de_busqueda((estado or {}).get("paso") or {})}{cuerpo}</main>
<!-- El aviso de que entraron ofertas. Nace escondido y en TODAS las pantallas,
     no sólo en Trabajos: el cartel de la corrida lo pisa con `hx-swap-oob`
     cuando la búsqueda termina, y para pisarlo tiene que existir. Si sólo
     estuviera en Trabajos, buscar desde Métricas no avisaría nada. -->
<div class="toast novedades" id="novedades" role="status"></div>
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
    46 veces la misma frase escrita a mano. Los motivos salen de lo que de
    verdad se escribió, no de lo que uno imagina que se va a escribir.

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
    contestarla hacen falta dos cosas juntas: **los motivos que dio el sistema**
    y **el aviso**, para poder ir a mirarlo. Por eso van arriba de todo y con su
    explicación completa, y no escondidos en un tooltip.

    **Van todos los motivos, no el primero.** Una oferta puede caer por idioma y
    por lugar a la vez, y mostrando uno solo la pantalla mentía: si el que se
    mostraba estaba mal atribuido, la respuesta honesta era "mal descartada" y
    la oferta volvía a la lista aunque el otro motivo la sacara con derecho.

    **Tres respuestas y no dos.** Faltaba justo la del medio, que es la que
    apareció usándolo: bien sacada, pero por el motivo equivocado. Con dos
    botones eso había que contestarlo mintiendo para un lado o para el otro.
    Sólo "mal" devuelve la oferta a Sin marcar; las otras dos la dejan afuera,
    que es lo correcto, y se cuentan por separado para poder ver qué filtro es
    el que atribuye mal.
    """
    url = oferta.get("url", "")
    razon = oferta.get("reason") or ""
    motivos = oferta.get("_motivos_sistema") or []
    if not motivos:
        motivos = [("", "")]
    porques = "".join(
        f'<p class="por-que"><b>{esc(_MOTIVOS_SISTEMA.get(clave, "El sistema la descartó"))}</b>'
        f'{f"""<span class="detalle">{esc(explica)}</span>""" if explica else ""}</p>'
        for clave, explica in motivos
    )
    y_ademas = ('<p class="ayuda">Cae por los dos: alcanza con que uno esté bien '
                'para que no tenga que llegarte.</p>' if len(motivos) > 1 else "")
    return f"""<article class="oferta filtrada">
{cabecera}
    {porques}{y_ademas}
    {f'<p class="razon">{esc(razon)}</p>' if razon else ''}
    <form class="acciones" method="post" action="/revisar-filtro">
      {_ocultos(perfil, "filtradas", desde, pagina, url)}
      <button class="primario" name="revision" value="bien"
              onclick="return marcar(this, false)">Bien descartada</button>
      <button name="revision" value="motivo"
              onclick="return marcar(this, false)">Bien, motivo equivocado</button>
      <button name="revision" value="mal"
              onclick="return marcar(this, false)">Mal descartada</button>
      <span class="ayuda">Sólo <b>Mal descartada</b> la devuelve a Sin marcar
      para que puedas aplicar.</span>
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
    {linea_de_cv(oferta.get('_cv'), 'Mandá tu CV')}
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


def _selector_de_periodo(perfil: str, ver: str, desde: str, elegido: str) -> str:
    """El desplegable de 7 días / 2 semanas / mes / ... del cartel de arriba.

    Es un GET con los otros filtros escondidos adentro: cambiar el período no
    tiene que perder en qué pestaña estabas ni el filtro de antigüedad.
    """
    from vacantia.ui.data import PERIODOS

    opciones = "".join(
        f'<option value="{esc(clave)}"'
        f'{" selected" if clave == elegido else ""}>{esc(etiqueta)}</option>'
        for clave, etiqueta, _ in PERIODOS
    )
    return f"""<form class="periodo" method="get" action="/trabajos">
  <input type="hidden" name="perfil" value="{esc(perfil)}">
  <input type="hidden" name="ver" value="{esc(ver)}">
  <input type="hidden" name="desde" value="{esc(desde)}">
  <label for="cuando-apliq">Período</label>
  <select id="cuando-apliq" name="apliq" onchange="this.form.submit()">{opciones}</select>
  <noscript><button>Ver el período</button></noscript>
</form>"""


def _postulaciones(perfil: str, ver: str, desde: str, aplicadas: dict | None,
                   descartadas: dict | None = None) -> str:
    """El cartel grande de arriba de la lista. **Cambia según la pestaña.**

    Antes era uno solo y vivía únicamente en *Sin marcar*. El problema es que el
    número de arriba y la lista de abajo hablaban de cosas distintas: parado en
    *Apliqué* veías nueve tarjetas y un cartel que decía once, porque el cartel
    sumaba las que contaste a mano desde un posteo de LinkedIn.

    Ahora cada pestaña trae el número que corresponde a lo que estás mirando:

    * **Sin marcar** — el total de postulaciones, de donde sea que salgan. Es la
      pantalla que se abre por defecto y la pregunta ahí es "¿estoy haciendo
      algo?", que no distingue de dónde salió cada una.
    * **Apliqué** — sólo las que marcaste en esta lista, que son las que tenés
      abajo. Un número más grande que la lista se lee como un error.
    * **Descarté** — no cuántas sino **por qué**, que es la única parte de esto
      que se puede accionar: "46 de 78 por inglés" es una perilla de Mi perfil
      esperando que la muevan.
    * **Filtradas** ya tiene su propio marcador de auditoría, y dos marcadores
      en la misma pantalla no se leen, compiten.

    El verde no decora: en este sistema significa lo que ya hiciste, igual que
    en la tarjeta de una oferta aplicada. Y va con la palabra al lado, nunca
    sólo el color. Por eso *Descarté* **no** va en verde: descartar no es un
    logro, es higiene.
    """
    if ver == "descartadas":
        return _cartel_de_descartes(perfil, ver, desde, descartadas)
    if ver not in ("pendientes", "aplicadas") or not aplicadas:
        return ""

    from vacantia.ui.graficos import columnas

    cuantas = aplicadas.get("cuantas", 0)
    selector = _selector_de_periodo(perfil, ver, desde, aplicadas.get("periodo", ""))

    if not cuantas:
        cuerpo = ('<p class="vacio-corto">Todavía no marcaste ninguna en este '
                  'período. Cuando mandes un CV, tocá <b>Apliqué</b> en esa '
                  'oferta y el número empieza a subir.</p>')
    else:
        # El reparto es lo que hace que el total signifique algo: 12
        # postulaciones en un mes puede ser tres semanas sin hacer nada y una a
        # los tiros, y eso no se ve en el total.
        #
        # En una semana el reparto es por día y no por semana: repartir siete
        # días en semanas daba una barra sola, que no compara con nada, y la
        # tarjeta quedaba con el número grande y un vacío al lado.
        tramos = [{"etiqueta": e, "cuantas": n}
                  for e, n in aplicadas.get("reparto") or []]
        por = "día" if aplicadas.get("unidad") == "día" else "semana"
        cuerpo = (f'<div class="reparto" aria-label="Postulaciones por {por}">'
                  f'{columnas(tramos, "postulaciones")}</div>'
                  if len(tramos) > 1 else "")

    trabajo = "trabajo" if cuantas == 1 else "trabajos"
    cuando = esc(aplicadas.get("etiqueta", ""))
    if ver == "aplicadas":
        # Parado acá el número YA es sólo el de la lista, así que en vez de
        # explicar qué se sumó hay que explicar qué se restó: si no, el cartel
        # y el contador de la barra de arriba no cierran y parece un bug.
        cuando += " · sólo las de esta lista"
    else:
        # De dónde salió el número, cuando parte no salió de esta lista. Sin
        # esto, el total sube sin que se haya marcado ninguna tarjeta y no hay
        # forma de entender por qué.
        a_mano = aplicadas.get("a_mano") or 0
        if a_mano:
            cuando += f" · {a_mano} anotadas en LinkedIn URLs"
    return f"""<section class="postulaciones" aria-label="Postulaciones">
  <p class="cuenta"><span class="numero">{cuantas}</span>
     <span class="que">{trabajo} a los que apliqué</span>
     <span class="cuando">{cuando}</span></p>
  {selector}
  {cuerpo}
</section>"""


def _cartel_de_descartes(perfil: str, ver: str, desde: str,
                         descartadas: dict | None) -> str:
    """Por qué venís descartando, con el mismo selector de período.

    El total de descartes no sirve para nada por sí solo: descartar no es
    trabajo que quieras sostener, así que no hay ritmo que cuidar. Lo que sirve
    es el desglose, porque cada motivo que se repite mucho es una perilla de Mi
    perfil que conviene mover: si 46 de 78 caen por inglés, o subís el nivel
    declarado o dejás de buscar puestos que lo piden, pero hay algo que hacer.

    Por eso acá el gráfico es de barras por motivo y no de columnas por semana,
    y por eso el número grande no va en verde: el verde en este sistema
    significa lo que ya hiciste, y descartar no es un logro.
    """
    from vacantia.ui.graficos import barras, vale_un_grafico

    if not descartadas:
        return ""

    cuantas = descartadas.get("cuantas", 0)
    filas = descartadas.get("motivos") or []
    selector = _selector_de_periodo(perfil, ver, desde, descartadas.get("periodo", ""))

    if not cuantas:
        cuerpo = ('<p class="vacio-corto">No descartaste ninguna en este período. '
                  'Cuando una no sirva, tocá <b>No apliqué</b> y elegí por qué: '
                  'ese motivo es lo que después afina las búsquedas.</p>')
    elif vale_un_grafico(filas):
        cuerpo = (f'<div class="reparto" aria-label="Motivos de descarte">'
                  f'{barras(filas, "ofertas")}</div>')
    else:
        # Con uno o dos motivos no hay nada que comparar: el gráfico sería una
        # barra al 100% al lado de otra al 30%, que dice menos que la frase.
        cuerpo = '<ul class="motivos-cortos">' + "".join(
            f"<li><b>{esc(n)}</b> {esc(etiqueta.lower())}</li>"
            for etiqueta, n in filas) + "</ul>"

    oferta = "oferta" if cuantas == 1 else "ofertas"
    return f"""<section class="postulaciones descartes" aria-label="Motivos de descarte">
  <p class="cuenta"><span class="numero">{cuantas}</span>
     <span class="que">{oferta} que descarté</span>
     <span class="cuando">{esc(descartadas.get("etiqueta", ""))}</span></p>
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
    # De las bien descartadas, cuántas lo estaban por el motivo equivocado. Va
    # adentro del contador de aciertos y no al lado: es un acierto del filtro y
    # un error de la explicación, y son dos cosas distintas.
    con_motivo_mal = revision.get("motivo_errado", 0)
    errado = (f'<span class="valor">{con_motivo_mal}</span> con el motivo mal'
              if con_motivo_mal else "")
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
     <span class="valor">{mal}</span> mal descartadas{errado}</p>
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
             revision: dict | None = None, aplicadas: dict | None = None,
             descartadas: dict | None = None) -> str:
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

    # El aviso de "entraron ofertas nuevas" ya no se arma acá. Lo trae el cartel
    # de la corrida del pie de la barra lateral: pregunta por la marca del
    # historial en el mismo pedido con el que pregunta en qué anda la búsqueda,
    # y pisa el aviso del shell con `hx-swap-oob`. Antes eran dos relojes
    # distintos preguntando por cosas parecidas.

    return f"""{avisos(mensajes)}
<h1>Trabajos</h1>
{_postulaciones(perfil, ver, desde, aplicadas, descartadas)}
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
# Las dos pestañas son la misma pantalla: constructor a la izquierda, dirección
# y favoritos a la derecha, y el anotador de lo aplicado abajo del botón.

#: (clave, etiqueta). La primera es la que se abre por defecto.
#:
#: Publicaciones va primero porque es la que resuelve el agujero real: los
#: avisos que se publican como posteo del feed y nunca llegan a la pestaña Jobs.
#: Jobs el scraper lo trae, pero tarde y sin los filtros de poca competencia.
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


def _desplegable(nombre: str, opciones, elegida: str, etiqueta: str,
                 ayuda: str = "") -> str:
    ops = "".join(
        f'<option value="{esc(c)}"{" selected" if c == elegida else ""}>{esc(e)}</option>'
        for c, e, *_ in opciones
    )
    rotulo = f'<label for="{esc(nombre)}">{esc(etiqueta)}</label>'
    if ayuda:
        rotulo = _rotulo_con_ayuda(rotulo, ayuda)
    return f"""<div class="campo">
  {rotulo}
  <select id="{esc(nombre)}" name="{esc(nombre)}">{ops}</select>
</div>"""


def _rotulo_con_ayuda(rotulo: str, ayuda: str) -> str:
    """El rótulo de un campo con el signo de pregunta al lado.

    El signo va **afuera** del `<label>`: adentro, pasarle el mouse o tocarlo
    marcaría la tilde, y lo que se quería era leer qué hace.
    """
    return f'<div class="rotulo-con-ayuda">{rotulo}{_ayuda_al_lado(ayuda, abajo=True)}</div>'


def _opciones(nombre: str, pares, marcadas, tipo: str = "checkbox") -> str:
    """Tildes o radios donde el valor no es lo que se lee (`f_WT=2` es Remoto)."""
    puestas = {str(m) for m in (marcadas or [])}
    return "".join(
        f'<label><input type="{tipo}" name="{esc(nombre)}" value="{esc(v)}"'
        f'{" checked" if str(v) in puestas else ""}> {esc(e)}</label>'
        for v, e, *_ in pares
    )


def _tilde_con_ayuda(nombre: str, etiqueta: str, marcada: bool, ayuda: str) -> str:
    return (f'<span class="tilde-con-ayuda"><label><input type="checkbox" '
            f'name="{esc(nombre)}" value="1"{" checked" if marcada else ""}> '
            f'{esc(etiqueta)}</label>{_ayuda_al_lado(ayuda, abajo=True)}</span>')


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
    if elegido.get("tab") == "jobs":
        return _volver_al_armador_jobs(perfil, elegido)
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


def _volver_al_armador_jobs(perfil: str, elegido: dict) -> str:
    """Lo mismo que `_volver_al_armador`, con los campos de la pestaña Jobs."""
    partes: list[tuple[str, str]] = [("perfil", perfil), ("tab", "jobs")]
    partes += [("puesto", str(p)) for p in elegido.get("puestos") or []]
    if elegido.get("tambien"):
        partes.append(("tambien", str(elegido["tambien"])))
    if elegido.get("sin_junior"):
        partes.append(("sin_junior", "1"))
    partes.append(("donde", str(elegido.get("donde") or "argentina")))
    partes += [("modalidad", str(m)) for m in elegido.get("modalidades") or []]
    partes += [("nivel", str(n)) for n in elegido.get("niveles") or []]
    for clave, porde in (("cuando", "24h"), ("orden", "recientes")):
        partes.append((clave, str(elegido.get(clave) or porde)))
    if elegido.get("pocos"):
        partes.append(("pocos", "1"))
    if elegido.get("sencilla"):
        partes.append(("sencilla", "1"))
    return urlencode(partes)


def _ayuda_al_lado(texto: str, abajo: bool = False) -> str:
    """El signo de pregunta que muestra la explicación al pasarle por encima.

    Para lo que hace falta una vez y estorba siempre. El texto largo suelto en
    la pantalla compite con el control que importa; escondido detrás de un
    ícono, está cuando se busca y no antes.

    **No es sólo hover.** Se abre también con el foco del teclado, porque quien
    tabula no pasa el mouse por ningún lado, y el texto está en el DOM desde el
    principio para que un lector de pantalla lo lea como nota del rótulo.

    Con `abajo`, el globo se abre hacia abajo y hacia la derecha. Es el de los
    rótulos del constructor: están arriba y a la izquierda de una columna que
    scrollea, y abierto hacia arriba y a la izquierda la columna lo cortaba.
    """
    clase = "ayuda-al-lado abajo" if abajo else "ayuda-al-lado"
    return (f'<span class="{clase}" tabindex="0" role="note">'
            f'<span class="signo" aria-hidden="true">?</span>'
            f'<span class="globo">{esc(texto)}</span></span>')


def _apliques(perfil: str, sin_confirmar: int, confirmadas: int,
              volver: str, tab: str = "publicaciones") -> str:
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
    if tab == "jobs":
        # El aviso de Jobs, a diferencia del posteo, puede haber entrado también
        # por el buscador automático: contarlo en los dos lados lo cuenta doble.
        explica = ("Contá acá lo que vayas mandando desde estas búsquedas y "
                   "confirmá al terminar. Si el aviso ya está en Trabajos, "
                   "marcalo ahí y no acá, para no contarlo dos veces. ")
    else:
        explica = "Contá acá lo que vayas mandando desde un posteo y confirmá al terminar. "
    return f"""<div class="apliques">
  <p class="rotulo">Apliqué desde acá{_ayuda_al_lado(
      explica +
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


def _constructor_jobs(perfil: str, elegido: dict, puestos: list[str],
                      apliques: dict | None = None) -> str:
    """El constructor de la pestaña Jobs. La misma forma que el de Publicaciones.

    Mismo formulario GET, mismas dos secciones, el mismo botón y el mismo
    anotador abajo: quien aprendió a usar una pestaña ya sabe usar la otra.
    Cambia lo que se elige, porque LinkedIn Jobs filtra por otras cosas.

    Lo que no se entiende con leer el rótulo lleva el signo de pregunta, igual
    que el anotador: nivel, menos de 10 candidatos, solicitud sencilla. Escrito
    suelto al pie de cada campo, eran seis párrafos compitiendo con el botón.
    """
    from vacantia.ui.linkedin_urls import (
        CUANDO_JOBS, DONDE_JOBS, EXCLUIR_JOBS, MODALIDADES, NIVELES, ORDEN_JOBS,
    )

    donde = elegido.get("donde") or "argentina"
    return f"""<form class="datos armador" method="get" action="/linkedin">
<input type="hidden" name="perfil" value="{esc(perfil)}">
<input type="hidden" name="tab" value="jobs">

<h2>Qué buscar</h2>
<div class="grilla">
  <div class="campo ancho">
    <label>Puestos</label>
    {_tildes("puesto", puestos, elegido.get("puestos"))}
    <p class="ayuda">Se buscan todos juntos: alcanza con que el aviso diga uno.
    Salen de <b>Palabras clave</b>, en
    <a href="/datos?perfil={esc(perfil)}">Mi perfil</a>.</p>
  </div>
  <div class="campo ancho">
    {_rotulo_con_ayuda('<label for="tambien">Que además diga</label>',
        "Palabras que el aviso tiene que tener, además del puesto, separadas "
        "por coma. Alcanza con que tenga una de ellas. Sirve para quedarte con "
        "los que piden lo tuyo, por ejemplo: Python, RAG, OpenAI. Vacío, no "
        "filtra nada.")}
    <input type="text" id="tambien" name="tambien" value="{esc(elegido.get("tambien", ""))}"
           placeholder="Python, RAG, OpenAI">
  </div>
  <div class="campo">
    {_rotulo_con_ayuda("<label>Dónde</label>",
        "Argentina incluye los remotos que LinkedIn ofrece para Argentina. "
        "Cualquier lugar agranda mucho la lista, y la mayoría de lo que suma "
        "pide inglés.")}
    <div class="checks">{_opciones("donde", DONDE_JOBS, [donde], tipo="radio")}</div>
  </div>
  <div class="campo">
    {_rotulo_con_ayuda("<label>Modalidad</label>",
        "Sin tildar ninguna, entran todas.")}
    <div class="checks">{_opciones("modalidad", MODALIDADES, elegido.get("modalidades"))}</div>
  </div>
  <div class="campo ancho">
    {_rotulo_con_ayuda("<label>Nivel</label>",
        "Son los niveles de LinkedIn. No hay uno que sea sólo Senior: "
        "«Intermedio» es su Mid-Senior, y ahí se cuelan semi seniors. Por eso "
        "conviene tildar también «Puestos junior y semi senior» en Qué dejar "
        "afuera. Sin tildar ninguno, entran todos.")}
    <div class="checks">{_opciones("nivel", NIVELES, elegido.get("niveles"))}</div>
  </div>
  <div class="campo ancho">
    <label>Qué dejar afuera</label>
    <div class="checks">
      <label><input type="checkbox" name="sin_junior" value="1"
      {" checked" if elegido.get("sin_junior") else ""}> Puestos junior y semi senior</label>
    </div>
    <p class="ayuda">Saca {esc(", ".join(EXCLUIR_JOBS))}.</p>
  </div>
</div>

<h2>Cómo mostrarlo</h2>
<div class="grilla">
  {_desplegable("cuando", CUANDO_JOBS, elegido.get("cuando", "24h"), "Publicado hace",
      ayuda="Última hora es para revisar dos o tres veces por día: llegás "
            "entre los primeros. Una semana es para un barrido, una vez por día.")}
  {_desplegable("orden", ORDEN_JOBS, elegido.get("orden", "recientes"), "Ordenar por")}
  <div class="campo ancho">
    <label>Poca competencia</label>
    <div class="checks">
      {_tilde_con_ayuda("pocos", "Menos de 10 candidatos", bool(elegido.get("pocos")),
          "Sólo los avisos a los que se postularon menos de 10 personas. Es "
          "donde tu CV tiene más chances de que alguien lo lea. Junto con "
          "Última hora, trae poco: si da cero, sacá uno de los dos.")}
      {_tilde_con_ayuda("sencilla", "Solicitud sencilla", bool(elegido.get("sencilla")),
          "Sólo los avisos que se aplican adentro de LinkedIn, en un clic, con "
          "el CV que tenés cargado allá. Sirven para mandar muchos rápido; los "
          "demás te llevan a la página de la empresa.")}
    </div>
  </div>
</div>

<div class="guardar">
  <button class="primario" type="submit">Armar la búsqueda</button>
  {_apliques(perfil, (apliques or {}).get("pendientes", 0),
              (apliques or {}).get("confirmadas", 0),
              _volver_al_armador_jobs(perfil, elegido), tab="jobs")}
</div>
</form>"""


def _bloque_de_url(perfil: str, url: str, nombre: str, ya_guardada: bool,
                   tab: str = "publicaciones") -> str:
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
  <input type="hidden" name="tab" value="{esc(tab)}">
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
  <p class="ayuda">{"Al abrirla, LinkedIn cae en Empleos con los filtros puestos: "
                    "fijate arriba de la lista que figuren todos." if tab == "jobs" else
                    "Al abrirla, LinkedIn cae directo en la pestaña Publicaciones "
                    "con los filtros puestos."} Si algún día deja de filtrar, rehacé
  los filtros a mano en LinkedIn y pegá acá la dirección nueva.</p>
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


def _favoritos(perfil: str, guardados: list[dict], tab: str = "publicaciones") -> str:
    """Las búsquedas que ya sabés que sirven, para no rearmarlas cada vez.

    En Jobs el título lleva la rutina del documento de estrategia adentro del
    signo de pregunta: es lo que dice qué guardar y cuándo abrirlo.
    """
    titulo = "<h2>Tus búsquedas guardadas</h2>"
    if tab == "jobs":
        titulo = ('<div class="titulo-con-ayuda"><h2>Tus búsquedas guardadas</h2>'
                  + _ayuda_al_lado(
                      "A la mañana, abrí las de última hora, la de menos de 10 "
                      "candidatos y la de solicitud sencilla, y aplicá a todo lo "
                      "que sirva. Después, un barrido de la última semana. A la "
                      "tarde, de nuevo las de última hora: ya traen avisos nuevos.",
                      abajo=True)
                  + "</div>")
    if not guardados:
        que = "avisos" if tab == "jobs" else "posteos"
        return f"""{titulo}
<div class="vacio"><b>Todavía no guardaste ninguna.</b>
Cuando armes una búsqueda que te traiga {que} que sirven, guardala acá y la
volvés a abrir de un toque. La idea es tener cuatro o cinco y revisarlas dos
veces por día: los {que} buenos duran horas.</div>"""

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
          <input type="hidden" name="tab" value="{esc(tab)}">
          <input type="hidden" name="url" value="{esc(f.get("url"))}">
          <button class="fantasma" name="borrar" value="1">Sacar de favoritos</button>
        </form>
      </div>
    </details>
  </div>
</li>""")
    return f"""{titulo}
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
    from vacantia.ui.linkedin_urls import (
        PUESTOS_SUGERIDOS, nombre_sugerido, nombre_sugerido_jobs,
    )

    if tab not in dict(PESTANIAS_LINKEDIN):
        tab = PESTANIAS_LINKEDIN[0][0]
    elegido = {**(elegido or {}), "tab": tab}
    guardados = guardados or []
    puestos = puestos or list(PUESTOS_SUGERIDOS)

    botones = "".join(
        f'<a class="pestania{" activa" if clave == tab else ""}" '
        f'href="/linkedin?perfil={esc(perfil)}&tab={esc(clave)}"'
        f'{" aria-current=page" if clave == tab else ""}>{esc(etiqueta)}</a>'
        for clave, etiqueta in PESTANIAS_LINKEDIN
    )

    ya = any(f.get("url") == url for f in guardados)
    if tab == "jobs":
        nombre = nombre_sugerido_jobs(elegido.get("puestos"), elegido.get("cuando", "24h"),
                                      bool(elegido.get("pocos")),
                                      bool(elegido.get("sencilla")))
        controles = _constructor_jobs(perfil, elegido, puestos, apliques)
        # En Jobs no se recorta nada: el tope de largo es del buscador de posteos.
        recorte = ""
        sub = """Los avisos de la pestaña Empleos, apenas salen. El buscador
automático también los trae, pero tarde y sin los filtros que más rinden:
publicado hace una hora, menos de 10 candidatos, solicitud sencilla. Esos sólo
los ve quien entra logueado."""
    else:
        nombre = nombre_sugerido(elegido.get("puestos"), elegido.get("cuando", "24h"),
                                 elegido.get("idioma") == "en")
        controles = _constructor(perfil, elegido, puestos, apliques)
        recorte = _aviso_de_recorte(elegido.get("entraron"), elegido.get("pedidos"))
        sub = """Muchas vacantes se publican como un posteo del muro y nunca llegan
a la pestaña de empleos. El buscador las indexa uno a tres días tarde, cuando ya
se llenaron de postulantes. Estas direcciones las muestran apenas se publican."""

    # Dos columnas: a la izquierda lo que elegís, a la derecha lo que sale.
    # Antes iba todo en una sola columna larga y la dirección aparecía abajo
    # de todo, fuera de pantalla; encima el formulario es GET, así que al
    # armarla la página se recargaba y el navegador la abría arriba. Así, el
    # resultado nace al lado de los controles y nada se mueve.
    cuerpo = f"""<div class="taller">
<div class="lado controles">{controles}</div>
<div class="lado resultado">{recorte}\
{_bloque_de_url(perfil, url, nombre, ya, tab) if url else _todavia_sin_armar()}\
{_favoritos(perfil, guardados, tab)}</div>
</div>"""

    return f"""{avisos(mensajes)}
<h1>LinkedIn URLs</h1>
<p class="sub">{sub}</p>
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


#: Cuántas frases escritas a mano van en el gráfico. Arriba quedan las que se
#: repiten, que son las que dicen algo; de ahí para abajo suelen ser de a una.
ESCRITOS_A_LA_VISTA = 10


def _cabecera(titulo: str, explica: str, total: int | None = None, que: str = "",
              de_donde: str = "") -> str:
    """Título y para qué sirve a la izquierda; el total, en grande, del otro lado.

    Las barras se medían contra la más larga, así que la de arriba salía
    siempre llena y "51" no decía de cuántas: 161 avisos que piden Python es
    casi todo sobre 200 y un "bueno de tener" sobre 1000. Primero el total se
    escribió como una frase más ("De las 219 ofertas analizadas. La barra
    entera son las 219.") y se perdía entre la explicación y el gráfico. En
    grande y del otro lado se lee antes que las barras, que es lo que
    corresponde: sin saber contra cuántas se mide, ninguna se entiende.

    `de_donde` es para cuando el total no es obvio: 219 analizadas son "de las
    230 que entraron", y sin decirlo parecía un número salido de la nada.
    """
    texto = " ".join(explica.split())
    lado = ""
    if total:
        extra = f'<span class="de-donde">{esc(de_donde)}</span>' if de_donde else ""
        lado = (f'<div class="panel-total"><span class="numero">{total}</span>'
                f'<span class="que">{esc(que)}</span>{extra}</div>')
    return (f'<div class="panel-cabeza"><div><h2>{esc(titulo)}</h2>'
            f'<p class="explica">{texto}</p></div>{lado}</div>')


def _escritos_a_mano(filas: list[tuple[str, int]], total: int | None = None) -> str:
    """Qué dice la barra "Escrito a mano", frase por frase.

    Sin esto, saber qué había adentro era abrir Descarté y leer tarjeta por
    tarjeta, o sea no saberlo.

    Va en barras como el gráfico de motivos de arriba, y **siempre en barras**,
    aunque sean dos frases: `_desglose` las pasaba a tabla con menos de tres, y
    son dos bloques del mismo panel que tienen que leerse igual. Las que no
    entran en el gráfico van en una tabla plegada, para que una lista de sesenta
    frases no empuje el resto de Métricas fuera de la pantalla.

    Se miden contra el mismo `total` que los motivos, todos los descartes, y
    no contra la suma de lo escrito: "2 de 4 escritas a mano" parece la mitad
    de algo, y de 84 descartes es casi nada.
    """
    from vacantia.ui.graficos import barras

    if not filas:
        return ""
    visibles, resto = filas[:ESCRITOS_A_LA_VISTA], filas[ESCRITOS_A_LA_VISTA:]
    plegadas = (f'<details class="como"><summary>Ver {len(resto)} más</summary>'
                f'{_tabla(("Lo que escribiste", "Veces"), resto)}</details>'
                if resto else "")
    return (f'<p class="explica">Lo que escribiste a mano, de lo más repetido a lo '
            f'menos:</p>{barras(visibles, "veces", total=total)}{plegadas}')


#: Cómo se lee cada motivo del sistema en la pantalla.
def _solapadas(e: dict) -> str:
    """Aviso de que las filas suman más que las ofertas.

    Una oferta puede caer por idioma y por lugar a la vez, y acá se cuenta en
    las dos filas: la pregunta que contesta esta tabla es cuánto saca cada
    filtro, no de a cuántas le tocó cada una. Sin decirlo, la suma no cierra
    contra el total de arriba y parece un error de cuentas.
    """
    cuantas = e.get("sistema_solapadas") or 0
    if not cuantas:
        return ""
    una = "oferta cae" if cuantas == 1 else "ofertas caen"
    return (f'<p class="explica">Las filas suman más que las ofertas: '
            f'{cuantas} {una} por los dos filtros a la vez y se cuentan en '
            f'los dos. Son {e.get("sistema_total", 0)} distintas.</p>')


_MOTIVOS_SISTEMA = {
    "idioma": "Piden un inglés más alto que el tuyo",
    "lugar": "El lugar o la modalidad no te sirven",
}


def _desglose(encabezados: tuple[str, str], filas: list[tuple[str, int]],
              total: int | None = None) -> str:
    """Un desglose, como gráfico o como tabla según cuántas filas tenga.

    El gráfico se gana el lugar cuando hay varias magnitudes que comparar de un
    vistazo. Con dos filas no hay comparación, hay dos números, y para dos
    números la tabla ocupa menos y se lee más rápido. El corte está en
    `graficos.MINIMO_PARA_GRAFICAR`.

    **Con `total` va siempre en barras**, medidas contra ese total. Ahí la
    pregunta ya no es cuál es más grande sino qué parte del total es cada una,
    y eso la tabla no lo muestra aunque haya una sola fila.

    **La tabla no desaparece nunca**: cuando hay gráfico va debajo, plegada.
    Un gráfico no da el valor exacto ni se puede copiar, y a veces lo que se
    quiere es justamente el número.
    """
    from vacantia.ui.graficos import barras, vale_un_grafico

    tabla = _tabla(encabezados, filas)
    if total:
        grafico = barras(filas, encabezados[1].lower(), total=total)
    elif vale_un_grafico(filas):
        grafico = barras(filas, encabezados[1].lower())
    else:
        return tabla
    if not grafico:
        return tabla
    return f"""{grafico}
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

    # **Acá NO va el botón de buscar.** Métricas es una pantalla de lectura: se
    # entra a entender qué está pasando, no a hacer algo. El botón vivía suelto
    # al final de todo, lejos de cualquier cosa con la que tuviera relación, y
    # además ya está donde corresponde, al pie de la barra lateral, que se ve
    # desde todas las pantallas y ésta incluida.
    ahora = ("<p>Hay una búsqueda en curso. Cuando entren ofertas nuevas te "
             "avisa la pantalla de Trabajos.</p>"
             if salud.get("corriendo") else "")

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

    # Primero el gráfico: contesta de un vistazo la pregunta de toda la sección.
    # Una búsqueda en cero puede ser un mal día; varios días seguidos en cero
    # es que algo dejó de andar, y la tabla de la última búsqueda no lo dice.
    #
    # Con las dos semanas enteras en cero no va el gráfico: catorce columnas
    # grises son un gráfico vacío, y la frase avisa más fuerte que el dibujo.
    entradas = ""
    if salud.get("entradas"):
        from vacantia.ui.graficos import columnas

        if any(d.get("cuantas") for d in salud["entradas"]):
            entradas = ('<p class="explica">Ofertas nuevas por día, en las últimas '
                        'dos semanas. Un día en cero puede pasar; varios seguidos, '
                        'es que algo dejó de andar.</p>' + columnas(salud["entradas"]))
        else:
            entradas = ('<p>No entró ninguna oferta nueva en las últimas dos '
                        'semanas.</p>')

    # Va en su propia sección al pie y **no como un panel más**: no es un dato
    # sobre tu búsqueda de trabajo, es el estado de la máquina. Mezclarlo con
    # los desgloses obliga a leer "cuántas ofertas piden inglés" y "cuándo corre
    # la tarea programada" como si fueran la misma clase de cosa.
    return f"""<section class="salud">
  <h2>Cómo viene funcionando</h2>
  <p class="explica">El estado del programa, no de tu búsqueda. Mirá acá cuando
  algo no cierre: si hace días que no entra nada, la respuesta suele estar
  abajo.</p>
  {entradas}
  {programado}
  {encontro}
  {aviso}
  {problemas}
  {ahora}
</section>"""


def _habilidades(h: dict | None) -> str:
    """Qué te están pidiendo los avisos que entraron.

    Sale del campo que el modelo ya devolvía por cada oferta cuando la puntúa,
    así que **no cuesta ninguna llamada extra**: el aviso ya se le manda entero
    para puntuarlo, y pedirle de paso qué piden son unos tokens más de
    respuesta.

    Eso es también lo que la hace servir para cualquier oficio. No hay ninguna
    lista de tecnologías escrita en el código: el modelo lee el aviso y devuelve
    lo que ese aviso pide, sea LangChain, Google Analytics o la ISO 45001. Una
    lista escrita a mano habría que mantenerla para siempre y aun así nunca
    cubriría los oficios de los demás perfiles de la casa.

    Cuando quedan ofertas sin analizar se dice cuántas. Sin eso, un gráfico
    flaco se lee como "no piden nada" en vez de "todavía no lo miré todo".

    **Cada barra se mide contra las ofertas analizadas**, no contra la habilidad
    más pedida. "Python 161, AWS 45" no decía si AWS era algo que hay que
    aprender o un "bueno de tener": con el total al lado se ve que es 18% de
    245. Las que no pasaron por el analizador no entran en el total, porque no
    tienen nada que pedir.
    """
    from vacantia.ui.graficos import barras

    if not h or not h.get("filas"):
        return ""

    pie = ""
    if h.get("sin_datos"):
        cuantas = h["sin_datos"]
        una = "oferta todavía no pasó" if cuantas == 1 else "ofertas todavía no pasaron"
        pie = (f'<p class="pie-grafico">{cuantas} {una} por el analizador y no '
               f'suman acá. Entran solas en la próxima búsqueda.</p>')
    analizadas = h.get("ofertas") or 0
    return f"""{barras(h["filas"], "ofertas", total=analizadas or None)}
{pie}"""


def _panel(titulo: str, explica: str, cuerpo: str, total: int | None = None,
           que: str = "", de_donde: str = "") -> str:
    """Un bloque de Métricas: título, para qué sirve, y el gráfico.

    Métricas era una columna larguísima de secciones apiladas, con el gráfico de
    una y la explicación de la siguiente pegados, y media pantalla vacía a la
    derecha. Cada bloque encerrado en su propio panel se puede acomodar en dos
    columnas, y sobre todo deja de haber duda de a qué gráfico corresponde cada
    texto.

    **La explicación va arriba del gráfico y nunca abajo.** Un gráfico sin saber
    qué mide no se puede leer, así que leerlo primero y buscar el pie después es
    hacer el trabajo dos veces.

    El `explica` llega con los saltos y la sangría del f-string que lo escribió;
    se aplastan acá para que el HTML no salga con veinte espacios en el medio de
    una oración.
    """
    if not cuerpo.strip():
        return ""
    return f"""<section class="panel">
  {_cabecera(titulo, explica, total, que, de_donde)}
  {cuerpo}
</section>"""


def estadisticas(perfil: str, e: dict, desde: str, mensajes,
                 salud: dict | None = None,
                 puntajes: list[dict] | None = None,
                 habilidades: dict | None = None) -> str:
    """Los números que antes vivían apretados en los botones de arriba.

    Se separó porque compiten: mientras uno revisa ofertas, el único número que
    importa es cuántas faltan. "Archivadas 83" no es una tarea, es un archivo, y
    ocupaba el mismo espacio.
    """
    ingles = e.get("ingles") or {}
    sistema = e.get("sistema") or {}

    # Las tarjetas tienen que sumar el total, y no sumaban: faltaban las que
    # sacó el filtro, que eran 132 de 230. Se veía 10 + 84 + 4 y abajo "230 en
    # total", y la pregunta obvia era "¿230 qué?".
    partes = (e["sin_marcar"], e["aplicadas"], e["descartadas"], e["archivadas"],
              e.get("sistema_total") or 0)
    tarjetas = (
        _dato(e["sin_marcar"], "sin mirar", destacado=True)
        + _dato(e["aplicadas"], "aplicaste")
        + _dato(e["descartadas"], "descartaste")
        + _dato(e["archivadas"], "archivadas")
        + _dato(partes[4], "las sacó el filtro")
        + _dato(e["total"], "ofertas en total")
    )
    # La cuenta va escrita sólo si cierra. Una oferta archivada que además está
    # marcada contaría en dos tarjetas, y una suma que no da es peor que ninguna.
    suma = ""
    if e["total"] and sum(partes) == e["total"]:
        cuenta = " + ".join(str(p) for p in partes)
        suma = (f'<p class="explica">Cada oferta que entró está en una sola de '
                f'estas tarjetas: {cuenta} = {e["total"]}.</p>')

    analizadas = (habilidades or {}).get("ofertas") or 0
    sin_analizar = (habilidades or {}).get("sin_datos") or 0
    de_donde_analizadas = (f"de las {analizadas + sin_analizar} que entraron"
                           if sin_analizar else "")
    puntuadas = sum(t.get("cuantas") or 0 for t in (puntajes or []))

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

    # La pantalla cuenta tres cosas distintas y en este orden, que es el orden
    # en que sirven: qué hiciste, qué te piden ahí afuera, y qué está entrando.
    # Antes eran cinco paneles idénticos uno atrás del otro sin nada que dijera
    # cuál mirar primero, que es lo que la hacía confusa: todo pesaba igual.
    pedido = _habilidades(habilidades)
    foco = f"""<section class="foco">
  {_cabecera("Qué te están pidiendo",
             '''Las habilidades, herramientas y certificaciones que nombran los
             avisos, y en qué parte de ellos aparece cada una. <b>Es lo único de
             esta pantalla que dice qué hacer mañana</b>: lo que está arriba y no
             tenés es lo que más te está costando entrevistas.''',
             analizadas, "ofertas analizadas", de_donde_analizadas)}
  {pedido}
</section>""" if pedido else ""

    return f"""{avisos(mensajes)}
<h1>Métricas</h1>
<div class="tarjetas">{tarjetas}</div>
{suma}

{foco}

<h2 class="seccion">Qué está entrando, y qué queda afuera</h2>
<div class="paneles">
{_panel("Qué tan bien te encajan",
        '''Cuántas ofertas hay en cada tramo de puntaje, sobre todo lo que se
        buscó alguna vez. Una montaña pegada al cero significa que las búsquedas
        están mal apuntadas; una repartida significa que el problema es otro.''',
        _grafico_de_puntajes(puntajes),
        puntuadas, "ofertas puntuadas", "desde siempre" if desde != "todo" else "")}

{_panel("Por qué descartaste vos",
        '''Los motivos que elegiste al marcar <b>No apliqué</b>, medidos contra
        todas las que descartaste. Es lo único que el sistema puede aprender de
        vos: si la mayoría cae en un mismo motivo, ahí hay un filtro que conviene
        apretar en Mi perfil. Abajo, lo que escribiste a mano cuando ninguno de
        la lista servía.''',
        _desglose(("Motivo", "Ofertas"), motivos_filas,
                  total=e.get("descartadas") or 0)
        + _escritos_a_mano(e.get("escritos") or [], e.get("descartadas") or 0),
        e.get("descartadas") or 0, "descartaste")}

{_panel("Lo que descartó el sistema, sin preguntarte",
        '''Son las que no llegan a <b>Sin marcar</b> porque ya hay un veredicto:
        no las borra nadie y vuelven solas si cambiás el filtro que las sacó.''',
        _solapadas(e)
        + _desglose(("Motivo", "Ofertas"), sistema_filas)
        + _cuesta_el_ingles(perfil, ingles),
        e.get("sistema_total") or 0, "sacó el filtro")}

{_panel("De dónde vienen",
        f'''Qué portal trajo cada oferta, medido contra todas las que entraron.
        Ventana de búsqueda: los últimos
        {esc(ventana if ventana is not None else "?")} días, que se cambia en
        Configuración.''',
        _desglose(("Portal", "Ofertas"), fuentes, total=e.get("total") or 0),
        e.get("total") or 0, "ofertas que entraron")}
</div>

{_como_viene_funcionando(perfil, salud)}"""


# --- mensajes para el reclutador -------------------------------------------

def linea_de_cv(cv: dict | None, que: str) -> str:
    """"Mandá tu CV Full Stack", con la marca de estimado cuando corresponde.

    La usan la tarjeta, Consejo y Mensajes, así las tres pantallas lo dicen
    igual. Vacía cuando no hay CV que nombrar, que es el caso de un perfil con
    un solo CV: ahí la línea no dice nada que la persona no sepa.

    Va en texto secundario y **no en índigo**: es información, no se toca, y en
    este sistema el índigo significa que algo se puede apretar.
    """
    if not cv or not cv.get("nombre"):
        return ""
    marca = (' <span class="cv-estimado" title="Calculado comparando las palabras '
             'del aviso con cada CV, sin preguntarle al modelo">estimado</span>'
             if cv.get("estimado") else "")
    return f'<p class="cv-recomendado">{que} <b>{esc(cv["nombre"])}</b>{marca}</p>'


def mensajes(perfil: str, oferta: dict, textos: dict[str, str], con_llm: bool,
             avisos_: list[tuple[str, str]], cv_usado: dict | None = None) -> str:
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
{linea_de_cv(cv_usado, 'Escrito para tu CV')}
<p class="sub"><span class="dato-linea">{esc(titulo)}</span>
<a href="{esc(url)}" {ABRIR_EL_AVISO}>Ver el aviso en el portal</a></p>
<p class="herramientas"><a class="boton" href="/trabajos?perfil={esc(perfil)}">Volver a Trabajos</a></p>
{cajas}
{boton}
<p class="ayuda">Estos moldes son un borrador: máximo 4 líneas, cero adjetivos
sobre uno mismo, y cerrar con una pregunta fácil de responder.</p>"""


# --- consejo sobre el CV ----------------------------------------------------

def consejo(perfil: str, oferta: dict, faltantes: list[str], texto: str,
            con_llm: bool, avisos_: list[tuple[str, str]],
            cv_usado: dict | None = None) -> str:
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
{linea_de_cv(cv_usado, 'Comparando con tu CV')}
<p class="sub"><span class="dato-linea">{esc(titulo)}</span>
<span class="dato-linea">{esc(oferta.get('company') or 'sin empresa')}</span>
<a href="{esc(url)}" {ABRIR_EL_AVISO}>Ver el aviso en el portal</a></p>
<p class="herramientas"><a class="boton" href="/trabajos?perfil={esc(perfil)}">Volver a Trabajos</a></p>

<h2>Palabras del aviso que no están en tu CV</h2>
<div class="mensaje">{huecos}</div>

<h2>Qué mover</h2>
{cuerpo}
<p class="ayuda">Tu CV no se toca: esto es para que lo edites vos con criterio.</p>"""
