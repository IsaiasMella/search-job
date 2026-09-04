# Notas para Isaías

**237 tests pasan.**

**Estado al 4/9/2026.** Andando: los 3 portales argentinos, el scoring con el
LLM (Gemini con crédito), la pantalla con filtro por fecha y modo oscuro.
Bloqueado: seguir reclutadores por su perfil de LinkedIn, que **no se puede** y
no es arreglable (2.5). Sin empezar: que el sistema aprenda de tus descartes,
que lo dejaste afuera a propósito. Lo que falta hacer a vos está en la primera
tabla.

```
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest tests -q      →  237 passed
```

---

# 1. LO QUE TENÉS QUE REPASAR VOS

Esta es la lista corta. Todo lo demás es contexto.

## Falta hacer

| # | Qué | Dónde | Cuánto te lleva |
|---|---|---|---|
| 1 | **Reemplazar la URL de LinkedIn de RRHH** por la página de la consultora. La que cargaste no puede funcionar | ver 2.1 | 5 min |
| 2 | **Corregir los moldes de mensaje** contra tu experiencia | `vacantia/mensajes.py` | 10 min |
| 3 | Una **corrida real** de punta a punta con todo prendido | `--dry-run` primero | 10 min |
| 4 | **Cargar el chat de Telegram de cada persona** cuando armes sus carpetas | ver 3.2 | 1 min c/u |
| 5 | **Correr `instalar.bat` de nuevo** cuando haya más de un perfil | — | 5 min |

## Ya hecho

| Qué | Cuándo |
|---|---|
| ~~Verificar los 3 portales argentinos~~ | 4/9/2026, ver 2.1 |
| ~~Verificar la fuente `rrhh`~~ probada: LinkedIn la bloquea, ver 2.5 | 4/9/2026 |
| ~~Poner crédito en la cuenta de Gemini~~ los 3 modelos responden | 4/9/2026 |
| ~~Confirmar la regla de ubicación~~ corrió con puntajes reales del LLM | 4/9/2026 |

---

# 2. LO QUE NO PUDE VERIFICAR

## 2.1. Las dos fuentes nuevas

| Qué | Por qué | Cómo lo verificás |
|---|---|---|
| ~~**Bumeran, Zonajobs, Computrabajo**~~ ✅ **verificados el 4/9/2026** | Se probaron los tres contra los sitios reales, uno por vez | Bumeran 12 avisos, Zonajobs 5, Computrabajo 20. Ninguno dio "0 aviso(s)": las direcciones y los patrones andan. Lo que sí apareció está en 2.4 |
| ~~**La fuente `rrhh`**~~ ⚠️ **probada el 4/9/2026: LinkedIn la bloquea** | El código anda; LinkedIn devuelve la página vacía a quien no tiene sesión | Ver 2.5. Sirve con páginas de consultoras, no con perfiles de LinkedIn |
| **El instalador multi-perfil** | Registra tareas programadas de verdad en Windows; no lo corrí | Corré `instalar.bat` con dos perfiles y fijate que aparezcan dos tareas en `estado.bat` |

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


## 2.3. ~~La cuenta de Gemini sin crédito~~ ✅ RESUELTO el 4/9/2026

> **Ya está arreglado.** Cargaste crédito y los tres modelos responden. La
> corrida siguiente trajo puntajes reales del LLM, con razones escritas y
> despegados entre sí (40, 50, 75, 88) en vez de todos apelotonados en 61-79.
> Queda escrito abajo por si vuelve a pasar, porque el mensaje de error
> apuntaba al lado equivocado.

Al verificar los portales salió que **el scoring con LLM no estaba corriendo**.
Falló en las tres corridas, con los tres modelos, siempre igual.

Son dos problemas encadenados, y el segundo es el que importa:

**a) Dos de los tres modelos ya no existen.** Google dio de baja
`gemini-2.5-flash-lite` y `gemini-2.5-flash` para las cuentas nuevas: devuelven
404 diciendo "no longer available to new users". **Ya lo arreglé**, el perfil
quedó apuntando a los vigentes:

```
model:            gemini-3.5-flash-lite
fallback_models:  gemini-flash-lite-latest, gemini-3.6-flash
```

**b) Pero la cuenta no tiene crédito, y eso no lo arregla el código.** Probé los
siete modelos flash que tu API key puede ver, uno por uno. Los siete responden
lo mismo:

```
429 - Your prepayment credits are depleted.
      Please go to AI Studio at https://ai.studio/projects
```

