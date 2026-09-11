# Guía práctica: cazar vacantes de AI Engineer Senior publicadas como POSTEOS en el feed de LinkedIn (para Isaias)

## TL;DR
- **Sí funciona y es un canal distinto al buscador de empleos**: LinkedIn tiene una búsqueda de CONTENIDO (`linkedin.com/search/results/content/`) donde podés cazar los posteos de reclutadores y líderes técnicos que anuncian vacantes de AI Engineer como publicación normal, a menudo antes de que salgan en la pestaña Jobs. La clave es filtrar por "Publicaciones", ordenar por "Más recientes" y usar frases-gatillo en español + el clúster de títulos AI Engineer. Como resume iProfesional: *"hay mucho trabajo que se publica como un posteo común y no llega a la sección de empleos"*.
- **Lo más potente hoy (2026)**: URLs de búsqueda de contenido editables con `keywords`, `datePosted` y `sortBy=date_posted`, combinadas con boolean (AND/OR/NOT en MAYÚSCULAS y comillas para frases exactas), más seguir a reclutadores concretos con la campanita activada. OJO: LinkedIn **eliminó el "seguir hashtag"** en octubre de 2024, así que el hashtag hoy sirve para BUSCAR, no para recibir en el feed.
- **Para maximizar entrevistas sin inglés fluido**: priorizá cuentas argentinas/LATAM que postean en español (Empleos IT Argentina, Chumi-IT, reclutadoras locales), guardá 4-6 URLs de búsqueda como favoritos, revisalas 2 veces por día, y postulate rápido (primeras horas) con un comentario corto + DM personalizado. Complementá con Telegram y Discord de habla hispana.

## Key Findings

1. **La búsqueda de contenido es un canal real y comprobado.** Medios y reclutadores confirman que muchas empresas publican vacantes como posteo en lugar de usar la pestaña Jobs. Una razón concreta es de costo: según el desglose de precios 2026 de Pin ("LinkedIn Job Posting Pricing 2026"), el aviso gratis está *"limited to one listing at a time with a 14-day active window"*, mientras que los posteos promocionados cuestan *"$7-$10/day minimum on a pay-per-click model, averaging $2.83 per applicant in the U.S."* — así que muchas empresas avisan gratis vía posteo. Estos avisos no salen en el buscador de empleos.
2. **Llegar temprano importa más que nunca.** Según datos de LinkedIn presentados en Talent Connect 2026, *"total US applicants per role on LinkedIn have doubled since 2022"*, y el 65% de los candidatos dice que buscar empleo se volvió más difícil por la competencia (HR Brew/Fortune, 7 ene. 2026). Cazar el posteo recién publicado te pone entre los primeros y contra pocos postulantes.
3. **Las URLs de contenido son editables**, aunque con menos parámetros que Jobs. Los que funcionan: `keywords`, `datePosted` (`past-24h`, `past-week`, `past-month`), `sortBy` (`date_posted` o `relevance`) y `origin`.
4. **El boolean funciona en la barra de búsqueda de contenido**: AND, OR, NOT (en MAYÚSCULAS), comillas para frases exactas y paréntesis para agrupar. No funcionan comodines (`*`), ni `+`/`-`, ni corchetes.
5. **Los hashtags ya NO se pueden "seguir"** desde octubre de 2024; hoy sirven como palabras clave de búsqueda. El descubrimiento en el feed pasa por a quién seguís y con quién interactuás.
6. **Seguir reclutadores + campanita** es hoy el mecanismo más confiable para que las vacantes te lleguen al feed apenas se publican.
7. **Hay ecosistema argentino/LATAM en español**: cuentas como Empleos IT Argentina, Chumi-IT, reclutadoras que postean "AI Engineer Buenos Aires", más Telegram y Discord con canal de ofertas.

## Details

### 1) Cómo buscar POSTEOS (no personas ni empleos) que sean ofertas

