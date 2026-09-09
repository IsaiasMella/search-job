# vacantia

Busca ofertas de trabajo sola, las puntúa contra tu CV y te avisa por Telegram
sólo las que valen la pena.

Corre en tu propia computadora. No hay servidor, no hay cuenta que crear, y los
datos no salen de acá.

Este archivo tiene dos partes:

- **Parte 1: cómo se usa.** Para cualquiera. Tres archivos y una pantalla.
- **Parte 2: cómo se configura.** Para quien lo instala.

---
---

# PARTE 1 — CÓMO SE USA

## Instalarlo, una sola vez

**Doble clic en `instalar.bat`.** Tarda unos minutos: instala lo que necesita y
**programa las búsquedas automáticas**.

Hay que volver a correrlo sólo en dos casos: si agregás una persona nueva, o si
movés la carpeta de lugar.

> **Mientras no corras `instalar.bat`, nada se ejecuta solo.** Podés usar todo a
> mano igual, pero no va a buscar por su cuenta.

## Después de instalar, ¿tengo que prender algo?

**No.** No queda ningún programa corriendo ni ningún ícono que atender.

`instalar.bat` registra una **tarea programada de Windows** por persona. Windows
la despierta sola, ella busca, te avisa por Telegram y se cierra. Entre corrida
y corrida no hay nada consumiendo la máquina.

Se despierta:

- **Cuando iniciás sesión en Windows**, tres minutos después de prender.
- **En sus tres horarios del día.** Con una sola persona: 12:00, 16:30 y 23:59.

Prendés la compu y a los tres minutos ya está trabajando.

Tres cosas que están resueltas y conviene saber:

- **Si la compu estaba apagada a las 12:00, la corrida no se pierde**: se ejecuta
  cuando la prendas.
- **No abre ninguna ventana negra.** Igual queda todo escrito en `vacantia.log`.
- **No se pisan entre sí**: si una corrida todavía no terminó, la siguiente se
  saltea en vez de encimarse.

## Los tres archivos

| Archivo | Para qué | Cuándo |
|---|---|---|
| `instalar.bat` | Instala y programa las búsquedas | Una vez. Y de nuevo si agregás una persona o movés la carpeta |
| `abrir.bat` | **La pantalla**: todo lo demás | Todos los días |
| `desinstalar.bat` | Deja de buscar y borra el programa | Cuando conseguiste trabajo |

Eran cinco. *Buscar ahora* y *"¿esto anda?"* eran dos archivos más que había que
ir a abrir al Explorador, y ahora son un botón y una sección adentro de la
pantalla: **Buscar ahora**, al pie de la barra lateral, y **Cómo viene
funcionando**, abajo de todo en Métricas.

## La pantalla

Doble clic en `abrir.bat`. Se abre el navegador solo en `http://localhost:8756`.
**Dejá la ventana negra abierta** mientras la usás.

No sale a internet: sirve la página desde tu propia máquina. Por eso no pide
contraseña y nadie más la puede ver.

A la izquierda, fija, la barra de navegación: arriba el perfil (cada persona de
la casa tiene el suyo), después **Trabajos** y **LinkedIn URLs**, y abajo,
separadas, **Métricas** y **Mi perfil**.

Al pie de esa barra, siempre a la vista, **el estado del sistema**: cuándo buscó
por última vez, cuándo vuelve a buscar y de cuántos días de antigüedad trae
avisos. Está ahí para contestar la única pregunta que importa cuando la lista se
ve corta: *"¿esto es todo lo que hay?"*. Y abajo, el botón **Buscar ahora**, que
es la salida de ese dato.

### Trabajos

La lista de ofertas, ordenadas por qué tan bien te quedan. Cada una tiene:

- **El puntaje** de 0 a 100, y abajo la razón que escribió el modelo.
- **Un botón: Apliqué.** Es la acción que venís a hacer, y es el único en color.
  Al marcarla, **la tarjeta se va con una animación** y arriba aparece un cartel
  que la nombra: *"Aplicaste a «Python Senior Developer»"*. Con dos ofertas del
  mismo puntaje pegadas, sin eso no se nota cuál desapareció.
- **Al lado, No apliqué.** Al tocarlo se abre, adentro de la misma tarjeta, el
  motivo: un desplegable con los cuatro de siempre y un campo para escribir. Con
  cualquiera de los dos alcanza. Ese motivo es lo único que después sirve para
  que el sistema aprenda qué no mostrarte.
