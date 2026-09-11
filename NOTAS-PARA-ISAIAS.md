# Notas para Isaías

**481 tests pasan.**

```
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest tests -q      →  481 passed
```

Andando todo: los 3 portales argentinos, Indeed, Get on Board, LinkedIn Jobs,
las páginas de empleo de las empresas, seguir reclutadores, el scoring con
Gemini y la pantalla.

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

Desde el 8/9 hay una pieza más lista para eso: los motivos vienen **clasificados**
(`motivo_clave`), y `ui.data.MOTIVOS_QUE_NO_ENSENIAN` marca cuáles NO tienen que
entrar al prompt. "Piden inglés" y "es presencial" son restricciones que los
filtros ya aplican solos y mejor; el caso especial lo pidió Isaías. Lo que sí
enseña es el texto libre, que es el descarte que dice algo del puesto (2.9).

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

O, sin abrir una consola, el botón **Buscar ahora** al pie de la barra lateral de
la pantalla: hace eso mismo, en un proceso aparte para no congelarla.

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

## 2.5. El 403 de Computrabajo: arreglado de raíz

**No tenés que hacer nada nunca más.** Se arregló en la pantalla y no vuelve a
pasar. Una sola vez, para limpiar la que quedó pegada de antes: apretá
**Ctrl+Shift+Supr** parado en Computrabajo, tildá *Cookies y otros datos de
sitios*, rango *Última hora*, Borrar. Listo para siempre.

### Qué estaba pasando

La causa era **la pantalla de vacantia**, y era una sola línea de HTML.

Cuando hacías clic en un aviso, el navegador le avisaba a Computrabajo de dónde
venías: `http://127.0.0.1:8756`, que es la dirección de la pantalla en tu propia
máquina. Computrabajo guarda esa dirección en una cookie suya, `extrfr` (de
*external referrer*). Y a partir de ese momento **todos** los pedidos de tu
navegador al sitio llevaban una dirección a `127.0.0.1` metida adentro de una
cookie.

Para el firewall de Amazon que Computrabajo tiene delante, eso es la firma
clásica de un ataque (se llama SSRF: hacer que un servidor le pegue a una
dirección interna). Entonces cortaba: `403 Forbidden` en el sitio **entero**,
desde tu navegador, hasta que se borrara la cookie.

Por eso te pasaba **cada** vez, y por eso te pasaba **justo con los que venían de
la app**: no era un aviso fallando: era el primer clic desde la pantalla el que
rompía todos los siguientes.

Verificado el 7/9/2026 armando la cookie a mano y pidiendo el mismo aviso:

| Cookie que se manda | Respuesta |
|---|---|
| `extrfr=http://127.0.0.1:8756/trabajos` | ❌ **403** |
| `extrfr=http://localhost:8756/trabajos` | ❌ **403** |
| la misma escapada (`http%3A%2F%2F127.0.0.1...`) | ❌ **403** — tampoco zafa |
| `extrfr=https://ejemplo.com/x` | ✅ 200 — un referrer normal no molesta |
| `extrfr=127.0.0.1:8756/trabajos` (sin el `http://`) | ✅ 200 — sin el esquema no dispara |
| sin la cookie | ✅ 200 |

### Qué se cambió

Los links a los avisos ahora salen con `rel="noreferrer"`: la pantalla **no le
cuenta al portal de dónde venís**. Sin eso, Computrabajo no tiene qué guardar, la
cookie `extrfr` no se crea, y el firewall no tiene nada que marcar.

Probado después del cambio: abrí los avisos uno atrás de otro desde la pantalla,
todos cargaron, y la cookie `extrfr` **no llegó a existir ni una vez**.

No se pierde nada a cambio: ese dato sólo le servía al portal para estadísticas.
Seguís entrando igual, logueado igual, y podés postularte igual.

### Dos correcciones que te debo

Diagnostiqué esto mal dos veces antes de dar con la buena:

- **El 5/9** dije que Computrabajo le contestaba 403 a cualquier navegador y que
  no había nada que hacer. Sobre esa conclusión se apagó la fuente y se sacaron
  17 avisos de tu historial.
- **Hoy más temprano** dije que lo rompía una ráfaga de pedidos y que sólo se
  arreglaba borrando la cookie a mano cada vez. También estaba mal: la ráfaga era
  una casualidad, la había disparado yo abriendo la app desde localhost.

Esta tercera es la buena, y se distingue de las otras dos en que **se puede
reproducir a voluntad**: pongo la cookie con `127.0.0.1` adentro y da 403, la
saco y da 200, las veces que quiera.

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
*Mi perfil*, el sistema no entra al perfil: le pregunta a Google cuáles son las
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

## 2.8. Las publicaciones viejas: una sola perilla, y las nuevas arriba

Tenías razón, y era peor de lo que sonaba. Medido sobre tu historial el
7/9/2026, con 216 avisos:

| Fuente | Total | Con fecha | **Sin fecha** |
|---|---:|---:|---:|
| linkedin | 114 | 85 | 29 |
| google_posts | 75 | 36 | 39 |
| **computrabajo** | 8 | **0** | **8** |
| **bumeran** | 9 | **0** | **9** |
| **zonajobs** | 3 | **0** | **3** |
| careers | 5 | 0 | 5 |
| rrhh | 2 | 0 | 2 |

Había posts de **2020, 2023 y 2024** mezclados con los de esta semana. Y **los
tres portales no reportaban fecha nunca**, ni una sola vez.

### Lo peor: el filtro que ya tenías estaba ciego

La pantalla ya tenía el filtro de antigüedad (Hoy / 7 días / 30 días). Y como un
aviso sin fecha no se descarta —que es la regla correcta: lo que no dice, no
filtra— **un aviso de Bumeran de dos meses te pasaba el filtro de "hoy"**,
porque no tenía fecha con qué compararse. El filtro andaba; le faltaba el dato.

Y no es que los portales no la tengan. Está escrita en la misma página que ya
bajábamos:

- Computrabajo: `Hace 6 días (actualizada)`
- Bumeran y Zonajobs: `Publicado el 20/08/2026`

La estábamos tirando a la basura.

### Lo que se cambió

**1. Ahora se lee la fecha de los tres portales.** Con una trampa que había que
esquivar: al pie de cada aviso el portal lista ocho *ofertas similares*, cada una
con **su** fecha. Agarrar la primera del documento daba la de otro aviso —uno
"Ayer" cuando el tuyo tenía 6 días—. Se corta el texto donde empiezan los avisos
ajenos y recién ahí se busca.