**Paso a paso (desktop):**
1. Escribí tu búsqueda en la barra de arriba y dale Enter.
2. En la fila de pestañas de resultados (People, Jobs, Posts...), hacé clic en **"Publicaciones" / "Posts"**. Esto te muestra contenido publicado por personas y empresas, no listados formales.
3. Hacé clic en **"Todos los filtros"** para afinar. Los filtros disponibles en contenido son: **Ordenar por** (Sort by: "Principales" / "Recientes"), **Fecha de publicación** (Date posted), **Tipo de contenido** (Content type — incluye "Publicaciones de empleo/Job posts"), **De un miembro** (From member), **De una empresa** (From company), **Publicado por** (Posted by: 1er grado / personas que sigo / todos), **Que menciona a miembro/empresa**, **Sector del autor** (Author industry) y **Empresa del autor** (Author company).
4. Poné **Ordenar por → "Recientes/Latest"**. Esto es clave: ves lo recién publicado y competís contra pocos postulantes.
5. Poné **Fecha de publicación → "Últimas 24 horas"** para lo más fresco.
6. **Guardá la URL como favorito** en el navegador: todos los filtros quedan guardados en la URL, así no rehacés nada.

> Término LinkedIn en una línea: **"Contenido/Posts"** = la pestaña que busca dentro de las publicaciones del feed (texto de los posteos), distinta de "Empleos" que busca dentro de los avisos formales.

**Formato de la URL de contenido y parámetros vigentes (2026):**
- Base: `https://www.linkedin.com/search/results/content/`
- `keywords=` → tus palabras/boolean (URL-encoded).
- `datePosted=` → `"past-24h"`, `"past-week"` o `"past-month"`.
- `sortBy=` → `"date_posted"` (recientes) o `"relevance"`.
- `origin=FACETED_SEARCH` (aparece cuando aplicás filtros).
- `postedBy=` → por ejemplo `["first","following"]` para ver solo de tu red / a quién seguís.
- `authorCompany=["<id>"]` → filtra por empresa del autor (ej. bookmarkear posteos de empleados de una empresa concreta).

**URLs listas para copiar y pegar (editá keywords según necesites):**

Recientes, últimas 24 h, AI Engineer + hiring en español:
```
https://www.linkedin.com/search/results/content/?keywords=("AI Engineer" OR "LLM Engineer" OR "GenAI Engineer") AND (buscamos OR "estamos buscando" OR vacante)&datePosted="past-24h"&sortBy="date_posted"&origin=FACETED_SEARCH
```

Última semana, clúster completo + Argentina/remoto:
```
https://www.linkedin.com/search/results/content/?keywords=("AI Engineer" OR "ML Engineer" OR "Machine Learning Engineer" OR "GenAI" OR "LLM Engineer") AND (Argentina OR remoto OR LATAM) AND (buscamos OR hiring OR vacante)&datePosted="past-week"&sortBy="date_posted"&origin=FACETED_SEARCH
```

Solo de gente que seguís / 1er grado (para tu lista de reclutadores):
```
https://www.linkedin.com/search/results/content/?keywords=("AI Engineer" OR "Applied AI" OR "RAG" OR "AI Agent") AND (buscamos OR hiring)&datePosted="past-week"&sortBy="date_posted"&postedBy=["first","following"]&origin=FACETED_SEARCH
```

> Nota honesta: LinkedIn cambia estos parámetros seguido y a veces la app móvil no respeta todos. Si una URL "no filtra", rehacé los filtros a mano desde "Todos los filtros" y volvé a guardar la URL nueva. Reportes de usuarios dicen que a veces no aparecen todos los posteos: si pasa, alterná entre "Recientes" y "Principales" y entre 24 h y semana.

### 2) Boolean y frases-gatillo listas para copiar