- **Un menú de tres puntos** en la esquina, con lo que no se usa todos los días:
  - **"Mensaje para escribirle"**: el mensaje para mandarle a quien publicó, por
    LinkedIn o por mail, escrito a partir del aviso y tu CV.
  - **"Consejo para el CV"**: qué reordenar y qué palabra falta para pasar el
    filtro automático de la empresa. **Nunca reescribe tu CV**: te dice qué mover
    para que lo edites vos.
  - **"Ya no está"**: para el aviso que bajaron o que quedó viejo. **No es lo
    mismo que descartar**: no pide motivo y no le enseña nada al sistema sobre lo
    que te gusta. Va a *Archivadas* y se puede devolver.

Lo demás está escondido a propósito: con seis controles a la vista por oferta,
cada tarjeta era una decisión de seis opciones en vez de una.

La lista va **ordenada por puntaje**, de la que mejor encaja a la que menos, y
**de a 20 por página**. El puntaje 0 lo sacan las que directamente no son para
vos, así que terminan al final.

Arriba hay dos filtros que se combinan:

- **Por estado**: sin marcar, apliqué, descarté, archivadas, todas. Al marcar una
  oferta se va de *Sin marcar* y aparece en su pestaña, así no perdés la cuenta
  de a cuáles ya les diste bola.
- **Por antigüedad del aviso**: hoy, últimos 7 días, últimos 30 días, sin filtro.
  Los avisos de hace un mes suelen estar cubiertos. Y hay un atajo para archivar
  de una todas las de más de 7, 14 o 30 días, que dice cuántas son antes de
  apretar.

**Apliqué y Descarté son para revisar, no para elegir**, así que se ordenan por
cuándo las marcaste, lo último arriba, y cada tarjeta dice cuándo fue. Sirven
para cuando te llaman y no te acordás a qué empresa le mandaste el CV, o para
releer por qué habías descartado algo. Esas tarjetas pierden el relieve y quedan
planas: de un vistazo se ve qué falta hacer y qué ya está hecho.

### LinkedIn URLs

El buscador trae lo que se publicó hace uno a tres días. Lo de hoy todavía no lo
indexó nadie, y son justo los avisos a los que menos gente se postuló. Acá van a
salir las direcciones de búsqueda de LinkedIn que los muestran, en dos pestañas:
**Jobs** y **Publicaciones**.

Por ahora es el lugar: las pestañas andan y dice qué va en cada una, pero todavía
no genera ninguna dirección.

### Métricas

Los totales, qué descartó el sistema sin preguntarte, por qué descartaste vos y
de qué portal viene cada oferta.

Y abajo de todo, **Cómo viene funcionando**: si está programado y cuándo vuelve,
cuánto tardó la última corrida y qué encontró, cuándo fue el último aviso por
Telegram, y las últimas quejas del registro.

Acá está también **cuántas ofertas se pierden por no saber inglés** y cuánto
puntuaba la mejor, con el link para cambiar tu nivel declarado al lado. Vive acá
y no arriba de la lista de trabajos a propósito: un número que no podés accionar,
leído todos los días antes de la primera oferta, es un reproche.

### Mi perfil

Todo lo tuyo, sin tocar ningún archivo: el CV, qué buscás, dónde, qué idioma,
de qué sitios traer ofertas, y tus claves.

Abajo de todo se crea el perfil de otra persona de la casa.

### ¿La pantalla muestra lo último, o hay que buscar de nuevo?

**Muestra siempre lo último que dejó la última búsqueda.** `abrir.bat` no busca:
sólo abre la pantalla, que lee el archivo donde quedaron guardadas las ofertas.

**Y si entran ofertas mientras la mirás, te avisa sola.** Aparece un cartel
abajo: *"Entraron 3 ofertas nuevas · Ver"*. Lo apretás y se actualiza.

No se recarga sola a propósito: si estás escribiendo el motivo de un descarte,
una recarga te lo borraría. Avisa, y decidís vos cuándo.

Para buscar en el momento, sin esperar el horario, está el botón **Buscar
ahora**, al pie de la barra lateral. Tarda unos minutos y podés seguir usando la
pantalla mientras tanto: cuando entren, el cartel de abajo te avisa.

> **Distinto es cuando cambia el código.** La pantalla carga el programa una sola
> vez, al arrancar: si alguien edita el código con la pantalla abierta, los
> cambios no se ven hasta cerrarla y volver a abrirla. Es normal, no es un error.
> **Las búsquedas programadas no tienen ese problema**: cada corrida arranca un
> proceso nuevo, así que siempre usan la última versión.
>
> En resumen: **ofertas nuevas → F5 alcanza. Código nuevo → cerrar y abrir.**

