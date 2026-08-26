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
  "notify_when_empty": false,      // avisar aunque no haya nada
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
  "location": { "country": "Argentina", "city": "" },
  "work_modes": ["remote", "hybrid"],
  "language": { "allow_english": false, "max_english_level": "A2" }
}
```

| | Efecto |
|---|---|
| `country` y `city` vacíos | ofertas de cualquier lado |
| sólo `country` | cualquier ciudad de ese país |
| `country` + `city` | únicamente esa ciudad |
| `work_modes` vacío | todas las modalidades |
| `work_modes: ["remote"]` | sólo remoto (lo que no aclara modalidad, pasa) |
| `allow_english: true` | avisos en español y en inglés |
| `allow_english: false` | sólo en español, y descarta los que pidan inglés B1+ |

Tanto `country` como `city` y `work_modes` aceptan un string o una lista.

**Regla transversal: lo que el aviso no dice, no filtra.** Si no aclara país,
modalidad o idioma, la oferta pasa igual — es preferible un falso positivo que
descartás de un vistazo antes que perder una oferta buena porque quien publicó
no completó un campo. Por lo mismo, sin LLM (scoring heurístico) no hay nada
extraído y los filtros dejan pasar todo.

Cada descarte queda en el log con su motivo (`LOG_LEVEL=DEBUG` para verlos).

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
  "region": "EU"
}
```

---

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
│   ├── base.py       interfaz Source: fetch() -> list[Job]
│   ├── careers.py    careers pages vía TinyFish
│   └── dummy.py      ofertas de ejemplo, para probar el pipeline sin credenciales
└── notifiers/
    ├── base.py       interfaz Notifier: send(jobs) -> bool
    ├── telegram.py   Telegram
    └── console.py    consola (fallback)
```

El estado vive en `state/<perfil>/` (`seen_jobs.json`, `last_run.json`, `job_history.json`),
así que dos perfiles no se pisan. Los borradores salen en `output/<perfil>/`.

---

## Agregar una fuente

1. Creá `sources/mi_fuente.py` con una clase que herede de `Source`, defina `name`
   e implemente `fetch() -> list[Job]`. Si necesita credenciales, sobreescribí
   `is_available()` para que el motor la saltee en vez de fallar.
2. Registrala en `SOURCE_REGISTRY` (`sources/__init__.py`).
3. Activala en el perfil: `{"type": "mi_fuente", "enabled": true}`.

Los notificadores funcionan igual con `Notifier` y `NOTIFIER_REGISTRY`.

**Próximas fases** (los TODO ya están puestos en `sources/__init__.py`):
`GooglePostsSource` (publicaciones vía Google) y `LinkedInJobsSource` (vía la librería JobSpy).

---

## Créditos

El motor de scoring, el wrapper de LLM, la lectura de careers pages con TinyFish y el
notificador de Telegram están adaptados de [autopilot-jobhunt](../autopilot-jobhunt).