**Qué funciona hoy en la búsqueda de contenido (2026):** AND, OR, NOT en MAYÚSCULAS; comillas `" "` para frases exactas; paréntesis `( )` para agrupar. **No funcionan:** comodín `*`, operadores `+`/`-`, corchetes `[ ]`/`{ }`. Mantené los strings cortos (si son muy largos LinkedIn los interpreta mal; dividilos en dos búsquedas).

**Frases-gatillo reales en español que usan los reclutadores:**
"estamos buscando", "buscamos", "nos encontramos en la búsqueda de", "se suma al equipo", "sumamos", "se une al equipo", "vacante", "posición abierta", "búsqueda abierta", "oportunidad laboral", "estamos contratando", "abrimos búsqueda". (La táctica de buscar "buscamos" en Posts la popularizó en TikTok la exreclutadora **@mimiworkbestie**, según iProfesional: *"muchas empresas no se limitan a utilizar la sección de trabajo, sino que directamente realizan una publicación. Para encontrarlas, se debe escribir en la sección del buscador la palabra 'buscamos'"*.)

**En inglés (para roles remotos LATAM):**
"we're hiring", "we are hiring", "we are looking for", "now hiring", "open role", "open position", "join our team", "hiring".

**Strings listos (pegá en la barra, elegí pestaña Posts):**

Núcleo AI Engineer + gatillos español:
```
("AI Engineer" OR "LLM Engineer" OR "GenAI Engineer" OR "Applied AI Engineer" OR "ML Engineer" OR "Machine Learning Engineer") AND (buscamos OR "estamos buscando" OR "nos encontramos en la búsqueda" OR vacante OR "posición abierta")
```

Con foco Argentina/remoto y stack:
```
("AI Engineer" OR "ML Engineer" OR "GenAI") AND (Python OR RAG OR LLM OR FastAPI) AND (Argentina OR remoto OR LATAM) AND (buscamos OR hiring OR vacante)
```

Excluyendo junior/semi (usás NOT):
```
("AI Engineer" OR "LLM Engineer" OR "Machine Learning Engineer") AND (buscamos OR hiring) NOT (Junior OR Semisenior OR Ssr OR trainee OR pasantía)
```

Inglés remoto LATAM:
```
("AI Engineer" OR "LLM Engineer" OR "GenAI Engineer" OR "ML Engineer") AND ("we're hiring" OR "we are looking for" OR "open role" OR "join our team") AND (LATAM OR remote OR Argentina)
```

X-Ray de Google como refuerzo (encuentra posteos que LinkedIn a veces oculta):
```
site:linkedin.com/posts ("AI Engineer" OR "LLM Engineer") (buscamos OR hiring OR vacante) (Argentina OR remoto OR LATAM)
```

### 3) Hashtags: cuáles sirven de verdad y cómo usarlos hoy

**Realidad 2026 (honesta):** LinkedIn **eliminó la opción de "seguir" hashtags** en octubre de 2024 y deshabilitó las páginas/feed de hashtag (los tags dejaron de ser clicables en desktop), citando "bajo uso". Rishi Jobanputra, Senior Director of Product Management for Feed de LinkedIn, calificó a los hashtags como *"a nice to have, not a need to have"*, y agregó en video: *"we used to have a hashtag feed in the past, but people were not really using it. So, we are actually in the process of getting rid of it"* (Digital Information World, jul. 2025). Hoy el hashtag funciona como palabra clave de búsqueda/SEO, NO como suscripción que llena tu feed. Aún así, buscarlos sirve para encontrar posteos.

**Cómo usarlos ahora:** escribí el hashtag en la barra, entrá a la pestaña **Publicaciones**, y ordená por **Recientes**. Podés combinar hashtag + boolean (ej. `#AIjobs AND Argentina`).

**Hashtags Argentina/LATAM con uso real (tech/IT/empleo):**
`#empleosIT`, `#empleos`, `#empleo`, `#trabajo`, `#busquedalaboral`, `#vacante`, `#vacantes`, `#trabajoremoto`, `#contratando`, `#oportunidadlaboral`, `#reclutamiento`, `#empleosargentina`, `#trabajoIT`, `#sistemas`, `#tecnología`.

