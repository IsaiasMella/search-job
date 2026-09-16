"""El cartel que dice en qué anda la búsqueda mientras corre.

La búsqueda tarda minutos y corre en otro proceso, así que la pantalla no puede
preguntarle nada: lo único que comparten es el registro. Estos tests arman un
registro falso etapa por etapa y verifican que salga la oración correcta.

Lo que se fija acá y no hay que perder:

* El progreso habla **de esta corrida**, no de la de ayer. Se lee desde el
  offset que se anotó al arrancar.
* Con `--all` el motor procesa un perfil atrás del otro. Al cambiar de perfil
  todos los contadores vuelven a cero, o el cartel mezcla dos corridas.
* Las etapas se pisan en orden: vale la más avanzada que ya apareció.
"""

import pytest

from vacantia.ui import corrida


@pytest.fixture
def registro(tmp_path, monkeypatch):
    """Un registro de mentira, y la corrida apuntada a él como si hubiera
    arrancado recién. Devuelve una función para ir agregándole líneas."""
    log = tmp_path / "vacantia.log"
    log.write_text("[2026-01-01 00:00:00] INFO    lo de ayer, que no cuenta\n",
                   encoding="utf-8")

    monkeypatch.setattr(corrida, "LOG", log)
    monkeypatch.setattr(corrida, "_desde_byte", log.stat().st_size)
    monkeypatch.setattr(corrida, "_arrancada", 1.0)
    monkeypatch.setattr(corrida, "esta_corriendo", lambda: True)

    def escribir(*mensajes):
        with log.open("a", encoding="utf-8") as f:
            for m in mensajes:
                f.write(f"[2026-01-01 10:00:00] INFO    {m}\n")

    return escribir


def test_recien_arrancada_no_inventa_una_etapa(registro):
    """Sin una sola línea todavía, dice que arrancó y no otra cosa."""
    assert corrida.progreso()["paso"] == "Arrancando la búsqueda"


def test_dice_en_que_fuente_esta_buscando(registro):
    registro("=== vacantia - perfil 'isaias' ===", "--- Fuente: LinkedIn Jobs ---")
    estado = corrida.progreso()
    assert estado["paso"] == "Buscando en LinkedIn Jobs"
    assert estado["perfil"] == "isaias"


def test_la_etapa_es_un_identificador_y_no_la_oracion(registro):
    """La oración cambia con la fuente y con el número de ofertas; el
    identificador no cambia nunca. Es lo que le permite al panel saber qué
    tramo ya pasó sin tener que adivinarlo del texto."""
    registro("--- Fuente: Getonbrd ---")
    assert corrida.progreso()["etapa"] == "fuentes"

    registro("Total recolectado: 125 oferta(s)")
    assert corrida.progreso()["etapa"] == "revisando"

    registro("Puntuando 78 oferta(s) con LLM (min_score=60)...")
    assert corrida.progreso()["etapa"] == "puntuando"

    registro("Filtros: 40 pasaron")
    assert corrida.progreso()["etapa"] == "filtrando"


def test_recien_arrancada_la_etapa_es_arranque(registro):
    """Todavía no empezó ningún tramo: el panel los dibuja todos por delante."""
    assert corrida.progreso()["etapa"] == "arranque"


def test_la_fuente_que_termina_no_borra_el_cartel(registro):
    """Entre que una fuente cierra y la próxima abre pasan milisegundos. Poner
    'esperando' ahí es un parpadeo, no información."""
    registro("--- Fuente: Getonbrd ---", "--- Getonbrd: 12 oferta(s) ---")
    assert corrida.progreso()["paso"] == "Buscando en Getonbrd"


def test_la_etapa_mas_avanzada_es_la_que_manda(registro):
    registro("--- Fuente: Getonbrd ---", "Total recolectado: 125 oferta(s)")
    assert corrida.progreso()["paso"] == "Revisando 125 ofertas"


