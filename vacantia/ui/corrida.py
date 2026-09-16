"""Arrancar una búsqueda desde la pantalla, y contar cómo viene funcionando.

Reemplaza dos archivos `.bat` que había que ir a buscar al Explorador:

* `buscar_ahora.bat` -> el botón **Buscar ahora**, al pie de la barra lateral.
* `estado.bat` -> el panel **Cómo viene funcionando**, en Métricas.

La regla que lo motiva está en `DESIGN.md`: *no nombrar archivos, scripts ni
comandos en el cuerpo de la interfaz; si hay que ejecutar algo, es un botón con
nombre humano*. Mientras la pantalla decía "doble clic en `buscar_ahora.bat`",
la pantalla no era la app: era la documentación de otro programa.

**La búsqueda corre en un proceso aparte, no adentro del servidor.** Tarda
minutos, y el servidor de la pantalla es de un solo hilo por pedido: si corriera
adentro, la pantalla se congelaría hasta que termine. Como proceso suelto, se
puede seguir marcando ofertas mientras busca, y si alguien cierra la ventana
negra la corrida sigue hasta el final.
"""

import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from vacantia.log import get_logger

logger = get_logger()

RAIZ = Path(__file__).resolve().parents[2]
LOG = RAIZ / "vacantia.log"

#: El proceso de la última búsqueda arrancada desde la pantalla. Vive sólo
#: mientras vive el servidor: si alguien cierra y vuelve a abrir la pantalla en
#: el medio de una corrida, la corrida sigue igual (es un proceso suelto) pero
#: la pantalla deja de saber que existe. Es aceptable: el aviso de "entraron
#: ofertas nuevas" avisa igual cuando termina.
_proceso: subprocess.Popen | None = None

#: Dónde terminaba el registro justo antes de arrancar la corrida que se está
#: mirando, y a qué hora arrancó. Leer el archivo **sólo desde ahí para
#: adelante** es lo que hace que el progreso hable de ESTA corrida y no de la de
#: ayer, y además que no cueste nada: el registro pesa varios MB y de acá se
#: leen unos pocos KB.
_desde_byte: int = 0
_arrancada: float = 0.0


def esta_corriendo() -> bool:
    """¿Hay una búsqueda en curso arrancada desde la pantalla?"""
    return _proceso is not None and _proceso.poll() is None