**Hashtags IA/tech (internacionales, para remoto):**
`#AIjobs`, `#MachineLearning`, `#hiring`, `#hiringnow`, `#techjobs`, `#remotejobs`, `#Python`, `#LLM`, `#GenAI`, `#dataengineering`, `#MLjobs`, `#AIEngineer`.

> Truco: como no podés "seguir" el hashtag, convertí tus hashtags favoritos en **URLs de búsqueda guardadas** (ver sección 1). Es el reemplazo funcional del hashtag seguido.

### 4) Identificar y seguir a los reclutadores correctos

**Cómo encontrarlos:**
- Buscá en pestaña **Personas**: `("IT recruiter" OR "tech recruiter" OR "talent acquisition" OR "reclutador IT") AND Argentina` y filtrá por ubicación Argentina.
- Cuando encuentres un posteo bueno de vacante, entrá al perfil del autor y **seguilo**.
- En cada empresa objetivo, buscá a su gente de Talent/RRHH y seguila.

**Cómo activar la campanita (notificaciones de posteos):**
1. Entrá al perfil de la persona.
2. Si la seguís/conectás, arriba a la derecha aparece una **campana**. Desde 2024, al seguir o conectar se activa automáticamente una campana gris (te avisa de lo más relevante que publique).
3. Hacé clic para elegir recibir **todo** lo que publica (icono de doble campana) en lugar de solo lo relevante. Así te enterás apenas postea una vacante.

**Cuentas y reclutadores concretos del ecosistema argentino/LATAM (verificados por investigación):**

*Individuos (postean vacantes como posteo):*
- **Agustina Urdapilleta** (Recruiter, "The Agency", Argentina) — `linkedin.com/in/agustinaurdapilleta/`. Postea semanalmente vacantes incluyendo "AI Engineer (Buenos Aires)", Data, Python; posteos en español, foco Argentina. El mejor match individual para AI + español.
- **Juan Ignacio Solito** (Recruiter, Intelletec) — `linkedin.com/in/juan-ignacio-solito-6bb02b118/`. Roles dev/IT, algunos Rosario/Argentina en español.
- **Giovanna Pinheiral** (Recruiter, Zallpy Digital, LATAM) — `linkedin.com/in/giovannapinheiral/`. Data Science/ML/GenAI/LLMs en LATAM (incluye Argentina), posteos en español/portugués.

*Páginas/empresas (postean vacantes IT/AI como contenido):*
- **Empleos IT Argentina** — `linkedin.com/company/empleositar` (31.050 seguidores). El portal IT #1 de Argentina; postea "búsquedas destacadas" semanales en español, foco Argentina, incluye Python. Top pick por volumen. Tiene también Telegram (`@empleositar`).
- **Chumi-IT** — `linkedin.com/company/chumi-it` (chumijobs.com). Vacantes Data & Analytics/AI en LATAM, posteos en español.
- **BEON.tech** — `linkedin.com/company/beontechlatam`. Staff augmentation con HQ en Buenos Aires; página de AI Engineering y Python. OJO: los roles **exigen inglés**.
- **AgileEngine** — `linkedin.com/company/agileengine`. Consultora con talento en Argentina; filtros de GenAI/ML/Python. Inglés generalmente requerido.

> Aclaración honesta: los datos de los reclutadores individuales vienen de vistas previas de LinkedIn; confirmá nombre/URL logueado. Las firmas de staff augmentation (BEON, AgileEngine, BairesDev, Globant, Distillery, Making Sense) son las que arman equipos argentinos, pero suelen exigir inglés en el rol. Para el patrón "equipo técnico argentino + PM que habla con el cliente", tus mejores apuestas en español son las cuentas y reclutadoras locales.