De paso, Bumeran y Zonajobs dicen la fecha dos veces y no valen lo mismo: arriba
`Publicado hace más de 15 días` (que deja de contar a los 15: puede ser 16 días o
dos años) y más abajo la exacta. Se usa la exacta.

**2. Una sola perilla, y es tuya, no de cada fuente.** En *Mi perfil* hay un
campo nuevo:

> **No traerme avisos de más de ___ días**

Ese número lo heredan **todas** las fuentes: los tres portales, LinkedIn, las
publicaciones por buscador y los reclutadores que seguís. Antes estaba repartido
en seis bloques del archivo y se desincronizaban sin que nadie se enterara.

- **Tu perfil: 7 días.** Para AI Engineer, a la semana la búsqueda ya está
  cubierta de postulantes.
- **El de tu papá: 30 días.** Seguridad e higiene en el campo es otro mercado: la
  búsqueda queda abierta, se postulan dos o tres y no quedan. *Este número lo
  puse yo; si querés 45, cambialo en Mi perfil y listo.*

`0` apaga el límite y vuelven a entrar los de 2020.

**Un aviso que no dice cuándo se publicó entra igual.** No se descarta por no
saber, que es lo que pediste y además es la regla de todo el proyecto.

**3. Las recién publicadas van arriba de todo.** Ésta es la parte que contesta lo
que vos decías —*"cuanto más reciente, más chance de que nos llamen"*—, y no es
un filtro sino un orden.

Antes la lista ordenaba sólo por puntaje. Pero "cuál encaja mejor con mi CV" no
es la misma pregunta que **"a cuál me conviene postularme ahora"**: una de 92
puntos de hace seis días ya tiene cien postulantes, y una de 88 de esta mañana no
tiene ninguno. Entre esas dos, la segunda.

Ahora la lista abre con una banda:

> **RECIÉN PUBLICADAS · 5** — Avisos de hoy o ayer. Son a los que menos gente se
> postuló todavía.
>
> **EL RESTO** — Ordenadas por puntaje, como siempre.

⚠️ **El puntaje que ves no se toca.** Sigue significando qué tan bien encaja con
tu CV; mezclarle la fecha lo arruinaría. Lo único que cambia es el orden.

Y hay dos cosas que **no** suben a la banda, a propósito:

- **Las que no llegan a tu puntaje mínimo** (60). Ser de hoy no vuelve buena a
  una oferta mala. Esto ya te había pasado antes con otra cosa: tres avisos de
  Lima puntuados 0 encabezaban la lista por haber entrado hoy. No se repite.
- **Las que no tienen fecha.** No sabemos que sean nuevas y ponerlas arriba sería
  inventarlo.

### Por qué la ventana es de 7 días y no de 1

Suena a que apretando a 1 día conseguís sólo lo del día, que es lo que querés.
No: se rompe. El buscador **tarda en indexar**, y un post de ayer puede aparecer
recién pasado mañana. Con la ventana en 1 día ese post queda afuera **para
siempre**, porque para cuando aparezca ya no entra. Perderías justo los que
buscás.

Medido con la misma búsqueda: **7 días devolvió 10 publicaciones, 1 día devolvió
2.**

Por eso las dos cosas están separadas y hacen trabajos distintos: **la ventana es
el colador de basura** (generosa, para no perder nada por la demora del índice) y
**la banda es la prioridad** (agresiva, lo de hoy primero).

## 2.9. Descartar sin escribir, y por qué tu lista bajó de 41 a 10

Medido sobre tu historial el 8/9/2026, con 107 ofertas y 60 descartes tuyos.

### Estabas haciendo a mano lo que el sistema ya había hecho

De las **41 que te esperaban sin marcar, 31 el filtro ya las había rechazado**:

| | Descartaste (60) | Te esperaban (41) |
|---|---:|---:|
| El filtro ya las había tirado por **idioma** | 38 | 20 |
| ...por **lugar o modalidad** | 11 | 11 |
| El filtro **sí las aceptaba** (decisión tuya de verdad) | 11 | 10 |

El motor guarda en el historial **todo lo que puntúa**, incluso lo que después
descartó. Eso está bien para poder contar lo que se pierde por inglés, pero la
pantalla lo mostraba todo junto, y por eso escribiste 46 veces "estaba en
inglés": eran avisos sobre los que el sistema ya había decidido.

**Ahora no llegan a *Sin marcar*.** No se borra nada, se cuentan en *Métricas*, y
**vuelven solas si cambiás el filtro que las sacó** — el día que subas tu nivel
de inglés en *Mi perfil*, esas 20 reaparecen sin que nadie corra nada. Por eso se
calcula al mirar la lista y no se guarda una marca: una marca guardada congelaría
la decisión que se tomó con la configuración de aquel día.

Tu lista pasó de **41 a 10**.

### El motivo ahora se elige de una lista

### Dos caminos, y con cualquiera alcanza

Debajo de los botones quedaron las dos cosas, **las dos siempre a la vista**:

1. **Un desplegable** con los tres motivos que se repiten.
2. **Un campo de texto, opcional**, para todo lo demás.

Los tres del desplegable salen de lo que de verdad escribiste, no de lo que yo
imaginé:

| | Lo habías escrito |
|---|---:|
| **Piden inglés** | 46 veces, en 4 redacciones distintas |
| **Es presencial y no puedo ir** | 4 |
| **Caso especial (que no aprenda de esto)** | 6 (era tu guion) |

**"Piden inglés" suma al contador**, como pediste: el cartel de arriba pasó de 72
a 76 apenas se contaron los que ya habías marcado a mano. Sube cada vez que
marcás una así, y baja solo si subís tu nivel en *Mi perfil*.

⚠️ **No hay una opción "Otro motivo" en la lista, y es a propósito.** La primera
versión la tenía y estaba mal: para escribir un motivo había que abrir el
desplegable, bajar hasta *Otro* y recién ahí aparecía el campo. Tres pasos de más
justo en el caso en que ya tenías la mano en el teclado, y multiplicado por las
veces que pasa. Ahora el campo está siempre ahí: si el motivo es uno de los tres,
lo elegís; si no, escribís y listo. Podés usar los dos a la vez si querés, y en
la tarjeta se muestran los dos.

⚠️ **Una cosa que hay que aclarar**: el guion lo venías usando para que el
sistema no aprendiera de ese descarte. **Todavía no aprende de ninguno.** Los
motivos se guardan y se cuentan, pero el scoring no los lee: el ciclo de
aprendizaje está descrito en el código y no implementado. Tu instinto de separar
los casos era correcto y ahora queda registrado como corresponde, pero por ahora
no cambia nada del puntaje. Si querés que aprenda de verdad, es otro trabajo.

