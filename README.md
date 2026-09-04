# vacantia

Motor de búsqueda de trabajo con fuentes y canales de salida enchufables.

**Flujo:** fuentes → normalizar a `Job` → quitar duplicados → puntuar contra tu CV con un LLM → filtrar por `min_score` → notificar.

El motor no sabe nada de TinyFish ni de Telegram: sólo habla con las interfaces `Source` y `Notifier`. Agregar una fuente nueva (o cambiar de canal) no toca `engine.py`.

---

## Arrancar

```bash
cd vacantia
python -m venv .venv
.venv\Scripts\activate          # Windows;  en Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

copy .env.example .env          # Linux/macOS: cp .env.example .env
python -m vacantia.run --profile isaias
```

Ese comando corre de punta a punta. **No necesita ninguna credencial para funcionar:**
si falta `TINYFISH_API_KEY` se saltea la fuente de careers pages y usa `DummySource`;
si falta `OPENROUTER_API_KEY` puntúa con una heurística por keywords en vez del LLM;
si falta el token de Telegram imprime los resultados por consola. Cada cosa que falta
se avisa en el log y aparece en el resumen final de la corrida.

Para que sirva de verdad, cargá en `.env` al menos `OPENROUTER_API_KEY` (tiene free tier)
y reemplazá `resume/isaias.md` con tu CV.

---

## Credenciales (`.env`)

| Variable | Para qué | Si falta |
|---|---|---|
| `OPENROUTER_API_KEY` | Puntuar ofertas con un LLM | Scoring heurístico por keywords |
| `TINYFISH_API_KEY` | Leer careers pages de empresas | Se saltea la fuente `careers` |
| `TELEGRAM_TOKEN` + `TELEGRAM_CHAT_ID` | Avisar por Telegram | Sale por consola |

Alternativas al LLM: `LLM_PROVIDER=claude_cli` usa tu login local de Claude Code sin API key,
y `llm.provider = "anthropic"` en el perfil usa la API de Anthropic con `ANTHROPIC_API_KEY`.

---

## Perfiles

Cada persona es un JSON en `profiles/`. `--profile isaias` carga `profiles/isaias.json`.
`--list-profiles` muestra los que hay.

**No hace falta escribirlo a mano.** En la pantalla (`abrir.bat`), *Mis datos →
Crear perfil* genera `profiles/<nombre>.json` y `resume/<nombre>.md` a partir del
molde `profiles/example.json`, con todo en blanco y los huecos marcados
(`COMPLETAR`, `PEGAR CV ACÁ`) para que cada uno cargue lo suyo desde el
formulario. Una instalación puede tener varios perfiles conviviendo.

```jsonc
{
  "cv_path": "resume/isaias.md",   // tu CV en Markdown, se le pasa entero al LLM
  "keywords": ["data scientist", "MLOps", "Python"],
  "min_score": 60,                 // umbral 0-100 para avisar
  "top_n": 5,                      // cuántas mandar como máximo
  "notify_when_empty": true,       // avisar aunque no haya nada (ver abajo)
  "filters":   { ... },            // ubicación / modalidad / idioma (ver abajo)
  "candidate": { "name": "...", "profile": "...", "seeking": "...", "not_suitable": "..." },
  "llm":       { "provider": "openrouter", "model": "...", "fallback_models": ["..."] },
  "sources":   [ { "type": "careers", "enabled": true }, { "type": "dummy", "enabled": true } ],
  "notifiers": [ { "type": "telegram", "enabled": true }, { "type": "console", "enabled": true } ]
}
```

---

## Filtros

Se aplican después del scoring, sobre lo que el LLM extrae **del aviso** (no de
`companies.json`, que describe a la empresa: Globant publica ofertas de Bologna
y Pune bajo una entrada que dice "Buenos Aires").

```jsonc
"filters": {
  "location": { "country": "Argentina", "city": ["Bahía Blanca", "Punta Alta"] },
  "work_modes": ["remote"],
  "language": { "allow_english": false, "max_english_level": "A2" }
}
```