*Herramienta adjacente útil:* **Radar IT Argentina** de Nicolás Nicolaide (`nicolasnicolaide.com/radar-it.html`) — agrega vacantes tech de 112+ fuentes, actualiza diario ~11:00 ART y permite exportar resultados como posteo de LinkedIn; señala crecimiento en "IA generativa, prompt engineering, LLMs y MLOps".

### 5) Workflow para aplicar vía posteos (sin parecer spam)

**Timing:** postulate en las primeras horas del posteo (por eso el orden "Recientes" + 24 h). Con los postulantes por rol duplicados desde 2022, ser de los primeros te pone en el grupo más chico y más mirado.

**Comentar vs. DM:** hacé las dos cosas, en orden.
1. **Comentario corto y profesional** en el posteo (aumenta visibilidad y le llega notificación al autor). Ejemplo: *"¡Hola [nombre]! Me interesa la posición de AI Engineer. Tengo 4+ años como AI Engineer Senior con Python y FastAPI (RAG/LLMs en producción). Te mando DM con más detalle. ¡Gracias!"*. Evitá el clásico "interesado" o "revisá mi perfil" a secas: los reclutadores lo mencionan explícitamente como error.
2. **DM / mensaje directo** (o solicitud de conexión con nota si no son 1er grado) mencionando el posteo puntual, 2-3 logros medibles y tu disponibilidad. Corto, humano, con palabras clave del aviso.

**Plantilla de primer mensaje (español):**
> "Hola [nombre], vi tu posteo sobre la búsqueda de [rol AI Engineer]. Soy AI Engineer Senior (4+ años) especializado en Python, FastAPI y sistemas RAG/LLM en producción. Me encajan mucho los requisitos y me interesa avanzar. ¿Te comparto mi CV o coordinamos una llamada breve? ¡Gracias por la oportunidad!"

**Buenas prácticas:** personalizá cada mensaje (nada de copy-paste evidente), incluí keywords del aviso, agradecé, respondé rápido pero pensado. **Errores a evitar:** comentar solo "interesado", pedir sin aportar contexto, mandar el mismo texto a 30 lados, escribir párrafos largos, o no leer si el rol pide inglés excluyente.

### 6) Sistema repetible + alertas

LinkedIn **no** ofrece alertas nativas para búsquedas de contenido (las alertas guardadas existen solo en Jobs). Workaround práctico:

1. **Carpeta de favoritos "AI feed"** con 4-6 URLs de búsqueda de contenido (las de la sección 1-2), variando keywords y fecha (24 h / semana).
2. **Rutina diaria**: revisá esas URLs a la mañana y a la tarde (10-15 min). Las vacantes buenas duran poco.
3. **Lista de reclutadores** con campanita en "todo lo que publica" (sección 4).
4. **X-Ray de Google** guardado como marcador para lo que LinkedIn oculta.
5. Opcional/avanzado: hay scrapers (ej. Apify "LinkedIn Post Search Scraper") que corren una URL de búsqueda de contenido y te devuelven posteos por keyword/fecha; útil si querés automatizar, pero cae fuera de los términos de LinkedIn y puede arriesgar la cuenta — usalo con criterio.

### 7) Otros canales donde la vacante aparece como posteo/mensaje

**Telegram (español, tech/remoto):**
- `@empleositar` (Empleos IT Argentina), `@empleo_it_latam`, `@ofertasteletrabajo`, `@trabajos_remotos_latam`, `@vacantesremotas`, `@STEMJobsLATAM`, `@remotejobscol`.