## Cuando algo no anda

**Primero, Métricas, abajo de todo: *Cómo viene funcionando*.** Te dice si está
programado, cuándo corrió por última vez, qué encontró, si te avisó por Telegram
y de qué se quejó.

**Después, `vacantia.log`.** Está todo ahí, incluso lo que no se ve en pantalla.
Lo que suele aparecer:

| Lo que dice el log | Qué significa |
|---|---|
| `0 aviso(s)` en un portal | El portal cambió sus direcciones. Ver *Portales argentinos* en la parte 2 |
| `0 publicación(es)` en `rrhh` | Pegaste la página de inicio de la consultora en vez de la que lista los puestos |
| `429 prepayment credits are depleted` | La cuenta de Gemini se quedó sin saldo. Ver *El modelo* en la parte 2 |
| `404 no longer available` | Google dio de baja ese modelo. Ver *El modelo* en la parte 2 |
| `[heurística, sin LLM]` | El modelo no respondió. **Los puntajes de esa corrida no significan nada**: sólo cuentan palabras del título |
| `falta TINYFISH_API_KEY` | Sin esa clave se saltean varias fuentes |

> **Un bloque rojo en la instalación no siempre es un error.** PowerShell pinta
> de rojo cualquier cosa que un programa escriba por la salida de errores,
> aunque el mensaje diga `INFO`. Si el bloque termina en `NativeCommandError` y
> el texto no dice que algo falló, la corrida está saliendo bien. Lo que vale es
> el `[OK]` de cada paso y el `LISTO` del final.

---
---

# PARTE 2 — CÓMO SE CONFIGURA

Todo lo de acá se puede hacer desde la pantalla, en *Mi perfil*. Lo que sigue es
el detalle de qué hace cada cosa y qué pasa por debajo.

## Cómo funciona por dentro

**Flujo:** fuentes → normalizar a `Job` → quitar duplicados → puntuar contra tu
CV con un modelo → filtrar → notificar.

El motor no sabe nada de TinyFish ni de Telegram: sólo habla con las interfaces
`Source` y `Notifier`. Agregar una fuente nueva no toca `engine.py`.

## Instalación a mano

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # Linux/macOS: cp .env.example .env
python -m vacantia.run --profile isaias
```

**No necesita ninguna credencial para arrancar**, pero cada cosa que falte
recorta lo que hace, y se avisa en el log y en el resumen final.

## Credenciales (`.env`)

| Variable | Para qué | Si falta |
|---|---|---|
| `GEMINI_API_KEY` | Puntuar ofertas con un modelo | Puntaje heurístico por keywords, que no sirve |
| `TINYFISH_API_KEY` | Leer páginas de empleo, portales y posts | Se saltean esas fuentes |
| `TELEGRAM_TOKEN` + `TELEGRAM_CHAT_ID` | Avisar por Telegram | Sale por consola |
| `OPENROUTER_API_KEY` | Plan B del modelo | — |

Se cargan desde la pantalla y se guardan en `.env`, que **no se sube a git**.

**Secretos en el perfil.** Un campo puede llevar el valor literal, o
`"${NOMBRE_DE_VAR}"` para leerlo del entorno. Los perfiles del repo usan `${...}`,
así que se pueden versionar sin secretos adentro.

## El modelo

```jsonc
"llm": {
  "provider": "gemini",
  "model": "gemini-3.5-flash-lite",
  "fallback_models": ["gemini-flash-lite-latest", "gemini-3.6-flash"]
}
```

Si fallan los tres, el log distingue dos causas que se parecen y no son lo mismo:

- **`404 no longer available`**: Google dio de baja ese modelo. Los vigentes
  salen de `https://generativelanguage.googleapis.com/v1beta/models?key=TU_KEY`.
- **`429 prepayment credits are depleted`**: la cuenta se quedó sin saldo. **No
  es el límite diario.** Se arregla en <https://ai.studio/projects>.

Ante una falla de cuenta la cadena corta enseguida en vez de reintentar los tres
modelos: probar el siguiente no arregla que la cuenta esté en cero.

**Plan B**: `"provider": "openrouter"`. Techo de 50 llamadas por día, que alcanza
para una corrida diaria por persona.

## El perfil

Cada persona es un JSON en `profiles/`. `--profile isaias` carga
`profiles/isaias.json`; `--list-profiles` muestra los que hay.

**No hace falta escribirlo a mano**: la pantalla lo genera en blanco con los
huecos marcados.

