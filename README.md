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
Usá `profiles/example.json` como molde y `--list-profiles` para ver los que hay.

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
  "location": { "country": "Argentina", "city": "", "home_city": "Bahía Blanca" },
  "work_modes": ["remote", "hybrid"],
  "language": { "allow_english": false, "max_english_level": "A2" }
}
```

| | Efecto |
|---|---|
| `country` y `city` vacíos | ofertas de cualquier lado |
| sólo `country` | cualquier ciudad de ese país |
| `country` + `city` | únicamente esa ciudad |
| `home_city` | la ciudad donde vivís — ver la regla de abajo |
| `remote_anywhere: false` | aplica el filtro de país también a las remotas |
| `work_modes` vacío | todas las modalidades |
| `work_modes: ["remote"]` | sólo remoto (lo que no aclara modalidad, pasa) |
| `allow_english: true` | avisos en español y en inglés |
| `allow_english: false` | sólo en español, y descarta los que pidan inglés B1+ |

Tanto `country` como `city` y `work_modes` aceptan un string o una lista.

**Ubicación y modalidad se evalúan juntas (la "regla de Bahía Blanca").** Por
separado se perdían ofertas: quien pone `work_modes: ["remote"]` lo hace porque
no se muda, no porque le moleste salir de su casa, y un presencial *en su
ciudad* le sirve igual. Entonces:

1. **Remoto en cualquier lado** — si el aviso dice remoto, la ubicación no
   filtra (se apaga con `remote_anywhere: false`).
2. **Presencial o híbrido en `home_city`** — pasa aunque `work_modes` pida sólo
   remoto. Requiere que el aviso *diga* la ciudad: si no la dice, no se asume
   que sea la tuya. Si no cargás `home_city` se usa `city`.
3. Todo lo demás, como siempre: primero modalidad, después ubicación.

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

## Comandos

```bash
python -m vacantia.run --profile isaias              # corrida completa
python -m vacantia.run --profile isaias --dry-run    # imprime, no notifica ni guarda estado
python -m vacantia.run --profile isaias --min-score 70 --top-n 10
python -m vacantia.run --list-profiles

python -m vacantia.drafter --profile isaias --job 1  # CV + carta a medida de la oferta #1
python -m vacantia.drafter --profile isaias --job https://...

LOG_LEVEL=DEBUG python -m vacantia.run --profile isaias   # detalle por oferta
```

El log completo siempre queda en `vacantia.log`, más allá de lo que se vea en consola.

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
| `dummy` | Ofertas de ejemplo para probar el pipeline | ninguna | no |

**`google_posts`** le pega a una search API con `site:linkedin.com/posts`: no hay
login ni scraping de LinkedIn, así que no hay riesgo para tu cuenta. Es la fuente
de menor competencia (posts sueltos de RRHH que no llegan a ningún portal), a
cambio de la latencia de indexación del buscador. Si el perfil tiene
`allow_english: false`, busca sólo con términos en español — filtrar en la query
evita traer decenas de posts que el filtro de idioma va a descartar igual.

**`rrhh`** vigila **personas**, no palabras clave: se le carga una lista de URLs
(el perfil de actividad de alguien de RRHH, la página de búsquedas de una
consultora) y de cada una saca los links a publicaciones, los links con pinta de
aviso, o —si no hay ninguno— los párrafos del texto que anuncian una búsqueda.
Esos párrafos se identifican con la URL de la página más un hash del texto: por
eso una página cuya dirección nunca cambia igual genera una oferta nueva cuando
publica algo nuevo. Para nichos chicos suele rendir más que buscar por keyword.

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