**Discord (comunidades con canal de #ofertas):**
- **Primer Empleo IT** (`discord.com/invite/primerempleoit`), **Argentina Developer 🧉** (`discord.com/invite/argentina-developer-913054176383225896`), **Programadores y Estudiantes** (`discord.com/invite/programacion`), **Comunidad de Programadores**.

**X/Twitter:** `@TrabajoenIT` (IT Argentina), `@Hire_LATAM` (#HireLATAM), buscá `#hiring LATAM` y `#trabajoremoto`.

**Newsletters/portales LATAM en español:** RemotoJob (remotojob.com), WeRemoto (weremoto.com), Vacantes Remotas (vacantesremotas.com), Get on Board (getonbrd.com.ar), Hireline, RemotoList; vacantesdigitales.com (foco IA LATAM, se describe publicando "una vacante cada 10 minutos").

### 8) Referentes/fuentes que enseñan esta técnica
- **Jan Tegze** (jobsearch.guide) — método detallado de buscar vacantes en Posts + Author Company + últimas 24 h (en inglés, muy completo).
- **iProfesional** (Argentina) — notas en español que explican el canal: *"LinkedIn Jobs es genial, pero hay mucho trabajo que se publica como un posteo común y no llega a la sección de empleos... filtrá por 'Publicaciones' y 'Fecha: Última semana'... muchas veces antes de que la oferta se llene de 500 candidatos"*.
- **@mimiworkbestie** (TikTok) — popularizó buscar "buscamos"/"hiring" + ciudad en Posts.
- **Luis Prado** (LinkedIn, en español) — enseña a rastrear vacantes publicadas por reclutadores desde sus perfiles personales.

## Recommendations

**Semana 1 (montar el sistema):**
1. Creá la carpeta de favoritos con 4-6 URLs de búsqueda de contenido (secciones 1-2), incluyendo una en español (Argentina) y una en inglés (LATAM remoto).
2. Seguí y ponele campanita ("todo lo que publica") a 15-20 reclutadores/cuentas: arrancá con Agustina Urdapilleta, Empleos IT Argentina, Chumi-IT, Giovanna Pinheiral, y sumá reclutadores que encuentres postulando.
3. Unite a 3-4 Telegram y 2 Discord de la sección 7.

**Rutina diaria (para llegar a 3+ entrevistas/semana):**
4. 2 pasadas por día a las URLs (Recientes + 24 h). Meta: 5-8 postulaciones relevantes/día vía posteos.
5. Por cada vacante que encaje: comentario corto + DM personalizado en la primera hora.
6. Llevá una planilla simple: fecha, rol, autor, canal, estado.

**Benchmarks que cambian la estrategia:**
- Si en 2 semanas no llegás a 3 entrevistas/semana → ampliá el clúster de títulos y sumá inglés en los strings (roles remotos LATAM suelen pagar mejor aunque pidan inglés; muchos aceptan inglés intermedio si el equipo es argentino).
- Si recibís respuestas pero caés en filtros de inglés → priorizá el patrón "equipo argentino + PM cliente" (reclutadoras locales, Empleos IT, Chumi-IT).
- Si los posteos rinden poco → subí el peso del canal Jobs (que ya tenés resuelto) y usá posteos solo para las vacantes "frescas sin competencia".

## Caveats
- LinkedIn cambió su buscador en el último año y sigue testeando: parámetros de URL, orden "Recientes" y filtros pueden variar o no respetarse en móvil. Si algo falla, rehacé filtros a mano y volvé a guardar la URL.
- **"Seguir hashtag" ya no existe** (desde octubre de 2024): el hashtag hoy es solo palabra de búsqueda. Reemplazalo por URLs guardadas + seguir cuentas.
- No hay alertas nativas de contenido; el sistema depende de tu rutina diaria (o de scrapers, que son zona gris y pueden arriesgar la cuenta).
- Los datos de reclutadores individuales provienen de vistas previas de búsqueda; confirmá nombres/URLs logueado, ya que la gente cambia de rol.
- Las firmas de staff augmentation top (BEON, AgileEngine, BairesDev, Globant) suelen exigir inglés en el rol aunque el equipo sea argentino; para roles realmente sin inglés excluyente, apuntá a cuentas y reclutadoras locales en español.
- Cuidado con estafas en Telegram/Discord/X: verificá siempre que el reclutador tenga perfil real y no pida datos financieros.