```jsonc
{
  "cv_path": "resume/isaias.md",   // el CV en Markdown, se le pasa entero al modelo
  "keywords": ["AI Engineer", "Python"],
  "min_score": 60,                 // umbral 0-100 para avisar
  "top_n": 5,                      // cuántas mandar como máximo
  "max_new_per_run": 30,           // techo de llamadas al modelo por corrida
  "notify_when_empty": true,
  "filters":   { ... },
  "candidate": { "name": "...", "headline": "...", "profile": "...",
                 "seeking": "...", "not_suitable": "..." },
  "llm":       { ... },
  "sources":   [ { "type": "careers", "enabled": true } ],
  "notifiers": [ { "type": "telegram", "enabled": true } ]
}
```

### `candidate`, y por qué `not_suitable` es el campo más importante

- **`name`** — el nombre.
- **`headline`** — cómo se presenta, dos o tres palabras. Va tal cual en el
  mensaje al reclutador: *"Mi nombre es Isaías, soy AI Engineer"*.
- **`profile`** — qué hace, en una línea.
- **`seeking`** — qué busca.
- **`not_suitable`** — **qué NO sirve.** Lo lee el que puntúa, y es lo que separa
  dos oficios que se confunden todo el tiempo.

> **Ejemplo real, y caro.** Conectar modelos ya entrenados a un producto (RAG,
> function calling, agentes) **no es Machine Learning**: entrenar modelos es otro
> oficio, y en la entrevista se nota en la primera pregunta. Mientras
> `not_suitable` no lo decía, una búsqueda de *Machine Learning Engineer* puntuaba
> **90**. Con la distinción escrita, la misma oferta puntúa **0**:
> *"El candidato no hace Machine Learning ni entrena modelos"*.
>
> Y cuidado con el CV, que es de donde sale todo: si dice *"entrené un modelo"*
> cuando en realidad construiste un RAG, el sistema te va a ofrecer lo que no
> hacés y el mensaje al reclutador lo va a repetir.

## Filtros

### Antes del scoring, para no pagar de más

`filters.excluir_titulos` es una lista de puestos. Si el **título** del aviso
nombra alguno, se descarta sin llamar al modelo. Sobre un historial real de 267
ofertas eso son 75 llamadas menos, un 28%.

```jsonc
"filters": { "excluir_titulos": ["Machine Learning", "MLOps", "Data Steward"] }
```

Mira **sólo el título**: un aviso de AI Engineer nombra "machine learning" entre
las tecnologías del equipo todo el tiempo, y descartarlo por eso sería tirar una
oferta buena.

También se descarta antes lo que la fuente ya dijo que es de otro país. **Sólo
el país, y a propósito**: un híbrido en tu ciudad tiene que entrar aunque pidas
sólo remoto, y para saber en qué ciudad es hace falta el dato que completa el
modelo. Filtrar por modalidad antes de tenerlo tiraría justo ésas.

### Después del scoring

Se aplican después del scoring, sobre lo que el modelo extrae **del aviso** (no
de `companies.json`, que describe a la empresa: Globant publica ofertas de
Bologna y Pune bajo una entrada que dice "Buenos Aires").

```jsonc
"filters": {
  "location": { "country": "Argentina", "city": ["Bahía Blanca", "Punta Alta"] },
  "work_modes": ["remote"],
  "language": { "allow_english": false, "max_english_level": "A2" }
}
```

**Ubicación y modalidad se evalúan juntas**, y el país y la ciudad no filtran lo
mismo:

| | Efecto |
|---|---|
| `country` vacío | ofertas de todo el mundo |
| `country` puesto | sólo de ese país, **también las remotas** |
| `city` vacía | cualquier lugar del país |
| `city` puesta (una o varias) | **sólo filtra presencial e híbrido**; el remoto entra venga de donde venga |
| `work_modes` vacío | todas las modalidades |
| `work_modes: ["remote"]` | sólo remoto, salvo un presencial en tu ciudad, que entra igual |
| `allow_english: true` | avisos en español y en inglés |
| `allow_english: false` | sólo en español, y descarta los que pidan inglés B1+ |

Las tres decisiones detrás de eso:

1. **El país filtra también al remoto.** "Remoto" no significa "desde cualquier
   parte del mundo": muchísimas búsquedas remotas de Buenos Aires o Córdoba son
   para todo el país, que es justo lo que se busca. Al revés, un remoto de
   Colombia o México suele ser remoto *para* Colombia o México por temas legales
   de contratación. (`"remote_anywhere": true` vuelve al comportamiento sin
   filtro de país.)
