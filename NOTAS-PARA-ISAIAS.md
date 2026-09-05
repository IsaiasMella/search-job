# Notas para Isaías

**273 tests pasan.**

```
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest tests -q      →  273 passed
```

Andando todo: los 3 portales argentinos, LinkedIn Jobs, las páginas de empleo de
las empresas, seguir reclutadores, el scoring con Gemini y la pantalla.

---

# 1. LO QUE FALTA HACER

| # | Qué | Dónde | Cuánto lleva |
|---|---|---|---|
| 1 | **Usarlo una semana** y anotar qué falla antes de pasárselo a nadie | — | tuyo |

**Ya está instalado y corriendo solo** (5/9/2026). La tarea `Vacantia - isaias`
quedó registrada, con la próxima corrida a las 12:00 y los cuatro disparadores:
uno al iniciar sesión y tres diarios. No hay que prender nada.

Lo de armarle la carpeta a cada persona queda para después de la semana de
prueba: no tiene sentido repartir algo que todavía no sabés si tiene bugs.

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

## 2.3. Cómo hacer una corrida de prueba

`--dry-run` es el ensayo: **corre todo** (busca en las fuentes, saca duplicados,
puntúa con el modelo, aplica los filtros), **imprime el resultado por consola**
y **no manda nada por Telegram ni escribe el historial**.

Abrí PowerShell en la carpeta del proyecto y pegá esto:

```
.venv\Scripts\python.exe -m vacantia.run --profile isaias --dry-run
```

Vas a ver el detalle por consola. Cuando el resultado te convenza, la de verdad
es la misma línea sin `--dry-run`:

```
.venv\Scripts\python.exe -m vacantia.run --profile isaias
```

O directamente doble clic en `buscar_ahora.bat`, que hace eso mismo para todos
los perfiles.

**Ojo con una cosa**: `--dry-run` no ahorra plata. Sí gasta llamadas al modelo y
a TinyFish, porque para saber qué te traería hay que traerlo. Lo único que evita
es la notificación y ensuciar el historial.

Si querés ver el detalle de por qué descartó cada oferta:

```
$env:LOG_LEVEL="DEBUG"; .venv\Scripts\python.exe -m vacantia.run --profile isaias --dry-run
```

Y todo queda escrito en `vacantia.log` igual, aunque cierres la ventana.

**Cómo salió la primera, el 4/9/2026** (para tener con qué comparar):

```
careers 17 · google_posts 40 · linkedin 61 · rrhh 7   = 125 recolectadas
Dedupe:  78 nuevas de 125 (43 por URL repetida, 4 por empresa+título)
Triaje:  puntúo las 30 más prometedoras, dejo 48 para la próxima
Filtros: 8 pasaron, 22 descartadas
         1 de 8 pasó el min_score de 60
```

Las cuatro fuentes anduvieron. **Ojo con el embudo**, que explica por qué de 125
salió una sola:

- **`max_new_per_run: 30`** dejó 48 sin puntuar. No se pierden: entran en la
  corrida siguiente.
- **20 de las 30 puntuadas se cayeron por inglés**, y la mejor de ésas puntuaba
  90. Ese es tu cuello de botella, no la cantidad de ofertas.

## 2.4. Los mensajes al reclutador

Son los tuyos, los que ya usabas y con los que te contactaron. Están en
`vacantia/mensajes.py` y salen desde la pantalla, en cada oferta, con el link
*"Mensaje para escribirle"*.

Lo que **escribe el modelo** leyendo el aviso y tu CV: la lista de requisitos
con ✔️ (los del aviso que tu CV respalda, entre 3 y 6) y el nombre limpio del
puesto. Tiene prohibido listar algo que el CV no diga, porque eso se cae en la
primera entrevista y quema el contacto.

Lo que **decide el código y no el modelo**:

- **El cierre según el día.** Lunes "buen comienzo de semana", martes y
  miércoles "buen transcurso de semana", jueves y viernes "buen último sprint de
  la semana". Un modelo no sabe qué día es hoy: lo inventa.
- **Tu nombre y cómo te presentás**, del perfil.
- **El nombre de pila de quien publicó**, del aviso.

**Campo nuevo en la pantalla: "Cómo me presento".** Va tal cual en la frase
*"Mi nombre es Isaías, soy AI Engineer"*. Es aparte del "en una línea, qué hago"
porque ahí tenías cargado el stack entero y en el mensaje tiene que entrar en
media frase. Te lo dejé en `AI Engineer`.

## 2.5. Computrabajo devuelve 403 en el navegador

Probado el 5/9/2026, con la URL que me pasaste y con otras:

| | |
|---|---|
| El aviso, desde el navegador | ❌ **403 Forbidden** |
| **Cualquier página del sitio**, desde el navegador | ❌ **403 Forbidden** |
| La misma URL con una request HTTP común | ✅ 200, 173 KB |

O sea que **no es esa URL ni es nuestro código**: Computrabajo le contesta 403 a
tu navegador y 200 a un script. Al revés de lo normal. Es su detección de bots,
y desde acá no hay nada que hacer.

**Consecuencia práctica**: sus avisos entran a la lista pero después no los podés
abrir para postularte, que es lo único que importa. Por eso la fuente está
**apagada** y saqué de tu historial los 18 que habían quedado de las corridas de
verificación.

Si algún día querés reintentarla, prendé el tilde de Computrabajo en *Mis datos*,
corré `buscar_ahora.bat` y probá abrir un aviso. Si sigue dando 403, apagala de
nuevo: juntar avisos que no se pueden leer no sirve.

## 2.6. Si un portal deja de traer nada

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

## 2.7. LinkedIn: cómo se lo esquiva

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

## 2.8. La cuenta de Gemini

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

## 2.9. Qué pasa cuando corrés `instalar.bat`

**No queda ningún proceso corriendo, y no tenés que prender nada a mano.**

`instalar.bat` registra una **tarea programada de Windows** por perfil, llamada
`Vacantia - <nombre>`. Windows la despierta sola, ella busca, avisa por Telegram
y se cierra. Entre corrida y corrida no hay nada en memoria.

Se despierta:

- **Cuando iniciás sesión en Windows**, con 3 minutos de retraso (13 para el
  segundo perfil, para que no arranquen juntos).
- **En sus tres horarios del día.** Con un solo perfil son 12:00, 16:30 y 23:59.

Prendés la compu y a los 3 minutos ya está trabajando. **No es como tu otro
proyecto**: ahí hay que levantar el proceso a mano; acá no.

Tres detalles que están resueltos y conviene saber:

- **Si la compu estaba apagada a las 12:00**, la corrida no se pierde: se ejecuta
  cuando la prendés (`StartWhenAvailable`).
- **No abre ventana negra.** Usa `pythonw.exe`. El log igual se escribe en
  `vacantia.log`, así que no se pierde nada.
- **No se pisan entre sí**: si una corrida todavía no terminó, la siguiente se
  saltea en vez de encimarse.

Para ver si está programada, cuándo corrió y cómo le fue: doble clic en
`estado.bat`. Para que deje de correr: `desinstalar.bat`.

## 2.10. AI Engineer no es Machine Learning

Es la distinción que más plata cuesta si se confunde, y estaba mal cargada.

**Lo que hacés**: conectás modelos ya entrenados (OpenAI, LLMs open source) a un
producto. RAG, function calling, prompt engineering, agentes, APIs.

**Lo que NO hacés**: entrenar modelos, fine-tuning, armar redes neuronales.

Estaba mal en tres lugares a la vez, y por eso se colaba:

1. **Tu CV decía "Entrené un modelo de IA"** para el chatbot regulatorio, cuando
   en la misma línea el stack dice `RAG, LangChain, Chroma`, que es lo contrario.
   Corregido: *"Construí un sistema RAG sobre documentación regulatoria..."*.
2. **Las fuentes buscaban `Machine Learning Engineer`, `Data Scientist` y
   `MLOps`.** Por eso te llegaban. Ahora buscan AI Engineer, LLM Engineer,
   GenAI Engineer, AI Agent Engineer, Backend Python y Prompt Engineer.
3. **`not_suitable` no lo decía.** Ahora lo dice con todas las letras, y es lo
   que lee el que puntúa.

**El efecto, medido sobre la misma oferta**: pasó de **90 a 0**, con la razón
*"El candidato no hace Machine Learning ni entrena modelos, y el puesto es de
Machine Learning Engineer"*.

⚠️ **Las 207 ofertas que ya tenés guardadas conservan su puntaje viejo.** Se
puntuaron con el perfil equivocado. Sólo las corridas nuevas salen bien.

## 2.11. Los puestos que no querés ni pagar por puntuar

Los filtros de ubicación corren **después** del scoring, porque el país y la
ciudad los saca el modelo leyendo el aviso. Eso significaba pagar por puntuar un
Data Steward de Lima para tirarlo después.

Sobre tus 267: **86 traían en el título un puesto que no hacés**, y 34 de ésos
igual pasaron el min_score y te llegaron por Telegram.

**Campo nuevo en la pantalla: "Puestos que NO quiero"**, en *Qué busco*. Si el
título del aviso dice alguno de esos términos, se descarta **sin gastar una
llamada al modelo**. Te lo dejé cargado con 17:

