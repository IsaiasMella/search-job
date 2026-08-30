# Notas de la noche del 30/08/2026

Seis tareas del checklist, un commit cada una, todo con tests. **60 tests pasan**
(`.venv\Scripts\python.exe -m pytest tests -q`). No toqué la UI, el drafter, los
perfiles de tu familia ni las fuentes nuevas.

No modifiqué `COSTOS.md` porque lo tenías abierto y editándolo. Al final de estas
notas está qué tildar.

---

## Qué hice

### 1. Regla de Bahía Blanca — `31ca6b5`

`filters.passes_place()` reemplaza a las dos llamadas sueltas a
`passes_work_mode` y `passes_location` dentro de `apply_filters`. La regla:

1. **Remoto en cualquier lado** → la ubicación no filtra.
2. **Presencial o híbrido en tu ciudad** → pasa aunque `work_modes` diga sólo
   remoto. Es el caso que se estaba perdiendo.
3. Todo lo demás, como antes.

Campo nuevo en el perfil: `filters.location.home_city`, cargado con
`"Bahía Blanca"` en `profiles/isaias.json` (tu `candidate.seeking` ya decía que
vivís ahí). Si un perfil no lo tiene, se usa `city`; si tampoco, la excepción
nunca dispara y el filtro se comporta como antes.

Una decisión que tomé y conviene que revises: **el presencial local exige que el
aviso diga la ciudad**. Si no la dice, no se asume que sea Bahía Blanca. Si se
asumiera, todo presencial sin ciudad entraría como local y sería un falso
positivo sistemático — justo lo contrario del criterio "lo que el aviso no dice,
no filtra", pero acá la asimetría se justifica: el que no dice ciudad casi nunca
es de Bahía Blanca.

### 2. Duplicados entre fuentes — `5fda322`

`Job.dedupe_key` = `"empresa|título"` normalizados, además de la URL:

- el título va con los tokens ordenados y sin ruido, así `"Senior Data Scientist
  (Remote)"` (LinkedIn) y `"data-scientist-senior"` (slug de la careers page) dan
  la misma clave;
- la empresa pierde el país y la forma societaria, así `"Globant Argentina"`
  (viene de `companies.json`) y `"Globant"` (viene de LinkedIn) también;
- **sin empresa la clave es vacía y no se deduplica por esta vía**: si no, un
  "Data Scientist" de `google_posts` sin empresa se comería al de cualquier otra.

Cuando las dos copias caen en el mismo lote se queda **la más completa**, no la
primera: primero pesa si trae modalidad y país como campos estructurados
(LinkedIn los trae, `careers` no), después el largo de la descripción. La clave
se persiste en `seen_alt_keys` para que la copia de la otra fuente no vuelva a
entrar en la corrida siguiente.

### 3. Vacantes ya cubiertas — `2fc4bff`

`filters.filled_marker()` busca "vacante cubierta", "ya cubierta", "posición
cerrada", "búsqueda cerrada" y variantes (más las de LinkedIn en inglés, "no
longer accepting applications") en URL, título y descripción. Se aplica en el
motor **antes del scoring**: puntuar una búsqueda cerrada es gastar una llamada
al LLM para tirarla después. Quedan marcadas como vistas para que no vuelvan en
cada corrida mientras el buscador las tenga indexadas.

### 4. `notify_when_empty` — `c8969f4`

La opción ya estaba implementada (motor y los dos notificadores). Lo que no
cumplía era el objetivo: el mensaje decía "Sin novedades hoy" a secas, así que
seguía sin distinguirse de "se rompió". Ahora el aviso vacío trae el detalle de
la corrida: cuántas ofertas se revisaron y de qué fuentes, cuántas ya estaban
vistas, cuántas eran vacantes cubiertas, cuántas se cayeron por cada filtro, si
ninguna llegó al `min_score`, y las fuentes o notificadores que no estuvieron
disponibles. Si no falló nada, lo dice: *"Ningún error en la corrida: el
silencio es del mercado, no del sistema."*

Lo dejé en `true` en tu perfil.

### 5. `use_search: false` en las 7 empresas — `a568580`

Mercado Libre, Mutt Data, Ualá, Despegar, Naranja X, Banco Galicia y Swiss
Medical Group. El flag ya estaba soportado por empresa en `careers.py`; sólo lo
activé. **Sus careers pages se siguen leyendo**: lo que se apaga es la búsqueda
por dominio, que es la parte cara (serial, ~3s cada una).

### 6. Campos de feedback — `4be80be`