2. **La ciudad filtra sólo lo presencial.** Un remoto publicado desde Córdoba se
   trabaja igual desde Bahía Blanca.
3. **Un presencial en tu ciudad entra aunque pidas sólo remoto.** Quien pone
   sólo remoto lo hace porque no se muda, no porque le moleste salir de la casa.
   Requiere que el aviso *diga* la ciudad: si no la dice, no se asume que sea la
   tuya.

`country`, `city` y `work_modes` aceptan un string o una lista. `home_city` es
el nombre viejo de `city` y se sigue leyendo.

**Regla transversal: lo que el aviso no dice, no filtra.** Es preferible un falso
positivo que descartás de un vistazo antes que perder una oferta buena porque
quien publicó no completó un campo.

Cada descarte queda en el log con su motivo (`LOG_LEVEL=DEBUG` para verlos).

## Corridas sin resultados

Con `notify_when_empty: true` el aviso llega igual y explica **por qué** no hubo
nada: cuántas ofertas se revisaron y de qué fuentes, cuántas ya estaban vistas,
cuántas se cayeron por cada filtro y si alguna fuente no estuvo disponible.

Sin eso, "hoy no salió nada" y "hace tres días que la fuente está caída" son el
mismo silencio, y el segundo no se descubre hasta que a alguien se le ocurre ir a
mirar.

## Fuentes disponibles

| `type` | Qué trae | Credenciales | Toca LinkedIn |
|---|---|---|---|
| `careers` | Páginas de empleo de las empresas de `companies.json` | `TINYFISH_API_KEY` | no |
| `google_posts` | Publicaciones de LinkedIn indexadas por un buscador | `TINYFISH_API_KEY` (o Google CSE) | **no** |
| `linkedin` | LinkedIn Jobs vía JobSpy | ninguna | **sí** |
| `rrhh` | Búsquedas de los reclutadores que seguís | `TINYFISH_API_KEY` | **no** |
| `bumeran` / `zonajobs` / `computrabajo` | Portales de empleo argentinos | `TINYFISH_API_KEY` | no |
| `dummy` | Ofertas de ejemplo para probar el pipeline | ninguna | no |

### Antigüedad máxima

`filters.max_age_days` en el perfil. **Una sola, de la persona, no de cada
fuente**: lo que sirve depende del rubro y no del portal. Para un AI Engineer una
búsqueda de hace 7 días ya está cubierta de postulantes; para un supervisor de
seguridad e higiene en el campo una de hace un mes sigue viva. Repartida en seis
bloques de fuente, quedaba desincronizada sin que nadie se enterara.

La resuelve `Source._resolver_antiguedad`, en este orden:

1. `max_age_days` en el bloque de la fuente — el escape para el caso puntual.
2. `filters.max_age_days` del perfil — **la que se configura**, desde *Mi perfil*.
3. `max_age_days_default` de la clase (`rrhh` usa 30; el resto, 7).

`0` apaga la ventana. Se compara contra `None` y no por verdadero/falso, porque
`0` es un valor válido y no "sin configurar".

Cada fuente la aplica como puede: `google_posts` y `rrhh` se la pasan al buscador
(`recency_minutes` / `dateRestrict`), `linkedin` la traduce a `hours_old`, y los
portales argentinos filtran después de bajar el detalle, que es donde aparece la
fecha. **Un aviso sin fecha nunca se descarta**: lo que no dice, no filtra.

### `google_posts`

Le pega a una search API con `site:linkedin.com/posts`: no hay login ni scraping,
así que no hay riesgo para tu cuenta. Es la fuente de **menor competencia** (posts
sueltos de RRHH que no llegan a ningún portal), a cambio de la latencia de
indexación del buscador.

Separa las ofertas del ruido: descarta los posts que no mencionan ninguna
búsqueda y los que usan ese vocabulario sin ofrecer nada (gente buscando trabajo
para sí misma, cursos, webinars, felicitaciones). Se apaga con
`"solo_ofertas": false`.

Si el perfil tiene `allow_english: false` busca sólo con términos en español:
filtrar en la query evita traer decenas de posts que el filtro va a descartar
igual.

**Ventana de tiempo — `filters.max_age_days` del perfil, 7 por defecto.** La
búsqueda pide sólo lo publicado en esos días. La resuelve `Source`, así que la
heredan todas las fuentes; ver **Antigüedad máxima** más abajo. Sin ella el buscador ordena por relevancia y la fecha le
da igual: medido sobre el historial real el 7/9/2026, de 75 publicaciones 28
tenían más de un mes y había posts de 2020, 2023 y 2024. Cada uno de ésos se
puntúa con el LLM antes de descartarse.