```
Machine Learning, MLOps, Data Scientist, Data Science, Data Steward,
Data Engineer, Data Governance, Data Analyst, Custodio, Deep Learning,
Computer Vision, Quality Assurance, QA Automation, Power BI, Big Data,
Científico de Datos, Analista de Datos
```

**Agregá los que veas.** Cada término que sumás es plata que no se gasta.

Dos decisiones que conviene conocer:

1. **Mira sólo el TÍTULO, nunca la descripción.** Un aviso de AI Engineer
   nombra "machine learning" entre las tecnologías del equipo todo el tiempo, y
   descartarlo por eso sería tirar una oferta buena.
2. **Antes de puntuar sólo se filtra por título y por país**, aunque el sistema
   sepa filtrar por modalidad. Un híbrido en Bahía Blanca tiene que entrar
   aunque pidas sólo remoto, y para saber que es en Bahía Blanca hace falta la
   ciudad, que la completa el modelo. Descartar por modalidad antes de tener la
   ciudad tiraría justo ésas.

Medido sobre tus datos, con sólo lo que la fuente sabe antes de puntuar:
**75 de 267 se van sin pagar**, un 28% de las llamadas.

**El historial viejo ya se limpió** (5/9/2026). Tenía 267 ofertas puntuadas con
el perfil de antes: quedaron **147**. Se fueron 86 por título y 34 por ubicación.

Lo que **no** se tocó, a propósito:

- **Las 75 que piden inglés.** Son las del cartel, y el cartel está para que
  moleste. Borrarlas sería taparte el número.
- **Las que marques con verde o rojo.** Ese feedback no se puede recuperar.
- **`seen_jobs.json`**, que es la lista de lo ya visto. Las borradas siguen
  marcadas como vistas, así que no vuelven a entrar ni a costar plata.

El backup quedó en `state/isaias/job_history.bak-20260905-004107.json`. Si algún
día agregás términos a "Puestos que NO quiero" y querés volver a limpiar,
avisame y corro lo mismo.

---

# 3. LO QUE YA ESTÁ HECHO

Sin detalle, para no volver a discutirlo:

- **La pantalla local** (`abrir.bat`), con las pestañas Trabajos y Mis datos.
  Modo oscuro, navegable con teclado, usable en celular.
- **Marcar ofertas** con verde y rojo, con motivo obligatorio al descartar. Al
  marcarla se va de *Sin marcar* con una animación, y el cartel de arriba la
  nombra: con dos ofertas de 90 pegadas no se notaba cuál había desaparecido.
- **Apliqué y Descarté sirven para revisar**: ordenadas por cuándo las marcaste,
  con la fecha en la tarjeta. Para cuando te llaman y no te acordás a qué
  empresa le mandaste el CV.
- **Ordenadas por puntaje y de a 20 por página.** Antes ordenaba por fecha y la
  lista abría con lo peor: las que puntúan 0 son las que no son para vos, y si
  entraron hoy quedaban arriba de todo.
- **Aviso de ofertas nuevas sin apretar F5**: si entra una corrida con la
  pantalla abierta, aparece un cartel abajo y vos decidís cuándo actualizar.
- **Filtro por antigüedad del aviso**: hoy, 7 días, 30 días, sin filtro. Lee las
  cuatro formas distintas en que los portales escriben la fecha.
- **Cartel de cuántas ofertas se pierden por no saber inglés**, con cuánto
  puntuaba la mejor. Baja solo si subís tu nivel en Mis datos.
- **Fuentes**: páginas de empleo de empresas, LinkedIn Jobs, publicaciones de
  LinkedIn vía buscador, Bumeran, Zonajobs, Computrabajo, y reclutadores que
  seguís. Los tres portales argentinos verificados contra los sitios.
- **Seguir a un reclutador de LinkedIn** aunque LinkedIn no deje leer su perfil:
  se buscan sus publicaciones en Google y se leen ésas (2.7).
- **Scoring con Gemini** leyendo tu CV contra cada aviso, con cadena de modelos
  de respaldo.
- **Regla de ubicación** (2.1) y filtro de idioma.
- **Descarte antes del scoring** por título y por país, para no pagar por
  puntuar lo que ya se sabe que no sirve (2.10).
- **Duplicados**: por URL, por empresa más título, y entre fuentes distintas.
- **Vacantes ya cubiertas** se descartan antes de gastar una llamada al modelo.
- **Multi-perfil**: cada persona su perfil, su CV, su Telegram y su horario.
  `instalar.bat` reparte los horarios y programa las tareas de Windows.
- **Modo consejo**: qué reordenar del CV para un aviso. No lo reescribe nunca.
- **Mensajes para el reclutador**, DM y mail, calcados de los que ya funcionaban:
  el modelo arma la lista de requisitos leyendo el aviso contra el CV, y el
  cierre sale del día de la semana (2.4).
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