No es el límite diario del plan gratis: es el saldo de la cuenta en cero. Es un
problema conocido y le está pasando a mucha gente, incluso en proyectos free
tier sin uso ([foro de Google, agosto-septiembre
2026](https://discuss.ai.google.dev/t/429-prepayment-credits-are-depleted-on-a-fresh-confirmed-free-tier-project/177394)).

**Qué hacer, en este orden:**

1. Entrá a <https://ai.studio/projects>, mirá el estado de facturación del
   proyecto y cargá crédito si hace falta.
2. Si eso no lo destraba, **el plan B ya está listo y probado**: tu key de
   OpenRouter funciona (responde 200, uso 0). Se cambia desde la pantalla,
   poniendo `provider` en `openrouter` en `profiles/isaias.json`. El techo son
   50 llamadas/día, que alcanza para una corrida diaria.

**Mientras tanto el sistema no se rompe, pero miente el puntaje.** Cae a una
heurística que sólo cuenta cuántas de tus keywords aparecen en el título:

```
[ 68] Ai Engineer Hibrido ... — [heurística, sin LLM] 1/2 keywords del perfil
```

Por eso los puntajes salen todos apelotonados entre 61 y 79 y ninguno se
despega. **Los avisos que te llegaron por Telegram estos días no están
ordenados por qué tan bien te quedan**: nadie leyó tu CV contra el aviso.

De paso arreglé el mensaje de error, que te mandaba por el camino equivocado.
Decía *"Revisá la API key del proveedor y su cuota diaria"* cuando el problema
era el saldo. Ahora, si la falla es de la cuenta, lo dice con esas palabras y
corta al toque en vez de reintentar los tres modelos (18s → 0,8s).

## 2.4. Lo que apareció al verificar los portales

Los tres andan. Pero la corrida real mostró cuatro cosas que no se veían.

**1. Bumeran y Zonajobs son la misma base de avisos.** Los dos son de Navent.
Zonajobs trajo 5 avisos y los 5 eran los mismos de Bumeran, con el mismo id:

```
bumeran   .../cloud-data-engineer-|-ai-real-time-marco-marketing-2188711.html
zonajobs  .../cloud-data-engineer-|-ai-real-time-marco-marketing-2188711.html
```

Lo dice el propio Bumeran en los avisos republicados: *"Este aviso fue publicado
por ZonaJobs"*. **Prendé uno de los dos, no los dos.** Ya está avisado en la
pantalla, abajo del tilde de cada uno.

**2. Computrabajo repetía el mismo aviso hasta 12 veces.** Cuelga la posición en
la lista de resultados del final de la dirección (`#lc=ListOffers-Score4-3`) y
publica el mismo puesto con varios ids. De 20 direcciones, había 9 avisos
reales. **Arreglado**: ahora el título sale del encabezado de la página del
aviso en vez del pedazo de la dirección, y con eso el dedupe por empresa+título
los junta.

**3. Ningún portal llenaba empresa, ciudad ni modalidad.** Eso los dejaba fuera
de tu regla de ubicación —así entró un presencial de Jujuy con el perfil puesto
en Bahía Blanca— y sin `company` el dedupe tampoco corría. **Arreglado**: se
leen de la página del aviso, que ya se baja igual para la descripción, así que
no cuesta ni una llamada más.

> Ojo con la causa, porque es sutil: `city` y `work_mode` los completa
> normalmente el LLM al puntuar. Estaban vacíos **porque el LLM estaba caído**
> (2.3), no porque los portales estuvieran mal escritos. Leerlos en la fuente es
> un cinturón de seguridad: ahora, si el modelo se cae, la regla de ubicación
> sigue filtrando igual.

**4. Buscó con 2 keywords, no con 5.** Tu perfil tiene dos (`AI engineer`,
`Python`) mientras que la fuente de LinkedIn tiene cinco términos. Si es a
propósito, ignoralo; si no, se agregan desde la pantalla en *Palabras clave*.

**Lo que quedó sin arreglar, a propósito**: cuando Bumeran republica un aviso de
Zonajobs, esa página viene recortada y no trae ni la empresa ni la ubicación.
Sin empresa, el dedupe por empresa+título no puede juntarlo con el original.
Juntarlos pedía tocar `Job.dedupe_key`, que es una decisión de diseño con su
motivo escrito, y el aviso en pantalla resuelve el caso real. Queda dicho acá.

## 2.5. ⚠️ Los perfiles de LinkedIn no se pueden seguir. Probado.

Cargaste el perfil de un reclutador peruano y **la URL estaba perfecta**, con
`/recent-activity/all/` y todo. El tilde también. No corriste la búsqueda
todavía, así que lo probé directo contra la página.

**Devuelve cero, y la culpa no es tuya ni del programa.** Lo comparé:

| Qué pedí | Qué volvió |
|---|---|
| `linkedin.com/in/<el-perfil>/recent-activity/all/` | **nada** |
| `linkedin.com/in/<el-perfil>/` (el perfil pelado) | **nada** |
| una página cualquiera de Computrabajo (control) | 9959 caracteres, 85 links |

O sea que no es el formato de la URL ni el lector: **LinkedIn devuelve la página
vacía a cualquiera que no tenga la sesión iniciada.** Y no hay forma de
arreglarlo desde acá sin entrar con usuario y contraseña, que es justamente lo
que este proyecto no hace: es lo que te haría bloquear la cuenta.

**Qué sí funciona:** cualquier página pública que liste búsquedas. La página de
la consultora del reclutador, el blog de empleos de una cámara, la bolsa de
trabajo de una universidad. Esas se leen enteras.

**Qué hacer con tu peruano:** buscalo en Google con el nombre de su consultora y
pegá la página donde ella lista los puestos, no la de inicio. Si trabaja por su
cuenta y sólo publica en LinkedIn, esa persona no se puede seguir con esta
herramienta.

**Ya está avisado en la pantalla**, en el recuadro debajo del campo, en rojo y
arriba de todo. Y el log ahora lo dice con todas las letras en vez del escueto
"sin contenido", que se leía igual que un error de configuración.

> Ojo con no confundirse: la fuente **`google_posts` sí trae publicaciones de
> LinkedIn** y sigue andando, porque las busca por el buscador y nunca toca
> LinkedIn. Lo que no se puede es seguir a una persona puntual.

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

> ⚠️ **Esta cuenta quedó vieja con lo del 4/9/2026.** El número de llamadas
> nunca fue el problema: la cuenta de Gemini se quedó **sin crédito**, que es
> otra cosa y no depende del uso. Ver 2.3. Si terminás pasando a OpenRouter,
> las 50/día sí pasan a ser el techo, y ahí alcanza para una corrida diaria por
> perfil, no para tres.

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

## 3.6. Filtro por antigüedad y el cartel del inglés

**El problema**: 207 avisos en la lista, muchos del mes pasado y ya cubiertos.

**Filtro nuevo**, arriba de la lista: *Hoy · Últimos 7 días · Últimos 30 días ·
Sin filtro*. Cada botón trae el número al lado, así se ve qué va a pasar antes
de apretarlo. Con tus datos de hoy: 44 / 66 / 170 / 207. **Siete días te corta
de 207 a 66.**

Se cruza con el filtro de estado sin pisarlo, y el rango sobrevive a marcar una
oferta: antes cada clic te devolvía a la lista completa.

**El dato de la fecha era un lío** y por eso esto no era trivial. `posted_at`
viene en cuatro formatos (`2026-08-21`, `hace 2 semanas`, `9 jun 2026`) y
**falta en el 44% de los avisos**. Se parsea todo en `vacantia/fechas.py`, con
tests para cada forma: si un portal cambia el formato, falla un test y no el
filtro en silencio.

Dos decisiones que conviene conocer:

1. **Un aviso sin fecha no se esconde nunca.** No tener el dato no es lo mismo
   que ser viejo. Si los tirara, "Hoy" te escondería media lista sin decir por
   qué.
2. **La tarjeta distingue "publicado" de "visto".** Cuando el aviso dice cuándo
   se publicó, dice *publicado hace 5 d*. Cuando no lo dice, cae a la fecha en
   que lo encontramos y dice *visto hace 5 d*, porque el aviso puede ser mucho
   más viejo. Pasale el mouse por arriba y te dice la fecha exacta.

**El cartel del inglés** también está, arriba de todo y sin botón de cerrar,
como lo pediste. Hoy dice:

> **103** ofertas que no podés tomar porque piden inglés. La mejor puntuaba
> **88**, *Senior Python AI Engineer*.

Se recalcula contra el historial cada vez que se abre la pantalla, no se guarda:
si subís tu nivel de inglés en *Mis datos*, el número baja solo. Y respeta el
filtro de fechas, así que con "Últimos 7 días" te dice cuántas perdiste esta
semana, no en total.

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
| ~~`349898d`~~ | ~~CV en PDF~~ — sacado el 4/9/2026 |
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

## Bloque 1 — La UI local ✅ COMPLETO Y VERIFICADO (4/9/2026)

El checklist de este bloque no estaba acá: vivía en `COSTOS.md`, que se borró en
`c73aea4`. Lo recuperé del historial de git y lo dejo escrito, que era lo que
faltaba para poder darlo por hecho de verdad.

- [x] Servidor local + `abrir.bat` que abra `http://localhost:8756`
      — arranca, `/` redirige a `/trabajos`, las dos pestañas dan 200
- [x] Pestaña **Mis datos**: CV, keywords, país/ciudad, modalidad, idioma, URLs de RRHH
      — los ocho campos están en el formulario
- [x] Pestaña **Trabajos**: verde/rojo + campo de motivo obligatorio en rojo
      — probado que descartar sin motivo lo frena **del lado del servidor**, no
      sólo con el JavaScript, y que no escribe nada
- [x] Campos nuevos en `Job`: `aplicado`, `motivo_descarte`, `fecha_feedback`
      — `models.py:96-98`, y `state.py:191` vuelve a exigir el motivo al guardar

Lo cubren 32 tests entre `test_ui.py` y `test_feedback.py`.

**Lo único que queda es mirarlo vos**: que se vea bien, que el doble clic en
`abrir.bat` le funcione a alguien que no programa. Eso no lo puede verificar un
test.


## Bloque 2 — Que el sistema aprenda ⬜ PENDIENTE (lo dejaste fuera a propósito)

- [x] Guardar el feedback — la pantalla ya lo escribe
- [ ] **Meter las últimas ~15 descartadas con su motivo al prompt de scoring**
      como ejemplos negativos, y las aplicadas como positivos.
      *Está todo listo para engancharlo*: `State.feedback_jobs(aplicado=False,
      limit=15)` devuelve exactamente eso. Falta armar el bloque de texto en
      `scoring.SCORE_PROMPT`. Media hora.

## Bloque 3 — Documentos para postularse ✅ COMPLETO

- [x] ~~CV en PDF con botón de descarga~~ — **sacado el 4/9/2026**: el PDF salía
      feo y no valía la pena arreglarlo. Se borró todo (`vacantia/pdf.py`, el
      botón, la ruta `/cv.pdf`, los tests y la dependencia `fpdf2`). El CV en
      Markdown sigue estando en `resume/` y se edita desde la pantalla.
- [x] Mensaje corto para DM y para mail — *borradores, corregilos*
- [x] Modo "consejo" en vez de generación

## Bloque 4 — Que la familia lo pueda usar 🟡

- [x] Fuentes para rubros no técnicos — **verificadas contra los sitios el 4/9/2026** (2.4)
- [x] Seguir perfiles de RRHH por URL — **probada: sirve para consultoras,
      NO para perfiles de LinkedIn** (2.5)
- [x] Que cada uno pueda armar su perfil y su Telegram por separado
- [ ] **Cargarle el `chat_id` a cada persona** cuando les pases la carpeta (3.2)

## Bloque 5 — Calidad de los resultados 🟡

- [x] Regla de Bahía Blanca — **corregida con tu criterio de remoto** (3.1)
- [x] Duplicados entre fuentes
- [x] Descartar vacantes ya cubiertas
- [x] `notify_when_empty`
- [x] `use_search: false` en las 7 empresas
- [x] Empresa, ciudad y modalidad en los portales — sin eso la regla de
      ubicación no corría en ninguno de los tres (2.4)
- [x] El mismo aviso repetido dentro de Computrabajo (2.4)
- [x] ~~Poner crédito en Gemini~~ — hecho el 4/9/2026, los 3 modelos responden
      y el scoring volvió a ser real (2.3)
- [x] Nombres de modelo actualizados: Google dio de baja los `gemini-2.5-*` (2.3)

## Bloque 6 — Vigilar ✅ COMPLETO

- [x] Ruido de posts de opinión en `google_posts`
- [x] País vacío en `google_posts`
- [x] Rareza geográfica de LinkedIn
- [x] La "pestaña de jobs" — es la pestaña Trabajos, ya está
- [x] ~~Recolección compartida~~ — **descartada**: todo aislado, cada uno en su compu

## Bloque 7 — La pantalla, segunda vuelta ✅ COMPLETO (4/9/2026)

- [x] Modo oscuro, foco visible con teclado, botones de dedo en el celular
- [x] Barra de guardar pegada abajo: el botón quedaba fuera de pantalla
- [x] El error de "falta el motivo" al lado del campo, no en un cartel que tapa todo
- [x] **Filtro por antigüedad del aviso** (3.6) — 7 días te corta de 207 a 66
- [x] **Cartel de cuántas se pierden por inglés** (3.6)

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
├── fechas.py         leer el 'posted_at' de cada portal (4 formatos)
├── mensajes.py       moldes de DM y mail (borradores)
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
