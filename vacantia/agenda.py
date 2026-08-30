"""Reparto de horarios cuando en una misma PC busca más de una persona.

El problema: los límites del plan gratis son **de la cuenta, no del perfil**.
Dos personas de la misma casa comparten la clave de Gemini y la de TinyFish, así
que si sus corridas arrancan a la misma hora se pisan entre ellas:

- Gemini free: 5–15 requests/minuto según modelo, 1000/día.
- TinyFish: 30 búsquedas/minuto, 150 URLs/minuto. Sin tope diario.
- OpenRouter free (si alguien lo usa en vez de Gemini): 20/minuto y **50/día**.

Los topes diarios sobran (~8 llamadas al LLM por persona por día). El que se
rompe si todos arrancan juntos es el **de por minuto**.

La solución es aburrida y funciona: correr escalonado. Cada perfil arranca
`SEPARACION_MINUTOS` después del anterior, sobre los tres horarios base ya
decididos: 12:00, 16:30 y 23:59.

    perfil 1 -> 12:00, 16:30, 23:59
    perfil 2 -> 12:20, 16:50, 00:19
    perfil 3 -> 12:40, 17:10, 00:39

Veinte minutos es más que de sobra: una corrida entera tarda minutos, no
decenas de minutos, así que ni siquiera se solapan. Con 6 perfiles el último
arranca 1:40 después del primero, y sigue entrando cómodo en el día.

Este módulo es la única fuente de verdad del reparto: lo usa el instalador
(`instalar.ps1` lee la salida de `python -m vacantia.agenda --json`) y se puede
mirar a mano con `python -m vacantia.agenda`.
"""

import argparse
import json
import sys

from vacantia.config import available_profiles

#: Los tres horarios elegidos: mediodía, antes de que RRHH se vaya, y tarde
#: para los que publican fuera de horario.
HORARIOS_BASE = ("12:00", "16:30", "23:59")

#: Cuánto se corre cada perfil respecto del anterior.
SEPARACION_MINUTOS = 20

#: Pausa entre perfiles cuando se corren todos de una (`--all`). No hace falta
#: que sea grande: al ser secuencial, la corrida anterior ya terminó. Es sólo
#: para no arrancar la siguiente pegada al último request de la anterior.
PAUSA_ENTRE_PERFILES = 60


def _mas_minutos(hora: str, minutos: int) -> str:
    """'23:59' + 20 -> '00:19'. Da la vuelta al día sin traer la fecha."""
    h, m = (int(x) for x in hora.split(":"))
    total = (h * 60 + m + minutos) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def horarios_de(indice: int) -> list[str]:
    """Los horarios del perfil número `indice` (0 es el primero)."""
    corrimiento = indice * SEPARACION_MINUTOS
    return [_mas_minutos(base, corrimiento) for base in HORARIOS_BASE]


def plan(perfiles: list[str]) -> dict[str, list[str]]:
    """{perfil: [horarios]}. El orden alfabético es el que fija el corrimiento.

    Que sea alfabético y no el orden del disco importa: así agregar un perfil
    nuevo no le cambia el horario a los que ya estaban, salvo a los que quedan
    después en el abecedario.
    """
    return {nombre: horarios_de(i) for i, nombre in enumerate(sorted(perfiles))}


def texto(perfiles: list[str] | None = None) -> str:
    perfiles = perfiles if perfiles is not None else available_profiles_reales()
    if not perfiles:
        return "No hay perfiles cargados todavía."
    reparto = plan(perfiles)
    ancho = max(len(n) for n in reparto)
    lineas = [f"{len(reparto)} perfil(es), separados {SEPARACION_MINUTOS} minutos:", ""]
    lineas += [f"  {n.ljust(ancho)}  {', '.join(h)}" for n, h in reparto.items()]
    return "\n".join(lineas)


def available_profiles_reales() -> list[str]:
    """Los perfiles de verdad: `example` es el molde, no busca trabajo."""
    return [p for p in available_profiles() if p != "example"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m vacantia.agenda",
        description="Cómo quedan repartidas las corridas entre los perfiles.",
    )
    parser.add_argument("--json", action="store_true",
                        help="Salida para el instalador, no para leer.")
    args = parser.parse_args(argv)

    perfiles = available_profiles_reales()
    if args.json:
        print(json.dumps(plan(perfiles), ensure_ascii=False))
    else:
        print(texto(perfiles))
    return 0


if __name__ == "__main__":
    sys.exit(main())
