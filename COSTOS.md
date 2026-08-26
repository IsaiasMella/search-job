# Vacantia — hasta dónde llega el plan gratis

> Documento de trabajo, borralo cuando no lo necesites más.
> Números medidos sobre corridas reales del 24 y 26 de agosto de 2026, no estimados a ojo.
> Precios verificados contra la documentación de cada proveedor en agosto de 2026.

---

## 0. EMPEZÁ ACÁ

### En qué anda el proyecto

El motor está **completo y funcionando**: tres fuentes, dedupe, scoring con LLM contra tu CV, filtros de país / modalidad / idioma, notificación por Telegram, y despliegue con doble clic para gente no técnica. Ya te llegaron ofertas reales al celular.

Lo que falta ahora **no es motor, es interfaz y personas**: que tu familia pueda usarlo y que el sistema aprenda de lo que descartás.

### Falta un paso tuyo, de 30 segundos

Pegar la API key de Gemini en `.env` (hueco `GEMINI_API_KEY`, se saca de [aistudio.google.com/apikey](https://aistudio.google.com/apikey)). Sin eso el scoring cae a keywords y los puntajes no significan nada. Ya se agotó la cuota diaria de OpenRouter una vez.

### El próximo paso, y por qué

**La UI local.** Destraba tres cosas de un saque: la carga de datos de cada persona, la pestaña de Trabajos, y el ciclo de aprendizaje. Sin ella, tu viejo y tu hermana no pueden usar esto aunque el motor ande perfecto.

### Decisiones cerradas — no volver a discutirlas

| Decisión | Por qué |
|---|---|
| **UI web local, no Notion** | Notion exige cuenta + token + base por persona. Rompe el "doble clic y listo" que ya resolvimos. |
| **Nada de Electron ni Obsidian** | Un runtime entero para mostrar dos tablas. |
| **Se instala en la PC de cada uno, no en Hostinger** | La IP residencial de cada casa es lo que LinkedIn no bloquea. Gratis y mejor. |
| **Tarea programada, no proceso residente** | No consume nada, se recupera solo, recupera corridas perdidas. |
| **LLM en Gemini** | 1000 req/día gratis contra 50 de OpenRouter. Y 5x más rápido. |
| **Fase 4 (Gmail inbox): descartada** | En Argentina no te ofrecen trabajo por mail en frío; te contactan después de que aplicás. |
| **Nada de "relocación a UE"** | Nadie de la familia se va del país. Sacado del perfil. |
| **PDF con botón de descarga, no Ctrl+P** | El usuario más difícil tiene 62 años. Si hay que explicar un paso, perdimos. `fpdf2`, ya probada. |
| **Nada de auto-apply** | Ya estaba decidido y sigue firme. |

---

## 1. Respuesta corta

**Sí, da para 3 corridas por día. Y da para 6 personas, gratis — pero hay que cambiar una cosa.**

| | 1 persona, 3x/día | 3 personas | 6 personas |
|---|---|---|---|
| TinyFish (careers + posts) | gratis | gratis | gratis |
| Telegram | gratis | gratis | gratis |
| JobSpy / LinkedIn | gratis | gratis | **riesgo de bloqueo de IP** |
| LLM con OpenRouter free | alcanza justo | **se rompe** | **se rompe** |
| LLM con **Gemini free** | gratis | gratis | **gratis** |

El único cuello de botella real es el LLM, y **tu API de Gemini lo resuelve sin gastar un peso**: el free tier de Gemini son **1000 requests/día** contra las **50/día** de OpenRouter. Veinte veces más.

Lo que sí puede costarte plata en algún momento no es una API, es **la IP** desde la que scrapeás LinkedIn.

---

## 2. Qué APIs usa el proyecto

| Servicio | Para qué | Obligatoria | Plan actual |
|---|---|---|---|
| **TinyFish** | `careers` (leer careers pages) y `google_posts` (buscar posts de LinkedIn) | Sí | Free |
| **OpenRouter** | Puntuar ofertas contra tu CV | Sí (o alternativa) | Free |
| **Telegram Bot** | Mandarte los resultados | No (cae a consola) | Free |
| **python-jobspy** | `linkedin` (LinkedIn Jobs) | No | Librería, sin API |
| Google Custom Search | Alternativa a TinyFish en `google_posts` | No | Sin usar |

### Límites de cada plan gratis

**TinyFish** — [pricing](https://www.tinyfish.ai/pricing)
- Search: **30 requests/minuto**
- Fetch: **150 URLs/minuto**
- **Sin tope diario ni mensual.** Search y Fetch son gratis para siempre.
- Lo que sí se paga es Agent ($0,016/step) y Browser ($0,002/min) — **vacantia no los usa**.

**OpenRouter** — [docs](https://openrouter.ai/docs/api-reference/limits)
- 20 requests/minuto
- **50 requests/día** con menos de US$10 de crédito histórico
- 1000/día si alguna vez compraste US$10 (el límite queda para siempre, aunque el saldo vuelva a cero)
- ⚠️ Las 50/día son **de la cuenta, compartidas entre todos los modelos free**. La cadena de 4 modelos de fallback no te da 200 requests: te da resiliencia si uno está caído.

**Gemini** — free tier
- 5–15 requests/minuto según modelo
- **hasta 1000 requests/día**
- ⚠️ En el free tier Google puede usar tus prompts para mejorar sus productos. Para algo con CVs de terceros, conviene el tier pago (que igual es centavos).

**Telegram Bot API** — gratis, ~30 mensajes/segundo. Irrelevante a esta escala.

---

## 3. Cuánto consume una corrida (medido)

De 33 llamadas reales al LLM:

```
tokens IN  por llamada : 3.138 promedio  (máx 5.113)
tokens OUT por llamada : 3.744 promedio  (máx 5.462)
duración               : 51s promedio    (máx 106s)
```

Con lotes de 6 ofertas por llamada:

| Ofertas nuevas | Llamadas | Tokens |
|---|---|---|
| 44 | 8 | 55k |
| 100 | 17 | 117k |

**Consumo de TinyFish por corrida:** 14 searches (10 de `careers` + 4 de `google_posts`) y ~27 URLs de fetch.

**Consumo de LinkedIn:** 3 sesiones de scraping (sin API, sin costo monetario).

### El dedupe es lo que hace viable las 3 corridas

Esto es clave y no es obvio. La primera corrida del día trae ~100 ofertas y ~40 son nuevas. Las siguientes traen **las mismas 100**, pero el estado ya las vio, así que sólo se puntúan las publicadas en el ínterin.

El dedupe es **por URL del aviso** (`state.py`, `Job.key`), no por query ni por empresa. Eso tiene una consecuencia importante que se explica en la sección 7 ter.

```
12:00  -> ~100 recolectadas, ~25 nuevas -> 5 llamadas al LLM
16:30  -> ~100 recolectadas,  ~5 nuevas -> 1 llamada
23:59  -> ~100 recolectadas, ~10 nuevas -> 2 llamadas
                                    total: ~8 llamadas/día/persona
```

**El LLM sólo paga por lo nuevo.** TinyFish y LinkedIn sí pagan las 3 corridas completas, pero ahí no hay tope diario.

---

## 4. ¿Da para 3 corridas por día?

**Con 1 persona: sí, sobrado, incluso con OpenRouter free.**

~8 llamadas/día contra un tope de 50. Te sobra para 6 corridas diarias.

El único día apretado es el primero después de cargar empresas nuevas o cambiar los `search_terms`: no porque se re-indexe nada, sino porque entran muchas ofertas genuinamente nuevas de golpe. Eso ya está resuelto con el triaje — ver sección 7 ter.

**Tu horario propuesto está bien pensado y no toca ningún límite:**

| Hora | Racional tuyo | Nota técnica |
|---|---|---|
| 12:00 | — | La corrida más cara del día (acumula la noche) |
| 16:30 | Antes de que RRHH se vaya | La más barata, casi todo ya visto |
| 23:59 | Freelancers y remotos que publican fuera de horario | Ojo: cruza la medianoche, ver abajo |

⚠️ **Detalle del cambio de día:** el tope de OpenRouter se resetea a medianoche UTC, que en Argentina es **las 21:00**. Una corrida a las 23:59 hora local cae en el día UTC siguiente. A tu favor, no en contra.

---

## 5. ¿Y para 3 y 6 personas?

Cada perfil tiene su propio estado (`state/<perfil>/`), así que **no comparten dedupe**: 6 personas son 6 veces todo.

### Los 6 perfiles son de rubros distintos, y eso cambia varias cosas

No es un equipo de gente parecida: AI engineer, supervisor de seguridad e higiene, marketing, y dos que hacen ventas / gastronomía / lo que aparezca. Sólo los dos últimos se solapan entre sí.

Consecuencias concretas:

1. **No se puede compartir la recolección.** Era mi recomendación principal para bajar la carga 6x, y con rubros distintos **no aplica**: cada perfil necesita sus propias búsquedas. Sólo sirve para los dos hermanos que sí se cruzan, y ahí el ahorro es 2x sobre dos perfiles, no 6x sobre seis.

2. **Cada perfil necesita su propio `companies.json`.** Las empresas que publican para seguridad e higiene no son las que publican para AI. La fuente `careers` ya acepta `companies_file` por perfil, así que se resuelve con configuración, sin tocar código.

3. **El mix de fuentes debería ser distinto por perfil, y esto es lo más importante.** Las tres fuentes que armamos están sesgadas a tecnología:
   - `linkedin` (JobSpy) sirve bien para AI, marketing y algo de ventas. Para gastronomía y mostrador es casi inútil: esos puestos no se publican ahí.
   - `google_posts` busca posts de RRHH — funciona para cualquier rubro, pero hay que cambiarle los `roles` y los `hiring_terms`.
   - `careers` sirve para empresas grandes con portal propio (útil para seguridad e higiene en industria).

   **Para los perfiles de gastronomía y ventas van a hacer falta fuentes que todavía no existen**: los portales argentinos donde sí se publican esos puestos (Bumeran, Zonajobs, Computrabajo). Es una fase 4, y sin eso esos dos perfiles van a recibir muy poco.

4. **El filtro de inglés casi no aplica fuera de tu perfil.** Para seguridad e higiene, gastronomía y ventas en Argentina, `allow_english: false` no va a descartar prácticamente nada. Y el `report.english_pain` sólo tiene sentido en tu perfil.

| | Llamadas LLM/día | ¿Entra en OpenRouter free (50)? | ¿Entra en Gemini free (1000)? |
|---|---|---|---|
| 1 persona | ~8 | Sí | Sí |
| 3 personas | ~24 | Sí, pero sin margen | Sí |
| 6 personas | ~48 | **No** — un día de picos lo revienta | Sí, con 20x de margen |

**Con 3 personas ya estarías rozando el techo de OpenRouter.** Un día en que cargues empresas nuevas para alguien, se cae al scoring heurístico por keywords sin avisarte más que en el log.

### Ya está: el LLM pasó a Gemini ✅

Implementado. `vacantia/llm.py` tiene ahora el proveedor `gemini`, usando el [endpoint compatible con OpenAI](https://ai.google.dev/gemini-api/docs/openai) (`https://generativelanguage.googleapis.com/v1beta/openai/`), así que reusa el mismo cliente y la misma cadena de fallback que OpenRouter — no hizo falta el SDK de Google.

Configuración en el perfil:

```jsonc
"llm": {
  "provider": "gemini",
  "gemini_api_key": "${GEMINI_API_KEY}",
  "model": "gemini-2.5-flash-lite",
  "fallback_models": ["gemini-flash-lite-latest", "gemini-2.5-flash"]
}
```

**Falta un solo paso tuyo:** pegar la key en `.env` (está el hueco `GEMINI_API_KEY`). Se saca de [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Sin la key, el motor avisa en el log y cae al scoring heurístico — no se rompe.

**Por qué esa cadena de fallback:** `gemini-2.5-flash-lite` es el más barato hoy ($0,10/$0,40), pero **Google lo retira el 16 de octubre de 2026** — dentro de siete semanas. Cuando deje de responder, la cadena pasa sola al siguiente sin que tengas que tocar nada. Por eso el segundo de la lista es `gemini-flash-lite-latest`, que es el alias que Google mantiene apuntando al Flash-Lite vigente.

Beneficio secundario: **velocidad**. Nemotron tardaba 51s por llamada y una corrida completa ~12 minutos. Flash-Lite responde en 5–10s. Con 6 perfiles × 3 corridas = 18 corridas/día, la diferencia es entre **3,6 horas** y **1,2 horas** de máquina prendida por día.

Para volver a OpenRouter alcanza con cambiar `"provider"`: la key sigue en el perfil.

---

## 6. ¿Y si igual hay que pagar? Cuánto sale

Costo por corrida de 100 ofertas nuevas (53k in + 64k out), con precios de agosto 2026:

| Modelo | Precio (in/out por 1M) | Por corrida | 6 personas, 3x/día, 30 días |
|---|---|---|---|
| **GPT-5 Nano** | $0,05 / $0,40 | $0,028 | **~$2,40/mes** |
| **Gemini 2.5 Flash-Lite** | $0,10 / $0,40 | $0,031 | ~$2,60/mes |
| GPT-5.6 Luna | $0,20 / $1,20 | $0,088 | ~$7,40/mes |
| Gemini 3.1 Flash-Lite | $0,25 / $1,50 | $0,110 | ~$9,20/mes |
| Gemini 3.7 Flash | $0,75 / $3,75 | $0,280 | ~$23,60/mes |

*(el mensual sale del consumo real con dedupe — 6 personas × 8 llamadas/día × 30 días = 1.440 llamadas, 4,5M tokens de entrada y 5,4M de salida — no de corridas completas)*

**Conclusión de plata: mantener esto para 6 personas cuesta entre US$2,40 y US$9 por mes**, según el modelo. La salida pesa 10x más que la entrada en la factura, así que el precio de *output* es el que hay que mirar al elegir.

Con crédito de Gemini y el modelo más barato: US$10 te dan **~4 meses**, US$30 te dan **~11 meses** — y eso *sin contar* el free tier de 1000/día, que a este volumen ya te cubre entero.

⚠️ Ojo con dos cosas del cuadro:
- **Gemini 2.5 Flash-Lite se retira el 16 de octubre de 2026.** Después el más barato de Google pasa a ser 3.1 Flash-Lite, casi 4x más caro.
- **Gemini 3.7 Flash duplica precio el 1 de enero de 2027** (hoy está en precio introductorio).

Tus US$2–3 de OpenAI dan para ~100 corridas completas con Nano. Alcanza para probar, no para producción de 6 personas.

---

## 7. El cuello de botella que NO se arregla con plata

**LinkedIn / JobSpy.** No hay API ni plan: es scraping sin login, y LinkedIn limita por IP. Con 1 persona son 9 sesiones de scraping por día. Con 6 personas son **54 sesiones diarias desde la misma IP**.

No puedo darte un número exacto de cuándo bloquea — no está documentado y depende de la IP. Lo que sí sé por el código: cuando pasa, `linkedin_jobs.py` loguea el error y sigue con las demás fuentes. **No se rompe la corrida, se rompe la fuente**, y te enterás sólo si mirás el log.

Con los perfiles siendo de rubros distintos, **la salida barata que te había propuesto (compartir la recolección) ya no aplica**. Quedan estas:

1. **Bajar la frecuencia de `linkedin` solamente.** Gratis y efectivo. No hace falta que las 3 corridas scrapeen LinkedIn: con `hours_old: 168` la ventana es de una semana, así que **una corrida diaria alcanza**. `careers` y `google_posts` siguen 3x/día. Esto solo baja la carga de 54 a 18 sesiones diarias.
2. **Sacar `linkedin` de los perfiles donde no rinde.** Gastronomía y mostrador no se publican ahí. Si sólo 3 de los 6 perfiles la usan, son 9 sesiones diarias.
3. **Compartir recolección entre los dos hermanos que sí se cruzan.** Ahorro 2x sobre esos dos perfiles.
4. **Proxies.** `linkedin_jobs.py` ya acepta el campo `proxies` y lo pasa a JobSpy. Es la última que probaría — ver abajo.

---

## 7 bis. Hostinger: la pregunta del hosting

**Respuesta corta: Hostinger no tiene rotación de IP, y mudarte ahí empeora el problema de LinkedIn en vez de mejorarlo.**

Según la [página de VPS de Hostinger](https://www.hostinger.com/vps-hosting), cada VPS KVM trae **una IP dedicada fija**. No ofrecen IPs adicionales, ni proxies, ni rotación. Los planes van de US$6,49 a US$25,99/mes.

Y el problema no es sólo que sea una sola IP: **es una IP de datacenter**. LinkedIn bloquea rangos de datacenter mucho más agresivamente que las conexiones residenciales. Hoy estás scrapeando desde tu casa, con una IP residencial de tu proveedor — que es el escenario *más favorable* que vas a tener. Mudarlo a un VPS te pone en el rango que LinkedIn filtra primero.

**Esto no significa no usar Hostinger.** Significa separar las cosas:

| Fuente | ¿Anda bien desde un VPS? | Por qué |
|---|---|---|
| `careers` | Sí | Le pega a TinyFish, no al sitio. La IP que scrapea es de TinyFish. |
| `google_posts` | Sí | Igual: le pega a TinyFish. **Por esto se diseñó así.** |
| `linkedin` (JobSpy) | **Riesgoso** | Es la única que sale desde tu IP hacia LinkedIn. |
| Telegram / Gemini | Sí | APIs normales. |

Tres opciones, en orden de lo que yo haría:

**a) Hostinger sin la fuente `linkedin`.** Ponés `"enabled": false` en esa fuente y listo. Perdés la fuente con datos estructurados, pero `google_posts` sigue trayendo ofertas de LinkedIn — indexadas por el buscador, sin tocar LinkedIn. Es gratis, es simple, y es exactamente el motivo por el que la fase 2 se hizo antes que la fase 3.

**b) Híbrido.** Todo en Hostinger salvo `linkedin`, que corre una vez al día desde tu PC. Es más trabajo de mantenimiento (dos lugares) pero conservás todo.

**c) Hostinger + proxies residenciales.** Precios reales de agosto 2026, de [Proxyway](https://proxyway.com/best/rotating-proxies):

| Proveedor | Tipo | Precio |
|---|---|---|
| **Webshare** | residencial | **plan gratis: 10 IPs y 1 GB/mes** |
| Byteful | residencial | $3,25/GB |
| Webshare | residencial | $3,50/GB |
| Decodo | residencial | desde $4/GB |
| Rayobyte | datacenter | $0,30/GB |

⚠️ **Los de datacenter son baratos pero no sirven acá** — son justamente el rango que LinkedIn bloquea. Para LinkedIn hay que ir a residencial.

Estimación de consumo: cada corrida de `linkedin` baja ~75 páginas de aviso con descripción completa, unos **10–15 MB**. Con 6 perfiles y una corrida diaria son ~2,7 GB/mes ≈ **US$9,50/mes** en residencial. Con 3 corridas diarias se va a ~8 GB ≈ **US$28/mes**.

**Ese número es mayor que todo el costo del LLM.** Y es una estimación, no una medición: habría que instrumentar el tráfico real antes de comprometerse.

El plan gratis de Webshare (1 GB/mes) te alcanza para probar el mecanismo con uno o dos perfiles antes de pagar nada.

---

## 7 ter. ¿Cómo evitar que se re-indexe todo al agregar una empresa?

**Buena noticia: eso ya no pasa, y mi documento decía lo contrario. Estaba mal y lo corregí.**

Fui a mirar `state.py`. El dedupe es por `Job.key`, que es la URL del aviso normalizada (sin query params, sin barra final, en minúsculas). **No** por query, ni por empresa, ni por hash del perfil. O sea: si agregás 20 empresas a `companies.json`, las ofertas de las 10 viejas siguen marcadas como vistas y no se vuelven a puntuar. Sólo entran las URLs nuevas.

Lo mismo vale para cambiar `search_terms` o `roles`: si una búsqueda nueva encuentra un aviso que ya viste por otra vía, el dedupe lo agarra.

### El problema real no es re-indexar, es el pico

Lo que sí pasa es un **pico de backfill**: cargás 20 empresas y entran 200 ofertas genuinamente nuevas de una. Eso son ~34 llamadas al LLM en una sola corrida, y con OpenRouter free (50/día) te comés la cuota del día entero.

**Ya está resuelto.** Agregué un triaje en `scoring.py`, activado con `max_new_per_run` en el perfil:

```jsonc
"max_new_per_run": 30
```

Cómo funciona:

1. Si las ofertas nuevas superan el tope, se ordenan con el **scoring heurístico por keywords**, que ya existía y es Python puro: **cero llamadas a la API, cero costo**.
2. Se le mandan al LLM sólo las N más prometedoras.
3. Las diferidas **no se marcan como vistas**, así que vuelven en la próxima corrida.

Probado con 50 ofertas y tope de 10:

```
corrida 1: nuevas=50  puntuadas=10  diferidas=40
corrida 2: nuevas=40  puntuadas=10  diferidas=30
corrida 3: nuevas=30  puntuadas=10  diferidas=20
corrida 4: nuevas=20  puntuadas=10  diferidas=10
corrida 5: nuevas=10  puntuadas=10  diferidas= 0
```

El backlog se drena en 5 corridas — o sea, en menos de dos días con tu horario. Y lo importante: **en la primera corrida se puntuaron las más prometedoras**, no las primeras que llegaron. En la prueba, las ofertas de AI Engineer salieron en la tanda 1 y las de mostrador quedaron para después.

Con `max_new_per_run: 30` (lo que te dejé puesto) el techo es de **5 llamadas al LLM por corrida**, pase lo que pase. Multiplicado por 6 personas y 3 corridas: 90 llamadas/día en el peor caso absoluto — que entra en Gemini (1000/día) con margen, y reventaría OpenRouter.

### Un efecto secundario que conviene conocer

Una oferta con heurística persistentemente baja podría quedar diferida muchas corridas. En la práctica el backlog se drena porque el tope es mayor que el flujo diario normal (~25 nuevas/día contra un tope de 30). Si algún día ves `diferidas` distinto de cero de forma sostenida en el log, es señal de que el tope quedó chico para el volumen de ese perfil.

---

## 7 quater. Cómo lo instalan los que no son técnicos

Resuelto. Cuatro archivos `.bat` en la raíz, pensados para que alguien que no programa no tenga que entender nada.

### Y de paso resuelve el problema de la IP

Esto no es sólo comodidad: **cada máquina de cada persona es una IP residencial distinta**. Es exactamente lo que LinkedIn no bloquea, y es gratis. Instalar en la PC de cada uno no es la alternativa pobre al hosting — para la fuente `linkedin` es *mejor* que cualquier VPS, y hace innecesarios los proxies de la sección 7 bis.

### Los cuatro archivos

| Archivo | Qué hace |
|---|---|
| `instalar.bat` | Todo. Instala Python si falta, arma el entorno, instala dependencias, programa las corridas y prueba que ande. |
| `estado.bat` | "¿Esto anda?" — muestra si está programado, cuándo corrió, cómo le fue y los avisos recientes. |
| `buscar_ahora.bat` | Una búsqueda ya, sin esperar el horario. |
| `desinstalar.bat` | Deja de correr solo. No borra nada. |

Más `LEEME.txt`, escrito sin una sola palabra técnica.

### Por qué tarea programada y no un proceso corriendo

Pediste que "quede corriendo en segundo plano". Lo implementé con el **Programador de tareas de Windows** en vez de un proceso residente, y es mejor por tres motivos:

- **No consume nada** entre corridas. Un proceso durmiendo 8 horas para despertarse 3 veces ocupa RAM al pedo.
- **Se recupera solo.** Si una corrida se cuelga o la PC se reinicia, la siguiente arranca igual. Un proceso residente que muere, muere.
- **Recupera las corridas perdidas.** Con `StartWhenAvailable`, si la máquina estaba apagada a las 12:00 la búsqueda se hace apenas la prenden. Esto es clave: tu papá y tus hermanos no dejan la PC prendida 24/7.

Disparadores: al iniciar sesión (con 3 minutos de espera para que levante la red) + 12:00, 16:30 y 23:59.

Corre con `pythonw.exe`, no `python.exe`: **no abre ninguna ventana negra**. Verificado que en ese modo `sys.stdout` es `None`, `print()` queda en no-op silencioso y el log igual se escribe completo en UTF-8 con acentos.

### El obstáculo que casi lo rompe

`Register-ScheduledTask` devolvía **"Acceso denegado"** en una cuenta sin privilegios de administrador. Para un instalador que van a correr personas no técnicas, eso lo mata.

Aislé la causa probando pieza por pieza: no eran los settings ni el nombre de la tarea, era **`New-ScheduledTaskTrigger -AtLogOn` sin `-User`**. Sin ese parámetro, Windows entiende "cuando inicie sesión *cualquier* usuario", que es una operación de administrador. Acotándolo al usuario actual, más un `-Principal` explícito con `RunLevel Limited`, **una cuenta común registra la tarea sin problema**.

Verificado sin elevación: 4 disparadores, `StartWhenAvailable=True`, próxima ejecución calculada.

### Lo que tenés que preparar vos antes de entregar cada carpeta

El instalador no le pregunta nada a la persona — a propósito. Vos preparás la carpeta y ellos sólo hacen doble clic. Por cada uno:

1. `profiles/<nombre>.json` — **un solo perfil por carpeta**, así el instalador lo detecta solo y no pregunta.
2. `.env` con las claves (pueden compartir la de TinyFish y la de Gemini; **el `TELEGRAM_CHAT_ID` tiene que ser el de cada uno**).
3. `resume/<nombre>.md` con su CV.
4. `companies.json` con empresas de *su* rubro.

### Dos cosas que van a pasar

- **Si mueven la carpeta, deja de funcionar.** La tarea guarda la ruta absoluta. Está avisado en `LEEME.txt` en mayúsculas, pero va a pasar igual. La solución es correr `instalar.bat` otra vez desde la ubicación nueva.
- **SmartScreen les va a mostrar el cartel azul** la primera vez. También está explicado en el `LEEME.txt`, con los dos clics que hay que hacer.

---

## 8. Resumen ejecutivo

- **Hoy, 1 persona, 3 corridas/día: gratis y sobra.**
- **Para 6 personas: gratis en APIs.** Con Gemini como LLM (ya implementado) el cuello de botella del LLM desaparece: 48 llamadas/día contra un tope de 1000.
- **Si algún día pagás LLM, son US$2,40–9/mes.** Es lo más barato de todo esto.
- **El gasto real que puede aparecer no es el LLM: son los proxies.** US$9,50–28/mes si insistís con la fuente `linkedin` desde un VPS. Y es evitable: `google_posts` trae ofertas de LinkedIn sin tocar LinkedIn.
- **Hostinger no resuelve lo de la IP, lo empeora** — y ya no hace falta. Instalando en la PC de cada uno, cada persona aporta su propia IP residencial, que es justo lo que LinkedIn no bloquea. El despliegue en las máquinas de ellos vuelve innecesarios los proxies.
- **El techo verdadero no es técnico ni económico: es de mantenimiento.** Seis perfiles de seis rubros distintos son seis `companies.json`, seis juegos de `search_terms` y, para dos de ellos, fuentes que todavía no existen.

---

## 9. La UI local — decidido, falta construirla

### Cómo funciona

Un `.bat` más, `abrir.bat`, que levanta un servidor web en la propia máquina y abre el navegador solo:

```
http://localhost:8756
```

El puerto es arbitrario, sólo tiene que ser uno alto y poco usado para no chocar con nada. La página **no sale a internet**: sirve archivos desde la misma PC y lee/escribe directo sobre `profiles/<nombre>.json` y `state/<nombre>/`.

### Por qué esto y no Notion

- **Cero instalación extra.** Python ya está después de `instalar.bat`.
- **Cero cuentas y cero tokens.** Notion pedía cuenta propia, token de integración y base creada a mano, por persona. Eso rompe todo lo que resolvimos para que la instalación sea un doble clic.
- **La interfaz ya la saben usar.** Es el navegador.
- **Una sola fuente de verdad.** Escribe sobre los archivos que el motor ya usa, sin sincronizar nada.
- **Encaja con el patrón** de los `.bat` que ya existen.

Lo que se pierde: acceso desde el celular. No importa — **Telegram avisa en el teléfono, la UI es para sentarse a revisar.** Son dos momentos distintos.

### Las dos pestañas

**Pestaña 1 — Mis datos.** Que cada uno cargue lo suyo sin tocar un JSON: CV, palabras clave, país y ciudad, modalidad, si quiere ofertas en inglés, y las URLs de perfiles de RRHH a seguir.

**Pestaña 2 — Trabajos.** La lista de ofertas con dos botones: **verde = apliqué**, **rojo = no apliqué**. Si es rojo, un campo de texto obligatorio con el motivo. Ese texto es lo que hace que el sistema aprenda (sección 11).

---

## 10. El drafter: qué generar, para quién, y los mensajes

### La distinción que ordena todo esto

**Tu CV no se toca.** Pagaste un curso, está afinado, y tenés evidencia de que funciona: mandaste pocos currículums y te contactaron de varias fuentes. Un CV generado que vos mismo describís como robótico es un downgrade.

**Pero tu familia no tiene eso.** Tu viejo y tus hermanos no hicieron ese curso. Para ellos, un CV generado a partir de sus datos es muchísimo mejor que lo que tienen. **Ahí sí generamos.**

O sea: la función existe para todos, pero para vos es opcional y para ellos es el valor principal.

### Qué hay que construir

- [ ] Generar el CV en PDF con `fpdf2` y un **botón de descarga** en la pestaña de Trabajos (nada de Ctrl+P). Acordarse de registrar `arial.ttf`: la fuente por defecto revienta con el guion largo.
- [ ] Sugerir el **mensaje corto** para mail y para DM a reclutador.
- [ ] Para tu perfil: en vez de reescribir el CV, que compare tu CV con el aviso y te diga qué reordenar o qué keyword te falta para el filtro ATS. Es consejo, no generación — riesgo cero sobre lo que ya funciona.

### El PDF: botón de descarga. Decidido, y ya verificado

Nada de "apretá Ctrl+P y elegí Guardar como PDF". **Un botón que dice "Descargar CV en PDF" y listo.** El usuario más difícil de este sistema tiene 62 años y se jubila en dos: si hay un paso que explicar, ya perdimos.

Librería: **`fpdf2`**. Probada en el entorno real antes de decidir:

- ✅ Instala en Python 3.14 **sin compilador** (a diferencia de lo que pasó con numpy/jobspy).
- ✅ Python puro, sin dependencias del sistema. Descartadas `weasyprint` (necesita GTK en Windows) y `xhtml2pdf` (arrastra reportlab).
- ✅ Ya está en `requirements.txt`, así que el instalador de cada persona lo trae solo.

⚠️ **La trampa que encontré probándola, y que hay que resolver al implementar:** las fuentes que `fpdf2` trae por defecto son latin-1 y **explotan** con caracteres que aparecen todo el tiempo en un CV:

```
FPDFUnicodeEncodingException: Character "—" ... outside the range of characters supported by the font
```

Revientan el guion largo (`—`), las comillas tipográficas (`“ ”`) y el símbolo de euro (`€`). Las tildes y la eñe sí entran en latin-1, pero el guion largo lo usamos en todos los textos generados.

**Solución verificada:** registrar una fuente Unicode del sistema antes de escribir.

```python
pdf.add_font("cv", "",  r"C:\Windows\Fonts\arial.ttf")
pdf.add_font("cv", "B", r"C:\Windows\Fonts\arialbd.ttf")
pdf.set_font("cv", size=10)
```

Probado con `Isaías`, `Bahía Blanca`, `—`, `“Aduana”`, `€ 50.000`, `ñ á é í ó ú ü ¿ ¡`: **PDF válido de 36 KB, todo renderiza bien**. Arial, Calibri, Segoe UI y Times están en cualquier Windows.

### Los mensajes — propuesta para que la corrijas

Pediste que sugiera yo primero. Estos son los moldes; lo que va entre `{}` lo completa el LLM leyendo el aviso y el CV.

**DM a un reclutador por LinkedIn** (máximo 4 líneas, lo leen en el celular entre 200 mensajes):

```
Hola {nombre}, vi la búsqueda de {puesto}.
Trabajo con {la tecnología o área principal que pide el aviso} hace {X} años;
lo último fue {logro concreto, con número si hay}.
¿Te sirve que te pase el CV?
```

**Mail a una consultora o a RRHH:**

```
Asunto: {Puesto} — {Nombre Apellido}

Hola, escribo por la búsqueda de {puesto}.

{Una línea: años de experiencia + la habilidad central que pide el aviso}
{Una línea: el logro más cercano a lo que pide el aviso}

Adjunto el CV. Quedo a disposición.
{Nombre} — {teléfono}
```

**Las tres reglas que hacen que funcionen** (esto es lo que hay que meter en el prompt):

1. **El logro lo elige el LLM leyendo el aviso.** Es la única parte que no se puede templatear y es la que hace la diferencia entre un mensaje genérico y uno que parece escrito para esa búsqueda.
2. **Cero adjetivos sobre uno mismo.** "Proactivo", "apasionado", "orientado a resultados" son ruido: todos los ponen y no dicen nada.
3. **Nunca más de 4 líneas**, y cerrar con una pregunta fácil de responder.

⚠️ Sobre la carta de presentación formal de una carilla: en Argentina casi no se usa. Lo que mueve la aguja es el mensaje corto. Confirmalo contra tu experiencia, que es más fresca que la mía.

---

## 11. Cómo aprende el sistema

Sin entrenar nada y sin llamadas extra al LLM.

1. Marcás rojo y escribís por qué. Ese motivo se guarda junto a la oferta.
2. En la corrida siguiente, las últimas ~15 descartadas con su justificación entran al prompt de scoring **como ejemplos negativos**. Las verdes, como positivos.
3. En dos semanas el prompt lleva tu criterio real, no el que escribimos a mano en `candidate.not_suitable`.

Es barato: aprovecha la llamada al LLM que ya se hace por lote. Lo único que hay que agregar es guardar el feedback y meterlo en el prompt.

Requiere: campos nuevos en el modelo `Job` (`aplicado`, `motivo_descarte`, `fecha_feedback`) y que la UI los escriba.

---

## 12. Checklist maestro

Ordenado por cómo lo encararía. Tildá a medida que salgan.

### Ahora mismo — 30 segundos

- [ ] **Pegar la API key de Gemini** en `.env`. Sin esto el scoring va por keywords y los puntajes no significan nada.

### Bloque 1 — La UI local (sección 9)

Es lo próximo. Destraba las dos pestañas y el aprendizaje.

- [ ] Servidor local + `abrir.bat` que abra `http://localhost:8756`
- [ ] Pestaña **Mis datos**: CV, keywords, país/ciudad, modalidad, idioma, URLs de RRHH a seguir
- [ ] Pestaña **Trabajos**: lista de ofertas con verde/rojo + campo de motivo obligatorio en rojo
- [ ] Campos nuevos en `Job`: `aplicado`, `motivo_descarte`, `fecha_feedback`

### Bloque 2 — Que el sistema aprenda (sección 11)

- [ ] Guardar el feedback de la pestaña Trabajos
- [ ] Meter las últimas ~15 descartadas (con su motivo) al prompt de scoring como ejemplos negativos, y las aplicadas como positivos

### Bloque 3 — Documentos para postularse (sección 10)

- [ ] Generar CV en PDF con **botón de descarga** (`fpdf2`, ya en requirements) — **el valor está en tu familia, no en vos**
- [ ] Mensaje corto para DM a reclutador y para mail (moldes propuestos en la sección 10, corregilos)
- [ ] Para tu perfil: modo "consejo" en vez de generación — qué reordenar y qué keyword falta para el ATS

### Bloque 4 — Que la familia lo pueda usar

- [ ] `profiles/hermana.json` + `resume/hermana.md` (marketing)
- [ ] `profiles/papa.json` + `resume/papa.md` (QHSE, presencial, oil & gas)
- [ ] Perfiles de tus dos hermanos menores (ventas / gastronomía)
- [ ] Una carpeta por persona: perfil, `.env` con **su** `TELEGRAM_CHAT_ID`, CV y `companies.json` de su rubro
- [ ] **Fuentes para rubros no técnicos** (Bumeran / Zonajobs / Computrabajo). Sin esto, dos de los seis perfiles no reciben casi nada. Es lo que más condiciona si esto sirve para tu familia o sólo para vos.
- [ ] **Seguir perfiles de RRHH puntuales** por URL. Está en tu spec original y no existe: `google_posts` busca por keyword, no vigila personas. Para el nicho de tu viejo probablemente rinda más que la búsqueda por keyword.

### Bloque 5 — Calidad de los resultados

- [ ] **Regla de Bahía Blanca**: remoto en cualquier lado, **o** presencial/híbrido en tu ciudad. Hoy se descarta un presencial en Bahía Blanca que sí podrías tomar. Requiere evaluar `passes_work_mode` y `passes_location` juntos.
- [ ] **Duplicados entre fuentes**: la misma oferta llega por `careers` y por `linkedin` con URLs distintas y recibe **dos veredictos opuestos**. Deduplicar por (empresa + título normalizado).
- [ ] **Descartar vacantes ya cubiertas**: buscar `vacante cubierta`, `ya cubierta`, `posición cerrada`, `búsqueda cerrada` en URL/snippet.
- [ ] **`notify_when_empty: true`**: hoy un silencio no distingue "no hubo ofertas" de "se rompió".
- [ ] **Cargar más empresas** en `companies.json`. Con los filtros puestos, `careers` no aportó ni una de las 8 ofertas que llegaron.
- [ ] **`use_search: false`** en las 7 empresas que nunca devolvieron nada (Mercado Libre, Mutt Data, Ualá, Despegar, Naranja X, Banco Galicia, Swiss Medical). Son ~21s por corrida tirados.

### Bloque 6 — Vigilar, sin urgencia

- [ ] Ruido de posts de opinión en `google_posts` (no son ofertas, consumen cuota)
- [ ] País vacío en `google_posts` (el snippet rara vez lo dice → entra LATAM en general)
- [ ] Rareza geográfica de LinkedIn (`Londres, Catamarca, Argentina` por acotar la búsqueda a Argentina)
- [ ] La pestaña de "shops" y las otras fuentes que mencionaste
- [ ] Recolección compartida — sólo entre los dos hermanos que se cruzan (ahorro 2x, no 6x)

### Hecho ✅

**Motor y fuentes**

- ~~CV real en `resume/isaias.md`~~ — ya está cargado.
- ~~Desactivar la fuente `dummy`~~ — hecho.
- ~~Flag de dolor por inglés~~ — hecho, `report.english_pain`.
- ~~Proveedor Gemini en `llm.py`~~ — hecho. Falta que pegues la key en `.env`.
- ~~Evitar el pico al agregar empresas~~ — hecho, `max_new_per_run` con triaje heurístico gratis.
- ~~Instalación para no técnicos~~ — hecho: `instalar.bat`, `estado.bat`, `buscar_ahora.bat`, `desinstalar.bat` y `LEEME.txt`.
- ~~Scheduling de las 3 corridas~~ — hecho, dentro del instalador. Sin permisos de administrador.
- ~~Bug: `chat_with_fallback` explotaba con `'NoneType' object is not subscriptable`~~ — pasa cuando el proveedor devuelve HTTP 200 con `choices` en null, que es lo que hace OpenRouter al agotarse la cuota diaria. Ahora da un mensaje que se entiende y pasa al siguiente modelo.
- ~~Fase 2: `google_posts`~~ — posts de LinkedIn vía buscador, sin tocar LinkedIn.
- ~~Fase 3: `linkedin`~~ — LinkedIn Jobs vía JobSpy, única fuente con datos estructurados.
- ~~Filtros de país, ciudad, modalidad e idioma~~ — con la regla "lo que el aviso no dice, no filtra".
- ~~Detección de inglés en 4 capas~~ — idioma del aviso, juicio del LLM, nivel CEFR, y escaneo de texto que no depende del LLM.

**Decisiones cerradas**

- ~~Fase 4 (Gmail inbox)~~ — **descartada**. En Argentina no te ofrecen trabajo por mail en frío. (Variante que sí serviría más adelante: leer respuestas *a tus postulaciones* para completar solo la pestaña Trabajos.)
- ~~"Remoto o relocación a UE" en el perfil~~ — sacado. Nadie de la familia se va del país.
- ~~Notion como pestaña de Trabajos~~ — descartado en favor de la UI local.
- ~~Hostinger~~ — descartado: IP de datacenter, peor que la de casa.

**Bugs encontrados y arreglados**

- ~~Bug: los moldes sin completar de `.env.example` no se detectaban~~ — `is_placeholder()` reconocía `YOUR_x_HERE` pero no `tu_openrouter_api_key_aca`, que es lo que el repo trae. El motor creía tener credencial y fallaba recién al llamar a la API en vez de avisar y degradar.
