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


def test_con_total_la_barra_entera_es_el_total_y_dice_que_parte_es():
    """"Piden inglés 51" no decía de cuántas.

    Medidas contra la fila más grande, la de arriba salía siempre llena: 9 que
    no son ofertas se dibujaba igual sobre 60 descartes que sobre 200, y en un
    caso es muchísimo y en el otro no es nada.
    """
    html = barras([("Piden inglés", 51), ("No es una oferta", 9)], total=84)
    assert "--ancho:60.7%" in html                  # 51 de 84, no la barra llena
    assert "--ancho:10.7%" in html
    assert '<span class="barra-valor">51</span><span class="barra-parte">61%</span>' in html
    assert '<span class="barra-parte">11%</span>' in html
    assert 'class="barras con-parte"' in html
    # Una que existe nunca dice 0%, y el "<" va escapado.
    assert '<span class="barra-parte">&lt;1%</span>' in barras([("Rara", 1)], total=300)
    # Sin total sigue como antes: la más grande llena el riel y no hay parte.
    sin_total = barras([("a", 5), ("b", 3)])
    assert "barra-parte" not in sin_total and "--ancho:100.0%" in sin_total


def test_que_te_piden_y_de_donde_vienen_se_miden_contra_el_total(sitio):
    """"Python 161, AWS 45" no decía de cuántas.

    Sobre 200 ofertas AWS es algo que hay que aprender; sobre 1000, un bueno de
    tener. Las habilidades se miden contra las ofertas analizadas y los
    portales contra todas las que entraron, y cada panel dice cuántas son.
    """
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": f"https://e/{i}", "title": f"Oferta {i}", "aplicado": None,
         "score": 70, "found_at": HOY_ISO,
         "source": "linkedin" if i < 3 else "indeed",
         "stack": "Python, AWS" if i == 0 else "Python"}
        for i in range(4)
    ])

    _, html, _ = get(base, "/estadisticas?perfil=test")
    assert '<span class="numero">4</span><span class="que">ofertas analizadas</span>' in html
    assert '<span class="numero">4</span><span class="que">ofertas que entraron</span>' in html
    assert '<span class="barra-parte">100%</span>' in html     # Python, 4 de 4
    assert '<span class="barra-parte">75%</span>' in html      # linkedin, 3 de 4
    assert '<span class="barra-parte">25%</span>' in html      # AWS e indeed


def test_las_tarjetas_suman_el_total_y_cada_bloque_dice_contra_cuantas():
    """"¿230 qué?"

    Arriba se veían 10 aplicadas, 84 descartadas y 4 archivadas, y al lado "230
    en total": faltaban las 132 que sacó el filtro, y la suma no cerraba. Y
    abajo "219 ofertas analizadas" era una frase suelta entre la explicación y
    el gráfico. Ahora cada bloque lleva su total en grande del otro lado del
    título, y dice de dónde sale cuando no es obvio.
    """
    from vacantia.ui import render

    e = {"sin_marcar": 0, "aplicadas": 10, "descartadas": 84, "archivadas": 4,
         "sistema_total": 132, "total": 230, "ingles": {},
         "sistema": {"idioma": 132}, "motivos": {"ingles": 84},
         "por_fuente": {"linkedin": 230}, "max_age_days": 7}
    habilidades = {"filas": [("Python", 161)], "ofertas": 219, "sin_datos": 11}
    html = render.estadisticas("ana", e, "todo", [], habilidades=habilidades)

    assert "las sacó el filtro" in html
    assert "0 + 10 + 84 + 4 + 132 = 230" in html
    assert html.count('class="panel-cabeza"') == 5     # foco y los cuatro paneles
    assert ('<span class="numero">219</span><span class="que">ofertas analizadas</span>'
            '<span class="de-donde">de las 230 que entraron</span>') in html
    assert '<span class="numero">132</span><span class="que">sacó el filtro</span>' in html
    assert "La barra entera" not in html               # el renglón viejo se fue

    # Si la cuenta no cierra, no se escribe: una suma que no da es peor.
    assert "0 + 10 + 84" not in render.estadisticas("ana", {**e, "total": 231},
                                                    "todo", [])


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
    assert resultado["reparto"][-1][1] == 1


