# Notas para Isaías

Dos tandas de trabajo nocturno. **172 tests pasan.**

```
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest tests -q      →  172 passed
```

Ordenado por importancia: primero lo que tenés que decidir o verificar vos,
después lo que se hizo, y al final el panorama completo de lo que falta.

---

# 1. LO PRIMERO QUE TENÉS QUE MIRAR

## 1.1. La duda de remoto + ubicación (sigue abierta, como pediste)

**No la toqué. El código quedó como estaba anoche**, que es:

1. **Remoto en cualquier lado** → si el aviso dice remoto, el filtro de país
   *no se aplica*.
2. **Presencial o híbrido en tu ciudad** (`filters.location.home_city`,
   cargada con "Bahía Blanca") → pasa aunque `work_modes` pida sólo remoto.
3. El resto, como siempre.

**El efecto que te va a molestar, si te molesta:** ahora entran remotos de
España, México y Estados Unidos que antes se caían por país. Al filtro de
idioma se le escapan los de México y Colombia, que son en español.

**Cómo lo corregís en 10 segundos**, sin tocar código:

| Qué querés | Qué hacés |
|---|---|
| Que las remotas vuelvan a ser sólo de Argentina | En `profiles/isaias.json`, dentro de `filters.location`, poné `"remote_anywhere": false` |
| Que además entre presencial en Punta Alta | `"home_city": ["Bahía Blanca", "Punta Alta"]` (acepta lista) |
| Que el presencial local NO entre | Borrá el valor de `home_city` (dejalo `""`) |

También se cambia desde la pantalla (`abrir.bat` → Mis datos → Dónde), salvo
`remote_anywhere`, que es sólo del JSON.

## 1.2. Lo que NO pude verificar y necesita tu ojo

| Qué | Por qué | Cómo lo verificás |
|---|---|---|
| **Los tres portales argentinos** (`bumeran`, `zonajobs`, `computrabajo`) | Escribí el código sin poder probarlo contra los sitios reales. Las direcciones de búsqueda y los patrones de URL son los que usan hoy según su estructura conocida, pero cambian sin avisar | Prendé una sola en el perfil, corré `buscar_ahora.bat` y mirá `vacantia.log`. Si dice "0 aviso(s)", el patrón cambió: ver 1.3 |
| **La fuente `rrhh`** | Probada con páginas de ejemplo, no con un perfil real de LinkedIn. LinkedIn puede devolver una página de login en vez del contenido | Cargá una URL en Mis datos → "Perfiles de reclutadores", corré, y mirá el log |
| **El instalador multi-perfil** | No lo corrí: registra tareas programadas de verdad en tu Windows | Corré `instalar.bat` cuando tengas dos perfiles y fijate que aparezcan dos tareas en `estado.bat` |
| **El PDF con tu CV real** | El PDF se genera y abre bien (59 KB, Arial, con `—`, `“”`, `€`), pero no juzgué cómo se ve | `abrir.bat` → Trabajos → "Descargar CV en PDF" |

## 1.3. Si un portal no devuelve nada

Está pensado para que lo arregles sin programar. En `profiles/isaias.json`, en
el bloque de esa fuente:

```jsonc
{
  "type": "bumeran",
  "enabled": true,
  "search_url": "PEGAR ACÁ la dirección de una búsqueda real, con {query} donde va el puesto",
  "job_url_pattern": "un pedazo de la dirección de un aviso, ej: /empleos/"
}
```

Buscá algo en el portal a mano, copiá la dirección de la barra del navegador y
reemplazá el término por `{query}`. Después abrí un aviso cualquiera y mirá qué
tienen en común todas las direcciones de aviso: eso va en `job_url_pattern`.

## 1.4. Decisiones que tomé solo (y cómo se revierten)