def test_el_puntaje_muestra_cuantas_lleva_de_cuantas(registro):
    """Es la etapa larga (una llamada al modelo por lote) y la única donde se
    sabe el total de verdad. Por eso es la única que lleva números."""
    registro("Puntuando 78 oferta(s) con LLM (min_score=60)...",
             "[ 82] Data Scientist - encaja", "[  0] Vendedor - no encaja")
    estado = corrida.progreso()
    assert estado["paso"] == "Puntuando contra tu CV"
    assert (estado["hechas"], estado["total"]) == (2, 78)


def test_un_lote_reintentado_no_pasa_del_total(registro):
    """Si el modelo falla, el motor rehace el lote y las líneas se repiten. Sin
    tope se veía 'Puntuando 84 de 78', que es obviamente un bug en pantalla."""
    registro("Puntuando 2 oferta(s) con LLM (min_score=60)...",
             *[f"[ {n:2d}] Oferta - texto" for n in range(5)])
    assert corrida.progreso()["hechas"] == 2


def test_cambiar_de_perfil_reinicia_los_contadores(registro):
    """Con --all corre un perfil atrás del otro. Sin reiniciar, el segundo
    perfil arrancaba mostrando el puntaje del primero."""
    registro("=== vacantia - perfil 'isaias' ===",
             "Puntuando 40 oferta(s) con LLM (min_score=60)...",
             "[ 70] Una - texto",
             "=== vacantia - perfil 'mama' ===",
             "--- Fuente: Getonbrd ---")
    estado = corrida.progreso()
    assert estado["perfil"] == "mama"
    assert estado["paso"] == "Buscando en Getonbrd"
    assert (estado["hechas"], estado["total"]) == (0, 0)


def test_no_lee_lo_que_paso_antes_de_arrancar(registro):
    """La línea de ayer está en el archivo y no tiene que teñir nada."""
    registro("--- Fuente: Getonbrd ---")
    assert "ayer" not in corrida.progreso()["paso"]


def test_sin_corrida_no_hay_paso(registro, monkeypatch):
    """Con el proceso muerto el cartel vuelve al botón, y no se lee el archivo."""
    monkeypatch.setattr(corrida, "esta_corriendo", lambda: False)
    registro("--- Fuente: Getonbrd ---")
    estado = corrida.progreso()
    assert estado["corriendo"] is False
    assert estado["paso"] == ""


def test_un_registro_rotado_no_rompe(registro, monkeypatch):
    """Si alguien borra vacantia.log en el medio, el offset viejo apunta más
    allá del final. Antes eso leía basura; ahora simplemente no hay progreso."""
    monkeypatch.setattr(corrida, "_desde_byte", 10_000_000)
    assert corrida.progreso()["paso"] == "Arrancando la búsqueda"


# --- el cartel que se dibuja con todo eso -----------------------------------

def _cartel(**kw):
    from vacantia.ui import render

    base = {"perfil": "ana", "paso": {"corriendo": False}, "marca": "m",
            "pendientes": 3}
    return render.corrida_estado(**{**base, **kw})


def test_el_ritmo_del_latido_lo_manda_el_fragmento():
    """Mientras busca pregunta cada 2 segundos; quieto, cada 15.

    El intervalo viaja en el HTML que vuelve, no en el JavaScript: por eso se
    acelera solo al arrancar la búsqueda y se afloja solo al terminar, sin una
    línea de código nuestro. Si esto se rompe, quieto quedan 1800 pedidos por
    hora contra el disco y el registro se llena de ruido.
    """
    assert 'hx-trigger="every 15s"' in _cartel()
    assert 'hx-trigger="every 2s"' in _cartel(paso={"corriendo": True, "paso": "x"})


def test_mientras_busca_no_ofrece_buscar_de_nuevo():
    """Los límites del plan gratis son de la cuenta, no del perfil."""
    corriendo = _cartel(paso={"corriendo": True, "paso": "Buscando en Indeed"})
    assert "Buscar ahora" not in corriendo
    assert "Buscando en Indeed" in corriendo


def test_sin_total_no_inventa_un_numero():
    """Durante las fuentes no se sabe cuántas van a entrar. Un "3 de 10" ahí
    sería mentira, así que en esa etapa el segundo renglón dice el perfil."""
    html = _cartel(paso={"corriendo": True, "paso": "Buscando en Indeed",
                         "perfil": "ana", "total": 0})
    assert "de" not in html.split('class="detalle"')[1].split("<")[0]
    assert "Perfil ana" in html


