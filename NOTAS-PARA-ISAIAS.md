# Notas para Isaías

**200 tests pasan.**

```
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest tests -q      →  200 passed
```

---

# 1. LO QUE TENÉS QUE REPASAR VOS

Esta es la lista corta. Todo lo demás es contexto.

| # | Qué | Dónde | Cuánto te lleva |
|---|---|---|---|
| 1 | **Verificar los 3 portales argentinos** contra los sitios reales | ver 2.1 | 15 min |
| 2 | **Verificar la fuente `rrhh`** con un perfil real de LinkedIn | ver 2.1 | 5 min |
| 3 | **Confirmar la nueva regla de ubicación** corriendo una búsqueda | ver 3.1 | 5 min |
| 4 | **Corregir los moldes de mensaje** contra tu experiencia | `vacantia/mensajes.py` | 10 min |
| 5 | **Cargar más empresas** en `companies.json` | pantalla → Mis datos | tuyo |
| 6 | **Cargar el chat de Telegram de cada persona** cuando armes sus carpetas | ver 3.2 | 1 min c/u |
| 7 | **Correr `instalar.bat` de nuevo** cuando haya más de un perfil | — | 5 min |
| 8 | Mirar cómo queda **tu CV en PDF** | pantalla → Trabajos | 1 min |
| 9 | Una **corrida real** de punta a punta con todo prendido | `--dry-run` primero | 10 min |

---

# 2. LO QUE NO PUDE VERIFICAR

## 2.1. Las dos fuentes nuevas

| Qué | Por qué | Cómo lo verificás |
|---|---|---|
| **Bumeran, Zonajobs, Computrabajo** | Escribí el código sin poder probarlo contra los sitios. Las direcciones y los patrones de URL son los que usan hoy según su estructura conocida, pero cambian sin avisar | Prendé una sola en la pantalla, corré `buscar_ahora.bat` y mirá `vacantia.log`. Si dice "0 aviso(s)", el patrón cambió → 2.2 |
| **La fuente `rrhh`** | Probada con páginas de ejemplo, no con un perfil real. LinkedIn puede devolver una pantalla de login en vez del contenido | Cargá una URL en Mis datos → "Perfiles de reclutadores", corré, mirá el log |
| **El instalador multi-perfil** | Registra tareas programadas de verdad en Windows; no lo corrí | Corré `instalar.bat` con dos perfiles y fijate que aparezcan dos tareas en `estado.bat` |
| **El PDF con tu CV real** | Se genera bien (59 KB, Arial, con `—`, `“”`, `€`) pero no juzgué cómo se ve | Pantalla → Trabajos → "Descargar CV en PDF" |

## 2.2. Si un portal no devuelve nada

Está pensado para que lo arregles sin programar. En `profiles/isaias.json`, en el
bloque de esa fuente:

```jsonc
{
  "type": "bumeran",
  "enabled": true,
  "search_url": "PEGAR la dirección de una búsqueda real, con {query} donde va el puesto",
  "job_url_pattern": "un pedazo común a las direcciones de aviso, ej: /empleos/"
}
```

Buscá algo a mano en el portal, copiá la dirección de la barra del navegador y
reemplazá el término buscado por `{query}`. Después abrí dos o tres avisos y
mirá qué tienen en común sus direcciones: eso va en `job_url_pattern`.

---

# 3. LO QUE CAMBIÉ CON TUS INDICACIONES

## 3.1. Ubicación — resuelto como me lo explicaste

Ahora funciona así:

| Campo | Qué hace |
|---|---|
| `country` vacío | de todo el mundo |
| `country: "Argentina"` | **sólo Argentina, también el remoto** |
| `city` vacía | cualquier lugar del país |
| `city: ["Bahía Blanca", "Punta Alta"]` | **sólo filtra presencial e híbrido**; el remoto entra venga de la ciudad que venga |
| `work_modes: ["remote"]` | sólo remoto… salvo un presencial en tus ciudades, que entra igual |

Las tres cosas que te importaban:

