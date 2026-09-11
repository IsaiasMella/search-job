"""El contador de postulaciones y los gráficos de Métricas.

Los gráficos se dibujan con HTML y los tokens del sistema, sin librería ni SVG:
una barra es un `div` con un ancho en porcentaje. Estos tests miran que el
marcado diga lo que tiene que decir; que se vea bien hay que mirarlo en la
pantalla, y eso se hizo.
"""

from datetime import datetime, timedelta, timezone

from vacantia.ui import data
from vacantia.ui.graficos import MINIMO_PARA_GRAFICAR, barras, columnas, vale_un_grafico

# El fixture `sitio` y los helpers viven en test_ui: una sola instalación de
# juguete para todos los tests de pantalla, en vez de dos que se desincronizan.
from tests.test_ui import HOY_ISO, _con_historial, get, sitio  # noqa: F401


# --- cuándo se gana un gráfico el lugar -------------------------------------

def test_con_dos_filas_la_tabla_dice_lo_mismo_mejor():
    """Un gráfico se gana el lugar cuando hay varias magnitudes que comparar.

    Con dos filas no hay comparación, hay dos números, y para dos números la
    tabla ocupa menos y se lee más rápido.
    """
    assert vale_un_grafico([("a", 5), ("b", 3)]) is False
    assert vale_un_grafico([("a", 5), ("b", 3), ("c", 1)]) is True
    # Las filas en cero no cuentan: no hay nada que comparar contra nada.
    assert vale_un_grafico([("a", 5), ("b", 0), ("c", 0)]) is False
    assert vale_un_grafico([]) is False
    assert MINIMO_PARA_GRAFICAR == 3


def test_metricas_usa_grafico_o_tabla_segun_el_caso(sitio):
    """Y cuando hay gráfico, la tabla sigue estando debajo, plegada.

    Un gráfico no da el valor exacto ni se puede copiar, y a veces lo que se
    quiere es justamente el número.
    """
    from vacantia.ui.render import _desglose

    dos = _desglose(("Motivo", "Ofertas"), [("Piden inglés", 40), ("El lugar", 22)])
    assert "<table" in dos and 'class="barras"' not in dos

    cuatro = _desglose(("Motivo", "Ofertas"),
                       [("a", 40), ("b", 22), ("c", 9), ("d", 3)])
    assert 'class="barras"' in cuatro
    assert "<table" in cuatro                       # la tabla no desaparece
    assert "Ver los números" in cuatro


# --- las barras -------------------------------------------------------------

def test_las_barras_van_de_mayor_a_menor_y_con_el_valor_al_lado():
    """El largo sirve para comparar de un vistazo; el número evita tener que
    estimarlo contra una grilla."""
    html = barras([("Poco", 10), ("Mucho", 50), ("Medio", 25)])
    assert html.index("Mucho") < html.index("Medio") < html.index("Poco")
    # La más grande llena el riel, el resto en proporción.
    assert "--ancho:100.0%" in html
    assert "--ancho:50.0%" in html                  # 25 de 50
    assert '<span class="barra-valor">50</span>' in html
    # Y el detalle al pasar por encima, sin JavaScript.
    assert 'title="50 ofertas, 59% de 85"' in html


def test_una_barra_en_cero_no_se_dibuja():
    """Una fila sin datos ocupa un renglón para no decir nada."""
    assert barras([("Nada", 0)]) == ""
    html = barras([("Algo", 5), ("Nada", 0)])
    assert "Algo" in html and "Nada" not in html


def test_las_columnas_respetan_el_orden_del_eje():
    """Van en columnas justamente porque el eje tiene un orden propio.

    Los tramos de puntaje van de 0 a 100 y las semanas de la más vieja a la más
    nueva: ordenarlos por magnitud, como hace `barras`, destruiría lo único que
    estos gráficos tienen para decir.
    """
    html = columnas([{"etiqueta": "0", "cuantas": 38},
                     {"etiqueta": "1 a 19", "cuantas": 3},
                     {"etiqueta": "80 a 100", "cuantas": 32, "destacada": True}])
    assert html.index(">0<") < html.index(">1 a 19<") < html.index(">80 a 100<")
    assert "destacada" in html


