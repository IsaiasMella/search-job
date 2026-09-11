"""La hoja de estilos, emitida entera desde acá.

Es la implementación de `DESIGN.md`: los tokens del front matter salen como
variables CSS y **ninguna regla escribe un color, un espacio o un radio
sueltos**. Si un componente necesita un valor que no está acá, se agrega arriba
como token; no se improvisa abajo.

Tres cosas que conviene tener presentes antes de tocar nada:

* **Un solo tema, oscuro.** La app se usa en escritorio, la usan cinco
  personas, y duplicar la paleta sólo agrega superficie de error. No hay
  `prefers-color-scheme: light` y no se agrega uno con `filter: invert`.
* **El vidrio esmerilado se gasta en tres lugares y nada más:** la barra
  lateral, las tarjetas de oferta sin marcar y el cartel de novedades. Una
  tarjeta de métrica con vidrio y una tarjeta de oferta con vidrio se ven
  iguales y destruyen la jerarquía.
* **El índigo conduce la interacción y no decora.** Si algo es índigo, se
  puede tocar. Nada de títulos, íconos ni bordes índigo por gusto.
"""

from pathlib import Path

#: Dónde busca las fuentes propias. Si los archivos no están, el CSS ni
#: siquiera declara las `@font-face` y todo cae en la pila del sistema, que es
#: lo que se ve hoy. **Nunca se llama a un CDN**: la app corre en una máquina
#: que puede estar sin internet, y una fuente que tarda 3 segundos en llegar es
#: una pantalla que parpadea al abrir.
FUENTES_DIR = Path(__file__).parent / "fuentes"

#: (archivo, familia, peso). Inter en tres pesos porque la escala usa 400, 500
#: y 600, y pedirle al navegador que engorde un 400 a 600 lo emborrona.
FUENTES = (
    ("Inter-Regular.woff2", "Inter", "400"),
    ("Inter-Medium.woff2", "Inter", "500"),
    ("Inter-SemiBold.woff2", "Inter", "600"),
    ("JetBrainsMono-Regular.woff2", "JetBrains Mono", "400"),
)


def _font_faces() -> str:
    """Las `@font-face` de las fuentes que de verdad están en disco."""
    reglas = []
    for archivo, familia, peso in FUENTES:
        if not (FUENTES_DIR / archivo).exists():
            continue
        reglas.append(
            f"@font-face {{ font-family: '{familia}'; font-weight: {peso};\n"
            f"  font-style: normal; font-display: swap;\n"
            f"  src: url('/fuentes/{archivo}') format('woff2'); }}"
        )
    return "\n".join(reglas)


TOKENS = """
/* ===========================================================================
   TOKENS. Los del front matter de DESIGN.md, uno a uno.
   Primitivos primero, semánticos después: las reglas de abajo referencian
   SIEMPRE los semánticos, nunca un primitivo y nunca un valor literal.
   =========================================================================== */
:root {
  color-scheme: dark;

  /* --- primitivos: neutrales fríos, nunca grises puros ni negro tintado --- */
  --neutral-50:  #F4F5F9;
  --neutral-100: #DCDEE8;
  --neutral-300: #9AA0B4;
  --neutral-500: #868EA2;
  --neutral-700: #2A2F3E;
  --neutral-900: #0F1117;
  --brand-300:   #A9ABFF;
  --brand-500:   #6366E8;
  --brand-700:   #4A4CC4;

  /* --- semánticos --- */
  --color-background:     var(--neutral-900);
  --color-surface:        #171A23;
  --color-surface-raised: #1E222E;
  --color-border:         var(--neutral-700);
  --color-border-subtle:  #232735;
  --color-text-primary:   var(--neutral-50);
  --color-text-secondary: var(--neutral-300);
  --color-text-tertiary:  var(--neutral-500);
  --color-text-on-action: #FFFFFF;
  --color-action:         var(--brand-700);
  --color-action-hover:   var(--brand-500);
  --color-focus-ring:     var(--brand-300);
  /* El índigo de acción (#6366E8) da 4.13:1 contra el fondo: alcanza para un
     relleno de botón con texto blanco, pero NO para texto índigo sobre oscuro.
     Los links usan el índigo claro, que da 8.95:1. Token nuevo, propuesto acá
     porque el front matter no traía un color de link. */
  --color-link:           var(--brand-300);
  --color-link-hover:     var(--neutral-50);

  /* --- datos. TOKENS NUEVOS: el front matter de DESIGN.md no tiene ninguno
         para gráficos, y Métricas los necesita.

         Son pocos porque **todos los gráficos de la app son de una sola
         serie**: la magnitud la lleva el largo de la barra, no el tono. No hay
         paleta categórica que validar ni leyenda que poner, porque no hay dos
         series que distinguir; el título dice qué se está midiendo.

         El relleno es el índigo de marca. En una tarjeta eso significaría
         "tocame", pero adentro de un gráfico con su eje y sus etiquetas una
         barra no se confunde con un botón, y el sistema tiene un solo hue.
         3.80:1 contra la superficie, arriba del 3:1 que piden los elementos
         gráficos no textuales. --- */
  --data-fill:      var(--brand-500);
  --data-track:     var(--color-border-subtle);
  --data-destacada: var(--color-success);

  /* --- estados. Verde = lo que ya hiciste. Rojo = error o destrucción, y
         nada más: "sin mirar" o "descartada" NO son errores. --- */
  --color-success:         #4ADE80;
  --color-success-surface: #16241C;
  --color-warning:         #E9B949;
  --color-warning-surface: #26200F;
  --color-danger:          #F87171;
  --color-danger-surface:  #26161A;
  --color-info:            #7DA8FF;
  --color-info-surface:    #151C2B;

  /* --- tipografía. Inter para todo; la mono sólo donde el ancho fijo
         significa algo: puntajes, contadores y columnas numéricas. --- */
  --font-sans: Inter, "Segoe UI", system-ui, -apple-system, Roboto, Arial, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, "Cascadia Mono", Consolas, monospace;
  /* TOKEN NUEVO. `display` (2rem) es el tope de la escala del front matter y
     alcanza para una tarjeta de métrica, donde hay cinco números del mismo
     peso. No alcanza para el contador de postulaciones, que es UN número y
     tiene que leerse cruzando la habitación: es lo único de la app que mide el
     trabajo de la persona y no el del sistema. Sigue la misma progresión de
     1.2 desde display. */
  --text-hero:      3.5rem;
  --text-display:   2rem;
  --text-h1:        1.75rem;
  --text-h2:        1.375rem;
  --text-h3:        1.125rem;
  --text-body-lg:   1.0625rem;
  --text-body-md:   1rem;
  --text-body-sm:   0.875rem;
  --text-caption:   0.75rem;
  --text-mono:      0.8125rem;
  --leading-tight:  1.2;
  --leading-title:  1.3;
  --leading-body:   1.6;
  --leading-snug:   1.45;
  --tracking-display: -0.02em;
  --tracking-h1:      -0.015em;
  --tracking-h2:      -0.01em;
  --weight-regular:  400;
  --weight-medium:   500;
  --weight-semibold: 600;   /* el máximo. En oscuro, más pesado florece. */

  /* --- espaciado, escala de 4 --- */
  --spacing-xs:  4px;
  --spacing-sm:  8px;
  --spacing-md:  16px;
  --spacing-lg:  24px;
  --spacing-xl:  40px;
  --spacing-2xl: 64px;
  --spacing-3xl: 96px;

  /* --- formas. El radio sigue la jerarquía del elemento: un solo radio para
         todo es la señal más clara de una interfaz hecha con plantilla. --- */
  --rounded-none: 0px;
  --rounded-sm:   6px;    /* inputs, desplegables, bloques de URL */
  --rounded-md:   10px;   /* botones, ítems de navegación, callouts */
  --rounded-lg:   16px;   /* tarjetas, modales, estados vacíos */
  --rounded-full: 9999px; /* etiquetas y píldoras de filtro */

  /* --- elevación. En oscuro la sombra funciona mal como señal, así que las
         capas se separan con borde y translucidez primero. --- */
  --elevation-flat:    none;
  --elevation-raised:  0 1px 2px rgba(0, 0, 0, 0.4);
  --elevation-overlay: 0 8px 24px rgba(0, 0, 0, 0.5);
  --elevation-modal:   0 24px 64px rgba(0, 0, 0, 0.65);

  /* --- efectos: la audacia del sistema, y se gasta en tres lugares --- */
  --glass-background: rgba(30, 34, 46, 0.72);
  --glass-blur:       blur(16px);
  --glass-border:     1px solid rgba(244, 245, 249, 0.06);
  --glow-action:      0 0 32px -8px rgba(99, 102, 232, 0.35);

  /* --- bordes --- */
  --border-hairline: 1px;
  --border-regular:  1px;
  --border-emphasis: 2px;

  /* --- layout --- */
  --container-max:   1200px;
  --content-max-ch:  72ch;
  --sidebar-width:   260px;
  --gutter:          var(--spacing-md);

  /* --- movimiento --- */
  --duration-instant: 80ms;
  --duration-fast:    140ms;
  --duration-normal:  220ms;
  --duration-slow:    320ms;
  --ease-standard: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-enter:    cubic-bezier(0.0, 0, 0.2, 1);
  --ease-exit:     cubic-bezier(0.4, 0, 1, 1);

  /* --- medidas de control. No estaban en el front matter y los componentes
         las necesitan: se agregan como token en vez de repetirlas sueltas.
         44px es el mínimo táctil que fija DESIGN.md y el alto de botón, input
         y select; 36px es el alto de la píldora de filtro; 40px el del ítem
         de navegación. --- */
  --control-height:    44px;
  --control-height-sm: 36px;
  --nav-item-height:   40px;
  --checkbox-size:     18px;
  --score-width:       64px;   /* la caja del puntaje en la tarjeta */
  --menu-width:        240px;  /* el panel de tres puntos */
  --menu-aire:         112px;  /* lo que mide ese panel, para dejarle lugar
                                  cuando se abre adentro de una columna que
                                  scrollea y lo recortaría */
  --table-max:         560px;  /* dos columnas: texto y número */
  --metric-min:        160px;  /* mínimo de una tarjeta de métrica */
  --textarea-min:      180px;

  /* --- iconografía (Lucide, dibujada a mano en el HTML) --- */
  --icon-stroke: 1.5;
  --icon-sm: 16px;
  --icon-md: 20px;
  --icon-lg: 24px;

  /* --- z-index: una escala, sin 9999 sueltos --- */
  --z-base:     0;
  --z-sticky:   100;
  --z-dropdown: 200;
  --z-overlay:  300;
  --z-modal:    400;
  --z-toast:    500;

  /* La flecha del desplegable, dibujada por nosotros: el color viaja adentro
     del SVG y ahí no se puede referenciar una variable, así que vive como
     token para que nadie cambie la paleta y se la olvide. Es text-secondary. */
  --select-arrow: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 8'%3E%3Cpath d='M1 1.5 6 6.5l5-5' fill='none' stroke='%239AA0B4' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
}
"""