def test_el_reparto_por_semana_es_lo_que_hace_que_el_total_signifique_algo(sitio):
    """12 postulaciones en un mes puede ser tres semanas sin hacer nada y una a
    los tiros. Eso no se ve en el total."""
    base, tmp = sitio
    ahora = datetime.now().astimezone()
    _con_historial(tmp, [_aplicada(f"n{i}", ahora) for i in range(9)])
    resultado = data.aplicadas_en("test", "30d")
    assert resultado["cuantas"] == 9
    semanas = resultado["reparto"]
    assert len(semanas) == 5                       # 30 días, redondeado a semanas
    assert semanas[-1][1] == 9                     # todas en la de esta semana
    assert sum(n for _, n in semanas[:-1]) == 0


def test_el_contador_va_grande_en_verde_en_sin_marcar(sitio):
    """Es lo único de la app que mide el trabajo de la persona y no el del
    sistema, así que es lo más grande de la pantalla.
    """
    base, tmp = sitio
    ahora = datetime.now().astimezone()
    _con_historial(tmp, [_aplicada(f"n{i}", ahora) for i in range(3)])

    _, home, _ = get(base, "/trabajos?perfil=test&ver=pendientes")
    assert 'class="postulaciones"' in home
    assert '<span class="numero">3</span>' in home
    assert "trabajos a los que apliqué" in home    # el color nunca va solo
    assert "Último mes" in home                     # el período, a la vista


def test_el_cartel_de_arriba_habla_de_la_pestania_en_la_que_estas(sitio):
    """El número de arriba y la lista de abajo tienen que ser lo mismo.

    Parado en Apliqué el cartel decía 11 y abajo había 9 tarjetas, porque sumaba
    las que se cuentan a mano desde un posteo de LinkedIn. Un cartel más grande
    que la lista que tiene debajo se lee como un error de la app.

    En Archivadas y Todas no va ningún cartel: no hay una pregunta que contestar
    ahí arriba. En Filtradas tampoco, porque ya está el marcador de la auditoría
    y dos marcadores en la misma pantalla no se leen, compiten.
    """
    base, tmp = sitio
    ahora = datetime.now().astimezone()
    _con_historial(tmp, [_aplicada(f"n{i}", ahora) for i in range(3)])

    _, aplique, _ = get(base, "/trabajos?perfil=test&ver=aplicadas")
    assert 'class="postulaciones"' in aplique
    assert '<span class="numero">3</span>' in aplique
    assert "sólo las de esta lista" in aplique
    # Y sigue habiendo selector de período: es la misma pregunta, otro recorte.
    assert "Último mes" in aplique

    for otra in ("filtradas", "archivadas", "todas"):
        assert 'class="postulaciones"' not in get(
            base, f"/trabajos?perfil=test&ver={otra}")[1], otra


def test_en_descarte_el_cartel_dice_por_que_y_no_cuantas(sitio):
    """El total de descartes solo no sirve para nada.

    Lo accionable es el desglose: si la mayoría cae por inglés, eso es una
    perilla de Mi perfil esperando que la muevan. Y no va en verde, porque el
    verde acá significa lo que ya hiciste y descartar no es un logro.
    """
    ahora = datetime.now().astimezone().isoformat()
    base, tmp = sitio
    _con_historial(tmp, [
        {"url": f"https://e/i{i}", "title": "Con inglés", "aplicado": False,
         "motivo_clave": "ingles", "fecha_feedback": ahora, "found_at": HOY_ISO}
        for i in range(4)
    ] + [
        {"url": "https://e/p", "title": "Presencial", "aplicado": False,
         "motivo_clave": "presencial", "fecha_feedback": ahora, "found_at": HOY_ISO},
        {"url": "https://e/m", "title": "A mano", "aplicado": False,
         "motivo_descarte": "pide .NET", "fecha_feedback": ahora,
         "found_at": HOY_ISO},
    ])

    _, html, _ = get(base, "/trabajos?perfil=test&ver=descartadas")

    assert 'class="postulaciones descartes"' in html
    assert '<span class="numero">6</span>' in html
    assert "ofertas que descarté" in html
    # El desglose, que es lo único accionable de todo esto.
    assert "Piden inglés" in html
    assert "Es presencial y no puedo ir" in html
    # El texto libre no es "otro": es el descarte que dice algo del puesto.
    assert "Escrito a mano" in html
    assert "Último mes" in html