| Asumí | Por qué | Se cambia en |
|---|---|---|
| Los perfiles arrancan **20 minutos** uno después del otro | Una corrida tarda minutos; 20 da margen de sobra sin estirar el día | `SEPARACION_MINUTOS` en `vacantia/agenda.py` |
| El orden de los horarios es **alfabético** | Así agregar un perfil no le cambia la hora a media familia | idem |
| **5 segundos** entre lotes del scoring | Gemini free permite 5-15 por minuto; 5s no se notan en una corrida de minutos | `"llm": {"batch_delay": N}` en el perfil |
| `--all` espera **60 segundos** entre perfiles | Al ser secuencial el anterior ya terminó; es sólo para no pegar dos requests seguidos | `--gap N` en la línea de comandos |
| Un perfil nuevo se crea con **todas las fuentes apagadas** | Que las prenda quien sepa cuáles le sirven; prender LinkedIn sin querer es scrapear | Mis datos → De dónde traer ofertas |
| El **motivo del descarte es obligatorio**, validado también en el servidor | El cliente se puede saltear, y sin motivo el feedback no sirve para nada | `vacantia/ui/server.py` |
| Las claves van al **`.env`, nunca al perfil** | Los perfiles se versionan en git | — |
| Un campo de clave vacío significa "no la cambies" | Si vaciarlo borrara la clave, entrar y guardar sin tocar nada te dejaría sin credenciales | — |
| `pytest` va en **`requirements-dev.txt`**, no en `requirements.txt` | Nadie de tu familia necesita pytest instalado | — |
| **No creé ningún perfil de nadie** | Me lo pediste explícitamente | — |

## 1.5. Los moldes de mensaje son un borrador

Están en `vacantia/mensajes.py`, copiados de la sección 10 de COSTOS.md tal como
los propusiste discutir. **Ajustalos**: tu experiencia es más fresca.

```
Hola {nombre}, vi la búsqueda de {puesto}.
Trabajo con {área} hace {X} años; lo último fue {logro}.
¿Te sirve que te pase el CV?
```

Lo que está entre llaves lo completa el LLM leyendo el aviso y tu CV, con un
botón. Sin credenciales, los huecos quedan a la vista — a propósito: es más
honesto que un mensaje genérico disfrazado de personalizado.

No hice molde de carta de presentación de una carilla: vos mismo anotaste que
en Argentina casi no se usa.

---

# 2. QUÉ SE HIZO ESTA NOCHE

## 2.1. La pantalla local — `ade760b`

`abrir.bat` levanta un servidor en `http://localhost:8756` y abre el navegador.
Sólo biblioteca estándar de Python, atado a `127.0.0.1`: no se ve desde la red
ni desde internet, por eso no pide contraseña.

**Trabajos**: las ofertas con puntaje, empresa, link y por qué. Botón verde
"Apliqué" y rojo "No apliqué" con motivo obligatorio. Filtros por sin marcar /
apliqué / descarté / todas. Se guarda en `aplicado`, `motivo_descarte` y
`fecha_feedback` dentro de `state/<perfil>/job_history.json`.

**Mis datos**: el perfil entero sin tocar JSON — CV, palabras clave,
país/ciudad/ciudad donde vivís, modalidad, idioma, fuentes, empresas, perfiles
de RRHH, claves y datos personales. Más el botón de crear un perfil nuevo.

El CSS es el mínimo para que se lea. El único JavaScript son ocho líneas para
exigir el motivo al descartar.

**Lo que NO hice, porque me lo pediste:** el ciclo de aprendizaje. El feedback
se guarda pero no entra al prompt del scoring.

## 2.2. Seguir reclutadores por URL — `a2715c3`

Fuente `rrhh`. Se le carga una lista de URLs (perfil de actividad de alguien de
RRHH, página de búsquedas de una consultora) y de cada una saca los links a
publicaciones, los links con pinta de aviso, o —si no hay ninguno— los párrafos
del texto que anuncian una búsqueda.

Ese último caso resuelve el problema de fondo: la dirección de la página de una
consultora no cambia nunca, así que el dedupe por URL taparía cada búsqueda
nueva. Cada párrafo se identifica con la URL más un hash de su texto, así una
publicación nueva es una clave nueva.

Para el perfil de tu viejo esto probablemente rinda más que la búsqueda por
keyword.

## 2.3. CV en PDF — `349898d`