## 2.10. La pestaña Métricas, y el número grande

Los contadores estaban repartidos en los cinco botones de arriba (*Sin marcar*,
*Apliqué*, *Descarté*, *Archivadas*, *Todas*), todos del mismo tamaño. Pero
mientras revisás ofertas hay **un solo número que importa: cuántas te faltan**.
"Archivadas 83" no es una tarea, es un archivo, y ocupaba el mismo lugar.

Ahora:

- **Sin marcar es un número grande** arriba a la izquierda, y a la derecha, en la
  misma línea, el filtro de antigüedad.
- **La antigüedad es un desplegable** en vez de cuatro botones: se toca una vez
  por semana y ocupaba una fila entera.
- **Todo lo demás vive en la pestaña Métricas**: los totales, qué descartó el
  sistema y por qué, por qué descartaste vos, y de qué fuente viene cada oferta.

## 2.11. Volver a donde estabas después de marcar

Lo que contaste: bajabas hasta una oferta de 20 puntos, la marcabas, y la página
volvía arriba de todo.

Es porque marcar es un POST que redirige a un GET —si no, recargar reenviaría el
formulario— y el navegador abre esa página nueva desde arriba. Ahora se guarda
dónde estabas justo antes de enviar y se vuelve ahí al llegar.

Un detalle que me comí y vale la pena dejar escrito: `form.submit()` **no dispara
el evento `submit`**, así que enganchar el guardado al evento no alcanzaba y la
primera versión seguía saltando arriba. Hay un test que lo fija.

## 2.12. Los desplegables, y el nombre que lleva al home

Dos cosas chicas de la pantalla.

**Los cuatro desplegables ahora se ven como el resto.** Había un problema real:
de los cuatro (el de perfil arriba, el de antigüedad, el de motivos y el de nivel
de inglés), **tres no tenían una sola línea de CSS**. Salía el control crudo de
Windows, que no se parece a nada del resto de la pantalla. El cuarto heredaba el
borde pero conservaba la flecha nativa del sistema.

Ahora los cuatro tienen el mismo alto, el mismo borde, el mismo radio y el mismo
fondo que los botones y los campos de texto, más lo que les faltaba y los botones
sí tenían: **hover, hundidito al apretar y transición**.

La flecha la dibujamos nosotros —la nativa es la única parte que el navegador no
deja pintar— y es un token más de la paleta, así que cambia sola en modo oscuro.
Hay un test que falla si alguien toca el gris de la paleta y se olvida de la
flecha.

La lista que se despliega al hacer clic **la dibuja Windows, no el navegador**.
Lo único que la hace acompañar el tema oscuro es `color-scheme`, que ya estaba.

**El nombre VACANTIA lleva al home.** Era lo primero que uno intenta. Se pinta
como el texto de al lado y no como un link, para no competir con la navegación.

## 2.13. La cuenta de Gemini

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

## 2.14. Qué pasa cuando corrés `instalar.bat`

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

Para ver si está programada, cuándo corrió y cómo le fue: **Métricas**, abajo de
todo, *Cómo viene funcionando*. Para que deje de correr: `desinstalar.bat`.

## 2.15. AI Engineer no es Machine Learning

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

## 2.16. Los puestos que no querés ni pagar por puntuar

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

## 2.17. Archivar: el aviso ya no está

Los avisos de más de una semana suelen estar cubiertos, o directamente los
bajaron. Pero **descartarlos sería mentirle al sistema**: el motivo de un
descarte va al prompt de scoring como ejemplo negativo, y "el aviso ya no está"
no dice nada de si el puesto te servía. Le enseñarías una preferencia que nunca
tuviste.

Por eso archivar es un estado aparte:

- **Botón "Ya no está"** en cada oferta. No pide motivo, no toca el veredicto.
- **Pestaña "Archivadas"**, con un botón para devolverlas a la lista.
- **Atajo arriba de la lista**: *Más de 7 días (43) · Más de 14 días (23) · Más
  de 30 días (14)*. Dice cuántas son antes de que aprietes.

**No vuelven a entrar en las corridas siguientes**, y no es por archivarlas: su
clave ya está en `seen_jobs.json` desde la primera vez que se guardaron, y el
dedupe las saca antes de gastar nada. Por eso archivar no borra nada y se puede
deshacer.

Dos cosas que **no** archiva el atajo:

- **Las que no dicen cuándo se publicaron.** No se sabe si están viejas, y
  archivar por las dudas es tirar una oferta que puede ser de ayer.
- **Las que ya marcaste.** Ésas ya las decidiste.

---

## 2.18. El rediseño: qué cambió de lugar

La pantalla se rehizo entera contra `DESIGN.md`. La lógica no se tocó: lo que
cambió es qué se ve, en qué orden y con qué peso. Lo que vas a notar el primer
día:

**La navegación pasó de arriba a la izquierda.** Una barra lateral fija, con el
perfil arriba y los cuatro destinos agrupados por lo que hacés: *Buscar* con
Trabajos; abajo, separado, *Métricas* y *Mi perfil*. Se llamaban *Métricas* y
*Mi perfil*: mismo lugar, nombre nuevo. Las direcciones (`/estadisticas`,
`/datos`) no cambiaron, así que un favorito viejo sigue andando.

**Abajo de todo, fijo, el estado del sistema:** *Última búsqueda: hoy 16:30 ·
Próxima: hoy 23:59* y la ventana de días que cubre. Está en todas las pantallas.
La razón es concreta: la pregunta que más pesa buscando trabajo no es "¿hay
ofertas?" sino "¿esto es todo lo que hay?", y esto la contesta sin que tengas
que abrir un archivo. Es texto quieto: no parpadea, no cuenta hacia atrás y no
se actualiza solo.

**La tarjeta de oferta muestra dos controles, no seis.** Antes se veían al mismo
tiempo *Apliqué*, *No apliqué*, el desplegable de motivos, el campo de texto y
*Ya no está*. Ahora:

- **Apliqué**, en índigo, que es la acción que venís a hacer.
- **No apliqué**, al lado, más callado. Al tocarlo se abre el bloque del motivo
  **adentro de la misma tarjeta**: el desplegable, el campo y el botón de
  confirmar. Sigue alcanzando con cualquiera de los dos, como antes.
- **Un menú de tres puntos** en la esquina, con *Mensaje para escribirle*,
  *Consejo para el CV* y *Ya no está*.

Y se fue el verde contra el rojo. Dos botones del mismo peso enfrentados te
obligan a decidir antes de leer, y encima el rojo decía "error" sobre una
decisión normal: no aplicar a una oferta no es un error. El verde queda sólo
donde significa algo, en *Aplicaste*.

