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