**Ubicación y modalidad se evalúan juntas** (la "regla de Bahía Blanca"), y el
país y la ciudad no filtran lo mismo:

| | Efecto |
|---|---|
| `country` vacío | ofertas de todo el mundo |
| `country` puesto | sólo de ese país — **también las remotas** |
| `city` vacía | cualquier lugar del país |
| `city` puesta (una o varias) | **sólo filtra presencial e híbrido**; el remoto entra venga de donde venga |
| `work_modes` vacío | todas las modalidades |
| `work_modes: ["remote"]` | sólo remoto… salvo un presencial en tu ciudad, que entra igual |
| `allow_english: true` | avisos en español y en inglés |
| `allow_english: false` | sólo en español, y descarta los que pidan inglés B1+ |

Las tres decisiones detrás de eso:

1. **El país filtra también al remoto.** "Remoto" no significa "desde cualquier
   parte del mundo": Argentina es enorme y muchísimas búsquedas remotas de
   Buenos Aires o Córdoba son para todo el país, que es justo lo que se busca.
   Al revés, un remoto de Colombia o México suele ser remoto *para* Colombia o
   México por temas legales de contratación, y traerlo es ruido.
   (`"remote_anywhere": true` vuelve al comportamiento sin filtro de país.)
2. **La ciudad filtra sólo lo presencial.** Un remoto publicado desde Córdoba se
   trabaja igual desde Bahía Blanca.
3. **Un presencial en tu ciudad entra aunque pidas sólo remoto.** Quien pone
   sólo remoto lo hace porque no se muda, no porque le moleste salir de su casa.
   Requiere que el aviso *diga* la ciudad: si no la dice, no se asume que sea la
   tuya.

`country`, `city` y `work_modes` aceptan un string o una lista. `home_city` es
el nombre viejo de `city` y se sigue leyendo en los perfiles que lo tengan.

**Regla transversal: lo que el aviso no dice, no filtra.** Si no aclara país,
modalidad o idioma, la oferta pasa igual — es preferible un falso positivo que
descartás de un vistazo antes que perder una oferta buena porque quien publicó
no completó un campo. Por lo mismo, sin LLM (scoring heurístico) no hay nada
extraído y los filtros dejan pasar todo.

Cada descarte queda en el log con su motivo (`LOG_LEVEL=DEBUG` para verlos).

---

## Corridas sin resultados

Con `notify_when_empty: true` el aviso llega igual, y explica **por qué** no hay
nada: cuántas ofertas se revisaron y de qué fuentes, cuántas ya estaban vistas,
cuántas eran vacantes ya cubiertas, cuántas se cayeron por cada filtro y si
alguna fuente no estuvo disponible. Sin eso, "hoy no salió nada" y "hace tres
días que la fuente está caída" son el mismo silencio y el segundo no se
descubre hasta que a alguien se le ocurre ir a mirar.

---

**Secretos en el perfil.** Un campo puede llevar el valor literal, o `"${NOMBRE_DE_VAR}"`
para leerlo del entorno, o quedar vacío y caer a la variable por defecto del campo
(`TINYFISH_API_KEY`, `TELEGRAM_TOKEN`, ...). Los perfiles del repo usan `${...}`, así que
se pueden versionar sin secretos adentro.

---

## Empresas

`companies.json` alimenta la fuente `careers`. Viene con una sola entrada de molde:
borrala y cargá las tuyas. Las entradas cuyo nombre empieza con `EJEMPLO` se ignoran.

```json
{
  "name": "Empresa SA",
  "careers_url": "https://empresa.com/careers/",
  "search_domain": "empresa.com",
  "location": "Barcelona, España / Remoto",
  "region": "EU",
  "use_search": true
}
```

La careers page se lee siempre. `"use_search": false` apaga sólo la búsqueda
por dominio de esa empresa: es la parte cara (la API no la batchea, va serial y
son ~3s por empresa), así que conviene apagarla en las que nunca devuelven
nada. En `companies.json` ya están apagadas las siete que no aportaron una sola
oferta.