**El cartel del inglés se mudó a Métricas.** Sigue estando, sigue contando lo
mismo y sigue diciendo cuánto puntuaba la mejor que se te escapó. Lo que cambió
es dónde: era lo primero que leías al abrir Trabajos, todos los días, antes de
la primera oferta. Ahora vive en Métricas, que es donde vas a mirar números, y
**con la salida al lado**: un link directo a cambiar tu nivel declarado. Un
número que no podés accionar es un reproche; con el link es información.

**Un solo tema, el oscuro.** Se sacó el modo claro. Manteníamos dos paletas
enteras y la mitad de las veces la segunda se olvidaba de alguna regla.

**El texto de ayuda de los formularios se acortó.** Lo que pasaba de tres
renglones se fue a un desplegable *Cómo funciona esto* debajo del campo. La
ayuda larga no se leía y encima empujaba el campo siguiente fuera de pantalla.

Los colores, tamaños y espacios salen todos de tokens definidos una sola vez en
`vacantia/ui/estilos.py`. Ninguna regla escribe un color suelto, y hay un test
que falla si alguien lo hace. Otro test verifica que todo par de texto y fondo
llegue a 4.5:1 de contraste; ése fue el que agarró que el índigo de acción no
servía como color de link sobre fondo oscuro.

---

## 2.19. Dos `.bat` menos: Buscar ahora y Cómo viene funcionando

`buscar_ahora.bat` y `estado.bat` ya no existen. Los dos hacían algo que la
pantalla puede hacer, y mientras existieran la pantalla tenía que nombrarlos:
*"doble clic en `buscar_ahora.bat`"* era la app explicando otro programa.

**Buscar ahora** está al pie de la barra lateral, pegado a *Última búsqueda: hoy
16:30*, porque es la acción sobre ese dato. En secundario: la acción de la
pantalla de Trabajos es aplicar a una oferta. Donde no hay ninguna oferta que
aplicar (la lista vacía, la primera corrida), ahí sí es el botón principal.

Tres cosas que resuelve y conviene saber:

- **Corre en un proceso aparte.** La búsqueda tarda minutos y el servidor de la
  pantalla atiende de a un pedido: corriéndola adentro, la pantalla quedaría
  congelada hasta que termine. Como proceso suelto, podés seguir marcando
  ofertas mientras busca, y si cerrás la pantalla la corrida sigue.
- **No abre ninguna ventana negra** (`CREATE_NO_WINDOW`), que era la mitad de la
  gracia de sacar el `.bat`.
- **No deja arrancar dos encimadas.** Mientras hay una en curso el botón queda
  apagado y dice *Buscando ofertas*. Los límites del plan gratis son de la
  cuenta, no del perfil.

Cuando termina no hace falta apretar nada: el vigilante que ya existía avisa
solo con *"Entraron 3 ofertas nuevas"*.

**Cómo viene funcionando** es lo que mostraba `estado.bat`, ahora abajo de todo
en Métricas: si está programado y cuándo vuelve, cuánto tardó la última corrida
y qué encontró, cuándo fue el último aviso por Telegram, y las últimas quejas
del registro adentro de un desplegable. Los números de la corrida se parsean del
registro y se muestran en una tabla en vez de pegar la línea cruda: la línea del
registro es texto de máquina, y en columnas los números se comparan de una
corrida a la otra.

El estado del Programador de tareas sale de `schtasks`, que ya viene con
Windows. En otro sistema operativo el panel lo dice en vez de mentir.

**Un bug que apareció construyendo esto:** la fecha de marcado se guarda en UTC,
y la tarjeta cortaba los primeros diez caracteres del texto para quedarse con el
día. Entre las 21:00 y la medianoche eso da la fecha de mañana, así que al día
siguiente la tarjeta decía *"Aplicaste hoy"* a algo de ayer. Son tres horas por
día, justo las que más se usa la pantalla. Ahora se pasa a la hora de acá antes
de quedarse con el día, y hay un test que lo cubre.

---

## 2.20. LinkedIn URLs: el lugar, todavía vacío

Sección nueva en la barra lateral, abajo de Trabajos y adentro del grupo
*Buscar*, con dos pestañas: **Jobs** (la que abre por defecto) y
**Publicaciones**.

Todavía no genera ninguna dirección. Está el lugar, las dos pestañas andando y
escrito qué va a caer en cada una, para poder discutirlo mirándolo en vez de
imaginándolo.

Por qué existe: el scraper trae lo publicado hace uno a tres días, porque antes
de eso ningún buscador lo indexó. Los avisos de hoy son justamente a los que
menos gente se postuló, y la única forma de verlos es entrar a LinkedIn con la
búsqueda ya armada. Son dos sistemas que se complementan, y la pantalla tiene
que dejarlo evidente sin explicarlo con un párrafo.

Son **pestañas** y no píldoras de filtro a propósito: las píldoras filtran una
lista que sigue siendo la misma, y las pestañas cambian el contenido. Por eso
van arriba del contenido, son links, y no viven adentro de una tarjeta.

---

## 2.21. La pestaña Filtradas: auditar el filtro en la semana de prueba

El 9/9 entraron 23 ofertas nuevas y a *Sin marcar* llegaron 2. Las otras 21 las
sacó el sistema solo: **13 por idioma, 7 por lugar**, una la marcaste vos. Y las
que se fueron por idioma eran las mejores del día: 95, 90, 85, 75, 75.

El problema no era el número, era que **no había forma de saber si esos 21
descartes estaban bien**. El sistema decide solo y no rendía cuentas.

**La pestaña Filtradas** es eso. Cae ahí todo lo que el filtro saca por su
cuenta, con el motivo que dio, y por cada oferta hay dos botones:

- **Bien descartada.** El filtro acertó. Se va de la lista y no vuelve.
- **Mal descartada.** El filtro se equivocó. Se va de la lista **y vuelve a Sin
  marcar**, porque la oferta sigue estando y todavía le podés aplicar.

Las dos la sacan de la pila, así que la lista se vacía a medida que revisás y no
hay que acordarse dónde quedaste. Lo que no tocás sigue ahí esperando.

**Arriba, el marcador**: cuántas veces acertó el filtro y cuántas se equivocó.
Es **acumulativo y no lo achica el filtro de fechas**: la pregunta es "en toda
la semana, ¿cuántas veces acertó?", y con dos días de muestra un porcentaje
sobre lo de hoy no dice nada.