`Job.aplicado` (True verde / False rojo / None sin mirar), `Job.motivo_descarte`
y `Job.fecha_feedback`. Persistencia:

- `State.record_feedback(url, aplicado, motivo_descarte)` escribe en
  `job_history.json` (el archivo durable; `last_run.json` se pisa en cada corrida
  con novedades) y espeja en `last_run.json` si la oferta es de la última tanda.
  Devuelve `False` si la URL no está, para que la UI lo avise en vez de perder
  el dato en silencio.
- `save()` ya no pisa las entradas del historial: una oferta que vuelve a
  aparecer conserva su feedback.
- `State.feedback_jobs(aplicado=False, limit=15)` devuelve las descartadas de la
  más reciente a la más vieja — es exactamente lo que va a consumir el prompt de
  scoring cuando hagas el Bloque 2.

**No construí la UI ni el wizard**, como pediste. Nada escribe ni lee estos
campos todavía.

---

## Tests

No había ninguno, así que armé `tests/` con pytest (lo instalé en el `.venv`;
**falta agregarlo a `requirements.txt`** — no lo toqué porque ese archivo tiene
las instrucciones de instalación para tu familia y quería que lo miraras vos).

```
.venv\Scripts\python.exe -m pytest tests -q      →  60 passed
```

| Archivo | Qué cubre |
|---|---|
| `test_filters_place.py` | Regla de Bahía Blanca: presencial local entra, presencial en otra ciudad no, presencial sin ciudad no se asume local, remoto en cualquier lado, `remote_anywhere: false`, perfiles sin `home_city` |
| `test_dedupe.py` | Normalización de empresa y título, dedupe dentro del lote y entre corridas, se queda la copia más completa, ofertas distintas no colapsan, estados viejos sin `seen_alt_keys` |
| `test_vacantes_cubiertas.py` | Las cuatro frases pedidas + variantes, en URL / título / descripción, sin tildes y en mayúsculas, y que no dispare con avisos abiertos |
| `test_corrida_vacia.py` | El aviso vacío distingue corrida sana de fuente caída |
| `test_engine_smoke.py` | Corrida completa de punta a punta con la fuente dummy, sin red ni LLM |
| `test_companies_use_search.py` | Las 7 empresas apagadas, y que `_discover_from_search` efectivamente las saltee |
| `test_feedback.py` | Ida y vuelta a JSON, guardado, URL con querystring, URL desconocida, que el feedback no se pierda cuando la oferta vuelve |

Lo que **no** probé: una corrida real contra TinyFish, LinkedIn y Gemini. No la
corrí para no gastarte cuota ni escribir estado real de noche. Cuando quieras
verificarlo:

```
.venv\Scripts\python.exe -m vacantia.run --profile isaias --dry-run
```

---

## Decisiones que necesito que tomes vos

1. **¿Remoto en cualquier lado, en serio?** Implementé la regla como está
   escrita en el checklist: si el aviso dice remoto, el filtro de país no se
   aplica. Efecto secundario: van a empezar a entrar remotos de España, México y
   Estados Unidos, que antes se caían por `country`. A muchos los va a frenar el
   filtro de idioma, pero no a todos (un remoto de México es en español). Si
   preferís que las remotas sigan acotadas a Argentina, es una línea:
   `"remote_anywhere": false` en `filters.location` del perfil. Lo dejé en `true`
   porque es lo que dice el checklist, pero no es obvio que sea lo que querés.

2. **¿Bahía Blanca y alrededores?** Hoy `home_city` es exactamente `"Bahía
   Blanca"` (el match es por contención, así que "Bahía Blanca, Buenos Aires"
   entra). Si te sirve un presencial en Punta Alta o en Ingeniero White, el campo
   acepta lista: `"home_city": ["Bahía Blanca", "Punta Alta"]`. No lo agregué
   porque no sé hasta dónde estás dispuesto a viajar.

3. **¿Híbrido local cuenta igual que presencial local?** Hoy sí, los dos entran.
   Un híbrido en Bahía Blanca es ir a la oficina algunos días. Si querés
   distinguirlos hay que partir la regla.

4. **`notify_when_empty: true` son 3 mensajes de Telegram por día aunque no haya
   nada.** Lo dejé prendido porque es lo que pedía el checklist y porque es lo
   que te avisa si se rompió algo, pero si molesta, es cambiar un `true` por un
   `false`.

5. **¿Las 7 empresas siguen en `companies.json`?** Les apagué la búsqueda por
   dominio, pero sus careers pages se siguen leyendo en cada corrida y tampoco
   aportaron nada (según la sección 5, `careers` no trajo ni una de las 8
   ofertas). Si querés, se sacan del archivo y ahorrás también los fetches. No lo
   hice porque borrar empresas es decisión tuya.