def arrancar(perfil: str = "") -> tuple[bool, str]:
    """Lanza la búsqueda. Devuelve (arrancó, mensaje para la persona).

    Sin `perfil` corre todos los de la máquina, uno después del otro y con una
    pausa en el medio, que es lo que hacía el `.bat`: los límites del plan
    gratis son de la cuenta, no del perfil.
    """
    global _proceso

    if esta_corriendo():
        return False, "Ya hay una búsqueda en curso. Cuando termine te avisa la pantalla."

    orden = [sys.executable, "-m", "vacantia.run"]
    orden += ["--profile", perfil] if perfil else ["--all"]

    # CREATE_NO_WINDOW: sin esto Windows abre una ventana negra por cada
    # búsqueda, que es exactamente lo que veníamos a sacar del medio.
    extra = {}
    if os.name == "nt":
        extra["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    # El final del registro ANTES de lanzar: todo lo que se escriba de acá en
    # adelante es de esta corrida. Se toma antes del Popen y no después para no
    # perderse las primeras líneas si el proceso arranca rápido.
    global _desde_byte, _arrancada
    try:
        _desde_byte = LOG.stat().st_size
    except OSError:
        _desde_byte = 0
    _arrancada = time.time()

    try:
        _proceso = subprocess.Popen(
            orden, cwd=RAIZ,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **extra,
        )
    except OSError as e:
        logger.exception("[ui] No pude arrancar la búsqueda")
        return False, f"No pude arrancar la búsqueda: {e}"

    logger.info("[ui] Búsqueda arrancada desde la pantalla (%s)",
                perfil or "todos los perfiles")
    return True, ("Buscando ofertas. Tarda unos minutos y podés seguir usando la "
                  "pantalla: cuando entren, te avisa acá abajo.")


# --- cómo viene funcionando -------------------------------------------------
#
# Lo que mostraba `estado.bat`, leído desde acá. Son dos fuentes: el registro de
# la app, que es un archivo de texto, y el Programador de tareas de Windows, que
# se le pregunta con `schtasks`.

#: Cuánto del final del registro se lee, y hasta dónde se agranda si la última
#: corrida no aparece. El archivo llega a varios MB y lo único que interesa son
#: las últimas corridas, pero un rato de uso intenso (o una tanda de tests)
#: puede empujar el resumen más atrás de lo esperado. Sin el crecimiento, el
#: panel decía "todavía no hay ninguna búsqueda" con el dato ahí nomás.
_COLA = 512_000
_COLA_MAXIMA = 8_000_000

#: La marca que cierra cada corrida. Es lo que se busca al agrandar la lectura.
_CIERRE = "=== Listo en"

_FECHA = re.compile(r"^\[(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})")


def _ultimas_lineas() -> list[str]:
    """El final del registro, sin leer el archivo entero.

    Se lee de a pedazos hacia atrás hasta encontrar el cierre de una corrida.
    Si no aparece en los últimos 8 MB, es que no hay ninguna: se devuelve lo
    leído igual, porque los avisos de error sí sirven.
    """
    crudo = ""
    try:
        with LOG.open("rb") as f:
            f.seek(0, os.SEEK_END)
            largo = f.tell()
            cola = _COLA
            while True:
                f.seek(max(0, largo - cola))
                crudo = f.read().decode("utf-8", errors="replace")
                if _CIERRE in crudo or cola >= largo or cola >= _COLA_MAXIMA:
                    break
                cola *= 4
    except OSError:
        return []
    return crudo.splitlines()[1:]      # la primera puede estar cortada al medio


def _cuando(linea: str) -> str:
    """La fecha con la que arranca una línea del registro, en lenguaje humano."""
    m = _FECHA.match(linea)
    if not m:
        return ""
    try:
        momento = datetime.fromisoformat(m.group(1).replace(" ", "T"))
    except ValueError:
        return ""
    from vacantia.ui.data import _hace_cuanto

    return _hace_cuanto(momento)


def _sin_prefijo(linea: str) -> str:
    """La línea sin la fecha ni el nivel: queda sólo lo que dice.

    Los guiones largos se pasan a guion común. El registro los usa como
    separador y en la pantalla quedan de firma de texto generado, que es
    justamente lo que el sistema de diseño no quiere ver en ningún lado.
    """
    limpia = re.sub(r"^\[.*?\]\s*\w+\s*", "", linea).strip()
    return limpia.replace("—", "-").replace("–", "-")


#: El resumen que escribe el motor al terminar:
#:
#:     === Listo en 41.3s — 125 recolectadas, 78 nuevas, 4 ya cubiertas, ... ===
#:
#: Se parsea en vez de mostrarlo crudo por dos razones: la línea es del registro
#: y no de la pantalla (lleva guion largo, signos igual y decimales de máquina),
#: y en columnas los números se comparan de una corrida a la otra, que es
#: justamente para lo que sirven.
_DURACION = re.compile(r"Listo en ([\d.]+)s")
_CUENTA = re.compile(r"(\d+) ([a-záéíóúñ ]+?)(?=,|\s*=|$)")


def _parsear_resumen(linea: str) -> tuple[str, list[tuple[str, int]]]:
    """(cuánto tardó, [(qué, cuántas)]) de la línea de cierre del motor."""
    if not linea:
        return "", []
    m = _DURACION.search(linea)
    duracion = ""
    if m:
        segundos = max(1, round(float(m.group(1))))
        duracion = f"{segundos} segundo" if segundos == 1 else f"{segundos} segundos"
    cuerpo = linea.split("—", 1)[-1] if "—" in linea else linea
    filas = [(que.strip(), int(n)) for n, que in _CUENTA.findall(cuerpo)]
    return duracion, filas


def _tarea_programada() -> dict:
    """Lo que sabe el Programador de tareas de Windows. {} si no aplica.

    `schtasks` es el que ya viene con Windows: no agrega ninguna dependencia. En
    cualquier otro sistema operativo simplemente no hay nada que preguntar, y el
    panel lo dice en vez de mentir.
    """
    if os.name != "nt":
        return {}
    try:
        salida = subprocess.run(
            ["schtasks", "/query", "/fo", "CSV", "/nh"],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {}

    # `schtasks` devuelve una fila por disparador, y cada perfil tiene cuatro
    # (uno al iniciar sesión y tres diarios). Se queda la próxima de cada tarea.
    tareas: dict[str, dict] = {}
    for linea in salida.splitlines():
        # "\Vacantia - isaias","8/9/2026 23:59:00","Listo"
        campos = [c.strip('"') for c in linea.split('","')]
        if len(campos) < 3:
            continue
        nombre = campos[0].strip('"').lstrip("\\")
        if not nombre.startswith("Vacantia"):
            continue
        previa = tareas.get(nombre)
        if previa is None or campos[1] < previa["proxima"]:
            tareas[nombre] = {"nombre": nombre, "proxima": campos[1],
                              "estado": campos[2]}
    return {"tareas": list(tareas.values())}


def salud() -> dict:
    """Todo lo que mostraba `estado.bat`, para dibujarlo en Métricas.

    Devuelve siempre las mismas claves, con vacío donde no hay dato: la pantalla
    no tiene que preguntarse si existen.
    """
    lineas = _ultimas_lineas()

    resumen, cuando_resumen = "", ""
    telegram = ""
    problemas: list[str] = []
    for linea in lineas:
        if "=== Listo en" in linea:
            resumen, cuando_resumen = _sin_prefijo(linea), _cuando(linea)
        elif "Telegram enviado" in linea:
            telegram = _cuando(linea)
        elif " ERROR " in linea or " WARNING " in linea:
            problemas.append(_sin_prefijo(linea))

    duracion, filas = _parsear_resumen(resumen)
    programada = _tarea_programada()
    return {
        "corriendo": esta_corriendo(),
        "cuando": cuando_resumen,
        "duracion": duracion,
        "encontro": filas,
        "telegram": telegram,
        # Los últimos cinco, del más nuevo al más viejo: si algo se repite
        # siempre, con cinco alcanza para verlo.
        "problemas": list(reversed(problemas[-5:])),
        "programada": programada.get("tareas") if programada else None,
    }


# --- qué está haciendo ahora mismo -------------------------------------------
#
# El motor deja en el registro una línea por cada etapa. Acá se leen esas líneas
# y se traducen a una oración en castellano, que es lo que muestra el cartel de
# la barra lateral mientras la búsqueda corre.
#
# **Nunca hay un porcentaje inventado, y es a propósito.** No se sabe de
# antemano cuántas fuentes van a contestar ni cuántas ofertas van a entrar. Lo
# que sí se sabe con exactitud es en qué etapa está y, durante el puntaje,
# cuántas lleva de cuántas. Eso se muestra, y nada más: la barra del panel sólo
# se llena de a poco durante el puntaje, y en las demás etapas es una barra sin
# porcentaje, que dice "esto sigue andando" sin prometer cuánto falta.

#: Los hitos del motor, en el orden del pipeline. El progreso es siempre el hito
#: más avanzado que ya apareció en el registro de esta corrida.
_PERFIL_ARRANCA = re.compile(r"=== vacantia .* perfil '(.+?)' ===")
_FUENTE_EMPIEZA = re.compile(r"--- Fuente: (.+?) ---")
_FUENTE_TERMINA = re.compile(r"--- (.+?): (\d+) oferta\(s\) ---")
_RECOLECTADO = re.compile(r"Total recolectado: (\d+) oferta")
_A_PUNTUAR = re.compile(r"Puntuando (\d+) oferta\(s\)")
_YA_PUNTUADA = re.compile(r"^\[\s*\d+\]")
_FILTRADAS = re.compile(r"Filtros: (\d+) pasaron")

#: Cuánto se lee como mucho del tramo de esta corrida. Una corrida larga con
#: `--all` y el nivel DEBUG escribe bastante; con el último medio MB alcanza y
#: sobra para saber en qué etapa está.
_TRAMO_MAXIMO = 500_000


def _lineas_de_esta_corrida() -> list[str]:
    """El registro desde que arrancó la búsqueda que se está mirando.

    Devuelve `[]` si no hay ninguna arrancada desde la pantalla. Es un `seek` a
    un offset conocido, así que el tamaño del archivo no importa.
    """
    if not _desde_byte:
        return []
    try:
        with LOG.open("rb") as f:
            f.seek(0, os.SEEK_END)
            fin = f.tell()
            # El registro se rota o se borra: el offset viejo ya no significa
            # nada y leer desde ahí daría cualquier cosa.
            if fin < _desde_byte:
                return []
            f.seek(max(_desde_byte, fin - _TRAMO_MAXIMO))
            return f.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return []


#: Las etapas, en el orden del pipeline, con el nombre corto que muestra el
#: panel de "Buscando trabajo".
#:
#: **El identificador va aparte de la oración a propósito.** La oración cambia
#: con la fuente y con el número de ofertas ("Buscando en Getonbrd", "Revisando
#: 125 ofertas"); el identificador no cambia nunca, y es lo que le permite al
#: panel saber qué tramo ya pasó sin tener que adivinarlo del texto.
#:
#: `arranque` y `cierre` no tienen nombre corto: no son tramos de la barra, son
#: el antes y el después. Con `arranque` la barra está entera por delante, y con
#: `cierre` entera cumplida.
ETAPAS = (
    ("fuentes", "Portales"),
    ("revisando", "Revisión"),
    ("puntuando", "Puntaje"),
    ("filtrando", "Filtros"),
)


def progreso() -> dict:
    """En qué anda la búsqueda ahora. Siempre las mismas claves.

    * `corriendo`: si hay un proceso vivo arrancado desde la pantalla.
    * `paso`: la oración que se muestra, ya en castellano.
    * `etapa`: el identificador de esa etapa, uno de `ETAPAS` más `arranque` y
      `cierre`. Es lo que dibuja la barra de tramos.
    * `hechas` / `total`: sólo durante el puntaje, que es la etapa larga.
    * `perfil`: cuál se está procesando, que con `--all` va cambiando.
    * `segundos`: cuánto hace que arrancó.
    """
    corriendo = esta_corriendo()
    estado = {
        "corriendo": corriendo,
        "paso": "",
        "etapa": "",
        "perfil": "",
        "hechas": 0,
        "total": 0,
        "segundos": int(time.time() - _arrancada) if _arrancada else 0,
    }
    if not corriendo:
        return estado

    paso, etapa = "Arrancando la búsqueda", "arranque"
    perfil = fuente = ""
    recolectadas = puntuar = puntuadas = 0

    for cruda in _lineas_de_esta_corrida():
        linea = _sin_prefijo(cruda)

        if m := _PERFIL_ARRANCA.search(linea):
            # Con `--all` cambia de perfil en el medio: todo lo de la etapa
            # anterior se reinicia o el cartel mezcla dos corridas en una.
            perfil, fuente = m.group(1), ""
            recolectadas = puntuar = puntuadas = 0
            paso, etapa = "Arrancando la búsqueda", "arranque"
        elif m := _FUENTE_EMPIEZA.search(linea):
            fuente = m.group(1)
            paso, etapa = f"Buscando en {fuente}", "fuentes"
        elif _FUENTE_TERMINA.search(linea):
            # La fuente terminó y todavía no empezó la próxima. Queda el texto
            # de la anterior: decir "esperando" por medio segundo es peor.
            pass
        elif m := _RECOLECTADO.search(linea):
            recolectadas = int(m.group(1))
            paso, etapa = f"Revisando {recolectadas} ofertas", "revisando"
        elif m := _A_PUNTUAR.search(linea):
            puntuar, puntuadas = int(m.group(1)), 0
            paso, etapa = "Puntuando contra tu CV", "puntuando"
        elif _YA_PUNTUADA.match(linea):
            puntuadas += 1
        elif _FILTRADAS.search(linea):
            paso, etapa = "Aplicando tus filtros", "filtrando"
        elif _CIERRE in linea:
            paso, etapa = "Terminando", "cierre"

    if puntuar:
        # Ojo con `min`: si el motor reintenta un lote, las líneas de puntaje se
        # repiten y sin el tope se ve "Puntuando 84 de 78".
        estado["hechas"], estado["total"] = min(puntuadas, puntuar), puntuar
    estado["paso"], estado["etapa"], estado["perfil"] = paso, etapa, perfil
    return estado
