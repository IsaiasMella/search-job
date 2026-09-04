# Notas para Isaías

**242 tests pasan.**

```
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest tests -q      →  242 passed
```

Andando: los 3 portales argentinos, LinkedIn Jobs, las páginas de empleo de las
empresas, el scoring con Gemini y la pantalla. Lo único que no se puede hacer es
seguir a un reclutador por su perfil de LinkedIn (ver 2.5).

---

# 1. LO QUE FALTA HACER

| # | Qué | Dónde | Cuánto lleva |
|---|---|---|---|
| 1 | **Corregir los moldes de mensaje** con tu experiencia | `vacantia/mensajes.py`, ver 2.3 | 10 min |
| 2 | Una **corrida real** de punta a punta con todo prendido | `--dry-run` primero | 10 min |
| 3 | **Cargar el chat de Telegram de cada persona** cuando armes sus carpetas | ver 2.2 | 1 min c/u |
| 4 | **Correr `instalar.bat` de nuevo** cuando haya más de un perfil | — | 5 min |

Sin empezar, y afuera a propósito: **que el sistema aprenda de tus descartes**.
`State.feedback_jobs(aplicado=False, limit=15)` ya devuelve las últimas
descartadas con su motivo; falta meterlas en `scoring.SCORE_PROMPT` como
ejemplos negativos. Media hora, y ahora que el LLM anda tiene sentido.

---

# 2. LO QUE TENÉS QUE SABER PARA USARLO

## 2.1. Cómo filtra por ubicación

| Campo | Qué hace |
|---|---|
| `country` vacío | de todo el mundo |
| `country: "Argentina"` | **sólo Argentina, también el remoto** |
| `city` vacía | cualquier lugar del país |
| `city: ["Bahía Blanca", "Punta Alta"]` | **sólo filtra presencial e híbrido**; el remoto entra venga de donde venga |
| `work_modes: ["remote"]` | sólo remoto, salvo un presencial en tus ciudades, que entra igual |

Las tres reglas que pediste:

1. **El remoto tiene que ser de Argentina.** Un remoto de Buenos Aires o Córdoba
   para todo el país entra; uno de Colombia o México, que por temas legales sólo
   contrata allá, no.
2. **La ciudad no filtra el remoto.** Un remoto de Córdoba se trabaja igual desde
   Bahía Blanca.
3. **Un presencial en tus ciudades entra aunque pidas sólo remoto.**

Tu perfil: `country: "Argentina"`, `city: "Bahía Blanca"`. Se edita en la
pantalla, en *"Ciudades a las que puedo ir en persona"*, separadas por coma.

**Escape hatch**: si algún día querés remoto de cualquier país,
`"remote_anywhere": true` dentro de `filters.location`. Está apagado.

## 2.2. Telegram: cada persona su chat

Las claves se comparten (el token del bot, Gemini, TinyFish son de la máquina)
**pero el chat de Telegram no**. Si dos personas usan la misma computadora y no
cargás esto, **los dos reciben todo en el mismo teléfono**.

Por persona:

1. Que le escriba a su bot de Telegram y le mande cualquier cosa.
2. Sacá su `chat_id`: abrí `https://api.telegram.org/bot<TOKEN>/getUpdates` y
   buscá `"chat":{"id":...}`.
3. Pantalla → elegí su perfil arriba a la derecha → *Mi Telegram* → pegá el
   número → Guardar.

Vacío = usa el `TELEGRAM_CHAT_ID` del `.env`, o sea el tuyo.

## 2.3. Los moldes de mensaje son borradores

Están en `vacantia/mensajes.py`. **Ajustalos**: tu experiencia es más fresca que
la de quien los escribió.

```
Hola {nombre}, vi la búsqueda de {puesto}.
Trabajo con {área} hace {X} años; lo último fue {logro}.
¿Te sirve que te pase el CV?
```

Lo de las llaves lo completa el modelo leyendo el aviso y tu CV, con un botón.
Sin usar el modelo los huecos quedan a la vista a propósito: es más honesto que
un mensaje genérico disfrazado de personalizado.

## 2.4. Si un portal deja de traer nada

Los portales cambian sus direcciones sin avisar. Se arregla sin programar, en
`profiles/isaias.json`, en el bloque de esa fuente:

```jsonc
{
  "type": "bumeran",
  "enabled": true,
  "search_url": "PEGAR una búsqueda real, con {query} donde va el puesto",
  "job_url_pattern": "un pedazo común a las direcciones de aviso, ej: /empleos/"
}
```

Buscá algo a mano en el portal, copiá la dirección de la barra del navegador y
reemplazá el término buscado por `{query}`. Abrí dos o tres avisos y mirá qué
tienen en común sus direcciones: eso va en `job_url_pattern`.

El síntoma es `0 aviso(s)` en `vacantia.log`.

## 2.5. LinkedIn: cómo se lo esquiva

Probado el 4/9/2026 contra un perfil real:

| | |
|---|---|
| Post suelto (`/posts/...`) | ✅ se lee |
| Búsqueda de LinkedIn Jobs | ✅ se lee |
| **Perfil de persona** (`/in/...`) | ❌ **vacío**, y `HTTP 999` desde tu IP |
| Página de empresa (`/company/...`) | ❌ vacío |

**El perfil de una persona no se puede leer**, y no hay forma de arreglarlo sin
poner usuario y contraseña, que es lo que haría que te bloqueen la cuenta.

**Pero se lo esquiva y ya está hecho.** Cuando cargás un perfil de LinkedIn en
*Mis datos*, el sistema no entra al perfil: le pregunta a Google cuáles son las
publicaciones de esa persona y lee ésas, que sí se pueden leer. Vos pegás el
perfil y funciona; el rodeo es invisible.

Filtra por el identificador del perfil, no por el nombre: buscando "Renzo Bazan"
aparecían otras dos personas que se llaman igual.

Cuesta **una búsqueda por reclutador y por corrida**. Se apaga con
`"buscar_posts": false` en el bloque `rrhh` del perfil.

**Ojo, no confundir**: la fuente `google_posts` **también** trae publicaciones de
LinkedIn, pero busca por puesto ("AI Engineer" y señales de que contratan), de
cualquiera. Esto otro busca por persona, la que vos elegiste seguir. Son
complementarias.

## 2.6. La cuenta de Gemini

Si un día el log dice que fallaron los modelos, son dos causas distintas:

- **`404 no longer available`**: Google dio de baja ese modelo. Los vigentes
  salen de `https://generativelanguage.googleapis.com/v1beta/models?key=TU_KEY`
  y se cambian en el perfil, en `llm.model` y `llm.fallback_models`.
- **`429 prepayment credits are depleted`**: la cuenta se quedó sin saldo. No es
  el límite diario. Se arregla en <https://ai.studio/projects>.

**Plan B probado**: tu key de OpenRouter funciona. Se cambia poniendo
`provider: "openrouter"` en el perfil. Techo de 50 llamadas por día, que alcanza
para una corrida diaria.

Cuando el LLM se cae, el sistema no se rompe: cae a una heurística que sólo
cuenta keywords en el título. **Los puntajes de esas corridas no significan
nada** y se reconocen porque salen todos apelotonados y el log dice
`[heurística, sin LLM]`.

---

# 3. LO QUE YA ESTÁ HECHO

Sin detalle, para no volver a discutirlo:

- **La pantalla local** (`abrir.bat`), con las pestañas Trabajos y Mis datos.
  Modo oscuro, navegable con teclado, usable en celular.
- **Marcar ofertas** con verde y rojo, con motivo obligatorio al descartar.
- **Filtro por antigüedad del aviso**: hoy, 7 días, 30 días, sin filtro. Lee las
  cuatro formas distintas en que los portales escriben la fecha.
- **Cartel de cuántas ofertas se pierden por no saber inglés**, con cuánto
  puntuaba la mejor. Baja solo si subís tu nivel en Mis datos.
- **Fuentes**: páginas de empleo de empresas, LinkedIn Jobs, publicaciones de
  LinkedIn vía buscador, Bumeran, Zonajobs, Computrabajo, y reclutadores que
  seguís. Los tres portales argentinos verificados contra los sitios.
- **Seguir a un reclutador de LinkedIn** aunque LinkedIn no deje leer su perfil:
  se buscan sus publicaciones en Google y se leen ésas (2.5).
- **Scoring con Gemini** leyendo tu CV contra cada aviso, con cadena de modelos
  de respaldo.