Botón "Descargar CV en PDF" en la pestaña Trabajos. Seguí al pie la advertencia
de la sección 10: registra Arial de `C:\Windows\Fonts` antes de escribir, porque
la fuente por defecto de fpdf2 revienta con el guion largo. Si no hubiera
ninguna fuente Unicode instalada, en vez de fallar reemplaza los caracteres
problemáticos y genera el PDF igual.

## 2.4. Mensajes para el reclutador — `19c6046`

Ver 1.5.

## 2.5. Portales argentinos — `8bd2dce`

`bumeran`, `zonajobs` y `computrabajo`. Ver 1.2 y 1.3: **necesitan verificación
contra el sitio real.**

## 2.6. Molde de perfil y de CV — `cf3441d`

`profiles/example.json` es ahora una plantilla de verdad (keywords vacías,
fuentes apagadas, `"COMPLETAR: ..."` en los datos personales) y
`resume/EJEMPLO_CV.md` arranca con "PEGAR CV ACÁ". De ahí sale cada perfil nuevo
que se crea desde la pantalla.

## 2.7. Varios perfiles con corridas escalonadas — `afb9a14`

El punto que más me importaba de esta tanda. Los límites del plan gratis son
**de la cuenta, no del perfil**: dos personas de la misma casa comparten la
clave de Gemini y la de TinyFish.

```
ana     12:00, 16:30, 23:59
mario   12:20, 16:50, 00:19
zoe     12:40, 17:10, 00:39
```

`python -m vacantia.agenda` muestra el reparto. `instalar.bat` lo lee y registra
una tarea programada por persona (limpiando antes las viejas, para que un perfil
borrado no deje una huérfana). `buscar_ahora.bat` ahora corre `--all`, así sirve
igual para uno que para seis.

**Si agregás un perfil**: corré `instalar.bat` de nuevo. Recalcula el reparto y
reprograma todo. Al ser alfabético, sólo se corren de horario los que quedan
después en el abecedario.

**El caso de las 50 empresas**: el techo por corrida sigue siendo el triaje
`max_new_per_run` (30 ofertas = 5 llamadas al LLM), más los 5 segundos entre
lotes que agregué. Con 6 perfiles y 3 corridas, el peor caso absoluto son 90
llamadas contra las 1000 diarias de Gemini.

## 2.8. Bloque 6 — `d053ae8`

- **Posts que no son ofertas**: se descartan los que no mencionan ninguna
  búsqueda y los que usan ese vocabulario sin ofrecer nada (gente buscando
  trabajo para sí misma, cursos, webinars, felicitaciones).
- **País en `google_posts`**: sale del texto cuando lo nombra. Si no, queda
  vacío (`default_country` es opt-in).
- **"Londres, Catamarca"**: la ciudad pasa a ser el primer segmento y la
  provincia va a `region`. "LATAM" y "Remote" ya no se toman por un país.

## 2.9. De la tanda anterior (ya estaba)

Regla de Bahía Blanca · dedupe entre fuentes por empresa+título · descartar
vacantes ya cubiertas · `notify_when_empty` con diagnóstico de la corrida ·
`use_search: false` en las 7 empresas · campos de feedback en `Job`.

---

# 3. QUÉ FALTA POR HACER

Contra el checklist maestro de COSTOS.md, sección 12.

## Bloque 1 — La UI local ✅ COMPLETO

- [x] Servidor local + `abrir.bat`
- [x] Pestaña **Mis datos**
- [x] Pestaña **Trabajos** con verde/rojo y motivo obligatorio
- [x] Campos nuevos en `Job`

## Bloque 2 — Que el sistema aprenda ⬜ PENDIENTE (lo dejaste fuera a propósito)

- [x] Guardar el feedback — la pantalla ya lo escribe
- [ ] **Meter las últimas ~15 descartadas con su motivo al prompt de scoring**
      como ejemplos negativos, y las aplicadas como positivos.
      *Está todo listo para engancharlo*: `State.feedback_jobs(aplicado=False,
      limit=15)` devuelve exactamente eso. Falta armar el bloque de texto en
      `scoring.SCORE_PROMPT`. Es media hora de trabajo.