BASE = """
/* ===========================================================================
   BASE
   =========================================================================== */
*, *::before, *::after { box-sizing: border-box; }

body {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--text-body-md);
  font-weight: var(--weight-regular);
  line-height: var(--leading-body);
  color: var(--color-text-primary);
  background: var(--color-background);
  -webkit-text-size-adjust: 100%;
}

/* --- la barra de desplazamiento ---
   `color-scheme: dark` ya la pinta oscura, pero deja la gris del sistema, que
   al lado de estos bordes se ve prestada. Se pinta con los tokens de la app:
   riel invisible y pulgar del color del borde, más claro al pasar por encima.
   El borde del pulgar es del color del fondo y hace de aire: sin él la barra
   toca el contenido.

   Firefox no tiene pseudoelementos y usa `scrollbar-color`; los dos caminos
   dicen lo mismo, así que si uno falla el otro alcanza. */
* { scrollbar-width: thin;
    scrollbar-color: var(--color-border) transparent; }
::-webkit-scrollbar { width: 12px; height: 12px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border: 3px solid var(--color-background);
  border-radius: var(--rounded-full);
}
::-webkit-scrollbar-thumb:hover { background: var(--color-text-tertiary); }
::-webkit-scrollbar-corner { background: transparent; }

/* Sentence case en todos lados, peso máximo 600, y ningún título en índigo. */
h1, h2, h3 { margin: 0; font-weight: var(--weight-semibold);
             color: var(--color-text-primary); text-wrap: balance; }
h1 { font-size: var(--text-h1); line-height: 1.25; letter-spacing: var(--tracking-h1); }
h2 { font-size: var(--text-h2); line-height: var(--leading-title);
     letter-spacing: var(--tracking-h2); }
h3 { font-size: var(--text-h3); line-height: 1.4; }

p { margin: 0; max-width: var(--content-max-ch); text-wrap: pretty; }

a { color: var(--color-link); text-underline-offset: 2px; }
a:hover { color: var(--color-link-hover); }

/* Foco visible en todo lo que se puede tabular, siempre con el mismo anillo y
   el mismo offset. Nunca se saca un outline sin reemplazarlo. */
:where(a, button, summary, input, select, textarea, [tabindex]):focus-visible {
  outline: var(--border-emphasis) solid var(--color-focus-ring);
  outline-offset: 2px;
  border-radius: var(--rounded-sm);
}

::selection { background: var(--color-action); color: var(--color-text-on-action); }

.saltar {
  position: absolute; left: -9999px; top: 0; z-index: var(--z-toast);
  background: var(--color-action); color: var(--color-text-on-action);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: 0 0 var(--rounded-md) 0;
  font-size: var(--text-body-sm); font-weight: var(--weight-medium);
  text-decoration: none;
}
.saltar:focus { left: 0; }
"""

SHELL = """
/* ===========================================================================
   SHELL: barra lateral fija + una sola columna de contenido, alineada a la
   izquierda. Nada centrado: la lectura empieza siempre en el mismo borde, y
   bajando por una lista de 40 ofertas eso se nota.
   =========================================================================== */
.app { display: flex; align-items: flex-start; min-height: 100dvh; }

/* Vidrio esmerilado 1 de 3. */
.lateral {
  position: sticky; top: 0; z-index: var(--z-sticky);
  flex: 0 0 var(--sidebar-width); width: var(--sidebar-width);
  height: 100dvh; overflow-y: auto;
  display: flex; flex-direction: column; gap: var(--spacing-xs);
  padding: var(--spacing-lg) var(--spacing-md);
  background: var(--glass-background);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border-right: var(--glass-border);
}

.marca-app {
  display: flex; align-items: center; gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-primary); text-decoration: none;
  font-size: var(--text-body-lg); font-weight: var(--weight-semibold);
  letter-spacing: var(--tracking-h2);
  border-radius: var(--rounded-md);
  transition: background-color var(--duration-fast) var(--ease-standard);
}
.marca-app:hover { background: var(--color-surface); color: var(--color-text-primary); }
.marca-app .sello {
  display: grid; place-items: center; flex: 0 0 auto;
  width: var(--icon-lg); height: var(--icon-lg);
  border-radius: var(--rounded-sm);
  background: var(--color-action); color: var(--color-text-on-action);
  font-size: var(--text-caption); font-weight: var(--weight-semibold);
}

.grupo {
  color: var(--color-text-tertiary);
  font-size: var(--text-caption); line-height: var(--leading-snug);
  padding: var(--spacing-md) var(--spacing-sm) var(--spacing-xs);
}

.lateral nav { display: flex; flex-direction: column; gap: 2px; }

.nav-item {
  display: flex; align-items: center; gap: var(--spacing-sm);
  min-height: var(--nav-item-height); padding: var(--spacing-sm) var(--spacing-md);
  border: var(--border-hairline) solid transparent;
  border-radius: var(--rounded-md);
  background: transparent; color: var(--color-text-secondary);
  font-size: var(--text-body-sm); text-decoration: none;
  transition: background-color var(--duration-fast) var(--ease-standard),
              color var(--duration-fast) var(--ease-standard);
}
.nav-item svg { flex: 0 0 auto; width: var(--icon-md); height: var(--icon-md); }
.nav-item:hover { background: var(--color-surface); color: var(--color-text-primary); }
.nav-item.activa {
  background: var(--color-surface-raised); color: var(--color-text-primary);
  border: var(--glass-border);
}

.separador { height: var(--border-hairline); margin: var(--spacing-md) var(--spacing-sm);
             background: var(--color-border-subtle); border: 0; }

/* El selector de perfil. Cinco personas comparten la máquina y cada una tiene
   su búsqueda: es lo primero que se toca al abrir. */
.perfil-sel { display: flex; flex-direction: column; gap: var(--spacing-xs);
              padding: 0 var(--spacing-sm) var(--spacing-sm); }
.perfil-sel label { color: var(--color-text-tertiary); font-size: var(--text-caption); }

/* El estado del sistema: cuándo buscó, cuándo vuelve, qué ventana cubre. Es el
   antídoto de la ansiedad y por eso tiene lugar fijo, no un tooltip. Texto
   estático: cambia cuando cambia el dato, no solo. */
.estado {
  margin-top: auto; padding: var(--spacing-md) var(--spacing-sm) 0;
  border-top: var(--border-hairline) solid var(--color-border-subtle);
  color: var(--color-text-tertiary);
  font-size: var(--text-caption); line-height: var(--leading-snug);
}
.estado p { margin: 0 0 var(--spacing-xs); }
.estado p:last-child { margin-bottom: 0; }
.estado .valor { color: var(--color-text-secondary); }

main {
  flex: 1 1 auto; min-width: 0;
  max-width: var(--container-max);
  padding: var(--spacing-xl) var(--spacing-lg) var(--spacing-3xl);
}
main > h1 { margin-bottom: var(--spacing-lg); }
main > h2 { margin: var(--spacing-xl) 0 var(--spacing-md); }
main > h2:first-child { margin-top: 0; }

/* --- responsive: abajo de md la lateral colapsa a íconos y el estado del
       sistema pasa a una línea arriba del contenido. --- */
@media (max-width: 900px) {
  .app { flex-direction: column; align-items: stretch; }
  .lateral {
    flex: 0 0 auto; width: 100%; height: auto;
    flex-direction: row; flex-wrap: wrap; align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    border-right: 0; border-bottom: var(--glass-border);
  }
  .marca-app { margin: 0; }
  .marca-app .nombre, .grupo, .nav-item .etiqueta { position: absolute;
    width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%);
    white-space: nowrap; }
  .lateral nav { flex-direction: row; gap: var(--spacing-xs); }
  .nav-item { min-width: var(--control-height); min-height: var(--control-height);
              justify-content: center;
              padding: var(--spacing-sm); }
  .separador { display: none; }
  .perfil-sel { flex-direction: row; align-items: center; margin-left: auto;
                padding: 0; }
  .estado { order: 9; flex-basis: 100%; margin-top: 0;
            padding: var(--spacing-sm) 0 0; }
  /* Las dos líneas del estado pasan a una sola. El punto medio va acá y no en
     otro lado: está reservado para la línea de estado del sistema. */
  .estado p { display: inline; margin: 0; }
  .estado p + p::before { content: " \\00b7 "; }
  main { padding: var(--spacing-lg) var(--spacing-md) var(--spacing-2xl); }
}
@media (max-width: 640px) {
  main { padding: var(--spacing-md) var(--spacing-md) var(--spacing-2xl); }
}
"""