1. **El remoto ahora tiene que ser de Argentina.** Un remoto publicado desde
   Buenos Aires o Córdoba para todo el país entra; uno de Colombia o México, que
   por temas legales sólo contrata allá, ya no.
2. **La ciudad no filtra el remoto.** Un remoto de Córdoba se trabaja igual
   desde Bahía Blanca, así que no se descarta.
3. **Un presencial en tus ciudades entra aunque pidas sólo remoto**, y `city`
   acepta lista: para tus hermanos de La Plata sería
   `"city": ["La Plata", "Buenos Aires", "CABA"]`.

**Tu perfil quedó así:** `country: "Argentina"`, `city: "Bahía Blanca"`.
Se edita desde la pantalla, en un solo campo: *"Ciudades a las que puedo ir en
persona"*, separadas por coma.

**Detalle técnico**: `city` y `home_city` eran dos nombres del mismo campo y los
unifiqué en `city`. Los perfiles viejos que tengan `home_city` se siguen
leyendo, y al guardar desde la pantalla se limpia solo.

**El escape hatch**: si algún día querés remoto worldwide, `"remote_anywhere":
true` dentro de `filters.location`. Está apagado.

## 3.2. Telegram: cada persona su chat ⚠️ ESTO ES LO QUE TE IBAS A OLVIDAR

**El problema que me planteaste**: tu hermana y su novio, una sola compu, cosas
separadas. Las claves sí se comparten (el token del bot, Gemini, TinyFish son de
la máquina) **pero el chat de Telegram no**: con uno solo, los avisos de los dos
caían en el mismo teléfono.

**Ya está arreglado.** El `chat_id` se guarda dentro de cada perfil, no en el
`.env`. En la pantalla hay una sección nueva, *Mi Telegram*, con un solo campo.

**Lo que tenés que hacer vos, por persona:**

1. Que le escriba a su bot de Telegram y le mande cualquier cosa.
2. Sacá su `chat_id` (el clásico: abrir
   `https://api.telegram.org/bot<TOKEN>/getUpdates` y buscar `"chat":{"id":...}`).
3. Pantalla → seleccionar su perfil arriba a la derecha → *Mi Telegram* → pegar
   el número → Guardar.

Si lo dejás vacío, ese perfil usa el `TELEGRAM_CHAT_ID` del `.env` — o sea, el
tuyo. **Si dos personas comparten compu y no cargás esto, los dos reciben todo
en el mismo chat.**

## 3.3. Confirmaciones que me pediste

**¿Hay botón de perfil nuevo?** Sí, ya estaba: pantalla → *Mis datos* → abajo de
todo, "Crear un perfil nuevo". Genera `profiles/<nombre>.json` y
`resume/<nombre>.md` en blanco, con los huecos marcados (`COMPLETAR`,
`PEGAR CV ACÁ`). Cada uno completa lo suyo desde el formulario.

**¿Una sola API key da para dos perfiles en la misma compu?** Sí, sobrado:

| | Techo absoluto con 2 perfiles | Límite del plan gratis |
|---|---|---|
| Gemini | 30 llamadas/día | 1000/día |
| TinyFish | 6 corridas/día | sin tope diario |
| Por minuto | nunca se cruzan | las corridas salen escalonadas 20 min |

Da incluso para 6 perfiles (90 llamadas/día contra 1000). Lo único que no
escala son las 50/día de OpenRouter, y ya no lo usás: el perfil está en Gemini.

**Los perfiles de tu familia**: los saqué de la lista de pendientes, como
pediste. Queda dicho que cada uno crea el suyo cuando le pases la carpeta.

**Recolección compartida entre hermanos**: descartada por decisión tuya. Cada
uno en su compu, todo aislado — que además es lo que hace que LinkedIn no
bloquee: cada casa aporta su propia IP residencial.

**La "pestaña de shops"**: era *jobs*, la pestaña de Trabajos. Ya está hecha, y
es justo lo que necesitás para tu viejo: doble clic en `abrir.bat` y ve sus
ofertas en el navegador, sin explicarle nada. Si igual le resulta difícil, la
alternativa que mencionaste (que le lleguen por mail) queda anotada abajo como
idea, no como pendiente.