## Bloque 3 — Documentos para postularse 🟡 CASI

- [x] CV en PDF con botón de descarga
- [x] Mensaje corto para DM y para mail (borradores, ver 1.5)
- [ ] **Modo "consejo" para tu perfil**: que compare tu CV con el aviso y te
      diga qué reordenar o qué keyword te falta para el ATS, en vez de
      reescribirte el CV. Riesgo cero sobre lo que ya te funciona.

## Bloque 4 — Que la familia lo pueda usar 🟡 A MEDIAS

- [ ] `profiles/hermana.json` + `resume/hermana.md` (marketing)
- [ ] `profiles/papa.json` + `resume/papa.md` (QHSE, presencial, oil & gas)
- [ ] Perfiles de tus dos hermanos menores (ventas / gastronomía)
      → **Los tres puntos de arriba son de ellos, no míos.** El sistema ya está
      listo: `abrir.bat` → Mis datos → Crear perfil, y que cada uno complete lo
      suyo. No inventé datos de nadie.
- [ ] Una carpeta por persona con su `.env` y su `TELEGRAM_CHAT_ID`
      → **Ya no hace falta una carpeta por persona**: una instalación maneja N
      perfiles con corridas escalonadas (2.7). Lo que sí sigue siendo de cada
      uno es el `TELEGRAM_CHAT_ID`. **Ojo: hoy el chat_id es uno solo para toda
      la instalación**, así que si dos personas comparten PC, los dos avisos
      llegan al mismo Telegram. Se arregla poniendo el chat_id literal en el
      perfil de cada uno en vez de `${TELEGRAM_CHAT_ID}` — pero conviene que lo
      decidas vos, porque quizás preferís verlos todos.
- [x] Fuentes para rubros no técnicos (Bumeran / Zonajobs / Computrabajo) —
      **hechas, sin verificar**
- [x] Seguir perfiles de RRHH puntuales por URL — **hecho, sin verificar**

## Bloque 5 — Calidad de los resultados 🟡 CASI

- [x] Regla de Bahía Blanca
- [x] Duplicados entre fuentes
- [x] Descartar vacantes ya cubiertas
- [x] `notify_when_empty`
- [x] `use_search: false` en las 7 empresas
- [ ] **Cargar más empresas en `companies.json`** — sigue siendo tuyo: hay que
      elegirlas. Ahora se cargan desde la pantalla, una por línea.

## Bloque 6 — Vigilar 🟡 CASI

- [x] Ruido de posts de opinión en `google_posts`
- [x] País vacío en `google_posts`
- [x] Rareza geográfica de LinkedIn
- [ ] La pestaña de "shops" y las otras fuentes que mencionaste
- [ ] Recolección compartida entre los dos hermanos que se cruzan

## Fuera del checklist

- [ ] Verificar los tres portales y la fuente `rrhh` contra los sitios reales (1.2)
- [ ] Decidir la regla de remoto/ubicación (1.1)
- [ ] Corregir los moldes de mensaje (1.5)
- [ ] Decidir si cada perfil lleva su propio `TELEGRAM_CHAT_ID` (Bloque 4)
- [ ] Una corrida real de punta a punta con todo esto prendido. No la hice para
      no gastarte cuota ni escribir estado real de noche:
      `python -m vacantia.run --profile isaias --dry-run`

---

## Dónde está cada cosa

```
vacantia/
├── agenda.py         reparto de horarios entre perfiles
├── mensajes.py       moldes de DM y mail (borradores)
├── pdf.py            CV a PDF (ojo con la fuente Unicode)
├── ui/
│   ├── server.py     el servidor y las rutas
│   ├── data.py       todo lo que toca disco
│   ├── formulario.py la pestaña Mis datos
│   └── render.py     el HTML y el CSS
└── sources/
    ├── rrhh_profiles.py   seguir reclutadores por URL
    └── portales_ar.py     Bumeran / Zonajobs / Computrabajo
```