def test_metricas_muestra_lo_que_escribiste_a_mano(sitio):
    """La barra "Escrito a mano" sola dice cuántas, no qué.

    Isaías sospechaba que se colaban posteos de LinkedIn que no son ofertas y no
    tenía cómo confirmarlo sin leer las frases. Van en barras, como el gráfico de
    motivos de arriba, aunque sean dos. Las que dicen lo mismo con otra
    mayúscula o un punto de más se cuentan juntas; las que salieron de la lista
    no aparecen, porque ya tienen su barra y se contarían dos veces.
    """
    ahora = datetime.now().astimezone().isoformat()
    base, tmp = sitio

    def descarte(i, **motivo):
        return {"url": f"https://e/{i}", "title": f"Oferta {i}", "aplicado": False,
                "fecha_feedback": ahora, "found_at": HOY_ISO, **motivo}

    _con_historial(tmp, [
        descarte(1, motivo_descarte="Es un puesto Jr y yo solo busco SR"),
        descarte(2, motivo_descarte="es un puesto jr y yo solo busco  SR."),
        descarte(3, motivo_descarte="ES UN PUESTO JR Y YO SOLO BUSCO SR"),
        descarte(4, motivo_descarte="pide .NET"),
        descarte(5, motivo_clave="ingles", motivo_descarte="y encima pide viajar"),
        # Escrita a mano, pero ya tiene su lugar en la lista.
        descarte(6, motivo_descarte="No era una oferta"),
    ])

    filas = data.estadisticas("test")["escritos"]
    assert [n for _, n in filas] == [3, 1]
    assert filas[1] == ("pide .NET", 1)
    textos = " ".join(texto for texto, _ in filas)
    assert "viajar" not in textos and "oferta" not in textos

    _, html, _ = get(base, "/estadisticas?perfil=test")
    assert "Lo que escribiste a mano" in html
    assert '<span class="barra-nombre">pide .NET</span>' in html
    assert "viajar" not in html

    # Todo se mide contra los 6 descartes, y el panel lo dice. Las frases a mano
    # también: las 3 del Jr son la mitad de los descartes, no 3 de 4 escritas.
    assert '<span class="numero">6</span><span class="que">descartaste</span>' in html
    assert '<span class="barra-parte">67%</span>' in html   # Escrito a mano, 4 de 6
    assert '<span class="barra-parte">17%</span>' in html   # Piden inglés, 1 de 6
    assert '<span class="barra-parte">50%</span>' in html   # el Jr, 3 de 6
    assert '<span class="barra-parte">75%</span>' not in html


def test_como_viene_funcionando_muestra_las_ofertas_nuevas_por_dia(sitio):
    """Una búsqueda en cero puede ser un mal día; varios días seguidos en cero
    es que algo dejó de andar, y eso la tabla de la última búsqueda no lo dice.

    Sale del historial y no del registro, que comparten todos los perfiles y
    los tests. Los días sin nada van igual, porque acá el cero es el dato.
    """
    base, tmp = sitio
    ahora = datetime.now().astimezone()

    def entro(url, cuando):
        return {"url": url, "title": url, "aplicado": None,
                "found_at": cuando.astimezone(timezone.utc).isoformat()}

    _con_historial(tmp, [entro(f"hoy{i}", ahora) for i in range(3)] + [
        entro("ayer", ahora - timedelta(days=1)),
        entro("vieja", ahora - timedelta(days=40)),
    ])

    dias = data.entradas_por_dia("test")
    assert len(dias) == data.DIAS_DE_ENTRADAS
    assert [d["cuantas"] for d in dias[-2:]] == [1, 3]
    assert sum(d["cuantas"] for d in dias) == 4        # la de hace 40 días no entra
    hoy = ahora.date()
    assert dias[-1]["etiqueta"] == f"{hoy.day}/{hoy.month}"

    _, html, _ = get(base, "/estadisticas?perfil=test")
    assert "Ofertas nuevas por día" in html


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
    # El título es corto porque el capítulo de arriba ya da el contexto:
    # "Qué está entrando, y qué queda afuera".
    assert "Qué tan bien te encajan" in html
    assert "Qué está entrando, y qué queda afuera" in html
    assert 'class="columna destacada"' in html
    assert "el sistema te avisa por Telegram" in html