def test_el_aviso_distingue_ofertas_nuevas_de_lista_cambiada():
    """No es lo mismo que entren ofertas a que la lista cambie.

    Una corrida puede traer veinte avisos y que los veinte se caigan por filtro,
    o podés estar marcando desde otra pestaña: el número no sube pero lo que
    estás mirando ya no es lo que hay. Antes ese caso no avisaba nada.
    """
    assert "Entraron 4 ofertas nuevas" in _cartel(nuevas=4, cambio=True)
    assert "Entró 1 oferta nueva" in _cartel(nuevas=1, cambio=True)

    cambiada = _cartel(nuevas=0, cambio=True)
    assert "La lista cambió" in cambiada
    # Y el botón acompaña: "Ver las nuevas" abajo de "La lista cambió" promete
    # ofertas que a lo mejor no hay.
    assert "Actualizar" in cambiada and "Ver las nuevas" not in cambiada


def test_sin_cambios_el_aviso_vuelve_vacio_de_verdad():
    """Vacío, no escondido. Si volviera el cartel escondido, pisaría al que la
    persona está mirando y el aviso desaparecería solo a los dos segundos."""
    assert "novedades" not in _cartel(nuevas=0, cambio=False)


def test_el_aviso_nunca_recarga_solo():
    """Si alguien está escribiendo el motivo de un descarte, una recarga se lo
    borra. Avisa, y decide la persona: la recarga la dispara el botón."""
    html = _cartel(nuevas=4, cambio=True)
    assert 'onclick="location.reload()"' in html
    assert "hx-trigger" in html                  # el reloj sigue, pero sólo pregunta


# --- el panel grande de arriba del contenido --------------------------------
#
# El cartel del pie dice lo mismo en dos renglones de texto chico, y ese era el
# problema: al costado del campo visual y en cuerpo 12, arrancar una búsqueda y
# que no pasara nada visible se sentía igual que apretar un botón roto.

def _panel(**paso):
    from vacantia.ui import render

    return render.panel_de_busqueda({"corriendo": True, **paso})


def test_el_panel_marca_los_tramos_cumplidos_el_actual_y_los_que_faltan():
    """Los tres estados tienen que verse distintos, o la fila de tramos no dice
    nada más que "hay cuatro etapas"."""
    html = _panel(paso="Puntuando contra tu CV", etapa="puntuando")
    tramos = html.split('<ol class="tramos">')[1].split("</ol>")[0]

    # Portales y Revisión ya pasaron, Puntaje es el de ahora, Filtros falta.
    assert tramos.count('class="hecho"') == 2
    assert tramos.count('class="activo"') == 1
    assert tramos.count('class="pendiente"') == 1
    assert tramos.index("Portales") < tramos.index("Puntaje") < tramos.index("Filtros")


def test_los_tramos_salen_de_las_etapas_del_motor():
    """Y no de una lista escrita en `render`. Si mañana el motor gana o pierde
    una etapa, se toca en un solo lado."""
    html = _panel(paso="Arrancando la búsqueda", etapa="arranque")
    for _, nombre in corrida.ETAPAS:
        assert f"<span>{nombre}</span>" in html


def test_recien_arrancada_ningun_tramo_esta_cumplido():
    html = _panel(paso="Arrancando la búsqueda", etapa="arranque")
    assert 'class="hecho"' not in html
    assert html.count('class="pendiente"') == len(corrida.ETAPAS)


def test_sin_total_la_barra_va_sin_porcentaje():
    """Durante las fuentes no se sabe cuántas ofertas van a entrar. Una barra
    clavada en 40% durante dos minutos es peor que una que no promete nada."""
    html = _panel(paso="Buscando en Getonbrd", etapa="fuentes", perfil="ana")
    assert "indefinida" in html
    assert "aria-valuenow" not in html
    assert "Perfil ana" in html


def test_durante_el_puntaje_la_barra_se_llena_de_verdad():
    """Es la única etapa donde el total se sabe con exactitud."""
    html = _panel(paso="Puntuando contra tu CV", etapa="puntuando",
                  hechas=39, total=78)
    assert "indefinida" not in html
    assert 'aria-valuenow="39"' in html and 'aria-valuemax="78"' in html
    assert "width: 50%" in html
    assert "39 de 78" in html