CONTROLES = """
/* ===========================================================================
   CONTROLES: botones, desplegables y campos.

   Un solo botón primario por pantalla, y es la acción que la persona vino a
   hacer. Nunca dos botones del mismo peso enfrentados: obligan a decidir antes
   de leer, que es exactamente lo que pasaba con "Apliqué" verde contra "No
   apliqué" rojo.
   =========================================================================== */
button, .boton {
  display: inline-flex; align-items: center; justify-content: center;
  gap: var(--spacing-sm);
  min-height: var(--control-height); padding: var(--spacing-sm) var(--spacing-lg);
  font-family: var(--font-sans); font-size: var(--text-body-sm);
  font-weight: var(--weight-medium); line-height: 1.2;
  border-radius: var(--rounded-md);
  border: var(--border-hairline) solid var(--color-border);
  background: var(--color-surface-raised); color: var(--color-text-primary);
  text-decoration: none; cursor: pointer;
  transition: background-color var(--duration-fast) var(--ease-standard),
              border-color var(--duration-fast) var(--ease-standard),
              box-shadow var(--duration-fast) var(--ease-standard);
}
button:hover, .boton:hover { background: var(--color-border); color: var(--color-text-primary); }
button:disabled, .boton[aria-disabled="true"] {
  background: var(--color-surface); color: var(--color-text-tertiary);
  cursor: not-allowed; }
button:disabled:hover { background: var(--color-surface); }

.primario, button.primario {
  background: var(--color-action); border-color: var(--color-action);
  color: var(--color-text-on-action); }
.primario:hover, button.primario:hover {
  background: var(--color-action-hover); border-color: var(--color-action-hover);
  box-shadow: var(--glow-action); }
.primario:active, button.primario:active {
  background: var(--brand-700); border-color: var(--brand-700); }
.primario:disabled {
  background: var(--color-border); border-color: var(--color-border);
  color: var(--color-text-tertiary); box-shadow: none; }

/* Mantenimiento: archivar, devolver a la lista, limpiar. No compite. */
.fantasma, button.fantasma {
  background: transparent; border-color: transparent;
  color: var(--color-text-secondary);
  padding: var(--spacing-sm) var(--spacing-md); }
.fantasma:hover, button.fantasma:hover {
  background: var(--color-surface); color: var(--color-text-primary); }

/* Los desplegables se ven y se comportan igual que los botones: mismo alto,
   mismo borde, mismo radio, mismo hover. `appearance: none` saca la flecha
   nativa, la única parte que no se puede pintar, y dibujamos la nuestra. La
   lista desplegada la dibuja el sistema operativo: lo único que la hace
   acompañar el tema es `color-scheme`, que está puesto arriba en :root. */
select {
  appearance: none; -webkit-appearance: none;
  font-family: var(--font-sans); font-size: var(--text-body-sm);
  min-height: var(--control-height); max-width: 100%;
  padding: var(--spacing-sm) var(--spacing-xl) var(--spacing-sm) var(--spacing-md);
  border: var(--border-hairline) solid var(--color-border);
  border-radius: var(--rounded-sm);
  color: var(--color-text-primary); cursor: pointer;
  background-color: var(--color-surface);
  background-image: var(--select-arrow);
  background-repeat: no-repeat;
  background-position: right var(--spacing-md) center;
  background-size: 11px 8px;
  transition: background-color var(--duration-fast) var(--ease-standard),
              border-color var(--duration-fast) var(--ease-standard);
}
select:hover { background-color: var(--color-surface-raised); }
select:focus { border-color: var(--color-focus-ring); }
select.mal { border-color: var(--color-danger); }
select option { background: var(--color-surface-raised); color: var(--color-text-primary); }

input[type=text], input[type=number], input[type=password], textarea {
  width: 100%; min-height: var(--control-height);
  padding: var(--spacing-sm) var(--spacing-md);
  font-family: var(--font-sans); font-size: var(--text-body-sm);
  line-height: var(--leading-body);
  border: var(--border-hairline) solid var(--color-border);
  border-radius: var(--rounded-sm);
  background: var(--color-surface); color: var(--color-text-primary);
  transition: border-color var(--duration-fast) var(--ease-standard);
}
input::placeholder, textarea::placeholder {
  color: var(--color-text-tertiary); opacity: 1; }
input:focus, textarea:focus { border-color: var(--color-focus-ring); }
input.mal, textarea.mal { border-color: var(--color-danger); }
input:disabled, textarea:disabled {
  background: var(--color-background); color: var(--color-text-tertiary);
  border-color: var(--color-border-subtle); }
textarea { font-family: var(--font-mono); font-size: var(--text-mono);
           line-height: var(--leading-body); resize: vertical; }

input[type=checkbox] { width: var(--checkbox-size); height: var(--checkbox-size);
                       margin: 0; cursor: pointer;
                       accent-color: var(--color-action); }
"""