---

## La pantalla local

```bash
python -m vacantia.ui          # http://localhost:8756, abre el navegador solo
```

En Windows: doble clic en `abrir.bat`. Escucha sólo en `127.0.0.1`, así que no
se ve desde otra máquina ni desde internet, y por eso no pide contraseña.

- **Trabajos** — las ofertas puntuadas, con dos botones: *Apliqué* (verde) y
  *No apliqué* (rojo). El rojo pide un motivo obligatorio; se guarda en
  `aplicado` / `motivo_descarte` / `fecha_feedback` dentro de
  `state/<perfil>/job_history.json`.
- **Mis datos** — el perfil sin tocar el JSON: CV, palabras clave, país/ciudad,
  modalidad, idioma, fuentes, empresas a seguir, perfiles de RRHH y las claves
  (que van al `.env`, no al perfil). Desde ahí también se crea un perfil nuevo
  en blanco para otra persona de la casa.

Cada oferta tiene además dos ayudas: **"Mensaje para escribirle"** (los moldes
de DM y mail) y **"Consejo para el CV"** — qué reordenar y qué palabra falta
para el filtro automático de la empresa, sin reescribir el CV. La lista de
términos del aviso que no están en tu CV sale sin gastar una llamada al modelo;
el consejo escrito se pide con un botón.

**El chat de Telegram es de cada persona, no de la computadora.** Las claves
—el token del bot, Gemini, TinyFish— se comparten entre todos los perfiles de la
máquina, pero el `chat_id` se guarda dentro de cada perfil: si en una misma PC
buscan dos personas, cada una recibe sólo sus ofertas. Vacío = usa el
`TELEGRAM_CHAT_ID` compartido del `.env`.

## Comandos

```bash
python -m vacantia.run --profile isaias              # corrida completa
python -m vacantia.run --profile isaias --dry-run    # imprime, no notifica ni guarda estado
python -m vacantia.run --profile isaias --min-score 70 --top-n 10
python -m vacantia.run --all                         # todos los perfiles
python -m vacantia.run --list-profiles

LOG_LEVEL=DEBUG python -m vacantia.run --profile isaias   # detalle por oferta
```

**`--dry-run` es el ensayo**: corre todo (fuentes, dedupe, scoring, filtros),
imprime el resultado por consola y **no manda Telegram ni escribe el historial**.
Sirve para ver qué haría sin ensuciar los datos ni gastar una notificación.
Ojo: sí gasta llamadas al LLM y a TinyFish, porque para saber qué traería hay
que traerlo.

> `python -m vacantia.drafter` todavía existe y genera un CV a medida de una
> oferta, pero **quedó fuera del camino principal**: la decisión fue no tocar el
> CV y usar el modo consejo de la pantalla. No lo llama ningún `.bat` ni la
> pantalla. Es candidato a borrarse.

El log completo siempre queda en `vacantia.log`, más allá de lo que se vea en consola.

## Varias personas en la misma computadora

Una instalación aguanta N perfiles, y busca para todos:

```bash
python -m vacantia.run --all      # todos, uno después del otro
python -m vacantia.agenda         # cómo quedaron repartidos los horarios
```

Las corridas **no arrancan todas juntas**, y no es un detalle: los límites del
plan gratis son de la *cuenta*, no del perfil (Gemini 5-15 req/min, TinyFish 30
búsquedas/min, OpenRouter 20/min). Dos personas de la misma casa comparten la
clave. `vacantia.agenda` reparte cada perfil 20 minutos después del anterior
sobre los tres horarios base:

```
ana     12:00, 16:30, 23:59
mario   12:20, 16:50, 00:19
zoe     12:40, 17:10, 00:39
```