def test_sin_ofertas_puntuadas_no_dibuja_un_grafico_vacio(sitio):
    base, tmp = sitio
    _con_historial(tmp, [])
    _, html, _ = get(base, "/estadisticas?perfil=test")
    assert "Todavía no hay ofertas puntuadas" in html
    assert 'class="columnas"' not in html
    # Tampoco el de ofertas nuevas por día: dos semanas en cero se dicen.
    assert "No entró ninguna oferta nueva en las últimas dos semanas" in html


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


def test_una_semana_se_reparte_por_dia_y_no_por_semana(sitio):
    """Siete días repartidos en semanas daban UNA barra, y una barra sola no
    compara con nada: la tarjeta quedaba con el número grande y un vacío al
    lado. Por día son siete barras y contestan lo que se pregunta en una semana,
    que es qué días mandaste y cuáles se te fueron en blanco."""
    base, tmp = sitio
    ahora = datetime.now().astimezone()
    _con_historial(tmp, [_aplicada(f"n{i}", ahora) for i in range(3)])

    semana = data.aplicadas_en("test", "7d")
    assert semana["unidad"] == "día"
    assert len(semana["reparto"]) == 7
    assert semana["reparto"][-1][1] == 3           # las tres son de hoy
    assert sum(n for _, n in semana["reparto"]) == 3

    # De 14 días para arriba vuelve a ser por semana: catorce o noventa barras
    # diarias no se leen, y ahí la pregunta ya es la del ritmo.
    for periodo, barras in (("14d", 2), ("30d", 5), ("90d", 12), ("todo", 12)):
        largo = data.aplicadas_en("test", periodo)
        assert largo["unidad"] == "semana", periodo
        assert len(largo["reparto"]) == barras, periodo

    # Y nunca una barra sola: no hay período que no se pueda comparar consigo.
    for clave, _, _ in data.PERIODOS:
        assert len(data.aplicadas_en("test", clave)["reparto"]) >= 2, clave


def test_el_selector_de_periodo_no_se_mueve_de_arriba_a_la_derecha(sitio):
    """Con la fila flexible cambiaba de lugar según hubiera gráfico o no, así
    que cambiar de período movía el control que acababas de tocar."""
    from vacantia.ui.estilos import CSS

    base, tmp = sitio
    ahora = datetime.now().astimezone()

    tarjeta = CSS[CSS.index(".postulaciones {"):CSS.index(".postulaciones .numero {")]
    assert 'grid-template-areas: "cuenta periodo"' in tarjeta
    assert ".postulaciones .periodo { grid-area: periodo;" in CSS
    # El gráfico y el cartel de "todavía ninguna" comparten celda: los dos van
    # abajo del selector, nunca en su lugar.
    assert ".postulaciones .vacio-corto { grid-area: reparto;" in CSS

    # Con datos y sin datos, el selector se dibuja siempre.
    _, vacio, _ = get(base, "/trabajos?perfil=test&ver=pendientes&apliq=7d")
    _con_historial(tmp, [_aplicada("n", ahora)])
    _, lleno, _ = get(base, "/trabajos?perfil=test&ver=pendientes&apliq=7d")
    for html in (vacio, lleno):
        assert 'class="periodo"' in html
        assert 'id="cuando-apliq"' in html