La ventana va **en la búsqueda**, no después de recibir los resultados: filtrar
al final devolvería una página de 10 posts viejos y cero utilizables. El chequeo
posterior (`es_reciente`) existe igual, para lo que se cuela — el buscador
aproxima el borde. Un post **sin fecha** pasa: lo que el aviso no dice, no filtra.

Segunda razón para pedirla, menos evidente: **la API sólo devuelve el campo
`date` cuando se le pide una ventana.** Sin ella los 10 resultados venían sin
fecha, y por eso más de la mitad del historial no tenía `posted_at`.

Cuanto más angosta, menos resultados: la misma query devolvió 10 publicaciones
con 7 días y 2 con 1 día. `"max_age_days": 0` la apaga.

| Proveedor | Cómo se pide |
|---|---|
| `tinyfish` | `recency_minutes` (días × 1440) |
| `google_cse` | `dateRestrict=d7` — el equivalente del `&tbs=qdr:` que se le pone a mano a una búsqueda de Google |

### `rrhh`

Vigila **personas**, no palabras clave. Para nichos chicos suele rendir más que
buscar por keyword. Sirven dos tipos de URL:

- **El perfil de LinkedIn de la persona** (`linkedin.com/in/nombre`). LinkedIn
  **no deja leer un perfil** sin sesión: devuelve la página vacía, y desde una IP
  común responde `HTTP 999`. Pero sus **posts sueltos sí se leen** y Google los
  indexa, así que la fuente no entra al perfil: busca
  `site:linkedin.com/posts "Nombre Apellido"` y lee esos posts. Filtra por el
  identificador del perfil y no por el nombre, porque hay homónimos. Cuesta una
  búsqueda por persona y por corrida; se apaga con `"buscar_posts": false`. Esa
  búsqueda tiene su propia ventana de tiempo, `"max_age_days": 30`, más ancha que
  la de `google_posts` a propósito: acá se sigue a alguien puntual, que puede
  pasarse tres semanas sin publicar.
- **La página de una consultora**, la que lista los puestos y no la de inicio. De
  ahí salen los links a publicaciones, los links con pinta de aviso, o —si no hay
  ninguno— los párrafos del texto que anuncian una búsqueda. Esos párrafos se
  identifican con la URL más un hash del texto: por eso una página cuya dirección
  nunca cambia igual genera una oferta nueva cuando publica algo.

### Portales argentinos

`bumeran`, `zonajobs` y `computrabajo` son los que importan para los rubros no
técnicos: ahí no hay páginas de empleo ni posts de LinkedIn, hay portal.

**Verificados contra los sitios el 4/9/2026**: Bumeran 12 avisos, Zonajobs 5,
Computrabajo 20. Igual cambian sin avisar, y el síntoma es `0 aviso(s)` en el
log. Se arregla sin tocar código:

```jsonc
{ "type": "bumeran", "enabled": true, "location": "bahia-blanca",
  "search_url": "https://www.bumeran.com.ar/empleos-busqueda-{query}.html",
  "job_url_pattern": "/empleos/.+-\d+\.html" }
```

Buscá algo a mano en el portal, copiá la dirección de la barra del navegador y
reemplazá el término buscado por `{query}`. Abrí dos o tres avisos y mirá qué
tienen en común sus direcciones: eso va en `job_url_pattern`.

⚠️ **Bumeran y Zonajobs son la misma base de avisos** (los dos son de Navent) y
devuelven los mismos puestos con el mismo id. **Prendé uno de los dos.** La
pantalla lo avisa abajo del tilde de cada uno.

De cada aviso se leen **empresa, ciudad, modalidad y fecha de publicación** de la
página del detalle, que se baja igual para la descripción. Los tres primeros los
completa normalmente el modelo al puntuar; leerlos también en la fuente es lo que
mantiene viva la regla de ubicación cuando el modelo se cae.

La **fecha** no la llenaba nadie: medido el 7/9/2026 sobre 216 avisos, los tres
portales reportaban `posted_at` en **cero** de sus 20. Eso dejaba ciego al filtro
de antigüedad de la pantalla justo ahí — un aviso de Bumeran de dos meses pasaba
el filtro de "hoy" por no tener con qué compararse. Formatos:

| Portal | Cómo la escribe |
|---|---|
| Computrabajo | `Hace 6 días (actualizada)`, `Ayer` — suelta, al final de la descripción |
| Bumeran / Zonajobs | `## Publicado hace más de 15 días` (tope, impreciso) y `Publicado el 20/08/2026` (exacta, más abajo) — se prefiere la exacta |