PIEZAS = """
/* ===========================================================================
   PIEZAS: píldoras, etiquetas, tarjetas, callouts, métricas, tablas.
   =========================================================================== */

/* --- avisos de la acción anterior (se guardó, falló, se marcó) --- */
.aviso {
  display: block; margin-bottom: var(--spacing-md);
  padding: var(--spacing-md); max-width: var(--content-max-ch);
  border: var(--border-hairline) solid var(--color-border);
  border-radius: var(--rounded-md);
  background: var(--color-surface); color: var(--color-text-secondary);
  font-size: var(--text-body-sm);
}
.aviso.ok { background: var(--color-success-surface); border-color: var(--color-success);
            color: var(--color-text-primary); }
.aviso.error { background: var(--color-danger-surface); border-color: var(--color-danger);
               color: var(--color-text-primary); }

/* --- píldoras de filtro. El activo se marca con borde índigo y superficie
       elevada, NUNCA con relleno índigo: un pill relleno del color de acción
       se confunde con un botón. El contador va siempre, aun en cero. --- */
.filtros { display: flex; flex-wrap: wrap; gap: var(--spacing-sm);
           margin-bottom: var(--spacing-md); }
.filtros a {
  display: inline-flex; align-items: center; gap: var(--spacing-sm);
  min-height: var(--control-height-sm); padding: var(--spacing-sm) var(--spacing-md);
  border: var(--border-hairline) solid var(--color-border);
  border-radius: var(--rounded-full);
  background: transparent; color: var(--color-text-secondary);
  font-size: var(--text-body-sm); text-decoration: none;
  transition: background-color var(--duration-fast) var(--ease-standard),
              color var(--duration-fast) var(--ease-standard),
              border-color var(--duration-fast) var(--ease-standard);
}
.filtros a:hover { background: var(--color-surface); color: var(--color-text-primary); }
.filtros a.activa { background: var(--color-surface-raised);
                    color: var(--color-text-primary);
                    border-color: var(--brand-500); }
.filtros .cuenta { font-family: var(--font-mono); font-size: var(--text-mono);
                   font-variant-numeric: tabular-nums;
                   color: var(--color-text-tertiary); }
.filtros a.activa .cuenta { color: var(--color-text-secondary); }
.filtros svg { width: var(--icon-sm); height: var(--icon-sm); flex: 0 0 auto; }

/* "Filtradas" no es una pestaña más: es la tarea de revisar si el filtro
   automático acierta, y hay que poder encontrarla de un vistazo. Va en el azul
   de "estado del sistema", que es lo que son esas ofertas: algo que decidió el
   sistema. NO en el índigo de acción, porque una píldora rellena del color de
   acción se confunde con un botón, y NO en rojo, porque un descarte del filtro
   no es un error. El color no está solo: lo acompañan la palabra y el embudo. */
.filtros a.revisar { background: var(--color-info-surface);
                     border-color: var(--color-info); color: var(--color-info); }
.filtros a.revisar:hover { background: var(--color-info-surface);
                           color: var(--color-info); border-color: var(--color-info); }
.filtros a.revisar .cuenta { color: var(--color-info); }
.filtros a.revisar.activa { background: var(--color-info-surface);
                            border-color: var(--color-info);
                            color: var(--color-info);
                            box-shadow: inset 0 0 0 1px var(--color-info); }

/* --- el número grande de "sin mirar" y el filtro de antigüedad --- */
.encabezado { display: flex; align-items: flex-end; justify-content: space-between;
              gap: var(--spacing-md); flex-wrap: wrap;
              margin: 0 0 var(--spacing-lg); }
.cuantas { display: flex; align-items: baseline; gap: var(--spacing-sm); margin: 0; }
/* Inter y no mono: es un titular, no una columna que se compara. Lo que sí
   necesita es `tabular-nums`, para que pasar de 9 a 10 no mueva el renglon. */
.cuantas .numero { font-size: var(--text-display); font-weight: var(--weight-semibold);
                   line-height: var(--leading-tight);
                   letter-spacing: var(--tracking-display);
                   font-variant-numeric: tabular-nums;
                   color: var(--color-text-primary); }
.cuantas .que { color: var(--color-text-secondary); font-size: var(--text-body-sm); }
.filtro-fecha { display: flex; align-items: center; gap: var(--spacing-sm); margin: 0; }
.filtro-fecha label { color: var(--color-text-tertiary); font-size: var(--text-body-sm); }
.filtro-fecha select { min-height: var(--control-height-sm);
                       padding: var(--spacing-xs) var(--spacing-xl) var(--spacing-xs) var(--spacing-md); }
.perfil-sel select { min-height: var(--control-height-sm);
                     padding: var(--spacing-xs) var(--spacing-xl) var(--spacing-xs) var(--spacing-md); }

/* --- pestañas. SÓLO para Jobs y Publicaciones dentro de LinkedIn URLs: son
       navegación adentro de la sección, no un filtro, y por eso van arriba del
       contenido y no adentro de una tarjeta. Para filtrar están las píldoras. --- */
.pestanias { display: flex; gap: var(--spacing-lg); flex-wrap: wrap;
             margin: 0 0 var(--spacing-lg);
             border-bottom: var(--border-hairline) solid var(--color-border-subtle); }
.pestania {
  display: inline-flex; align-items: center;
  min-height: var(--control-height);
  padding: var(--spacing-sm) 0;
  margin-bottom: calc(var(--border-emphasis) * -1);
  border-bottom: var(--border-emphasis) solid transparent;
  background: transparent; color: var(--color-text-secondary);
  font-size: var(--text-body-md); text-decoration: none;
  transition: color var(--duration-fast) var(--ease-standard),
              border-color var(--duration-fast) var(--ease-standard);
}
.pestania:hover { color: var(--color-text-primary); }
.pestania.activa { color: var(--color-text-primary); border-color: var(--brand-500); }

/* --- dónde termina lo recién publicado y empieza el resto. Es una línea que
       cruza la lista, no un adorno de cada tarjeta. Sentence case, sin
       mayúsculas forzadas y sin índigo decorativo. --- */
.banda { display: flex; align-items: baseline; gap: var(--spacing-sm);
         flex-wrap: wrap; margin: var(--spacing-xl) 0 var(--spacing-md);
         padding-bottom: var(--spacing-sm);
         border-bottom: var(--border-hairline) solid var(--color-border-subtle);
         font-size: var(--text-body-md); }
.banda:first-child { margin-top: 0; }
.banda .cuenta { font-family: var(--font-mono); font-size: var(--text-mono);
                 font-variant-numeric: tabular-nums;
                 color: var(--color-text-secondary); }
.banda .detalle { font-weight: var(--weight-regular); font-size: var(--text-caption);
                  color: var(--color-text-tertiary); }
.banda + .oferta { margin-top: 0; }

/* --- tarjeta de oferta. Vidrio esmerilado 2 de 3, y sólo mientras está sin
       marcar: una vez aplicada pierde el vidrio y baja a superficie plana, así
       se distingue de un vistazo lo que queda por hacer de lo que ya está. --- */
.oferta {
  display: grid; grid-template-columns: var(--score-width) 1fr; gap: var(--spacing-md);
  align-items: start;
  margin-bottom: var(--spacing-md); padding: var(--spacing-lg);
  border: var(--glass-border); border-radius: var(--rounded-lg);
  background: var(--glass-background);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  box-shadow: var(--elevation-raised);
  transition: border-color var(--duration-fast) var(--ease-standard);
}
.oferta:hover { border-color: var(--color-border); }
.oferta:focus-within { border-color: var(--color-focus-ring); }
/* Con el menú de tres puntos abierto, la tarjeta sube por encima de las de
   abajo. El z-index del panel NO alcanza, y subirlo a 9999 tampoco: el
   `backdrop-filter` del vidrio esmerilado convierte cada tarjeta en un contexto
   de apilado propio, y adentro de ese contexto el panel puede valer lo que sea
   que igual se dibuja con su tarjeta. Entre tarjetas hermanas manda el orden
   del documento, así que la de abajo tapaba al panel de la de arriba. Lo que
   hay que levantar es la tarjeta entera, no el panel. */
.oferta:has(.menu[open]) { position: relative; z-index: var(--z-dropdown); }
/* Ya decidida: pierde el vidrio, baja a superficie plana y se aprieta. Estas
   pestañas son para revisar lo hecho, no para elegir, y ahí lo que sirve es
   ver muchas de un saque. */
.oferta.marcada { background: var(--color-surface);
                  border: var(--border-hairline) solid var(--color-border-subtle);
                  backdrop-filter: none; -webkit-backdrop-filter: none;
                  box-shadow: var(--elevation-flat);
                  padding: var(--spacing-md); margin-bottom: var(--spacing-sm); }

.puntaje {
  display: grid; place-items: center; padding: var(--spacing-sm) 0;
  font-family: var(--font-mono); font-size: var(--text-h3);
  font-variant-numeric: tabular-nums; line-height: 1.1;
  border: var(--border-hairline) solid var(--color-border);
  border-radius: var(--rounded-md);
  background: var(--color-surface-raised); color: var(--color-text-primary);
}
.puntaje .de { display: block; font-size: var(--text-caption); letter-spacing: 0;
               color: var(--color-text-tertiary); }
.puntaje.alto { border-color: var(--color-success); color: var(--color-success); }
.puntaje.alto .de { color: var(--color-success); }

.oferta h3 { margin: 0 0 var(--spacing-xs); }
.oferta h3 a { color: var(--color-text-primary); text-decoration: none; }
.oferta h3 a:hover { color: var(--color-text-primary); text-decoration: underline; }

/* Cada dato en su propia etiqueta, nunca una tira "A · B · C": con cuatro
   datos la tira se lee como una frase y no deja distinguir qué es cada cosa. */
.datos-meta { display: flex; flex-wrap: wrap; gap: var(--spacing-sm);
              list-style: none; margin: 0 0 var(--spacing-sm); padding: 0; }
.datos-meta li {
  padding: var(--spacing-xs) var(--spacing-sm);
  border: var(--border-hairline) solid var(--color-border-subtle);
  border-radius: var(--rounded-full);
  background: var(--color-surface); color: var(--color-text-secondary);
  font-size: var(--text-caption);
}
.datos-meta li.cuando { font-family: var(--font-mono); cursor: help; }
.stack { color: var(--color-text-secondary); font-size: var(--text-body-sm);
         margin: 0 0 var(--spacing-sm); }
.razon { color: var(--color-text-secondary); font-size: var(--text-body-sm);
         margin: 0 0 var(--spacing-md); max-width: var(--content-max-ch); }

/* La fila de acciones: la primaria, la alternativa real de ese momento, y el
   menú de tres puntos. Más de dos controles visibles por oferta es un error
   de diseño, así que todo lo demás vive adentro del menú. */
.acciones { display: flex; align-items: center; gap: var(--spacing-sm);
            flex-wrap: wrap; margin: 0;
            padding-top: var(--spacing-md);
            border-top: var(--border-hairline) solid var(--color-border-subtle); }
/* Lo ya decidido va en la misma posición que iría la fila de acciones. */
.datos > .marca, .datos > .marca-motivo { margin-top: var(--spacing-md); }

/* El bloque de motivo se despliega adentro de la misma tarjeta cuando se marca
   "No apliqué". Es la única animación de layout del sistema. Cerrado, el
   disparador ocupa lo que mide y va al lado de "Apliqué"; abierto pasa a la
   fila de abajo, que es donde entra el desplegable y el campo de texto. */
.motivo { flex: 0 1 auto; min-width: 0; }
/* `order` y no sólo el ancho: sin esto el bloque abierto empuja el menú de tres
   puntos a una tercera fila y la esquina de la tarjeta queda vacía. */
.motivo[open] { flex: 1 1 100%; order: 9; }
.motivo > summary {
  display: inline-flex; align-items: center; justify-content: center;
  gap: var(--spacing-sm); list-style: none; cursor: pointer;
  min-height: var(--control-height); padding: var(--spacing-sm) var(--spacing-lg);
  border: var(--border-hairline) solid var(--color-border);
  border-radius: var(--rounded-md);
  background: var(--color-surface-raised); color: var(--color-text-primary);
  font-size: var(--text-body-sm); font-weight: var(--weight-medium);
  transition: background-color var(--duration-fast) var(--ease-standard);
}
.motivo > summary::-webkit-details-marker { display: none; }
.motivo > summary:hover { background: var(--color-border); }
/* Abierto, el disparador pasa a ser el título del bloque: se marca con el borde
   índigo, igual que la píldora de filtro activa, para que se lea como sección
   abierta y no como un botón que quedó a medio apretar. */
.motivo[open] { margin-top: var(--spacing-sm); }
.motivo[open] > summary { margin-bottom: var(--spacing-md);
                          border-color: var(--brand-500); }
.motivo .cuerpo { display: flex; flex-direction: column; gap: var(--spacing-sm);
                  max-width: var(--content-max-ch); }
.motivo[open] .cuerpo { animation: desplegar var(--duration-normal) var(--ease-enter); }
@keyframes desplegar {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: none; }
}
.error-motivo { display: none; margin: 0; color: var(--color-danger);
                font-size: var(--text-caption); }
.error-motivo.visible { display: block; }

/* El menú de tres puntos: "Ya no está" y los links auxiliares. Sin JavaScript,
   con <details>: se abre, se cierra, y se tabula. */
.menu { position: relative; margin-left: auto; }
.menu > summary {
  display: grid; place-items: center; list-style: none; cursor: pointer;
  width: var(--control-height); height: var(--control-height);
  border-radius: var(--rounded-md);
  color: var(--color-text-secondary);
  transition: background-color var(--duration-fast) var(--ease-standard);
}
.menu > summary::-webkit-details-marker { display: none; }
.menu > summary:hover { background: var(--color-surface); color: var(--color-text-primary); }
.menu .panel {
  position: absolute; right: 0; top: calc(100% + var(--spacing-xs));
  z-index: var(--z-dropdown); min-width: var(--menu-width);
  display: flex; flex-direction: column; gap: 2px;
  padding: var(--spacing-xs);
  border: var(--border-hairline) solid var(--color-border);
  border-radius: var(--rounded-sm);
  background: var(--color-surface-raised);
  box-shadow: var(--elevation-overlay);
  animation: aparecer var(--duration-normal) var(--ease-enter);
}
@keyframes aparecer { from { opacity: 0; } to { opacity: 1; } }
.menu .panel a, .menu .panel button {
  display: block; width: 100%; min-height: var(--control-height-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border: 0; border-radius: var(--rounded-sm); background: transparent;
  color: var(--color-text-secondary); font-size: var(--text-body-sm);
  font-weight: var(--weight-regular); text-align: left; text-decoration: none;
}
.menu .panel a:hover, .menu .panel button:hover {
  background: var(--color-surface); color: var(--color-text-primary); }
.menu .panel .nota { padding: var(--spacing-xs) var(--spacing-md) var(--spacing-sm);
                     color: var(--color-text-tertiary); font-size: var(--text-caption); }

/* Lo ya decidido: etiqueta con texto, nunca sólo color. "Descartada" y
   "Archivada" son estados neutrales y se pintan con neutrales, no con rojo. */
.marca { display: inline-flex; align-items: center; gap: var(--spacing-sm);
         padding: var(--spacing-xs) var(--spacing-md);
         border: var(--border-hairline) solid var(--color-border-subtle);
         border-radius: var(--rounded-full);
         background: var(--color-surface); color: var(--color-text-secondary);
         font-size: var(--text-caption); }
.marca.si { background: var(--color-success-surface); border-color: var(--color-success);
            color: var(--color-success); }
.marca .cuando { color: var(--color-text-tertiary); font-family: var(--font-mono);
                 font-size: var(--text-mono); }
/* El motivo elegido de la lista y el escrito a mano, cada uno en su elemento.
   Se separan con espacio, no con un punto medio: unidos se leen como una sola
   frase y no se distingue cuál eligió la persona y cuál escribió. */
.marca-motivo { display: flex; flex-wrap: wrap; gap: var(--spacing-sm);
                margin: var(--spacing-sm) 0 0; color: var(--color-text-tertiary);
                font-size: var(--text-caption); }
.marca-motivo .motivo-elegido { color: var(--color-text-secondary); }

/* Al marcarla, la tarjeta se va antes de que la página se recargue: con dos
   ofertas de 90 al lado, sin esto la lista vuelve igual y no sabés a cuál le
   diste. */
.oferta.yendose { animation: sale var(--duration-normal) var(--ease-exit) forwards;
                  pointer-events: none; }
@keyframes sale { to { opacity: 0; transform: translateX(24px); } }

/* --- la tarjeta de la pestaña Filtradas. Es la misma tarjeta, pero acá la
       pregunta no es "¿me postulo?" sino "¿el filtro acertó?", así que lo
       primero que se lee es el motivo que dio el sistema. Sin vidrio: no está
       esperando una postulación, está esperando un veredicto sobre el filtro. */
.oferta.filtrada { background: var(--color-surface);
                   border: var(--border-hairline) solid var(--color-border-subtle);
                   backdrop-filter: none; -webkit-backdrop-filter: none;
                   box-shadow: var(--elevation-flat); }
.por-que { margin: 0 0 var(--spacing-sm); max-width: var(--content-max-ch);
           color: var(--color-text-secondary); font-size: var(--text-body-sm); }
.por-que b { color: var(--color-text-primary); font-weight: var(--weight-medium); }
.por-que .detalle { display: block; margin-top: 2px;
                    color: var(--color-text-tertiary); font-size: var(--text-caption);
                    line-height: var(--leading-snug); }
.acciones .ayuda { flex-basis: 100%; }

/* El marcador de la auditoría: cuántas veces acertó el filtro y cuántas no.
   Los dos números en mono, que es para lo que está la mono: números que se
   comparan entre sí y que van a cambiar todos los días. */
.callout.marcador .cuenta { display: flex; flex-wrap: wrap;
                            gap: var(--spacing-xs) var(--spacing-lg);
                            align-items: baseline; margin: 0 0 var(--spacing-sm);
                            color: var(--color-text-secondary);
                            font-size: var(--text-body-sm); }
.callout.marcador .valor { font-family: var(--font-mono);
                           font-size: var(--text-h2); font-weight: var(--weight-semibold);
                           font-variant-numeric: tabular-nums;
                           color: var(--color-text-primary);
                           margin-right: var(--spacing-sm); }

/* --- callout. Agrupa una explicación corta con su salida al lado. --- */
.callout, .pista {
  max-width: var(--content-max-ch);
  margin: 0 0 var(--spacing-md); padding: var(--spacing-md);
  border: var(--border-hairline) solid var(--color-border);
  border-radius: var(--rounded-md);
  background: var(--color-surface); color: var(--color-text-secondary);
  font-size: var(--text-body-sm); line-height: var(--leading-body);
}
.callout.atencion { background: var(--color-warning-surface);
                    border-color: var(--color-warning);
                    color: var(--color-text-primary); }
.callout p, .pista p { max-width: none; }
.callout p + p, .pista p + p { margin-top: var(--spacing-sm); }
.callout .salida { display: inline-block; margin-top: var(--spacing-sm); }
.pista b { display: block; margin-bottom: var(--spacing-xs);
           color: var(--color-text-primary); font-weight: var(--weight-semibold); }
.pista li b, .pista p b { display: inline; margin: 0; }
.pista ul { margin: var(--spacing-sm) 0 0; padding-left: var(--spacing-lg); }
.pista li { margin: var(--spacing-xs) 0; }
.pista code, code {
  padding: 1px var(--spacing-xs); border-radius: var(--rounded-sm);
  border: var(--border-hairline) solid var(--color-border-subtle);
  background: var(--color-background);
  font-family: var(--font-mono); font-size: var(--text-mono); }
/* Marcan un ejemplo correcto y uno equivocado. El rojo acá sí es un error:
   es el valor que no hay que pegar. */
.pista .bien { color: var(--color-success); font-weight: var(--weight-semibold); }
.pista .mal { color: var(--color-danger); font-weight: var(--weight-semibold); }

/* --- archivar de a muchas: mantenimiento, todo en fantasma --- */
.encajonar { display: flex; align-items: center; flex-wrap: wrap;
             gap: var(--spacing-sm); margin: 0 0 var(--spacing-lg);
             padding: var(--spacing-md);
             border: var(--border-hairline) solid var(--color-border-subtle);
             border-radius: var(--rounded-md);
             background: var(--color-surface);
             color: var(--color-text-secondary); font-size: var(--text-body-sm); }
.encajonar button { min-height: var(--control-height-sm);
                    padding: var(--spacing-xs) var(--spacing-md);
                    font-size: var(--text-body-sm); }
.encajonar .ayuda { flex-basis: 100%; margin: 0; }

/* --- métricas. El valor en display, el label debajo en terciario, y el label
       nunca más grande que el valor. --- */
.tarjetas { display: grid; gap: var(--spacing-md); margin-bottom: var(--spacing-lg);
            grid-template-columns: repeat(auto-fit, minmax(var(--metric-min), 1fr)); }
.dato { padding: var(--spacing-lg);
        border: var(--border-hairline) solid var(--color-border-subtle);
        border-radius: var(--rounded-lg);
        background: var(--color-surface); box-shadow: var(--elevation-flat); }
.dato.destacado { border-color: var(--color-border); }
.dato .numero { display: block;
                font-size: var(--text-display); font-weight: var(--weight-semibold);
                line-height: var(--leading-tight);
                letter-spacing: var(--tracking-display);
                font-variant-numeric: tabular-nums;
                color: var(--color-text-primary); }
.dato .que { display: block; margin-top: var(--spacing-xs);
             color: var(--color-text-tertiary); font-size: var(--text-body-sm); }

/* --- tablas: apretadas, cabecera sin fondo, sin rayado alterno --- */
table.numeros { width: 100%; max-width: var(--table-max); border-collapse: collapse;
                margin: 0 0 var(--spacing-sm); }
table.numeros th, table.numeros td {
  text-align: left; padding: var(--spacing-sm) var(--spacing-md);
  border-bottom: var(--border-hairline) solid var(--color-border-subtle);
  font-size: var(--text-body-sm); }
table.numeros th { color: var(--color-text-tertiary);
                   font-weight: var(--weight-regular);
                   border-bottom-color: var(--color-border); }
table.numeros td { color: var(--color-text-primary); }
table.numeros td.n { width: 5em; text-align: right;
                     font-family: var(--font-mono); font-size: var(--text-mono);
                     font-variant-numeric: tabular-nums; }
/* Una fecha con hora no entra en la columna angosta de los números y se parte
   en dos renglones. Va en mono igual, pero sin ancho fijo y sin cortarse. */
table.numeros .fecha { text-align: right; white-space: nowrap;
                       font-family: var(--font-mono); font-size: var(--text-mono);
                       font-variant-numeric: tabular-nums; }
table.numeros th.fecha { font-family: var(--font-sans); font-size: var(--text-body-sm); }
table.numeros tr:last-child td { border-bottom: 0; }
table.numeros tr:hover td { background: var(--color-surface); }

.explica { color: var(--color-text-tertiary); font-size: var(--text-body-sm);
           max-width: var(--content-max-ch); margin: 0 0 var(--spacing-lg); }

/* --- estado vacío: qué va a aparecer acá y qué se puede hacer ahora --- */
.vacio { max-width: var(--content-max-ch);
         padding: var(--spacing-2xl) var(--spacing-xl);
         border: var(--border-hairline) solid var(--color-border-subtle);
         border-radius: var(--rounded-lg);
         background: transparent; color: var(--color-text-secondary);
         font-size: var(--text-body-md); line-height: var(--leading-body); }
.vacio b { display: block; margin-bottom: var(--spacing-sm);
           color: var(--color-text-primary); font-weight: var(--weight-semibold); }
/* En un estado vacío no hay ninguna oferta que aplicar, así que acá sí la
   salida es el primario de la pantalla. */
.vacio .salida { margin-top: var(--spacing-lg); }

/* --- cómo viene funcionando: lo que antes había que abrir en una ventana
       negra aparte. Las quejas del registro son texto de máquina y van en
       mono, adentro del desplegable. --- */
.acciones-sueltas { margin: var(--spacing-md) 0 var(--spacing-lg); }
.registro { list-style: none; margin: var(--spacing-sm) 0 0; padding: 0;
            max-width: var(--content-max-ch); }
.registro li { padding: var(--spacing-sm) 0;
               border-bottom: var(--border-hairline) solid var(--color-border-subtle);
               color: var(--color-text-tertiary);
               font-family: var(--font-mono); font-size: var(--text-mono);
               line-height: var(--leading-body); overflow-wrap: anywhere; }
.registro li:last-child { border-bottom: 0; }

/* --- paginación --- */
.paginas { display: flex; align-items: center; gap: var(--spacing-md);
           flex-wrap: wrap; margin: var(--spacing-lg) 0 0; }
.paginas a, .paginas span.quieto {
  display: inline-flex; align-items: center; min-height: var(--nav-item-height);
  padding: var(--spacing-sm) var(--spacing-md);
  border: var(--border-hairline) solid var(--color-border);
  border-radius: var(--rounded-md);
  background: transparent; color: var(--color-text-secondary);
  font-size: var(--text-body-sm); text-decoration: none; }
.paginas a:hover { background: var(--color-surface); color: var(--color-text-primary); }
.paginas span.quieto { color: var(--color-text-tertiary); border-color: var(--color-border-subtle); }
.paginas .donde { color: var(--color-text-tertiary); font-size: var(--text-body-sm); }
.paginas .donde .n { font-family: var(--font-mono); font-size: var(--text-mono);
                     font-variant-numeric: tabular-nums; }

/* El cartel de que entraron ofertas es un toast más: mismo lugar, mismo
   vidrio, misma entrada. Lo único suyo es que no se va solo a los 4 segundos,
   porque no avisa que algo pasó sino que hay algo para hacer. El componente
   está definido abajo, con el resto de los toasts. */
.novedades.visible { display: flex; align-items: center; gap: var(--spacing-md); }
.novedades button { min-height: var(--control-height-sm);
                    padding: var(--spacing-xs) var(--spacing-md); }
@keyframes entra-toast { from { opacity: 0; transform: translateY(8px); }
                         to { opacity: 1; transform: none; } }

/* --- formularios. Un formulario largo va en un panel, no troceado en
       tarjetas idénticas: trocear todo en cards iguales aplana la jerarquía. --- */
form.datos { padding: var(--spacing-lg);
             border: var(--border-hairline) solid var(--color-border-subtle);
             border-radius: var(--rounded-lg);
             background: var(--color-surface); }
form.datos h2 { margin: var(--spacing-xl) 0 var(--spacing-md);
                padding-top: var(--spacing-lg);
                border-top: var(--border-hairline) solid var(--color-border-subtle); }
form.datos h2:first-of-type { margin-top: 0; padding-top: 0; border-top: 0; }

.grilla { display: grid; gap: var(--spacing-lg) var(--gutter);
          grid-template-columns: repeat(3, minmax(0, 1fr)); }
@media (max-width: 1200px) { .grilla { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px)  { .grilla { grid-template-columns: minmax(0, 1fr); } }
.ancho { grid-column: 1 / -1; }

.campo { display: flex; flex-direction: column; gap: var(--spacing-xs);
         min-width: 0; }
.campo > label { color: var(--color-text-secondary); font-size: var(--text-body-sm);
                 font-weight: var(--weight-medium); }
/* El texto de ayuda explica la consecuencia de la elección, va en terciario y
   no pasa de 72 caracteres de ancho: si crece a lo ancho de la columna, compite
   con el contenido. Lo que no entra en tres líneas se va a "Cómo funciona". */
.ayuda { max-width: var(--content-max-ch); margin: 0;
         color: var(--color-text-tertiary); font-size: var(--text-caption);
         line-height: var(--leading-snug); }
.como > summary { cursor: pointer; color: var(--color-text-secondary);
                  font-size: var(--text-caption); }
.como > summary:hover { color: var(--color-text-primary); }
.como .ayuda { margin-top: var(--spacing-xs); }

.checks { display: flex; flex-wrap: wrap; gap: var(--spacing-sm) var(--spacing-lg);
          align-items: flex-start; }
.checks label { display: flex; align-items: center; gap: var(--spacing-sm);
                min-height: var(--control-height-sm); cursor: pointer;
                font-size: var(--text-body-sm); color: var(--color-text-primary); }
.tilde { display: flex; flex-direction: column; gap: 2px; }
.tilde .nota { padding-left: var(--spacing-lg); max-width: var(--content-max-ch);
               color: var(--color-text-tertiary); font-size: var(--text-caption);
               line-height: var(--leading-snug); }

/* La barra de guardar se pega abajo: el formulario es largo y el botón quedaba
   fuera de pantalla, así que se guardaba a ciegas o no se guardaba. */
.guardar { position: sticky; bottom: 0; z-index: var(--z-sticky);
           margin: var(--spacing-lg) calc(var(--spacing-lg) * -1) calc(var(--spacing-lg) * -1);
           padding: var(--spacing-md) var(--spacing-lg);
           background: var(--color-surface-raised);
           border-top: var(--border-hairline) solid var(--color-border-subtle);
           border-radius: 0 0 var(--rounded-lg) var(--rounded-lg); }

/* --- páginas de mensaje y consejo --- */
.herramientas { display: flex; flex-wrap: wrap; gap: var(--spacing-sm);
                margin: 0 0 var(--spacing-lg); }
.mensaje { margin-bottom: var(--spacing-md); padding: var(--spacing-lg);
           border: var(--border-hairline) solid var(--color-border-subtle);
           border-radius: var(--rounded-lg); background: var(--color-surface); }
.mensaje h3 { margin: 0 0 var(--spacing-sm); }
.mensaje textarea { min-height: var(--textarea-min); margin-bottom: var(--spacing-sm); }
.mensaje .ayuda { margin-top: var(--spacing-sm); }
pre.consejo { margin: 0; white-space: pre-wrap;
              font-family: var(--font-sans); font-size: var(--text-body-sm);
              line-height: var(--leading-body); color: var(--color-text-primary); }
.terminos { display: flex; flex-wrap: wrap; gap: var(--spacing-sm);
            list-style: none; margin: 0 0 var(--spacing-md); padding: 0; }
.terminos li { padding: var(--spacing-xs) var(--spacing-md);
               border: var(--border-hairline) solid var(--color-info);
               border-radius: var(--rounded-full);
               background: var(--color-info-surface); color: var(--color-info);
               font-size: var(--text-caption); }
.sub { margin: 0 0 var(--spacing-lg); color: var(--color-text-secondary);
       font-size: var(--text-body-sm); }
.sub .dato-linea { display: block; }

@media (max-width: 640px) {
  .oferta { grid-template-columns: minmax(0, 1fr); padding: var(--spacing-md); }
  .puntaje { width: var(--score-width); }
  .acciones { flex-direction: column; align-items: stretch; }
  .acciones .menu { margin-left: 0; }
  .menu .panel { right: auto; left: 0; }
  form.datos { padding: var(--spacing-md); }
  .guardar { margin: var(--spacing-md) calc(var(--spacing-md) * -1) calc(var(--spacing-md) * -1);
             padding: var(--spacing-md); }
  .guardar button { width: 100%; }
}

/* Quien pide menos movimiento no recibe ninguno: tampoco la expansión de la
   tarjeta ni la salida al marcar. */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition-duration: 1ms !important;
    animation-duration: 1ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
  }
}
"""


