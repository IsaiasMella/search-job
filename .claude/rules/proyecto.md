# vacantia: comandos, arquitectura y convenciones

vacantia busca ofertas de trabajo en varios portales, las puntúa contra el CV con un modelo y avisa por Telegram, con una pantalla local para revisarlas. Lo usan personas de una familia, sin conocimientos técnicos, cada una en su computadora. Todo en Windows y en Python: sin Node ni paso de compilación.

El código, los comentarios, los tests y la interfaz están en castellano rioplatense. Seguí esa convención.

## Comandos

Siempre con el Python del venv (Windows):

```
.venv\Scripts\python.exe -m pytest tests -q                              # suite completa (~90 s)
.venv\Scripts\python.exe -m pytest tests/test_linkedin_urls.py -q        # un archivo
.venv\Scripts\python.exe -m pytest tests/test_ui.py -k anotador -q       # por nombre
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt          # pytest, sólo para desarrollo

.venv\Scripts\python.exe -m vacantia.ui --port 9000 --sin-navegador      # la pantalla (abrir.bat usa el 8756)
.venv\Scripts\python.exe -m vacantia.run --profile <perfil> --dry-run   # ensayo: no notifica ni guarda
.venv\Scripts\python.exe -m vacantia.run --all | --list-profiles
.venv\Scripts\python.exe -m vacantia.agenda                              # reparto de horarios entre perfiles
$env:LOG_LEVEL="DEBUG"; ...                                               # detalle por oferta; log completo en vacantia.log
```

No hay linter configurado.

- **`--dry-run` gasta llamadas reales** al modelo y a TinyFish: pedí permiso antes de correrlo.
- **Cambios en Python:** el servidor de la pantalla hay que reiniciarlo. Si se abrió con `abrir.bat`, hay que cerrar esa ventana y volver a abrirla.
- **Cambios en `ui/css/*.css` o `ui/static/app.js`:** alcanza con F5.
- **Dependencias:** `instalar.bat` sólo lee `requirements.txt`, así que una dependencia nueva ahí se instala en cada máquina. Lo de desarrollo va en `requirements-dev.txt`.
- **Documentos que no se editan salvo pedido explícito:** `DESIGN.md`, `sistema_De_likns_post_linkedin.md` y `estrategia-links-linkedin-pestana-jobs.md`. Son material de referencia.
- **Finales de línea:** hay archivos con CRLF y otros con LF. Respetá el que ya tiene cada archivo.

## Arquitectura

**Motor.** `run.py` → `engine.run(profile)`: fuentes → `Job` normalizado (`models.py`) → dedupe (`state.py`) → filtros previos → scoring (`scoring.py` + `llm.py`) → filtros de ubicación, modalidad e idioma (`filters.py`) → notificadores.

- **Interfaces:** el motor sólo conoce `Source.fetch() -> list[Job]` y `Notifier.send(jobs)`, registradas en `SOURCE_REGISTRY` y `NOTIFIER_REGISTRY`.
- **Agregar una fuente:** registrarla y sumarla también a `FUENTES` en `ui/formulario.py`.

**Perfiles y estado.**
- **El perfil:** cada persona es `profiles/<nombre>.json`, con su CV en `resume/*.md` y sus empresas en `companies-<nombre>.json`.
- **Estado:** `state/<perfil>/`. Adentro, `job_history.json` es el archivo durable, con el feedback `aplicado` y `motivo_descarte`.
- **Claves y Telegram:** las claves son compartidas en `.env`; el `chat_id` de Telegram es por perfil.
- **Rutas relativas:** todas son relativas al directorio de trabajo (`STATE_ROOT = Path("state")`), así que todo se corre desde la raíz del repo.
- **`instalar.bat`:** programa una tarea de Windows por cada perfil que haya en `profiles/`.

**Varios CV por perfil.** El perfil tiene `cvs: [{id, nombre, path, palabras_clave}]`. Un perfil viejo con sólo `cv_path` se sintetiza como un CV `id="principal"` (`config.cvs_del_perfil`).
- **Un solo punto para los términos de búsqueda:** `config.terminos_de_busqueda()`, que junta keywords del perfil y las de cada CV. Las fuentes no leen `search_terms` ni `keywords` directo.
- **Con un solo CV:** el prompt de scoring queda byte a byte igual al histórico.
- **Con 2 o más:** la oferta guarda `cv_recomendado`, que es un id y no un nombre.

**Pantalla (`vacantia/ui/`).**
- **Servidor:** `ThreadingHTTPServer` de biblioteca estándar, que escucha sólo en 127.0.0.1 y no tiene login.
- **Disco:** `data.py` tiene todo lo que lee o escribe.
- **HTML:** `render.py` y `formulario.py` lo arman con f-strings y escapan con `esc()`.
- **Estilos:** `css/*.css`, concatenados en el orden de `estilos.ORDEN`.
- **htmx:** vendorizado en `static/`. Nunca desde un CDN, porque la máquina puede estar sin internet.
- **Patrón de las pantallas:**
  - Filtros y constructores: formularios GET.
  - Acciones: POST, que redirige con 303 a un GET y avisa con `?ok=` o `?error=`.
- **Buscar ahora:** `corrida.py` corre la búsqueda en un proceso aparte.

## Estilo del código

Docstrings y comentarios explican el *por qué*, muchas veces con la medición o el incidente que motivó la decisión. Mantené ese estilo y no borres esas explicaciones al refactorizar.