def test_una_columna_en_cero_se_dibuja_igual():
    """Un hueco en el eje se lee como "acá no hay dato", y acá el cero ES el
    dato: una semana sin postulaciones es justamente lo que hay que ver.

    Pero no en verde: no hay nada que celebrar y el color llamaba la atención
    sin tener nada que decir.
    """
    html = columnas([{"etiqueta": "7/8", "cuantas": 0},
                     {"etiqueta": "14/8", "cuantas": 9}])
    assert html.count("columna-relleno") == 2
    assert "columna vacia" in html


# --- el contador de postulaciones -------------------------------------------

def _aplicada(url, cuando):
    return {"url": url, "title": f"Oferta {url}", "score": 80, "aplicado": True,
            "fecha_feedback": cuando.astimezone(timezone.utc).isoformat(),
            "found_at": cuando.astimezone(timezone.utc).isoformat()}


def test_cuenta_las_postulaciones_del_periodo_elegido(sitio):
    base, tmp = sitio
    ahora = datetime.now().astimezone()
    _con_historial(tmp, [
        _aplicada("hoy", ahora),
        _aplicada("hace5", ahora - timedelta(days=5)),
        _aplicada("hace20", ahora - timedelta(days=20)),
        _aplicada("hace70", ahora - timedelta(days=70)),
    ])
    assert data.aplicadas_en("test", "7d")["cuantas"] == 2
    assert data.aplicadas_en("test", "30d")["cuantas"] == 3
    assert data.aplicadas_en("test", "90d")["cuantas"] == 4
    assert data.aplicadas_en("test", "todo")["cuantas"] == 4
    # Un período inventado cae en el de siempre y no rompe.
    assert data.aplicadas_en("test", "cualquiera")["periodo"] == data.PERIODO_POR_DEFECTO


def test_la_fecha_de_postulacion_se_lee_en_la_hora_de_aca(sitio):
    """Se guarda en UTC. Entre las 21:00 y la medianoche el UTC ya es de mañana,
    y sin convertir, una postulación de hoy contaba para el día siguiente."""
    base, tmp = sitio
    ahora = datetime.now().astimezone()
    _con_historial(tmp, [_aplicada("ahora", ahora)])
    resultado = data.aplicadas_en("test", "7d")
    assert resultado["cuantas"] == 1
    # Y cae en la última semana del reparto, no en la siguiente.
    assert resultado["por_semana"][-1][1] == 1


def test_el_reparto_por_semana_es_lo_que_hace_que_el_total_signifique_algo(sitio):
    """12 postulaciones en un mes puede ser tres semanas sin hacer nada y una a
    los tiros. Eso no se ve en el total."""
    base, tmp = sitio
    ahora = datetime.now().astimezone()
    _con_historial(tmp, [_aplicada(f"n{i}", ahora) for i in range(9)])
    resultado = data.aplicadas_en("test", "30d")
    assert resultado["cuantas"] == 9
    semanas = resultado["por_semana"]
    assert len(semanas) == 5                       # 30 días, redondeado a semanas
    assert semanas[-1][1] == 9                     # todas en la de esta semana
    assert sum(n for _, n in semanas[:-1]) == 0


def test_el_contador_va_grande_en_verde_y_solo_en_sin_marcar(sitio):
    """Es lo único de la app que mide el trabajo de la persona y no el del
    sistema, así que es lo más grande de la pantalla.

    Y va sólo en Sin marcar: en Filtradas ya está el marcador de la auditoría,
    y dos marcadores en la misma pantalla no se leen, compiten.
    """
    base, tmp = sitio
    ahora = datetime.now().astimezone()
    _con_historial(tmp, [_aplicada(f"n{i}", ahora) for i in range(3)])

    _, home, _ = get(base, "/trabajos?perfil=test&ver=pendientes")
    assert 'class="postulaciones"' in home
    assert '<span class="numero">3</span>' in home
    assert "trabajos a los que apliqué" in home    # el color nunca va solo
    assert "Último mes" in home                     # el período, a la vista

    for otra in ("aplicadas", "descartadas", "filtradas", "archivadas", "todas"):
        assert 'class="postulaciones"' not in get(
            base, f"/trabajos?perfil=test&ver={otra}")[1], otra