## 3.4. Modo consejo — hecho

Link "Consejo para el CV" en cada oferta. Dos partes:

- **Palabras del aviso que no están en tu CV.** Gratis, sin llamar al modelo. Es
  literalmente lo que hace un ATS. Con la advertencia bien visible: *no las
  agregues si no las hacés*.
- **Qué mover**, con un botón: tres bloques (qué subir, qué palabra falta, qué
  no tocar). El prompt tiene prohibido reescribir el CV e inventar experiencia,
  y si el aviso pide algo que no tenés lo dice como riesgo en vez de sugerirte
  ponerlo.

Tu CV no se toca nunca. Es consejo para que lo edites vos.

## 3.5. Los moldes de mensaje siguen siendo borradores

Están en `vacantia/mensajes.py`, tal como los habíamos propuesto.
**Ajustalos**: tu experiencia es más fresca que la de quien los escribió.

```
Hola {nombre}, vi la búsqueda de {puesto}.
Trabajo con {área} hace {X} años; lo último fue {logro}.
¿Te sirve que te pase el CV?
```

Lo que está entre llaves lo completa el modelo leyendo el aviso y tu CV, con un
botón. Sin credenciales, los huecos quedan a la vista a propósito: es más
honesto que un mensaje genérico disfrazado de personalizado.

---

# 4. QUÉ HAY CONSTRUIDO

| Commit | Qué |
|---|---|
| `878a6b4` | **Ubicación**: el país filtra también el remoto, la ciudad sólo lo presencial, `city` acepta lista |
| `40b0bb8` | **Telegram por persona** |
| `07af321` | **Modo consejo** para el CV |
| `d053ae8` | Bloque 6: posts que no son ofertas, país en `google_posts`, "Londres, Catamarca" |
| `afb9a14` | **Multi-perfil escalonado** + `run --all` + instalador |
| `cf3441d` | Molde de perfil y CV con huecos marcados |
| `8bd2dce` | **Bumeran / Zonajobs / Computrabajo** |
| `19c6046` | Moldes de mensaje |
| `349898d` | **CV en PDF** |
| `a2715c3` | **Fuente `rrhh`** |
| `ade760b` | **La pantalla local** |
| tanda 1 | Regla de Bahía Blanca · dedupe entre fuentes · vacantes cubiertas · `notify_when_empty` · `use_search: false` · campos de feedback |

**Horarios cuando hay varios perfiles** (`python -m vacantia.agenda`):

```
ana     12:00, 16:30, 23:59
mario   12:20, 16:50, 00:19
zoe     12:40, 17:10, 00:39
```

Si agregás un perfil, corré `instalar.bat` de nuevo: recalcula y reprograma
todo. El orden es alfabético, así que sólo se corren de horario los que quedan
después en el abecedario.

---

# 5. QUÉ FALTA

El checklist maestro, que antes vivía en `COSTOS.md`. Ese archivo se borró: lo
que seguía valiendo (las decisiones cerradas y lo que falta) quedó acá, y lo
demás eran cuentas de consumo de API que ya no cambian nada. Si alguna vez lo
querés releer, está en el historial de git.

## Bloque 1 — La UI local ✅ COMPLETO

## Bloque 2 — Que el sistema aprenda ⬜ PENDIENTE (lo dejaste fuera a propósito)

- [x] Guardar el feedback — la pantalla ya lo escribe
- [ ] **Meter las últimas ~15 descartadas con su motivo al prompt de scoring**
      como ejemplos negativos, y las aplicadas como positivos.
      *Está todo listo para engancharlo*: `State.feedback_jobs(aplicado=False,
      limit=15)` devuelve exactamente eso. Falta armar el bloque de texto en
      `scoring.SCORE_PROMPT`. Media hora.

## Bloque 3 — Documentos para postularse ✅ COMPLETO

- [x] CV en PDF con botón de descarga
- [x] Mensaje corto para DM y para mail — *borradores, corregilos*
- [x] Modo "consejo" en vez de generación

## Bloque 4 — Que la familia lo pueda usar 🟡