6. **¿Qué significa `aplicado = True`?** Lo dejé como "verde": te sirve. Pero
   podría significar "me postulé". Son cosas distintas y el prompt de scoring va
   a aprender distinto según cuál sea. Definilo antes de construir la pestaña
   Trabajos: una vez que empieces a cargar datos, cambiar el significado
   invalida lo cargado.

7. **`pytest` en `requirements.txt`.** No lo agregué (ver arriba). Si va, iría
   como dependencia de desarrollo, separada de lo que instala tu familia.

---

## Qué tildar en el checklist de COSTOS.md

**Bloque 1:** `Campos nuevos en Job: aplicado, motivo_descarte, fecha_feedback`
(hecho el modelo y el guardado; la UI que los escribe, no).

**Bloque 5:** Regla de Bahía Blanca · Duplicados entre fuentes · Descartar
vacantes ya cubiertas · `notify_when_empty` · `use_search: false` en las 7
empresas.

---

## Lo que falta — todo el checklist pendiente

### Bloque 1 — La UI local
- [ ] Servidor local + `abrir.bat` que abra `http://localhost:8756`
- [ ] Pestaña **Mis datos**: CV, keywords, país/ciudad, modalidad, idioma, URLs de RRHH a seguir
- [ ] Pestaña **Trabajos**: lista con verde/rojo + motivo obligatorio en rojo
- [x] Campos nuevos en `Job` — *hecho esta noche (modelo + persistencia)*

### Bloque 2 — Que el sistema aprenda
- [ ] Guardar el feedback desde la pestaña Trabajos → *la parte de estado ya está:
      `State.record_feedback()`. Falta quién la llame.*
- [ ] Meter las últimas ~15 descartadas con su motivo al prompt de scoring como
      ejemplos negativos, y las aplicadas como positivos → *`State.feedback_jobs()`
      ya devuelve exactamente eso; falta armar el bloque del prompt en `scoring.py`*

### Bloque 3 — Documentos para postularse
- [ ] CV en PDF con botón de descarga (`fpdf2`, ya en requirements; ojo con la fuente Unicode)
- [ ] Mensaje corto para DM a reclutador y para mail (los moldes de la sección 10, corregidos por vos)
- [ ] Para tu perfil: modo "consejo" en vez de generación (qué reordenar, qué keyword falta para el ATS)

### Bloque 4 — Que la familia lo pueda usar
- [ ] `profiles/hermana.json` + `resume/hermana.md` (marketing)
- [ ] `profiles/papa.json` + `resume/papa.md` (QHSE, presencial, oil & gas)
- [ ] Perfiles de tus dos hermanos menores (ventas / gastronomía)
- [ ] Una carpeta por persona: perfil, `.env` con **su** `TELEGRAM_CHAT_ID`, CV y `companies.json` de su rubro
- [ ] **Fuentes para rubros no técnicos** (Bumeran / Zonajobs / Computrabajo) — lo que más condiciona si esto sirve para tu familia
- [ ] **Seguir perfiles de RRHH puntuales por URL** — está en tu spec original y no existe

*Nota: la regla de Bahía Blanca le sirve directo al perfil de tu viejo. QHSE en
oil & gas es presencial casi siempre; con `home_city` cargada y `work_modes`
vacío, los presenciales de su zona entran solos.*

### Bloque 5 — Calidad de los resultados
- [x] Regla de Bahía Blanca — *hecho*
- [x] Duplicados entre fuentes — *hecho*
- [x] Descartar vacantes ya cubiertas — *hecho*
- [x] `notify_when_empty` — *hecho*
- [x] `use_search: false` en las 7 empresas — *hecho*
- [ ] **Cargar más empresas** en `companies.json` — sigue pendiente y es tuyo: hay que elegirlas

### Bloque 6 — Vigilar, sin urgencia
- [ ] Ruido de posts de opinión en `google_posts`
- [ ] País vacío en `google_posts` (el snippet rara vez lo dice → entra LATAM en general)
- [ ] Rareza geográfica de LinkedIn (`Londres, Catamarca, Argentina`)
- [ ] La pestaña de "shops" y las otras fuentes que mencionaste
- [ ] Recolección compartida entre los dos hermanos que se cruzan

### Fuera del checklist, apareció ahora
- [ ] Decidir si `pytest` va a `requirements.txt` (como dependencia de desarrollo)
- [ ] Las 7 decisiones de arriba