def test_sin_postulaciones_dice_como_empezar(sitio):
    """Un cero gigante sin explicación se lee como un reproche."""
    base, tmp = sitio
    _con_historial(tmp, [{"url": "https://e/1", "title": "Una", "aplicado": None,
                          "score": 70, "found_at": HOY_ISO}])
    _, html, _ = get(base, "/trabajos?perfil=test")
    assert '<span class="numero">0</span>' in html
    assert "Todavía no marcaste ninguna en este" in html
    assert "el número empieza a subir" in html


def test_el_selector_de_periodo_anda_sin_javascript(sitio):
    """Es un `form method=get` con su botón, que el `onchange` sólo adelanta."""
    base, tmp = sitio
    ahora = datetime.now().astimezone()
    _con_historial(tmp, [_aplicada("hace20", ahora - timedelta(days=20))])

    _, mes, _ = get(base, "/trabajos?perfil=test&apliq=30d")
    assert '<span class="numero">1</span>' in mes
    _, semana, _ = get(base, "/trabajos?perfil=test&apliq=7d")
    assert '<span class="numero">0</span>' in semana
    assert "<noscript><button>Ver el período</button></noscript>" in semana
    # El período viaja con el resto de los filtros, no los pisa.
    assert '<input type="hidden" name="ver" value="pendientes">' in semana


# --- el histograma de puntajes ----------------------------------------------

def test_el_histograma_marca_de_donde_para_arriba_te_avisa(sitio):
    """Es el único tramo con color distinto, y lo lleva porque significa algo:
    de ahí para arriba el sistema manda el Telegram."""
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": f"https://e/{i}", "title": f"O{i}", "aplicado": None,
         "score": s, "found_at": HOY_ISO}
        for i, s in enumerate((0, 10, 30, 50, 70, 90, 95))
    ])
    tramos = data.distribucion_de_puntajes("test")
    assert [t["cuantas"] for t in tramos] == [1, 1, 1, 1, 1, 2]
    # min_score del perfil de prueba: de ahí para arriba, destacado.
    avisan = [t["etiqueta"] for t in tramos if t["avisa"]]
    assert avisan == ["60 a 79", "80 a 100"]

    _, html, _ = get(base, "/estadisticas?perfil=test")
    assert "Qué tan bien te encajan las ofertas" in html
    assert 'class="columna destacada"' in html
    assert "el sistema te avisa por Telegram" in html


def test_sin_ofertas_puntuadas_no_dibuja_un_grafico_vacio(sitio):
    base, tmp = sitio
    _con_historial(tmp, [])
    _, html, _ = get(base, "/estadisticas?perfil=test")
    assert "Todavía no hay ofertas puntuadas" in html
    assert 'class="columnas"' not in html


# --- los tokens nuevos ------------------------------------------------------

def test_los_tokens_de_datos_existen_y_no_son_valores_sueltos():
    """DESIGN.md no trae ninguno para gráficos, así que hubo que proponerlos.

    Son pocos porque todos los gráficos de la app son de una sola serie: la
    magnitud la lleva el largo de la barra, no el tono. No hay paleta
    categórica que validar ni leyenda que poner.
    """
    import re

    from vacantia.ui.estilos import CSS, TOKENS

    for token in ("--data-fill", "--data-track", "--data-destacada", "--text-hero"):
        assert f"{token}:" in TOKENS, token

    # Y las reglas los usan por nombre, sin escribir un color propio. Se busca
    # la definición base, la que arranca el renglón: `.columna-relleno` también
    # aparece dentro de `.postulaciones`, donde la pisa a propósito con el verde.
    for bloque in (".barra-relleno", ".columna-relleno"):
        regla = CSS[CSS.index(chr(10) + bloque + " {"):]
        regla = regla[:regla.index("}")]
        assert "var(--data-" in regla, bloque
        assert not re.search(r"#[0-9A-Fa-f]{3,8}\b", regla), bloque