- [x] Fuentes para rubros no técnicos — **hechas, sin verificar**
- [x] Seguir perfiles de RRHH por URL — **hecha, sin verificar**
- [x] Que cada uno pueda armar su perfil y su Telegram por separado
- [ ] **Cargarle el `chat_id` a cada persona** cuando les pases la carpeta (3.2)

## Bloque 5 — Calidad de los resultados 🟡

- [x] Regla de Bahía Blanca — **corregida con tu criterio de remoto** (3.1)
- [x] Duplicados entre fuentes
- [x] Descartar vacantes ya cubiertas
- [x] `notify_when_empty`
- [x] `use_search: false` en las 7 empresas
- [ ] **Cargar más empresas** en `companies.json` — tuyo

## Bloque 6 — Vigilar 🟡

- [x] Ruido de posts de opinión en `google_posts`
- [x] País vacío en `google_posts`
- [x] Rareza geográfica de LinkedIn
- [x] La "pestaña de jobs" — es la pestaña Trabajos, ya está
- [x] ~~Recolección compartida~~ — **descartada**: todo aislado, cada uno en su compu

## Ideas, no pendientes

- Que a tu viejo le lleguen las ofertas **por mail** además de por Telegram. El
  motor ya tiene la interfaz `Notifier` lista (`vacantia/notifiers/`): agregar
  un canal nuevo es un archivo, no tocar el motor. Decidilo después de ver si se
  arregla con `abrir.bat`.
- Que la pantalla muestre el resumen de la última corrida (hoy eso está en
  `estado.bat`).

---

## Qué es cada archivo de la raíz

Los cinco `.bat` son todo lo que tocan las personas que no programan:

| Archivo | Para qué | Cuándo se usa |
|---|---|---|
| `instalar.bat` | Instala todo y programa las búsquedas automáticas | Una vez, al principio. Y de nuevo cada vez que agregues un perfil o muevas la carpeta |
| `abrir.bat` | **La pantalla**: ver las ofertas y cargar los datos | Todos los días |
| `buscar_ahora.bat` | Una búsqueda ya, sin esperar el horario | Cuando no querés esperar |
| `estado.bat` | "¿Esto anda?" — si está programado, cuándo corrió, cómo le fue | Cuando algo parece raro |
| `desinstalar.bat` | Deja de buscar y borra el programa. Pregunta aparte si borrar también los datos | Cuando consiguieron trabajo |

El resto:

| | |
|---|---|
| `README.md` | La documentación técnica. **Falta reescribirlo** como guía de instalación para cada persona |
| `NOTAS-PARA-ISAIAS.md` | Este archivo: lo que hay que repasar y lo que falta |
| `companies.json` | Las empresas que sigue la fuente `careers`. Se edita desde la pantalla |
| `.env` | Las claves. Se edita desde la pantalla. **No se sube a git** |
| `.env.example` | El molde del `.env`, sin claves |
| `requirements.txt` | Lo que instala `instalar.bat` |
| `requirements-dev.txt` | pytest. Sólo para vos, nadie más lo necesita |
| `conftest.py` | Deja que los tests encuentren el paquete |
| `profiles/` `resume/` `state/` `output/` | Perfiles, CVs, ofertas guardadas y documentos generados |
| `vacantia/` `tests/` `scripts/` | El programa, sus pruebas, y los scripts de PowerShell que usan los `.bat` |

## Dónde está cada cosa del código

```
vacantia/
├── agenda.py         reparto de horarios entre perfiles
├── consejo.py        qué reordenar del CV (no lo reescribe)
├── mensajes.py       moldes de DM y mail (borradores)
├── pdf.py            CV a PDF (ojo con la fuente Unicode)
├── filters.py        la regla de ubicación y modalidad
├── ui/
│   ├── server.py     el servidor y las rutas
│   ├── data.py       todo lo que toca disco
│   ├── formulario.py la pestaña Mis datos
│   └── render.py     el HTML y el CSS
└── sources/
    ├── rrhh_profiles.py   seguir reclutadores por URL
    └── portales_ar.py     Bumeran / Zonajobs / Computrabajo
```