def test_un_lote_reintentado_no_desborda_la_barra():
    """`hechas` viene topeado desde `progreso`, pero si algún día no lo
    estuviera, la barra igual no se pasa del ancho del contenedor."""
    html = _panel(paso="Puntuando contra tu CV", etapa="puntuando",
                  hechas=90, total=78)
    assert "width: 100%" in html


def test_sin_corrida_el_panel_vuelve_vacio_de_verdad():
    """Vacío, no escondido con una clase. Es el único elemento de la pantalla
    que tiene que poder *desaparecer* solo cuando la búsqueda termina, y el CSS
    lo saca del layout con `:empty`. El contenedor tiene que quedar igual: si
    volviera vacío del todo, el reemplazo no tendría a qué apuntar y el panel
    quedaría clavado hasta que alguien recargue."""
    from vacantia.ui import render

    vacio = render.panel_de_busqueda({"corriendo": False})
    assert vacio == '<div class="buscando" id="buscando"></div>'


def test_el_tiempo_se_dice_en_minutos_y_no_con_el_segundero_corriendo():
    """El segundero al lado de una barra que no avanza es lo que hace que cinco
    minutos se sientan veinte. Lo que el número contesta es si arrancó recién o
    hace un rato."""
    from vacantia.ui.render import _cuanto_hace

    assert _cuanto_hace(0) == "recién arrancó"
    assert _cuanto_hace(59) == "recién arrancó"
    assert _cuanto_hace(60) == "hace 1 minuto"
    assert _cuanto_hace(84) == "hace 1 minuto"
    assert _cuanto_hace(200) == "hace 3 minutos"


def test_un_solo_pedido_actualiza_el_cartel_y_el_panel():
    """Los dos viven en lugares distintos de la pantalla y se actualizan con la
    misma respuesta: el cartel al pie de la barra lateral por el camino normal,
    y el panel de arriba del contenido marcado para pisar al que ya está."""
    html = _cartel(paso={"corriendo": True, "paso": "Puntuando contra tu CV",
                         "etapa": "puntuando"})
    panel = html.split('<div class="buscando"')[1]
    assert 'hx-swap-oob="true"' in panel.split(">")[0]


def test_al_terminar_la_respuesta_trae_el_panel_vacio():
    """Es lo que lo hace desaparecer en el mismo pedido en que la búsqueda
    termina, sin que nadie recargue."""
    html = _cartel(paso={"corriendo": False})
    assert '<div class="buscando" id="buscando" hx-swap-oob="true"></div>' in html


def test_la_pagina_no_deja_dos_elementos_con_el_mismo_id():
    """El panel lo pone `pagina()` adentro de `main`; el cartel del pie, en el
    armado inicial, no lo manda. Con dos `id="buscando"`, htmx pisa el que no
    es."""
    from vacantia.ui import render

    paso = {"corriendo": True, "paso": "Buscando en Getonbrd", "etapa": "fuentes"}
    estado = {"ultima": "hace 6 horas", "proxima": "hoy 23:59", "ventana": 7,
              "paso": paso, "marca": "m", "pendientes": 3}
    html = render.pagina("Trabajos", "<h1>Trabajos</h1>", "ana", ["ana"],
                         "trabajos", estado)
    assert html.count('id="buscando"') == 1
    # Y va adentro del contenido, no de la barra lateral: es lo que lo pone
    # adelante del campo visual, que es todo el punto del panel.
    assert '<main id="contenido"><div class="buscando"' in html


def test_la_pagina_sin_busqueda_igual_deja_el_hueco():
    """Vacío no se ve ni ocupa, pero tiene que existir: es el lugar donde el
    cartel del pie va a ir a poner el panel cuando la búsqueda arranque."""
    from vacantia.ui import render

    html = render.pagina("Trabajos", "<h1>Trabajos</h1>", "ana", ["ana"],
                         "trabajos", None)
    assert '<div class="buscando" id="buscando"></div>' in html