**Sólo entran las de 50 puntos para arriba** (`PUNTAJE_PARA_REVISAR`). Si el
filtro se equivocó con una de 20, esa oferta no te iba a servir igual: revisar
ese tramo es gastar la atención donde el error no tiene consecuencia. Y son las
que más quedan cuando el pozo se va agotando. El contador de la píldora cuenta
sólo las que se muestran, así que no miente.

**La meta son 40 revisadas** (`META_REVISION`). Con 40 y ningún error, el filtro
acierta arriba del 90% y no hay nada que tocar; con 4 o más errores hay un patrón
que mirar. Menos que eso es anécdota, y por eso el marcador muestra el progreso
hacia la meta y no un porcentaje de aciertos: con 19 revisadas un "100%" suena a
veredicto y todavía no lo es.

**Cómo venía el 9/9:** 19 revisadas, 19 bien descartadas, 0 mal. Y las 43 que
quedaban sin revisar puntuaban todas menos de 50, así que la pestaña quedó vacía
hasta la corrida siguiente. Ese vacío lo dice con todas las letras, porque una
pantalla vacía sin explicación se lee como "se terminaron las ofertas".

Tres decisiones más que conviene tener escritas:

- **La tarjeta muestra el motivo del sistema arriba de todo, con la explicación
  completa.** En Sin marcar la pregunta es "¿me postulo?"; acá es "¿el filtro
  acertó?", y sin el motivo a la vista no se puede contestar. Ya sirvió para ver
  algo: varias de las mejores no se caen por nivel de inglés sino por
  *"aviso en 'en'"*, que es la capa 1 del filtro, la del idioma del aviso.
- **Ordenadas por puntaje, sin la banda de recientes.** Las de 95 son las que más
  duele perder si el filtro erró, y son las primeras que hay que mirar.
- **No es un veredicto sobre la oferta, es un veredicto sobre el filtro.** Vive
  en su propio campo (`revision_filtro`) y no toca `aplicado`. Una marcada "mal"
  vuelve a Sin marcar y después se puede aplicar o descartar normalmente, y el
  contador no se pierde.

**La píldora Filtradas se pinta distinta del resto**, con el azul de "estado del
sistema" y un embudo al lado. Es lo que son esas ofertas: algo que decidió el
sistema. No va en el índigo de acción, que convertiría la píldora en un botón, y
no va en rojo, que acá significa error o destrucción: que el filtro descarte algo
no es ninguna de las dos.

Los dos botones de la tarjeta tampoco son rojos, y son de peso distinto
(*Bien descartada* en índigo, que es la respuesta que vas a dar la mayoría de las
veces) para que revisar 60 sea rápido.

---

## 2.22. Dos fuentes nuevas: Indeed y Get on Board

Prendidas en tu perfil desde el 9/9. La recolección pasó de ~95 avisos por
corrida a **115**.

### Get on Board: la única que no scrapea nada

Get on Board tiene **API pública, abierta, sin token**. Se lee con `urllib`, que
ya viene con Python. No usa TinyFish, no gasta una sola credencial, y devuelve
el aviso ya estructurado: título, descripción, modalidad, países y fecha de
publicación.

Eso la vuelve la fuente más barata y más confiable del sistema, y conviene
tenerla prendida por una razón de fondo: **cuando falte `TINYFISH_API_KEY`,
todas las demás se saltean solas y ésta sigue trayendo.**

Dos cosas que hubo que resolver:

- **Es un portal chileno.** Sin recorte, la mitad de lo que trae son
  presenciales en Santiago. Se le pide `country_code=AR`, que devuelve los que
  aplican a la Argentina: en la prueba, 60 de 60 remotos.
- **`countries` mezcla la modalidad con el país.** Un aviso remoto viene con
  `["Remote"]` ahí adentro, y meter eso en `country` hacía que el filtro de
  ubicación lo comparara contra "Argentina" y lo tirara. "Remote" se lee como
  modalidad, no como país.

### Indeed: Cloudflare deja pasar el listado y no el aviso

Éste dio pelea, y las tres trampas salieron de probar contra el sitio, no de
suponer:

**1. Desde Python es `403 Forbidden`, con `server: cloudflare`.** Con TinyFish
el listado sí vuelve. Pero la página del aviso, `viewjob?jk=...`, vuelve
**vacía**: 0 bytes. La única forma de leerla es por el link de redirección que
trae el propio listado, `rc/clk?jk=<id>&bb=<token>`.

**2. Ese link lleva un token de sesión que cambia en cada corrida.** Si se
guardara como identidad del aviso, el mismo puesto entraría de nuevo tres veces
por día y el dedupe no lo agarraría nunca. Es el mismo tipo de bug que el 403 de
Computrabajo: algo que parece cosmético y rompe el sistema entero. El token se
usa **sólo para bajar el detalle, dentro de la misma corrida**, y lo que se
guarda es `viewjob?jk=<id>`, que es estable y **abre perfecto en tu navegador**.
Lo verifiqué abriendo uno: la bloquea el scraper, no el browser.

**3. El aviso no dice cuándo se publicó**, ni en el listado ni en el detalle. La
ventana la aplica el propio Indeed con `fromage`, igual que LinkedIn con
`hours_old`: se piden sólo los últimos N días y lo que vuelve ya viene
recortado. Se redondea a los valores que Indeed acepta (1, 3, 7, 14) y siempre
para arriba, para no traer de más.

**La mitad de los avisos no se puede leer, y esos no entran.** Cloudflare deja
afuera a unos 10 de cada 20. Sin la página del aviso lo único que queda es la
URL: el título sale del slug y dice "viewjob", sin empresa y sin descripción.
Eso no se puede ni mostrar en una tarjeta, el modelo le pone 0 igual que a una
oferta que de verdad no sirve, y encima cuesta una llamada. Se descartan y el
log dice cuántas fueron. **Indeed aporta 9 a 11 avisos completos por corrida**,
que es lo que de verdad rinde.

Hay un reintento, y uno solo: medido dos veces, la primera ronda recupera
algunos y la segunda no recupera ninguno. Las que faltan después del reintento
son siempre las mismas.

### Por qué no se puede paginar, y qué se hizo en cambio

Pedir la segunda página (`&start=10`) devuelve 550 bytes que dicen, literal:

> *"Para ver más de una página de empleos, crea una cuenta o inicia sesión."*

**No es Cloudflare ni un problema de scraping: es una decisión de producto de
Indeed.** Se probaron `start`, `sort=date`, la versión móvil y con
`l=Argentina`: todas devuelven la misma primera página de 16 avisos, o el cartel
de login. Y por lo mismo **el filtro de "no vistas" tampoco se puede usar**: ese
filtro vive en tu cuenta de Indeed, y el sistema entra sin cuenta.