El orden es alfabético, así agregar un perfil no le cambia el horario a media
familia. `instalar.bat` lee ese reparto y registra una tarea programada por
persona; `buscar_ahora.bat` corre `--all`. Además, dentro de una misma corrida
los lotes del scoring van espaciados 5 segundos (`llm.batch_delay`) y sigue
mandando el triaje `max_new_per_run`, que pone el techo en 5 llamadas al LLM por
corrida por más empresas o portales que se carguen.

---

## Estructura

```
vacantia/
├── run.py            entry point (--profile)
├── engine.py         el flujo: fuentes → quitar duplicados → scoring → filtro → notificación
├── models.py         Job: el modelo normalizado que hablan todas las fuentes
├── scoring.py        puntuar 0-100 contra el CV (LLM, con fallback heurístico)
├── llm.py            wrapper de LLM con cadena de fallback de OpenRouter
├── state.py          quitar duplicados y persistencia, namespaceada por perfil
├── config.py         carga de perfiles y resolución de secretos
├── filters.py        filtros de ubicación, modalidad e idioma
├── drafter.py        CV y carta a medida de una oferta
├── sources/
│   ├── base.py           interfaz Source: fetch() -> list[Job]
│   ├── careers.py        careers pages vía TinyFish
│   ├── google_posts.py   publicaciones de LinkedIn vía buscador (no toca LinkedIn)
│   ├── linkedin_jobs.py  LinkedIn Jobs vía JobSpy (sí scrapea LinkedIn)
│   └── dummy.py          ofertas de ejemplo, para probar el pipeline sin credenciales
└── notifiers/
    ├── base.py       interfaz Notifier: send(jobs) -> bool
    ├── telegram.py   Telegram
    └── console.py    consola (fallback)
```

El estado vive en `state/<perfil>/` (`seen_jobs.json`, `last_run.json`, `job_history.json`),
así que dos perfiles no se pisan. Los borradores salen en `output/<perfil>/`.

**Feedback.** `Job` tiene tres campos que escribe la persona, no el motor:
`aplicado` (verde/rojo/sin mirar), `motivo_descarte` y `fecha_feedback`. Se
guardan con `State.record_feedback(url, aplicado, motivo_descarte)` en
`job_history.json`, que es el archivo durable: una oferta que vuelve a aparecer
no pisa a la que ya está marcada. `State.feedback_jobs(aplicado=False)` devuelve
las descartadas de la más reciente a la más vieja. Todavía nada las escribe ni
las lee: es la base para la pestaña Trabajos y para meter esos ejemplos en el
prompt de scoring.

---

## Agregar una fuente

1. Creá `sources/mi_fuente.py` con una clase que herede de `Source`, defina `name`
   e implemente `fetch() -> list[Job]`. Si necesita credenciales, sobreescribí
   `is_available()` para que el motor la saltee en vez de fallar.
2. Registrala en `SOURCE_REGISTRY` (`sources/__init__.py`).
3. Activala en el perfil: `{"type": "mi_fuente", "enabled": true}`.

Los notificadores funcionan igual con `Notifier` y `NOTIFIER_REGISTRY`.

---

## Fuentes disponibles

| `type` | Qué trae | Credenciales | Toca LinkedIn |
|---|---|---|---|
| `careers` | Careers pages de las empresas de `companies.json` | `TINYFISH_API_KEY` | no |
| `google_posts` | Publicaciones de LinkedIn indexadas por un buscador | `TINYFISH_API_KEY` (o Google CSE) | **no** |
| `linkedin` | LinkedIn Jobs vía JobSpy | ninguna | **sí** |
| `rrhh` | Publicaciones de reclutadores que seguís por URL | `TINYFISH_API_KEY` | **no** |
| `bumeran` / `zonajobs` / `computrabajo` | Portales de empleo argentinos | `TINYFISH_API_KEY` | no |
| `dummy` | Ofertas de ejemplo para probar el pipeline | ninguna | no |