- **Regla de ubicación** (2.1) y filtro de idioma.
- **Duplicados**: por URL, por empresa más título, y entre fuentes distintas.
- **Vacantes ya cubiertas** se descartan antes de gastar una llamada al modelo.
- **Multi-perfil**: cada persona su perfil, su CV, su Telegram y su horario.
  `instalar.bat` reparte los horarios y programa las tareas de Windows.
- **Modo consejo**: qué reordenar del CV para un aviso. No lo reescribe nunca.
- **Moldes de mensaje** para DM y mail (borradores, ver 2.3).
- **Notificación por Telegram**, con aviso opcional cuando no hubo nada.

**Descartado a propósito:**

- **CV en PDF**: salía feo. Se borró todo. El CV en Markdown sigue en `resume/`
  y se edita desde la pantalla. No volver a construirlo sin acordarse de esto.
- **Recolección compartida entre hermanos**: cada uno en su compu, todo aislado.
  Además es lo que hace que LinkedIn no bloquee, porque cada casa aporta su
  propia IP residencial.
- **Hosting en un servidor**: empeora lo de la IP. Una IP de datacenter es justo
  el rango que LinkedIn filtra primero.

---

# 4. IDEAS, NO PENDIENTES

- **Que las ofertas lleguen por mail** además de por Telegram, para tu viejo. El
  motor ya tiene la interfaz `Notifier` lista (`vacantia/notifiers/`): agregar un
  canal es un archivo, no tocar el motor.
- **Un filtro "sólo las que puedo tomar"**, que esconda las que ya cayeron por
  idioma o ubicación. Hoy aparecen mezcladas con las que sí servís.
- **Que la pantalla muestre el resumen de la última corrida**, que hoy está en
  `estado.bat`.
- **Reescribir el `README.md`** como guía de instalación para cada persona.

---

# 5. LOS ARCHIVOS

Los cinco `.bat` son todo lo que tocan las personas que no programan:

| Archivo | Para qué | Cuándo se usa |
|---|---|---|
| `instalar.bat` | Instala todo y programa las búsquedas automáticas | Una vez al principio, y de nuevo cada vez que agregues un perfil o muevas la carpeta |
| `abrir.bat` | **La pantalla**: ver las ofertas y cargar los datos | Todos los días |
| `buscar_ahora.bat` | Una búsqueda ya, sin esperar el horario | Cuando no querés esperar |
| `estado.bat` | "¿Esto anda?": si está programado, cuándo corrió, cómo le fue | Cuando algo parece raro |
| `desinstalar.bat` | Deja de buscar y borra el programa. Pregunta aparte si borrar los datos | Cuando consiguieron trabajo |

El resto:

| | |
|---|---|
| `README.md` | La documentación técnica |
| `NOTAS-PARA-ISAIAS.md` | Este archivo |
| `companies.json` | Las empresas que sigue la fuente `careers`. Se edita desde la pantalla |
| `.env` | Las claves. Se edita desde la pantalla. **No se sube a git** |
| `.env.example` | El molde del `.env`, sin claves |
| `requirements.txt` | Lo que instala `instalar.bat` |
| `requirements-dev.txt` | pytest. Sólo para vos |
| `conftest.py` | Deja que los tests encuentren el paquete |
| `vacantia.log` | Todo lo que pasó. Es lo primero que hay que mirar cuando algo falla |
| `profiles/` `resume/` `state/` `output/` | Perfiles, CVs, ofertas guardadas y documentos generados |
| `vacantia/` `tests/` `scripts/` | El programa, sus pruebas, y los scripts de PowerShell que usan los `.bat` |

Dónde está cada cosa del código:

```
vacantia/
├── agenda.py         reparto de horarios entre perfiles
├── consejo.py        qué reordenar del CV (no lo reescribe)
├── fechas.py         leer el 'posted_at' de cada portal (4 formatos)
├── mensajes.py       moldes de DM y mail (borradores)
├── filters.py        la regla de ubicación, modalidad e idioma
├── scoring.py        el prompt que puntúa cada aviso contra el CV
├── llm.py            la cadena de modelos y sus errores
├── ui/
│   ├── server.py     el servidor y las rutas
│   ├── data.py       todo lo que toca disco
│   ├── formulario.py la pestaña Mis datos
│   └── render.py     el HTML y el CSS
└── sources/
    ├── rrhh_profiles.py   seguir reclutadores por URL
    └── portales_ar.py     Bumeran / Zonajobs / Computrabajo
```