Eso último no importa tanto, porque **lo que hace ese filtro ya lo hace el
sistema, y mejor**: el dedupe contra `seen_jobs.json` no te muestra dos veces el
mismo aviso, y lo hace para las ocho fuentes a la vez, no sólo para Indeed. En
la corrida del 9/9 sacó 72 avisos repetidos de 115.

**Lo que sí trae más es buscar por más términos**, porque cada búsqueda tiene su
propia primera página. Medido con la misma ventana de 7 días:

```
1 término   -> 16 avisos
6 términos  -> 51 avisos únicos
```

Por eso tu perfil quedó con seis términos y `max_queries: 4`: se consultan
cuatro por corrida, rotando, y en dos días se cubren los seis.

También quedó `sort=date`. Como sólo se puede leer la primera página, lo que
entre ahí es todo lo que vamos a ver, y conviene que sea lo más nuevo. Encaja
con lo que decías de que a veces publican todo junto y a veces de a uno.

### El techo de Indeed son unos 11 avisos por corrida

Traer más del listado **no sirve**, y esto está medido: el cuello no está en el
listado sino en el detalle. De los avisos que se encuentran sólo se puede leer
entre el 38% y el 50%, y no es rate-limiting: probado con lotes de 10, 5 y 3 con
pausas crecientes, la tasa no se mueve (33%, 38%, 38%). Los que fallan son
siempre los mismos en dos rondas seguidas, así que es una propiedad del aviso,
no de la request. Traer 30 del listado en vez de 20 sube el gasto de TinyFish y
deja los mismos 11.

Se evaluó y **se descartó** exprimir el listado, que sí trae empresa, ubicación
y un pedazo de la descripción: los links vienen en una lista aparte, sin el
texto al lado, así que habría que emparejar cada bloque con su aviso por
posición. Basta que Indeed intercale un anuncio para que los títulos y las
empresas queden cruzados, y un aviso con la empresa equivocada es peor que un
aviso que no está.

### Un detalle que se arregló probando

Las dos fuentes pedían el cupo entero (`results_wanted`) en cada término, así
que el primero lo llenaba solo y el segundo no aportaba nunca: `Backend`
devolvía 30 y `AI Engineer` 0 nuevos. Ahora el cupo se reparte entre los
términos, y Get on Board pasó de 7 avisos a 10.

---

## 2.23. El contador de postulaciones, y los gráficos de Métricas

**"9 trabajos a los que apliqué", grande y en verde, arriba de la lista.** Es lo
único de toda la app que mide el trabajo de **la persona** y no el del sistema:
los otros contadores dicen cuántas ofertas hay, éste dice cuántas veces te
postulaste. Por eso es lo más grande de la pantalla y lo único que usa un tamaño
de letra por encima de la escala (`--text-hero`, token nuevo).

Con un selector de período al lado: 7 días, 2 semanas, un mes, 2 meses, 3 meses,
o desde que empezaste.

**Y al lado, el reparto por semana.** Eso es lo que hace que el total signifique
algo: 9 postulaciones en un mes puede ser tres semanas sin hacer nada y una a
los tiros, y en el total eso no se ve. Hoy tu gráfico dice exactamente eso: 9,
todas en la última semana, las once anteriores en cero.

Tres decisiones:

- **Va sólo en Sin marcar**, que es la pantalla que se abre por defecto. En
  Filtradas ya está el marcador de la auditoría, y dos marcadores en la misma
  pantalla no se leen: compiten.
- **El verde no decora.** En este sistema significa lo que ya hiciste, igual que
  en la tarjeta de una oferta aplicada, y va siempre con la palabra al lado.
- **Las semanas en cero se dibujan igual**, pero en gris. Un hueco en el eje se
  lee como "acá no hay dato", y acá el cero es el dato. En verde llamaban la
  atención sin tener nada que decir.

### Los gráficos: cuáles sí y cuáles no

Los gráficos se dibujan **con HTML y los tokens del sistema, sin librería, sin
SVG y sin una sola llamada a la red**. Una barra es un `div` con un ancho en
porcentaje: el navegador ya sabe hacer eso, el texto usa la tipografía del
sistema y escala con ella, y si cambia la paleta cambian también los gráficos.

**Un gráfico se gana el lugar cuando hay varias magnitudes que comparar de un
vistazo.** Con dos filas no hay comparación, hay dos números, y para dos números
la tabla ocupa menos y se lee más rápido. El corte está en tres filas:

| Sección | Qué quedó | Por qué |
|---|---|---|
| Lo que descartó el sistema | **tabla** | Son dos filas: idioma y lugar |
| Por qué descartaste vos | **barras** | Cuatro motivos que se comparan entre sí |
| De dónde vienen | **barras** | Ocho portales, y lo que importa es cuál pesa |
| Puntajes | **columnas** | Nuevo. Ver abajo |

**Cuando hay gráfico, la tabla sigue estando debajo, plegada** en *Ver los
números*. Un gráfico no da el valor exacto ni se puede copiar, y a veces lo que
se quiere es justamente el número.

### El gráfico nuevo: qué tan bien te encajan las ofertas

Es el que no existía y el que más dice. Muestra cuántas ofertas hay en cada
tramo de puntaje, y contesta *"¿el sistema me está trayendo cosas buenas?"* sin
abrir la lista. Una montaña pegada al cero significa que las búsquedas están mal
apuntadas; una repartida significa que el problema es otro.

Va en columnas y no en barras horizontales porque **el eje tiene un orden propio,
de 0 a 100**: ordenarlo por tamaño, como se ordenan las barras, destruiría lo
único que este gráfico tiene para decir.

Los dos tramos de arriba van en verde, y ése es el único color distinto de todos
los gráficos. Lo lleva porque significa algo: de ahí para arriba el sistema te
avisa por Telegram.

### Los tokens que hubo que agregar

`DESIGN.md` no trae ninguno para gráficos, así que se propusieron cuatro:
`--data-fill`, `--data-track`, `--data-destacada` y `--text-hero`. Son pocos
porque **todos los gráficos de la app son de una sola serie**: la magnitud la
lleva el largo de la barra, no el tono. No hay dos series que distinguir, así
que no hay paleta que validar ni leyenda que poner, y el título dice qué se está
midiendo.

Un test falla si alguna regla de gráfico escribe un color propio en vez de usar
esos tokens.

---

## 2.24. LinkedIn URLs: armar la búsqueda de publicaciones a mano