⚠️ **La trampa**: al pie, los tres listan *ofertas similares* con **sus** fechas.
La primera fecha del documento puede ser de otro aviso. `_solo_este_aviso` corta
el texto donde arrancan los ajenos.

> ⚠️ **Computrabajo devolvía `403 Forbidden` en el navegador, y la causa era la
> UI. Arreglado con `rel="noreferrer"` en los links al aviso** (ver
> `ABRIR_EL_AVISO` en `ui/render.py`, que lleva la medición completa).
>
> Al abrir un aviso desde la pantalla, el navegador mandaba el referrer
> `http://127.0.0.1:8756`. Computrabajo lo guarda en su cookie `extrfr`, y desde
> ahí **todos** los pedidos del navegador al sitio llevaban una URL a loopback
> dentro de una cookie — firma de SSRF. El WAF que tiene delante
> (`server: awselb/2.0`) respondía 403 en el sitio entero hasta borrar la cookie.
> No fallaba un aviso: el primer clic desde la UI rompía todos los siguientes.
>
> Verificado el 7/9/2026 armando la cookie a mano:
> `extrfr=http://127.0.0.1:8756/trabajos` → 403; `extrfr=http://localhost:...` →
> 403; escapada → 403; `extrfr=https://ejemplo.com/x` → 200; sin esquema → 200;
> sin cookie → 200.
>
> Nunca afectó al scraping: la fuente lee por TinyFish, con otra IP y sin cookies.
> Corrige dos diagnósticos previos equivocados (5/9: "el sitio 403ea a cualquier
> navegador"; 7/9 temprano: "lo rompe una ráfaga de pedidos").

### `linkedin`

Sí scrapea LinkedIn, sin login. Rate-limitea por IP y se corta cerca de la página
10, así que conviene `results_wanted` moderado y acotar con `hours_old`.

A cambio es la única fuente con datos **estructurados**: `is_remote` y `location`
vienen como campos propios, no como texto a interpretar, y `scoring.py` respeta
lo que la fuente ya trajo en vez de pisarlo con la deducción del modelo. Si no
está instalada (ver `requirements.txt`), el motor la saltea con un aviso.

## Empresas

`companies.json` alimenta la fuente `careers`. Se edita desde la pantalla. Las
entradas cuyo nombre empieza con `EJEMPLO` se ignoran.

```json
{
  "name": "Empresa SA",
  "careers_url": "https://empresa.com/careers/",
  "search_domain": "empresa.com",
  "use_search": true
}
```

La página de empleo se lee siempre. `"use_search": false` apaga sólo la búsqueda
por dominio de esa empresa: es la parte cara (la API no la batchea, va serial y
son ~3s por empresa), así que conviene apagarla en las que nunca devuelven nada.

## Varias personas en la misma computadora

Una instalación aguanta N perfiles y busca para todos:

```bash
python -m vacantia.run --all      # todos, uno después del otro
python -m vacantia.agenda         # cómo quedaron repartidos los horarios
```

Las corridas **no arrancan todas juntas**, y no es un detalle: los límites del
plan gratis son de la *cuenta*, no del perfil. Dos personas de la misma casa
comparten la clave. `vacantia.agenda` reparte cada perfil 20 minutos después del
anterior:

```
ana     12:00, 16:30, 23:59
mario   12:20, 16:50, 00:19
zoe     12:40, 17:10, 00:39
```

El orden es alfabético, así agregar un perfil no le cambia el horario a media
familia. `instalar.bat` lee ese reparto y registra una tarea por persona.

**El chat de Telegram es de cada persona, no de la computadora.** Las claves se
comparten, pero el `chat_id` se guarda dentro de cada perfil: si en una misma PC
buscan dos personas, cada una recibe sólo sus ofertas. Vacío = usa el
`TELEGRAM_CHAT_ID` compartido del `.env`.

Para cargarlo: que la persona le escriba a su bot, abrí
`https://api.telegram.org/bot<TOKEN>/getUpdates`, buscá `"chat":{"id":...}` y
pegá el número en la pantalla, en *Mi Telegram*.

## Comandos

```bash
python -m vacantia.run --profile isaias              # corrida completa
python -m vacantia.run --profile isaias --dry-run    # imprime, no notifica ni guarda
python -m vacantia.run --profile isaias --min-score 70 --top-n 10
python -m vacantia.run --all                         # todos los perfiles
python -m vacantia.run --list-profiles

LOG_LEVEL=DEBUG python -m vacantia.run --profile isaias   # detalle por oferta
```

**`--dry-run` es el ensayo**: corre todo (fuentes, dedupe, scoring, filtros),
imprime el resultado por consola y **no manda Telegram ni escribe el historial**.
Ojo: sí gasta llamadas al modelo y a TinyFish, porque para saber qué traería hay
que traerlo. Lo único que evita es la notificación y ensuciar los datos.

En PowerShell, para el modo detallado:

```
$env:LOG_LEVEL="DEBUG"; .venv\Scripts\python.exe -m vacantia.run --profile isaias --dry-run
```

El log completo siempre queda en `vacantia.log`, más allá de lo que se vea en
consola.

> `python -m vacantia.drafter` todavía existe y genera un CV a medida de una
> oferta, pero **quedó fuera del camino principal**: la decisión fue no tocar el
> CV y usar el modo consejo de la pantalla. No lo llama ningún `.bat` ni la
> pantalla. Es candidato a borrarse.

## Estructura

```
vacantia/
├── run.py            entry point (--profile)
├── engine.py         el flujo: fuentes → dedupe → scoring → filtros → notificación
├── models.py         Job: el modelo normalizado que hablan todas las fuentes
├── scoring.py        puntuar 0-100 contra el CV, con fallback heurístico
├── llm.py            cadena de modelos, y distinguir sus errores
├── state.py          quitar duplicados y persistencia, por perfil
├── config.py         carga de perfiles y resolución de secretos
├── filters.py        ubicación, modalidad e idioma
├── fechas.py         leer el 'posted_at' de cada portal (4 formatos distintos)
├── agenda.py         reparto de horarios entre perfiles
├── mensajes.py       los mensajes al reclutador (DM y mail)
├── consejo.py        qué reordenar del CV, sin reescribirlo
├── drafter.py        CV a medida (fuera del camino principal)
├── ui/
│   ├── server.py     el servidor y las rutas
│   ├── data.py       todo lo que toca disco
│   ├── formulario.py la pestaña Mi perfil
│   ├── render.py     el HTML
│   ├── estilos.py    el CSS: los tokens de DESIGN.md, una sola vez
│   └── corrida.py    buscar ahora, y como viene funcionando el motor
├── sources/
│   ├── base.py            interfaz Source: fetch() -> list[Job]
│   ├── careers.py         páginas de empleo vía TinyFish
│   ├── google_posts.py    publicaciones de LinkedIn vía buscador
│   ├── linkedin_jobs.py   LinkedIn Jobs vía JobSpy
│   ├── rrhh_profiles.py   los reclutadores que seguís
│   ├── portales_ar.py     Bumeran / Zonajobs / Computrabajo
│   └── dummy.py           ofertas de ejemplo, sin credenciales
└── notifiers/
    ├── base.py       interfaz Notifier: send(jobs) -> bool
    ├── telegram.py   Telegram
    └── console.py    consola (fallback)
```

El estado vive en `state/<perfil>/` (`seen_jobs.json`, `last_run.json`,
`job_history.json`), así que dos perfiles no se pisan.

**Feedback.** `Job` tiene tres campos que escribe la persona, no el motor:
`aplicado`, `motivo_descarte` y `fecha_feedback`. Se guardan con
`State.record_feedback(...)` en `job_history.json`, que es el archivo durable:
una oferta que vuelve a aparecer no pisa a la que ya está marcada.
`State.feedback_jobs(aplicado=False)` devuelve las descartadas de la más reciente
a la más vieja. **Todavía nada las lee**: es la base para meter esos ejemplos en
el prompt de scoring y que el sistema aprenda.

## Agregar una fuente

1. Creá `sources/mi_fuente.py` con una clase que herede de `Source`, defina
   `name` e implemente `fetch() -> list[Job]`. Si necesita credenciales,
   sobreescribí `is_available()` para que el motor la saltee en vez de fallar.
2. Registrala en `SOURCE_REGISTRY` (`sources/__init__.py`).
3. Agregala a `FUENTES` en `ui/formulario.py` para que se pueda prender desde la
   pantalla.
4. Activala en el perfil: `{"type": "mi_fuente", "enabled": true}`.

Los notificadores funcionan igual con `Notifier` y `NOTIFIER_REGISTRY`.

## Tests

```bash
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest tests -q      →  401 passed
```

---

## Créditos

El motor de scoring, el wrapper de LLM, la lectura de páginas de empleo con
TinyFish y el notificador de Telegram están adaptados de
[autopilot-jobhunt](../autopilot-jobhunt).