GRAFICOS = """
/* ===========================================================================
   EL CONTADOR DE POSTULACIONES Y LOS GRÁFICOS
   =========================================================================== */

/* --- "Apliqué a N trabajos". Es lo único de la app que mide el trabajo de la
       persona y no el del sistema, y por eso es lo más grande de la pantalla.
       Va en verde porque el verde acá significa lo que significa en todo el
       sistema: lo que ya hiciste. Y va con la palabra al lado, nunca sólo el
       color. --- */
.postulaciones {
  display: flex; flex-wrap: wrap; align-items: flex-end;
  gap: var(--spacing-lg); margin: 0 0 var(--spacing-lg);
  padding: var(--spacing-lg);
  border: var(--border-hairline) solid var(--color-success);
  border-radius: var(--rounded-lg);
  background: var(--color-success-surface);
}
.postulaciones .cuenta { flex: 0 0 auto; margin: 0; }
.postulaciones .numero {
  display: block; font-size: var(--text-hero);
  font-weight: var(--weight-semibold); line-height: var(--leading-tight);
  letter-spacing: var(--tracking-display);
  font-variant-numeric: tabular-nums;
  color: var(--color-success);
}
.postulaciones .que { display: block; margin-top: var(--spacing-xs);
                      color: var(--color-text-primary);
                      font-size: var(--text-body-md); }
.postulaciones .cuando { display: block; margin-top: 2px;
                         color: var(--color-text-secondary);
                         font-size: var(--text-body-sm); }
.postulaciones .periodo { margin-left: auto; align-self: flex-start; }
.postulaciones .periodo label { color: var(--color-text-secondary);
                                font-size: var(--text-body-sm); }
/* El reparto por semana, al lado del número. 12 postulaciones en un mes puede
   ser tres semanas sin hacer nada y una a los tiros: eso es lo que se ve acá y
   no en el total. */
.postulaciones .semanas { flex: 1 1 240px; min-width: 0;
                          align-self: flex-end; }
.postulaciones .semanas .columnas { height: 72px; }
.postulaciones .semanas .columna-relleno { background: var(--color-success); }
.postulaciones .semanas .columna-valor { color: var(--color-success); }
/* Una semana sin postulaciones no merece el verde: no hay nada que celebrar y
   el color llamaba la atención sin tener nada que decir. */
.columna.vacia .columna-valor,
.postulaciones .semanas .columna.vacia .columna-valor {
  color: var(--color-text-tertiary); }
.columna.vacia .columna-relleno { background: var(--color-border); }
.postulaciones .vacio-corto { color: var(--color-text-secondary);
                              font-size: var(--text-body-sm);
                              max-width: var(--content-max-ch); }

/* --- barras horizontales. La etiqueta a la izquierda, la barra en el medio y
       el valor a la derecha en mono: el largo sirve para comparar de un
       vistazo y el número evita tener que estimarlo contra una grilla. --- */
.barras { display: flex; flex-direction: column; gap: var(--spacing-sm);
          max-width: var(--content-max-ch); margin: 0 0 var(--spacing-lg); }
.barra-fila { display: grid; grid-template-columns: minmax(0, 14rem) 1fr auto;
              align-items: center; gap: var(--spacing-md);
              font-size: var(--text-body-sm); }
.barra-nombre { color: var(--color-text-primary); overflow-wrap: anywhere; }
.barra-riel { display: block; height: 10px; border-radius: var(--rounded-full);
              background: var(--data-track); overflow: hidden; }
.barra-relleno { display: block; width: var(--ancho); height: 100%;
                 border-radius: var(--rounded-full);
                 background: var(--data-fill); }
.barra-valor { font-family: var(--font-mono); font-size: var(--text-mono);
               font-variant-numeric: tabular-nums;
               color: var(--color-text-secondary); text-align: right;
               min-width: 3ch; }

/* --- barras verticales. Para cuando el eje tiene un orden propio que no se
       puede reordenar por tamaño: los tramos de puntaje van de 0 a 100 y las
       semanas de la más vieja a la más nueva. --- */
.columnas { display: flex; align-items: flex-end; gap: var(--spacing-sm);
            height: 180px; max-width: var(--content-max-ch);
            margin: 0 0 var(--spacing-lg);
            border-bottom: var(--border-hairline) solid var(--color-border); }
.columna { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column;
           align-items: center; justify-content: flex-end; height: 100%;
           gap: var(--spacing-xs); }
.columna-relleno { display: block; width: 100%; height: var(--alto);
                   background: var(--data-fill);
                   border-radius: var(--rounded-sm) var(--rounded-sm) 0 0; }
.columna.destacada .columna-relleno { background: var(--data-destacada); }
.columna-valor { font-family: var(--font-mono); font-size: var(--text-mono);
                 font-variant-numeric: tabular-nums;
                 color: var(--color-text-secondary); }
.columna.destacada .columna-valor { color: var(--color-success); }
/* El nombre del eje cuelga por debajo de la línea base, para que la línea
   quede donde tiene que quedar: en el cero. `top: 100%` lo cuelga del alto de
   la columna; con un `translateY(100%)` se corría su propio alto y terminaba
   montado sobre la línea y sobre el pie del gráfico. */
.columna { position: relative; }
.columna-nombre { position: absolute; top: 100%; margin-top: var(--spacing-xs);
                  color: var(--color-text-tertiary); font-size: var(--text-caption);
                  white-space: nowrap; }
/* El renglón que dejan libre los nombres colgados, para que nada se les monte. */
.columnas { margin-bottom: var(--spacing-xl); }

/* La leyenda de un gráfico de una sola serie no existe: el título dice qué se
   está midiendo. Lo que sí va es la aclaración de qué significa el color
   distinto, cuando lo hay. */
.pie-grafico { max-width: var(--content-max-ch);
               margin: 0 0 var(--spacing-lg);
               color: var(--color-text-tertiary); font-size: var(--text-caption); }
.pie-grafico .marca-color { display: inline-block; width: 10px; height: 10px;
                            border-radius: 2px; margin-right: var(--spacing-xs);
                            background: var(--data-destacada);
                            vertical-align: baseline; }

@media (max-width: 640px) {
  .barra-fila { grid-template-columns: 1fr auto; }
  .barra-nombre { grid-column: 1 / -1; }
  .postulaciones .periodo { margin-left: 0; }
  .postulaciones .semanas { flex-basis: 100%; }
}
"""