El agujero que tapa esto es el único del sistema que **no se puede resolver
scrapeando**: muchas vacantes se publican como posteo del muro y nunca llegan a
la pestaña de empleos (publicar así le sale gratis a la empresa). LinkedIn no
deja leer eso desde afuera, y Google lo indexa uno a tres días tarde, así que
cuando `google_posts` lo trae ya se llenó de postulantes.

La salida es al revés: **la app arma la dirección y vos la abrís**. Es trabajo
tuyo, pero te da lo único que importa acá, que es llegar temprano.

**Publicaciones ahora va primero**, y Jobs quedó atrás: Jobs ya lo cubre el
buscador automático.

### Cómo se usa

La pantalla va partida al medio: **a la izquierda lo que elegís, a la derecha lo
que sale**. Tildás puestos, elegís si el reclutador escribe en español o inglés,
dónde, qué dejar afuera, y de cuándo. Apretás **Armar la búsqueda** y la
dirección aparece al lado, entera y a la vista. Tres botones: **Abrir en
LinkedIn** (el principal), **Copiar link** y **Guardar en favoritos** con un
nombre.

Es la única pantalla de la app que **no scrollea**: mide lo que mide la ventana
y lo que se mueve es cada mitad por dentro. Antes iba todo en una columna larga,
así que la dirección nacía abajo de todo, fuera de pantalla; y como el
constructor es un formulario GET, armarla recarga la página y el navegador la
abre arriba. O sea que cada intento te mandaba al principio y encima el
resultado quedaba donde no lo veías. Partido en dos eso desaparece, y además la
columna del constructor vuelve al renglón donde estabas.

Los favoritos quedan abajo, con *Abrir*, *Copiar* y *Sacar de favoritos*. La
idea es tener cuatro o cinco y revisarlas dos veces por día: los posteos buenos
duran horas.

**Los puestos que aparecen tildables son tus palabras clave**, las mismas de
*Mi perfil* → *Qué busco*. No hay una lista aparte que mantener: si agregás
"GenAI Engineer" ahí, aparece acá; si sacás "Machine Learning Engineer", se va
de acá. Un solo lugar donde tocar.

Tiene una consecuencia, y conviene tenerla presente: **esas mismas palabras son
las que el buscador automático usa para pegarle a los portales**. Si agregás una
sólo para armar búsquedas de LinkedIn, también vas a empezar a recibir ofertas
de ese puesto en la lista de Trabajos. Suele ser lo que querés, pero no es
gratis.

Si todavía no cargaste ninguna palabra clave, la pantalla ofrece seis puestos
sugeridos para que no arranque vacía.

### Los favoritos

*Abrir* va en violeta, igual que *Armar la búsqueda*: es la acción de esa
tarjeta, la única razón por la que guardaste la búsqueda. Copiar y sacar quedan
en el menú de tres puntos, como en las ofertas.

**La misma dirección no se guarda dos veces.** Si intentás guardar una que ya
tenías, no se agrega ni se pisa la que estaba: aparece un cartel verde que dice
con qué nombre ya la tenías, que es el dato que hace falta para encontrarla en
la lista. Para renombrar una, se saca y se guarda de nuevo.

Antes las dos formas de fallar contestaban lo mismo, y guardar algo repetido
decía *"esa dirección no es una búsqueda de publicaciones"*: mentira, y encima
te mandaba a corregir lo que estaba bien.

### El anotador de al lado del botón

**Apliqué desde acá**, con un menos, el número, un más y **Confirmar**, pegado a
*Armar la búsqueda*. Al lado del rótulo hay un signo de pregunta: pasás el mouse
por encima y ahí está la explicación entera, sin ocupar lugar el resto del
tiempo.

Existe porque lo que mandás desde un posteo no pasa por ninguna oferta de la
lista: no entró por el scraper, no está en el historial y no hay tarjeta que
marcar. Sin esto, justo el trabajo que más cuesta (buscar a mano, temprano, el
mismo día que se publicó) era el único que no se contaba, y el número grande de
Trabajos mentía para abajo.

**Son dos pasos y no uno.** El más y el menos mueven un anotador que todavía no
cuenta para nada. *Confirmar* lo pasa al contador grande de Trabajos y **lo deja
en cero**. Así podés contar mientras mandás, corregir un toque de más, y recién
cerrar la cuenta cuando terminaste.

Lo que no confirmás **no se borra solo**: si cerrás la pantalla con 3 anotadas,
siguen ahí cuando volvés. Y armar una búsqueda tampoco lo resetea, que es
justamente lo que hacía falta: armar recarga la pantalla.

Al confirmar aparece un cartel verde arriba que dice cuántas sumaste y cuántas
van en total. Es lo único de los tres que avisa: el más y el menos se ven en el
número mismo.

Lo confirmado **suma al contador grande de Trabajos** y al reparto por semana.
Es el mismo trabajo: mandar un CV. Cuando hay postulaciones anotadas así, el
contador grande lo dice en su línea de abajo, para que no suba solo y sin
explicación.

De lo confirmado se guarda la fecha y hora, no un total: si fuera un número
pelado, el selector de período no podría contestar "¿cuántas mandé esta
semana?". La hora es la de cuando confirmaste, no la de cada envío, que nadie
anotó; para lo que se usa, el día es el mismo.

**Una cosa que todavía no se puede hacer**: deshacer un *Confirmar*. El menos
saca del anotador, no de lo confirmado. Si algún día confirmás de más, avisame y
lo arreglamos a mano.

Las pestañas de Métricas no lo cuentan a propósito: sus números son un reparto
de las 183 ofertas que entraron al sistema, y estas postulaciones no son ofertas
del sistema. Meterlas ahí rompería la suma.

### Lo que se descubrió probando contra LinkedIn

Todo esto se verificó el 10/9/2026 con la cuenta abierta, no salió de leer
documentación. Está acá porque si algún día deja de funcionar, esto es el mapa.

**Los parámetros que andan:**

```
keywords=(boolean)               el texto, con AND/OR/NOT y comillas
datePosted="past-24h"            y "past-week", "past-month"
sortBy="date_posted"             o "relevance"
postedBy=["first","following"]   mi red y a quien sigo
origin=FACETED_SEARCH
```

Los valores van **con comillas adentro**. LinkedIn acepta las dos formas pero
devuelve ésta, así que la guardada es igual a la suya.

**`contentType=["jobs"]` existe y quedó afuera.** Es el filtro "Anuncios de
empleo". Funciona, pero deja la lista en **cero**: ese tipo de contenido es el
posteo con formato de vacante de LinkedIn, no el texto libre que escribe un
reclutador, que es justo lo que buscamos. Un control que rompe la búsqueda no
es una opción, es una trampa.