**`google_posts`** le pega a una search API con `site:linkedin.com/posts`: no hay
login ni scraping de LinkedIn, así que no hay riesgo para tu cuenta. Es la fuente
de menor competencia (posts sueltos de RRHH que no llegan a ningún portal), a
cambio de la latencia de indexación del buscador. Si el perfil tiene
`allow_english: false`, busca sólo con términos en español — filtrar en la query
evita traer decenas de posts que el filtro de idioma va a descartar igual.

**`google_posts`** además separa las ofertas del ruido: descarta los posts que
no mencionan ninguna búsqueda y los que usan ese vocabulario sin ofrecer nada
(gente buscando trabajo para sí misma, cursos, webinars, felicitaciones). Se
apaga con `"solo_ofertas": false`. El país sale del texto del post cuando lo
nombra; si no lo nombra queda vacío, salvo que se cargue `"default_country"`.

**`rrhh`** vigila **personas**, no palabras clave: se le carga una lista de URLs
y de cada una saca las búsquedas que publicó. Para nichos chicos suele rendir
más que buscar por keyword.

Sirven dos tipos de URL:

- **El perfil de LinkedIn de la persona** (`linkedin.com/in/nombre`). LinkedIn
  **no deja leer un perfil** sin sesión: devuelve la página vacía, y desde una
  IP común responde `HTTP 999`. Pero sus **posts sueltos sí se leen** y Google
  los indexa, así que la fuente no entra al perfil: busca
  `site:linkedin.com/posts "Nombre Apellido"` y lee esos posts. Los resultados
  se filtran por el identificador del perfil y no por el nombre, porque hay
  homónimos. Cuesta una búsqueda por persona y por corrida; se apaga con
  `"buscar_posts": false`.
- **La página de una consultora**, la que lista los puestos y no la de inicio.
  De ahí salen los links a publicaciones, los links con pinta de aviso, o —si no
  hay ninguno— los párrafos del texto que anuncian una búsqueda. Esos párrafos
  se identifican con la URL de la página más un hash del texto: por eso una
  página cuya dirección nunca cambia igual genera una oferta nueva cuando
  publica algo nuevo.

**Los tres portales argentinos** (`bumeran`, `zonajobs`, `computrabajo`) son los
que importan para los rubros no técnicos: ahí no hay careers pages ni posts de
LinkedIn, hay portal. **Verificados contra los sitios el 4/9/2026**: Bumeran 12
avisos, Zonajobs 5, Computrabajo 20. Igual cambian sin avisar, así que lo frágil
—la dirección de búsqueda y el patrón de URL de aviso— se puede pisar desde el
perfil con `search_url` y `job_url_pattern`, sin tocar código:

```jsonc
{ "type": "bumeran", "enabled": true, "location": "bahia-blanca",
  "search_url": "https://www.bumeran.com.ar/empleos-busqueda-{query}.html",
  "job_url_pattern": "/empleos/.+-\d+\.html" }
```

⚠️ **Bumeran y Zonajobs son la misma base de avisos** (los dos son de Navent) y
devuelven exactamente los mismos puestos con el mismo id. Prendé uno de los dos.
La pantalla lo avisa abajo del tilde de cada uno.

De cada aviso se leen **empresa, ciudad y modalidad** de la página del detalle,
que se baja igual para la descripción. Normalmente esos campos los completa el
LLM al puntuar; leerlos también en la fuente es lo que mantiene viva la regla de
ubicación cuando el modelo se cae.

**`linkedin`** sí scrapea LinkedIn, sin login. Rate-limitea por IP y se corta
cerca de la página 10, así que conviene `results_wanted` moderado y acotar con
`hours_old`. A cambio es la única fuente con datos **estructurados**: `is_remote`
y `location` vienen como campos propios, no como texto a interpretar, y
`scoring.py` respeta lo que la fuente ya trajo en vez de pisarlo con la
deducción del LLM. Si no está instalada (ver `requirements.txt`), el motor la
saltea con un aviso.

---

## Créditos

El motor de scoring, el wrapper de LLM, la lectura de careers pages con TinyFish y el
notificador de Telegram están adaptados de [autopilot-jobhunt](../autopilot-jobhunt).