LINKEDIN = """
/* ===========================================================================
   EL CONSTRUCTOR DE BÚSQUEDAS DE LINKEDIN
   =========================================================================== */

/* --- el taller: los controles a la izquierda, lo que sale a la derecha ---

   Antes era una sola columna larga: armabas la búsqueda arriba y la dirección
   aparecía abajo de todo, fuera de pantalla. Como el constructor es un
   `form method=get`, apretar "Armar la búsqueda" recarga la página, y el
   navegador la abre arriba: el resultado nacía justo donde no lo veías y la
   pantalla saltaba en cada intento.

   Partido en dos, el resultado nace al lado de los controles. La página en sí
   ya no scrollea: la altura es la del viewport y lo que se mueve es cada
   columna por dentro. Es la única pantalla que trabaja así, porque es la única
   donde mirás dos cosas a la vez.

   Se llaman `.lado` y no `.columna` porque `.columna` ya es una barra vertical
   de los gráficos de Métricas, con su propio `flex` y su `justify-content`.
   Dos clases con el mismo nombre y distinta idea es un choque silencioso: la
   primera vez, el formulario apareció encogido y flotando fuera de su caja. */
.taller {
  flex: 1 1 auto; min-height: 0;
  display: grid; grid-template-columns: 1fr 1fr; gap: var(--gutter);
}
.taller > .lado {
  min-width: 0; min-height: 0;
  overflow-y: auto; scrollbar-gutter: stable;
  padding-right: var(--spacing-sm);
}
.taller > .lado > h2 { margin: var(--spacing-lg) 0 var(--spacing-sm); }
.taller > .lado > h2:first-child { margin-top: 0; }

/* --- el aire, más corto que en el resto de la app ---
   Las separaciones de las pantallas largas están calculadas para leer bajando:
   ahí el aire ayuda a que un bloque no se confunda con el siguiente. Acá no se
   baja, se mira todo junto adentro de una ventana, y ese mismo aire empuja
   controles fuera de la vista. Se acorta un escalón, no dos: sin nada de aire
   los bloques se pegan y hay que buscar dónde termina uno. */
.taller .grilla { gap: var(--spacing-md) var(--gutter); }
.taller form.datos { padding: var(--spacing-md); }
.taller form.datos h2 { margin: var(--spacing-lg) 0 var(--spacing-sm);
                        padding-top: var(--spacing-md); }
/* El primero no lleva nada de eso: no separa dos bloques, abre la tarjeta. La
   regla general de `form.datos` ya lo dice, pero ésta pesa igual y viene
   después, así que la pisaba y dejaba 40px de hueco arriba de "Qué buscar". */
.taller form.datos h2:first-of-type { margin-top: 0; padding-top: 0; }
.taller .armada { margin-bottom: var(--spacing-lg); }
.taller .callout { margin-bottom: var(--spacing-md); }
.taller .guardar { margin: var(--spacing-md) calc(var(--spacing-md) * -1)
                           calc(var(--spacing-md) * -1);
                   padding: var(--spacing-sm) var(--spacing-md); }

/* El taller usa todo el ancho que queda, no los 1200px de las pantallas de
   lectura: son dos columnas mirándose, no un texto para leer de corrido. El
   tope alto existe igual, porque a 2500px las dos columnas se separan tanto
   que dejan de leerse juntas. */
main:has(> .taller) {
  height: 100dvh; overflow: hidden;
  display: flex; flex-direction: column;
  max-width: 1600px;
  padding-bottom: var(--spacing-lg);
}

/* La grilla del constructor se acomoda al ancho de SU columna, no al de la
   ventana: adentro de media pantalla, tres columnas de campos no entran. */
.taller .grilla { grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); }

/* Las tildes de puestos son largas: en una fila sola cada una queda a media
   pantalla de la siguiente y hay que barrer con la vista. En columnas se leen
   como una lista. */
.checks.en-columnas { display: grid; gap: var(--spacing-sm) var(--spacing-lg);
                      grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); }
.armador { margin-bottom: 0; }

/* --- la barra de abajo del constructor ---
   A la izquierda la acción, a la derecha el contador de lo que aplicaste desde
   acá. Van juntos porque son las dos cosas que se tocan en esta pantalla: una
   abre la búsqueda, la otra anota lo que salió de ella. */
.armador .guardar { display: flex; flex-wrap: wrap; align-items: center;
                    justify-content: space-between; gap: var(--spacing-sm); }

/* Nada de esto se encoge: si no entra al lado del botón, baja entero a la
   línea de abajo. Encogiendo, el "Confirmar" se montaba arriba del "+". */
.armador .guardar > * { flex: 0 0 auto; }

/* --- el anotador de postulaciones ---
   El rótulo arriba, el control abajo. Antes iba todo en una fila y con tres
   renglones de explicación al pie: al lado del único botón que importa de esta
   pantalla, eso era un párrafo compitiendo con una acción. */
.apliques { display: flex; flex-direction: column; align-items: flex-end;
            gap: var(--spacing-xs); }
.apliques .rotulo { display: flex; align-items: center; gap: var(--spacing-xs);
                    margin: 0; color: var(--color-text-secondary);
                    font-size: var(--text-body-sm); }
.apliques .pasos { display: flex; align-items: center; gap: var(--spacing-sm); }
.apliques .pasos > * { flex: 0 0 auto; }

/* Una sola pieza, no tres cajas sueltas: tres cajas iguales no dicen que se
   tocan juntas ni cuál es el número y cuáles los botones. */
.stepper {
  display: inline-flex; align-items: stretch; overflow: hidden;
  border: var(--border-hairline) solid var(--color-border);
  border-radius: var(--rounded-md);
  background: var(--color-surface-raised);
}
.stepper .paso {
  width: 2.5rem; min-width: 0; height: var(--control-height-sm); padding: 0;
  display: grid; place-items: center;
  border: 0; border-radius: 0; background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--text-body-lg); line-height: 1;
}
.stepper .paso:hover:not(:disabled) { background: var(--color-surface);
                                      color: var(--color-text-primary); }
.stepper .paso:disabled { opacity: 0.35; cursor: not-allowed; }
/* El número es lo que se mira, y es lo único verde de la pieza: el más y el
   menos todavía no son nada, y el verde acá significa lo que ya hiciste. */
.stepper .numero {
  display: grid; place-items: center;
  min-width: 3ch; padding: 0 var(--spacing-xs);
  border-left: var(--border-hairline) solid var(--color-border);
  border-right: var(--border-hairline) solid var(--color-border);
  color: var(--color-success); font-size: var(--text-body-lg);
  font-weight: var(--weight-semibold); font-variant-numeric: tabular-nums;
}
.apliques .confirmar {
  min-height: var(--control-height-sm); padding: 0 var(--spacing-md);
  border: var(--border-hairline) solid var(--color-success);
  border-radius: var(--rounded-md);
  background: var(--color-success-surface); color: var(--color-success);
  font-size: var(--text-body-sm); font-weight: var(--weight-medium);
}
.apliques .confirmar:hover:not(:disabled) { background: var(--color-success);
                                            color: var(--color-background); }
.apliques .confirmar:disabled { opacity: 0.35; cursor: not-allowed; }

/* --- el signo de pregunta con la explicación adentro ---
   Para lo que hace falta una vez y estorba siempre. Se abre con el mouse y
   también con el foco del teclado: quien tabula no pasa el mouse por ningún
   lado. Sale del flujo (`position: absolute`) para que abrirlo no mueva nada
   de lugar. */
.ayuda-al-lado { position: relative; display: inline-flex; }
.ayuda-al-lado .signo {
  display: grid; place-items: center;
  width: var(--icon-md); height: var(--icon-md);
  border: var(--border-hairline) solid var(--color-border);
  border-radius: var(--rounded-full);
  color: var(--color-text-tertiary); font-size: var(--text-caption);
  line-height: 1; cursor: help;
}
.ayuda-al-lado:hover .signo, .ayuda-al-lado:focus-visible .signo {
  border-color: var(--color-text-secondary); color: var(--color-text-primary);
}
.ayuda-al-lado .globo {
  position: absolute; bottom: calc(100% + var(--spacing-xs)); right: 0;
  z-index: var(--z-dropdown);
  display: none; width: max-content; max-width: 30ch;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--rounded-sm);
  background: var(--neutral-700); color: var(--neutral-50);
  box-shadow: var(--elevation-overlay);
  font-size: var(--text-caption); line-height: var(--leading-snug);
  text-align: left; white-space: normal;
}
.ayuda-al-lado:hover .globo, .ayuda-al-lado:focus-visible .globo,
.ayuda-al-lado:focus-within .globo { display: block; }

/* --- abajo del ancho del taller vuelve a ser una sola columna ---
   Dos columnas de media pantalla adentro de una pantalla chica no son dos
   columnas, son dos rendijas. Y con la lateral arriba, 100dvh se pasa. */
@media (max-width: 1100px) {
  main:has(> .taller) { display: block; height: auto; overflow: visible;
                        max-width: var(--container-max);
                        padding-bottom: var(--spacing-3xl); }
  .taller { display: block; }
  .taller > .lado { overflow: visible; padding-right: 0; }
  .taller > .lado + .lado { margin-top: var(--spacing-xl); }
}

/* --- la dirección armada, entera y a la vista ---
   Nunca escondida detrás de un botón: es un texto largo con comillas y
   paréntesis que LinkedIn a veces interpreta distinto, y si algo sale raro lo
   primero que se mira es esto. Por eso se corta donde sea (`anywhere`) en vez
   de truncarse con puntos suspensivos. */
.armada { margin: 0 0 var(--spacing-xl); }
.armada h2 { margin: 0 0 var(--spacing-md); }
.url-generada {
  max-width: var(--content-max-ch);
  margin: 0 0 var(--spacing-md);
  padding: var(--spacing-md);
  border: var(--border-hairline) solid var(--color-border);
  border-radius: var(--rounded-sm);
  background: var(--color-background);
  color: var(--color-text-secondary);
  font-family: var(--font-mono); font-size: var(--text-mono);
  line-height: var(--leading-body);
  overflow-wrap: anywhere;
}
/* En la lista de guardadas la dirección se recorta a dos renglones, y ahí sí
   corresponde: ya la verificaste cuando la guardaste, y lo que hace falta es
   reconocer cuál es. Con `max-height` cortaba a mitad de un renglón y quedaba
   media línea de letras comida; `line-clamp` corta limpio y pone los puntos. */
.url-generada.chica { margin: var(--spacing-sm) 0 0; padding: var(--spacing-sm);
                      color: var(--color-text-tertiary);
                      display: -webkit-box; -webkit-box-orient: vertical;
                      -webkit-line-clamp: 2; line-clamp: 2; overflow: hidden; }

.guardar-favorito { display: flex; flex-wrap: wrap; align-items: flex-end;
                    gap: var(--spacing-sm); margin: 0 0 var(--spacing-md);
                    max-width: var(--content-max-ch); }
.guardar-favorito label { color: var(--color-text-secondary);
                          font-size: var(--text-body-sm);
                          flex-basis: 100%; }
.guardar-favorito input[type=text] { flex: 1 1 18rem; min-width: 0; }

/* --- las búsquedas guardadas --- */
.favoritos { list-style: none; margin: 0 0 var(--spacing-xl); padding: 0;
             display: flex; flex-direction: column; gap: var(--spacing-sm); }
.favorito { display: flex; align-items: flex-start; gap: var(--spacing-md);
            padding: var(--spacing-md);
            border: var(--border-hairline) solid var(--color-border-subtle);
            border-radius: var(--rounded-lg);
            background: var(--color-surface); }
.favorito .datos { flex: 1 1 auto; min-width: 0; }
.favorito h3 { margin: 0; }
.favorito .cuando { margin: 2px 0 0; color: var(--color-text-tertiary);
                    font-size: var(--text-caption); }
.favorito .acciones { flex: 0 0 auto; display: flex; align-items: center;
                      gap: var(--spacing-sm); padding: 0; border: 0; }
.favorito .menu { margin-left: 0; }
.favorito:has(.menu[open]) { position: relative; z-index: var(--z-dropdown); }

/* La columna scrollea, así que recorta lo que se salga de ella: el menú de la
   última guardada quedaría cortado por abajo. Hace falta aire al final, pero
   **sólo mientras hay un menú abierto**: dejarlo fijo abría un hueco vacío
   enorme abajo de la lista, todo el tiempo, para algo que se usa un segundo.
   El `:has()` lo pone al abrir y lo saca al cerrar, y `scrollIntoView` baja
   hasta él. */
.taller .favoritos { margin-bottom: 0; }
.taller .favoritos:has(.menu[open]) { padding-bottom: var(--menu-aire); }

/* --- el toast ---
   4 segundos, abajo a la derecha, uno solo a la vez. Vidrio esmerilado: es el
   tercero y último lugar donde se usa, junto con la barra lateral y la tarjeta
   de oferta sin marcar.

   Avisa sólo lo que NO se ve: el link copiado, porque el portapapeles es
   invisible. Guardar un favorito no lleva toast, porque el favorito aparece en
   la lista. */
.toast {
  position: fixed; right: var(--spacing-lg); bottom: var(--spacing-lg);
  z-index: var(--z-toast); display: none;
  padding: var(--spacing-md);
  border: var(--glass-border); border-radius: var(--rounded-md);
  background: var(--glass-background);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  box-shadow: var(--elevation-overlay);
  color: var(--color-text-primary); font-size: var(--text-body-sm);
}
.toast.visible { display: block;
                 animation: entra-toast var(--duration-normal) var(--ease-enter); }

@media (max-width: 640px) {
  .favorito { flex-wrap: wrap; }
  .favorito .acciones { flex-basis: 100%; }
  .toast { left: var(--spacing-md); right: var(--spacing-md); }
}
"""

#: La hoja completa, en el orden en que se lee: fuentes, tokens, base, shell,
#: controles, piezas y gráficos. Se sirve embebida en el `<head>` de cada
#: página: son 20 KB y ahorran un pedido más contra un servidor que corre en la
#: misma máquina.
CSS = "\n".join((_font_faces(), TOKENS, BASE, SHELL, CONTROLES, PIEZAS,
                 GRAFICOS, LINKEDIN))