**`NOT (a OR b)` devuelve cero.** Éste fue el hallazgo que más costó:

```
... AND buscamos NOT (Junior OR trainee OR pasantía)   ->  CERO
... AND buscamos NOT Junior                            ->  trae posteos
... AND buscamos NOT Junior NOT trainee NOT pasantía   ->  trae posteos
```

LinkedIn agrupa con paréntesis en todos lados **menos después de un NOT**. Se
emite un NOT por término.

**Y hay un largo máximo.** Arriba de cierto punto LinkedIn devuelve cero sin
avisar: aplica los filtros, muestra "No se han encontrado resultados" y te deja
creyendo que no hay vacantes. Medido la misma tarde, con la misma cuenta:

| Caracteres | Qué tenía | Resultado |
|---|---|---|
| 70 | 2 puestos + 2 frases | trae posteos |
| 96 | 2 puestos + 2 frases + lugar | trae posteos |
| 117 | 2 puestos + 4 frases | trae posteos, de hace 1 minuto |
| 164 | 2 puestos + 6 frases | **cero** |

El tope quedó en **110**, con margen. Cuando lo que elegís no entra, **se
recorta y la pantalla te lo dice**: qué quedó afuera y por qué. Callarlo sería
peor que el problema, porque creerías estar buscando "vacante" y no.

Qué se sacrifica primero, en orden: se conservan **dos frases-gatillo antes que
nada** (sin ellas la búsqueda deja de traer vacantes y trae cualquier posteo que
hable de AI Engineer), después los NOT, y último las frases de más.

### Una cosa que NO quedó cerrada

Varias búsquedas con el NOT puesto dieron cero, y **no pude distinguir si el NOT
rompe la consulta o si simplemente filtró los pocos posteos que había**. En 24
horas hay dos o tres posteos de AI Engineer: alcanza con que uno diga "Ssr" para
que el NOT lo saque y quede vacío. Como no lo pude probar, **no se codificó
ninguna regla al respecto**: el NOT se emite con la sintaxis correcta y listo.

Si al usarlo ves que tildar *Puestos junior* siempre te deja en cero, destildalo
y avisá: ahí sí hay algo para mirar con datos de verdad.

---

# 3. LO QUE YA ESTÁ HECHO

Sin detalle, para no volver a discutirlo:

- **La pantalla local** (`abrir.bat`): barra lateral con Trabajos, Métricas y Mi
  perfil, y el estado del sistema fijo al pie. Oscura, navegable con teclado,
  usable en celular.
- **Marcar ofertas**, con motivo obligatorio al descartar. Al
  marcarla se va de *Sin marcar* con una animación, y el cartel de arriba la
  nombra: con dos ofertas de 90 pegadas no se notaba cuál había desaparecido.
- **Archivar** los avisos vencidos, de a uno o todos los de más de N días, sin
  ensuciar lo que el sistema aprende de tus descartes (2.17).
- **Apliqué y Descarté sirven para revisar**: ordenadas por cuándo las marcaste,
  con la fecha en la tarjeta. Para cuando te llaman y no te acordás a qué
  empresa le mandaste el CV.
- **Ordenadas por puntaje y de a 20 por página**, con las recién publicadas
  arriba de todo. Ordenar sólo por fecha abría la lista con lo peor: las que
  puntúan 0 son las que no son para vos, y si entraron hoy quedaban primeras.
  Por eso a la banda de recientes sólo suben las que llegan a tu puntaje mínimo.
- **Aviso de ofertas nuevas sin apretar F5**: si entra una corrida con la
  pantalla abierta, aparece un cartel abajo y vos decidís cuándo actualizar.
- **Filtro por antigüedad del aviso**: hoy, 7 días, 30 días, sin filtro. Lee las
  cuatro formas distintas en que los portales escriben la fecha.
- **Cartel de cuántas ofertas se pierden por no saber inglés**, con cuánto
  puntuaba la mejor. Baja solo si subís tu nivel en Mi perfil.
- **Fuentes**: páginas de empleo de empresas, LinkedIn Jobs, publicaciones de
  LinkedIn vía buscador, Bumeran, Zonajobs, Computrabajo, y reclutadores que
  seguís. Los tres portales argentinos verificados contra los sitios.
- **Seguir a un reclutador de LinkedIn** aunque LinkedIn no deje leer su perfil:
  se buscan sus publicaciones en Google y se leen ésas (2.7).
- **Antigüedad máxima, una sola perilla en Mi perfil**, que heredan todas las
  fuentes. Los tres portales ahora sí reportan cuándo se publicó el aviso, que
  antes no lo hacían nunca (2.8).
- **Las recién publicadas van arriba de todo**, separadas con un rótulo, sin
  tocar el puntaje: a las de hoy se postuló menos gente (2.8).
- **Scoring con Gemini** leyendo tu CV contra cada aviso, con cadena de modelos
  de respaldo.
- **Regla de ubicación** (2.1) y filtro de idioma.
- **Descarte antes del scoring** por título y por país, para no pagar por
  puntuar lo que ya se sabe que no sirve (2.16).
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
- **Reescribir el `README.md`** como guía de instalación para cada persona.

---

# 5. LOS ARCHIVOS

Los tres `.bat` son todo lo que tocan las personas que no programan:

| Archivo | Para qué | Cuándo se usa |
|---|---|---|
| `instalar.bat` | Instala todo y programa las búsquedas automáticas | Una vez al principio, y de nuevo cada vez que agregues un perfil o muevas la carpeta |
| `abrir.bat` | **La pantalla**: todo lo demás | Todos los días |
| `desinstalar.bat` | Deja de buscar y borra el programa. Pregunta aparte si borrar los datos | Cuando consiguieron trabajo |

Eran cinco. `buscar_ahora.bat` y `estado.bat` se borraron: son un botón y una
sección adentro de la pantalla (2.19). Cada `.bat` menos es una cosa menos que
explicarle a alguien que no programa, y una ventana negra menos abriéndose.

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
│   ├── formulario.py la pestaña Mi perfil
│   ├── render.py     el HTML
│   ├── estilos.py    el CSS: los tokens de DESIGN.md, una sola vez
│   └── corrida.py    buscar ahora, y como viene funcionando el motor
└── sources/
    ├── rrhh_profiles.py   seguir reclutadores por URL
    ├── portales_ar.py     Bumeran / Zonajobs / Computrabajo
    ├── indeed.py          Indeed AR (Cloudflare: ver 2.22)
    └── getonbrd.py        Get on Board, por su API publica
```
