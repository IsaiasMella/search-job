"""Los gráficos de Métricas, dibujados con HTML y los tokens del sistema.

**Sin librería, sin SVG y sin una sola llamada a la red.** Una barra es un `div`
con un ancho en porcentaje: el navegador ya sabe hacer eso, y hacerlo así trae
tres cosas que un SVG generado no da gratis. El texto usa la tipografía del
sistema y escala con ella; la escala es responsive sin recalcular nada; y los
colores salen de las mismas variables CSS que el resto de la pantalla, así que
si cambia la paleta cambian también los gráficos.

**Qué se dibuja y qué no.** Un gráfico se gana el lugar cuando hay que comparar
varias magnitudes de un vistazo. Con dos filas no hay nada que comparar y la
tabla dice lo mismo en menos espacio, así que ahí se queda la tabla. La regla
está en `vale_un_grafico`.

**Todos los gráficos de acá son de una sola serie**, y eso simplifica el color:
la magnitud la lleva el largo de la barra, no el tono. Por eso todas las barras
son del mismo color y no hay leyenda: el título dice qué se está midiendo. El
único tono distinto es el del tramo que supera el puntaje mínimo, y lo lleva
porque significa algo (de ahí para arriba el sistema avisa), no para decorar.
"""

from html import escape

#: Abajo de esto, una tabla dice lo mismo mejor. Dos filas no son una
#: comparación: son dos números, y para dos números la tabla ocupa menos y se
#: lee más rápido.
MINIMO_PARA_GRAFICAR = 3


def _esc(texto) -> str:
    return escape("" if texto is None else str(texto), quote=True)


def vale_un_grafico(filas) -> bool:
    """¿Hay algo que comparar acá, o alcanza con la tabla?"""
    utiles = [f for f in (filas or []) if (f[1] if isinstance(f, tuple) else f) ]
    return len(utiles) >= MINIMO_PARA_GRAFICAR


def barras(filas: list[tuple[str, int]], unidad: str = "ofertas",
           maximo: int | None = None) -> str:
    """Barras horizontales, una por categoría, ordenadas de mayor a menor.

    Horizontales y no verticales porque las etiquetas son frases enteras
    ("Piden un inglés más alto que el tuyo"): en vertical habría que rotarlas o
    recortarlas, y una etiqueta cortada obliga a adivinar.

    El valor va escrito al lado de cada barra, siempre. Un gráfico donde hay que
    estimar la altura contra una grilla obliga a un trabajo que el número
    resuelve gratis, y el largo de la barra sigue estando para comparar de un
    vistazo.
    """
    filas = [(k, int(v)) for k, v in (filas or []) if v]
    if not filas:
        return ""
    filas.sort(key=lambda kv: -kv[1])
    tope = maximo or max(v for _, v in filas)
    total = sum(v for _, v in filas)

    barras_html = []
    for etiqueta, valor in filas:
        ancho = max(1.0, 100.0 * valor / tope) if tope else 0.0
        parte = f"{round(100 * valor / total)}% de {total}" if total else ""
        barras_html.append(
            f'<div class="barra-fila">'
            f'<span class="barra-nombre">{_esc(etiqueta)}</span>'
            f'<span class="barra-riel" title="{_esc(f"{valor} {unidad}, {parte}")}">'
            f'<span class="barra-relleno" style="--ancho:{ancho:.1f}%"></span></span>'
            f'<span class="barra-valor">{valor}</span>'
            f"</div>"
        )
    return f'<div class="barras">{"".join(barras_html)}</div>'


def columnas(datos: list[dict], unidad: str = "ofertas") -> str:
    """Barras verticales. Para cuando el eje tiene un orden propio.

    Se usa en dos lugares y en los dos el orden importa y no se puede reordenar
    por tamaño: los tramos de puntaje van de 0 a 100, y las semanas van de la
    más vieja a la más nueva. En esos casos ordenar por magnitud, como hace
    `barras`, destruiría el sentido del eje.

    Cada dict lleva `etiqueta`, `cuantas`, y opcionalmente `destacada` para el
    tramo que significa algo.
    """
    datos = list(datos or [])
    if not datos:
        return ""
    tope = max((d.get("cuantas") or 0) for d in datos) or 1

    columnas_html = []
    for d in datos:
        valor = int(d.get("cuantas") or 0)
        etiqueta = d.get("etiqueta")
        # Las de valor cero se dibujan igual, con una línea al ras: un hueco en
        # el eje se lee como "acá no hay dato", y acá el cero es el dato.
        alto = max(2.0, 100.0 * valor / tope)
        clase = "columna"
        if d.get("destacada"):
            clase += " destacada"
        if not valor:
            clase += " vacia"
        detalle = _esc(f"{etiqueta}: {valor} {unidad}")
        columnas_html.append(
            f'<div class="{clase}" title="{detalle}">'
            f'<span class="columna-valor">{valor}</span>'
            f'<span class="columna-relleno" style="--alto:{alto:.1f}%"></span>'
            f'<span class="columna-nombre">{_esc(etiqueta)}</span>'
            f"</div>"
        )
    return f'<div class="columnas">{"".join(columnas_html)}</div>'
