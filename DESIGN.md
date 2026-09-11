---
version: alpha
name: VACANTIA Design System
description: Sistema de diseño para una app privada de búsqueda de trabajo que junta ofertas de varios portales y genera URLs de búsqueda de LinkedIn.

# ---- COLORES ----------------------------------------------
# Solo tema oscuro. No hay light mode: la app se usa en escritorio,
# por pocas personas, y duplicar la paleta solo agrega superficie de error.
colors:
  # primitivos — neutrales fríos, nunca grises puros ni negro tintado
  neutral-50: "#F4F5F9"
  neutral-100: "#DCDEE8"
  neutral-300: "#9AA0B4"
  neutral-500: "#868EA2"
  neutral-700: "#2A2F3E"
  neutral-900: "#0F1117"
  brand-300: "#A9ABFF"
  brand-500: "#6366E8"
  brand-700: "#4A4CC4"

  # semánticos
  background: "{colors.neutral-900}"
  surface: "#171A23"
  surface-raised: "#1E222E"
  border: "{colors.neutral-700}"
  border-subtle: "#232735"
  text-primary: "{colors.neutral-50}"
  text-secondary: "{colors.neutral-300}"
  text-tertiary: "{colors.neutral-500}"
  text-on-action: "#FFFFFF"
  action: "{colors.brand-700}"
  action-hover: "{colors.brand-500}"
  focus-ring: "{colors.brand-300}"

  # estados
  success: "#4ADE80"
  success-surface: "#16241C"
  warning: "#E9B949"
  warning-surface: "#26200F"
  danger: "#F87171"
  danger-surface: "#26161A"
  info: "#7DA8FF"
  info-surface: "#151C2B"

# ---- TIPOGRAFÍA -------------------------------------------
# Inter para todo. JetBrains Mono solo para datos e identificadores.
typography:
  display:
    fontFamily: Inter
    fontSize: 2rem
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  h1:
    fontFamily: Inter
    fontSize: 1.75rem
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.015em"
  h2:
    fontFamily: Inter
    fontSize: 1.375rem
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  h3:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: 600
    lineHeight: 1.4
  body-lg:
    fontFamily: Inter
    fontSize: 1.0625rem
    fontWeight: 400
    lineHeight: 1.6
  body-md:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.6
  body-sm:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.55
  caption:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: 400
    lineHeight: 1.45
  mono:
    fontFamily: "JetBrains Mono"
    fontSize: 0.8125rem
    fontWeight: 400
    lineHeight: 1.5

# ---- ESPACIADO --------------------------------------------
spacing:
  unit: 4
  xs: 4
  sm: 8
  md: 16
  lg: 24
  xl: 40
  2xl: 64
  3xl: 96

# ---- FORMAS / RADIOS --------------------------------------
rounded:
  none: 0px
  sm: 6px
  md: 10px
  lg: 16px
  full: 9999px

# ---- ELEVACIÓN / SOMBRAS ----------------------------------
elevation:
  flat: none
  raised: "0 1px 2px rgba(0, 0, 0, 0.4)"
  overlay: "0 8px 24px rgba(0, 0, 0, 0.5)"
  modal: "0 24px 64px rgba(0, 0, 0, 0.65)"

# ---- EFECTOS (glass y glow) --------------------------------
# El glass es la audacia del sistema. Se usa en 3 lugares y nada más.
effects:
  glass-background: "rgba(30, 34, 46, 0.72)"
  glass-blur: "blur(16px)"
  glass-border: "1px solid rgba(244, 245, 249, 0.06)"
  glow-action: "0 0 32px -8px rgba(99, 102, 232, 0.35)"
  glow-none: none

# ---- BORDES ------------------------------------------------
borders:
  hairline: 1px
  regular: 1px
  emphasis: 2px

# ---- LAYOUT ------------------------------------------------
layout:
  container-max: 1200px
  content-max-ch: 72
  sidebar-width: 260px
  grid-columns: 12
  gutter: "{spacing.md}"
breakpoints:
  sm: 640px
  md: 900px
  lg: 1200px
  xl: 1600px

# ---- MOTION ------------------------------------------------
motion:
  duration-instant: 80ms
  duration-fast: 140ms
  duration-normal: 220ms
  duration-slow: 320ms
  ease-standard: "cubic-bezier(0.4, 0, 0.2, 1)"
  ease-enter: "cubic-bezier(0.0, 0, 0.2, 1)"
  ease-exit: "cubic-bezier(0.4, 0, 1, 1)"
  reduced-motion: respect

# ---- ICONOGRAFÍA -------------------------------------------
iconography:
  library: Lucide
  stroke-width: 1.5
  size-sm: 16px
  size-md: 20px
  size-lg: 24px

# ---- Z-INDEX -----------------------------------------------
z-index:
  base: 0
  sticky: 100
  dropdown: 200
  overlay: 300
  modal: 400
  toast: 500

# ---- COMPONENTES -------------------------------------------
components:
  app-shell:
    backgroundColor: "{colors.background}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body-md}"

  sidebar:
    backgroundColor: "{effects.glass-background}"
    backdropFilter: "{effects.glass-blur}"
    border: "{effects.glass-border}"
    width: "{layout.sidebar-width}"
    padding: "{spacing.lg} {spacing.md}"

  sidebar-group-label:
    textColor: "{colors.text-tertiary}"
    typography: "{typography.caption}"
    padding: "{spacing.md} {spacing.sm} {spacing.xs}"

  sidebar-status:
    textColor: "{colors.text-tertiary}"
    typography: "{typography.caption}"
    padding: "{spacing.md}"
    borderTop: "{borders.hairline}"
    borderColor: "{colors.border-subtle}"

  nav-item:
    backgroundColor: transparent
    textColor: "{colors.text-secondary}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: "{spacing.sm} {spacing.md}"
    height: 40px
    iconSize: "{iconography.size-md}"
  nav-item-hover:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
  nav-item-active:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text-primary}"
    border: "{effects.glass-border}"
  nav-item-focus:
    outline: "{borders.emphasis}"
    outlineColor: "{colors.focus-ring}"
    outlineOffset: 2px

  button-primary:
    backgroundColor: "{colors.action}"
    textColor: "{colors.text-on-action}"
    typography: "{typography.body-sm}"
    fontWeight: 500
    rounded: "{rounded.md}"
    padding: "{spacing.sm} {spacing.lg}"
    height: 44px
  button-primary-hover:
    backgroundColor: "{colors.action-hover}"
    boxShadow: "{effects.glow-action}"
  button-primary-focus:
    backgroundColor: "{colors.action}"
    outline: "{borders.emphasis}"
    outlineColor: "{colors.focus-ring}"
    outlineOffset: 2px
  button-primary-active:
    backgroundColor: "{colors.brand-700}"
  button-primary-disabled:
    backgroundColor: "{colors.neutral-700}"
    textColor: "{colors.text-tertiary}"
  button-primary-loading:
    backgroundColor: "{colors.action}"
    textColor: "{colors.text-on-action}"

  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body-sm}"
    border: "{borders.hairline}"
    borderColor: "{colors.border}"
    rounded: "{rounded.md}"
    padding: "{spacing.sm} {spacing.lg}"
    height: 44px
  button-secondary-hover:
    backgroundColor: "{colors.neutral-700}"
  button-secondary-focus:
    outline: "{borders.emphasis}"
    outlineColor: "{colors.focus-ring}"
    outlineOffset: 2px
  button-secondary-disabled:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-tertiary}"

  button-ghost:
    backgroundColor: transparent
    textColor: "{colors.text-secondary}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: "{spacing.sm} {spacing.md}"
    height: 44px
  button-ghost-hover:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
  button-ghost-focus:
    outline: "{borders.emphasis}"
    outlineColor: "{colors.focus-ring}"
    outlineOffset: 2px

  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body-sm}"
    border: "{borders.hairline}"
    borderColor: "{colors.border}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm} {spacing.md}"
    height: 44px
  input-placeholder:
    textColor: "{colors.text-tertiary}"
  input-focus:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.focus-ring}"
    outline: "{borders.emphasis}"
    outlineColor: "{colors.focus-ring}"
    outlineOffset: 1px
  input-error:
    borderColor: "{colors.danger}"
    textColor: "{colors.text-primary}"
  input-disabled:
    backgroundColor: "{colors.background}"
    textColor: "{colors.text-tertiary}"
    borderColor: "{colors.border-subtle}"

  input-label:
    textColor: "{colors.text-secondary}"
    typography: "{typography.body-sm}"
    fontWeight: 500
    padding: "0 0 {spacing.xs}"
  input-help:
    textColor: "{colors.text-tertiary}"
    typography: "{typography.caption}"
    maxWidth: "{layout.content-max-ch}"
    padding: "{spacing.xs} 0 0"
  input-error-message:
    textColor: "{colors.danger}"
    typography: "{typography.caption}"
    padding: "{spacing.xs} 0 0"

  card:
    backgroundColor: "{colors.surface}"
    border: "{borders.hairline}"
    borderColor: "{colors.border-subtle}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
    boxShadow: "{elevation.flat}"

  job-card:
    backgroundColor: "{effects.glass-background}"
    backdropFilter: "{effects.glass-blur}"
    border: "{effects.glass-border}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
    boxShadow: "{elevation.raised}"
  job-card-hover:
    borderColor: "{colors.border}"
  job-card-focus-within:
    borderColor: "{colors.focus-ring}"
  job-card-applied:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.border-subtle}"
    boxShadow: "{elevation.flat}"
  job-card-title:
    textColor: "{colors.text-primary}"
    typography: "{typography.h3}"
  job-card-company:
    textColor: "{colors.text-secondary}"
    typography: "{typography.body-sm}"
  job-card-reason:
    textColor: "{colors.text-secondary}"
    typography: "{typography.body-sm}"
    maxWidth: "{layout.content-max-ch}"
  job-card-actions:
    padding: "{spacing.md} 0 0"
    borderTop: "{borders.hairline}"
    borderColor: "{colors.border-subtle}"

  score-badge:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text-primary}"
    typography: "{typography.mono}"
    border: "{borders.hairline}"
    borderColor: "{colors.border}"
    rounded: "{rounded.md}"
    padding: "{spacing.sm}"
  score-badge-high:
    borderColor: "{colors.success}"
    textColor: "{colors.success}"
  score-badge-mid:
    borderColor: "{colors.border}"
    textColor: "{colors.text-primary}"

  badge:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.caption}"
    border: "{borders.hairline}"
    borderColor: "{colors.border-subtle}"
    rounded: "{rounded.full}"
    padding: "{spacing.xs} {spacing.sm}"
  badge-success:
    backgroundColor: "{colors.success-surface}"
    textColor: "{colors.success}"
    borderColor: "{colors.success}"
  badge-info:
    backgroundColor: "{colors.info-surface}"
    textColor: "{colors.info}"
    borderColor: "{colors.info}"

  filter-pill:
    backgroundColor: transparent
    textColor: "{colors.text-secondary}"
    typography: "{typography.body-sm}"
    border: "{borders.hairline}"
    borderColor: "{colors.border}"
    rounded: "{rounded.full}"
    padding: "{spacing.sm} {spacing.md}"
    height: 36px
  filter-pill-hover:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
  filter-pill-active:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text-primary}"
    borderColor: "{colors.brand-500}"
  filter-pill-count:
    textColor: "{colors.text-tertiary}"
    typography: "{typography.mono}"
  filter-pill-focus:
    outline: "{borders.emphasis}"
    outlineColor: "{colors.focus-ring}"
    outlineOffset: 2px

  tab:
    backgroundColor: transparent
    textColor: "{colors.text-secondary}"
    typography: "{typography.body-md}"
    padding: "{spacing.sm} {spacing.md}"
    borderBottom: "{borders.emphasis}"
    borderColor: transparent
    height: 44px
  tab-hover:
    textColor: "{colors.text-primary}"
  tab-active:
    textColor: "{colors.text-primary}"
    borderColor: "{colors.brand-500}"
  tab-focus:
    outline: "{borders.emphasis}"
    outlineColor: "{colors.focus-ring}"
    outlineOffset: 2px

  url-preview:
    backgroundColor: "{colors.background}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.mono}"
    border: "{borders.hairline}"
    borderColor: "{colors.border}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"

  metric:
    backgroundColor: "{colors.surface}"
    border: "{borders.hairline}"
    borderColor: "{colors.border-subtle}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  metric-value:
    textColor: "{colors.text-primary}"
    typography: "{typography.display}"
  metric-label:
    textColor: "{colors.text-tertiary}"
    typography: "{typography.body-sm}"

  callout:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.body-sm}"
    border: "{borders.hairline}"
    borderColor: "{colors.border}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
    maxWidth: "{layout.content-max-ch}"
  callout-warning:
    backgroundColor: "{colors.warning-surface}"
    borderColor: "{colors.warning}"
    textColor: "{colors.text-primary}"

  modal:
    backgroundColor: "{colors.surface-raised}"
    border: "{effects.glass-border}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
    boxShadow: "{elevation.modal}"
  modal-overlay:
    backgroundColor: "rgba(15, 17, 23, 0.72)"
    backdropFilter: "{effects.glass-blur}"

  toast:
    backgroundColor: "{effects.glass-background}"
    backdropFilter: "{effects.glass-blur}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body-sm}"
    border: "{effects.glass-border}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
    boxShadow: "{elevation.overlay}"

  dropdown:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body-sm}"
    border: "{borders.hairline}"
    borderColor: "{colors.border}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs}"
    boxShadow: "{elevation.overlay}"
  dropdown-item:
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm} {spacing.md}"
  dropdown-item-hover:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"

  table-header:
    backgroundColor: transparent
    textColor: "{colors.text-tertiary}"
    typography: "{typography.body-sm}"
    padding: "{spacing.sm} {spacing.md}"
    borderBottom: "{borders.hairline}"
    borderColor: "{colors.border}"
  table-row:
    backgroundColor: transparent
    textColor: "{colors.text-primary}"
    typography: "{typography.body-sm}"
    padding: "{spacing.md}"
    borderBottom: "{borders.hairline}"
    borderColor: "{colors.border-subtle}"
  table-row-hover:
    backgroundColor: "{colors.surface}"
  table-cell-numeric:
    typography: "{typography.mono}"
    textAlign: right

  empty-state:
    backgroundColor: transparent
    textColor: "{colors.text-secondary}"
    typography: "{typography.body-md}"
    border: "{borders.hairline}"
    borderColor: "{colors.border-subtle}"
    rounded: "{rounded.lg}"
    padding: "{spacing.2xl} {spacing.xl}"
    maxWidth: "{layout.content-max-ch}"

  skeleton:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.sm}"

  tooltip:
    backgroundColor: "{colors.neutral-700}"
    textColor: "{colors.neutral-50}"
    typography: "{typography.caption}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs} {spacing.sm}"
    boxShadow: "{elevation.overlay}"
---

## Overview

VACANTIA junta ofertas de trabajo de varios portales tres veces al día y las
presenta en una sola lista, con un puntaje de ajuste por oferta. Además genera
URLs de búsqueda de LinkedIn para cubrir los avisos publicados hoy, que ningún
buscador indexó todavía.

**Audiencia:** cinco personas de una misma familia, cada una con su profesión y
su perfil de búsqueda. En escritorio, en sesiones cortas y con propósito: entran,
aplican a todo lo que pueden, y cierran cuando no queda nada más. No es un
producto comercial y no tiene usuarios anónimos.

**Trabajo principal de la interfaz:** que la persona aplique a un trabajo. Todo
lo demás —métricas, perfil, favoritos, filtros— existe únicamente para que eso
pase más rápido y con menos dudas.

**El problema real que resuelve la interfaz:** buscar trabajo genera ansiedad, y
la mayor parte de esa ansiedad no viene de la falta de ofertas sino de la duda
de "¿esto es todo lo que hay?". La app la responde con dos sistemas que se
complementan: el scraper trae lo publicado hace uno a tres días, y las URLs de
LinkedIn traen lo de hoy. La interfaz tiene que dejar eso evidente sin
explicarlo con un párrafo.

**Personalidad:** calma, no clínica. Concreta, no corporativa. Oscura, no
dramática. Honesta, no culposa. Silenciosa, no vacía.

**Principios de diseño** — las reglas que ganan cualquier discusión:

1. **Una decisión por vez.** En pantalla se muestra la acción que la persona
   viene a hacer. Los controles secundarios aparecen cuando se necesitan, no
   antes. Si un elemento muestra seis opciones simultáneas para un solo ítem,
   está mal diseñado.
2. **Nunca mostrar lo que la persona se pierde antes de mostrarle lo que puede
   hacer.** Los números sobre ofertas descartadas o inalcanzables son
   información legítima, y viven en Métricas. Arriba de la lista de trabajos no
   va ningún recuento de pérdidas.
3. **El estado del sistema es siempre visible y está escrito en castellano
   llano.** Cuándo buscó por última vez, cuándo vuelve a buscar, qué ventana de
   días cubre. Esta información es el antídoto de la ansiedad y por eso tiene
   un lugar fijo, no un tooltip.

## Colors

La paleta es un neutral frío con un solo acento índigo. El fondo nunca es negro
puro: tiene tinte azulado, lo que permite que las superficies con vidrio
esmerilado se separen sin verse sucias ni grises.

- **Fondo y superficies:** `background` es el lienzo de la app y no lleva
  contenido directamente encima salvo texto de sección. `surface` es para
  agrupaciones tranquilas: paneles de formulario, tarjetas de métrica, callouts,
  filas de tabla en hover. `surface-raised` es para lo que flota de verdad:
  modales, dropdowns, el ítem activo del sidebar. Nunca se anidan tres niveles
  de superficie; si hace falta un tercero, el layout está mal.
- **Texto:** tres niveles y se respetan. `text-primary` es el contenido que la
  persona vino a leer: títulos de oferta, valores de métrica, texto que escribió
  en un campo. `text-secondary` es el contexto que acompaña: empresa, ubicación,
  el motivo del puntaje, labels de campo. `text-tertiary` es lo que está por si
  acaso: texto de ayuda debajo de un input, timestamps, labels de métrica,
  contadores dentro de un pill. Este tercer nivel es el que evita que la app se
  lea como un muro: sin él, la ayuda extensa compite con el contenido.
- **Acción:** el índigo `action` conduce toda la interacción y nada más. Un solo
  botón primario por pantalla. El glow índigo aparece únicamente en hover de ese
  botón. Si el índigo está presente, algo es clickeable.
- **Estados:** `success` marca lo que ya hiciste —una oferta aplicada, un link
  guardado— y siempre con texto, nunca solo con color. `warning` se reserva para
  información que la persona puede accionar, en la pantalla de Métricas.
  `danger` es exclusivamente para errores de validación y acciones destructivas
  reales. Una oferta sin mirar, sin aplicar o descartada **no es un error**: se
  pinta con neutrales. `info` es para el estado del sistema (última búsqueda,
  próxima corrida).

**Reglas de color**

- Todo par texto/fondo cumple WCAG AA (4.5:1 en texto normal, 3:1 en texto
  grande). `text-tertiary` sobre `surface-raised` es el par más ajustado del
  sistema: no bajar ese valor.
- El color nunca es el único portador de significado: siempre lo acompaña texto
  o ícono.
- El color de acción no se usa para decorar. Nada de títulos índigo, íconos
  índigo decorativos ni bordes índigo en cards.
- Los fondos de estado (`success-surface` y compañía) son muy oscuros a
  propósito. No aclararlos para "que se note más".

## Typography

Inter para toda la interfaz: es neutral, tiene buen rendimiento en pesos
intermedios y no aporta personalidad falsa. JetBrains Mono aparece únicamente
donde el carácter monoespaciado significa algo: puntajes, URLs generadas, IDs de
aviso, columnas numéricas de tabla y contadores. Nunca para labels chicos.

**Escala:** progresión aproximada de 1.2 desde 0.75rem hasta 2rem. Los tamaños
de cuerpo se quedan en tres (`body-lg`, `body-md`, `body-sm`) y el interlineado
sube a 1.6 en todos, porque sobre fondo oscuro el texto necesita más aire
vertical para no cansar.

**Reglas**

- Largo de línea por debajo de 72 caracteres en cualquier párrafo. Esto aplica
  con fuerza al texto de ayuda de los formularios, que es largo y hoy se
  desparrama a lo ancho.
- El peso máximo es 600. Nunca 700 ni 800: en oscuro, el texto muy pesado
  florece y se lee peor.
- Sentence case en títulos, botones, labels y navegación.
- Sin ALL CAPS para labels. Los labels de grupo del sidebar y las cabeceras de
  tabla van en sentence case con `text-tertiary`, no en mayúsculas con
  letter-spacing.
- Sin resaltar una sola palabra del título en otro color o itálica.
- Los números que la persona compara (puntajes, contadores, columnas) van en
  mono y alineados a la derecha.

## Layout

Un shell de dos zonas: sidebar fijo a la izquierda y una sola columna de
contenido a la derecha, alineada a la izquierda. Nada centrado: la lectura
empieza siempre en el mismo borde, lo que reduce el trabajo de reencontrar el
inicio de línea al bajar por una lista larga.

**Grilla:** sidebar de 260px fijo, contenido con `container-max` de 1200px y
gutter de 16px. Los formularios usan tres columnas en `lg`, dos en `md` y una en
`sm`, y cada campo lleva su texto de ayuda directamente debajo, limitado a 72
caracteres de ancho.

**Estructura de navegación** — el sidebar agrupa por lo que la persona hace, no
por lo que la sección es:

- Marca **VACANTIA** arriba, clickeable, lleva a Trabajos.
- Grupo **Buscar**: `Trabajos` · `LinkedIn URLs`
- Separador, y abajo: `Métricas` · `Mi perfil`
- Al pie, fijo, el estado del sistema: última búsqueda y próxima corrida, en
  `caption` con `text-tertiary`.

`LinkedIn URLs` abre con dos pestañas en la parte superior del contenido: **Jobs**
y **Publicaciones**. Las pestañas son navegación dentro de la sección, no
filtros, y por eso van arriba del contenido y no dentro de una card.

**Densidad:** apretada en las listas de ofertas y en las tablas, aireada en
formularios y estados vacíos. La lista de trabajos privilegia ver muchas ofertas
sin scrollear; el perfil privilegia entender qué hace cada campo.

**Responsive:** por debajo de `md` el sidebar colapsa a solo íconos, y el estado
del sistema pasa a una línea sticky arriba del contenido. Lo primero que colapsa
en las cards de oferta son las etiquetas de tecnología, después la fila de
metadatos. El título, el puntaje y la acción primaria nunca se colapsan. Los
targets táctiles nunca bajan de 44px.

## Elevation & Depth

La elevación indica jerarquía, no decoración. Si dos cosas están al mismo nivel
conceptual, comparten sombra. En un tema oscuro la sombra funciona mal como
señal, así que el sistema separa las capas con **borde y translucidez** primero,
y usa la sombra solo cuando algo realmente se despega del plano.

- `flat`: contenido dentro del flujo. Cards de métrica, paneles de formulario,
  filas de tabla, callouts. La mayoría de la app vive acá.
- `raised`: cards de oferta. Se despegan apenas porque son accionables.
- `overlay`: dropdowns, tooltips, toasts. Elementos temporales anclados a algo.
- `modal`: solo modales, con el overlay de fondo difuminado.

**El glass se usa en exactamente tres lugares:** el sidebar, las cards de oferta
sin marcar y los toasts. En ningún otro. Una card de métrica con vidrio
esmerilado y una card de oferta con vidrio esmerilado se ven iguales y destruyen
la jerarquía. Una oferta ya aplicada pierde el glass y pasa a `surface` plano:
así se distingue de un vistazo lo que queda por hacer de lo que ya está hecho.

## Shapes

Tres radios que siguen la jerarquía del elemento, más el pill para etiquetas.
Un solo radio para todo es la señal más clara de una interfaz hecha con
plantilla.

- `sm` (6px): inputs, dropdowns, bloques de URL, skeletons, tooltips. Controles
  precisos, donde el radio no debe distraer del contenido.
- `md` (10px): botones, ítems de navegación, toasts, callouts. Elementos
  accionables de tamaño medio.
- `lg` (16px): cards, modales, estados vacíos. Contenedores que agrupan.
- `full`: etiquetas y pills de filtro. La forma redonda dice "esto es una
  categoría, no un botón".

## Motion

El movimiento responde a acciones y muestra qué cambió. En una app cuyo objetivo
es reducir la ansiedad, el movimiento innecesario es activamente dañino.

- Cambios de color y de borde en hover y focus: `duration-fast` con
  `ease-standard`.
- Apertura de los controles secundarios de una card (el bloque de motivo tras
  marcar "No apliqué"): `duration-normal` con `ease-enter`, expandiendo la
  altura. Es la única animación de layout del sistema.
- Modales y dropdowns: `duration-normal`, entrada con `ease-enter`, salida con
  `ease-exit`.
- Toasts: entran desde abajo a la derecha con `duration-normal`.
- Sin entradas fade-and-slide-up en cada sección al cargar la página.
- Sin transiciones de hover en cada card más allá del borde.
- **Sin nada que parpadee, pulse, cuente hacia atrás o se actualice solo.** No
  hay indicadores en vivo, ni contadores de tiempo transcurrido que corran, ni
  puntos animados de "actualizando". El estado del sistema es texto estático que
  cambia cuando cambia el dato.
- Como máximo un momento orquestado por pantalla.
- `prefers-reduced-motion` se respeta siempre, y desactiva también la expansión
  de la card.

## Voice & Content

La interfaz habla como alguien que ya pasó por esto y te está ayudando a
ordenarte. Informa sin evaluar y nunca hace sentir mal a quien la usa.

- Voz activa. El botón dice exactamente qué pasa: "Guardar cambios", no
  "Enviar". "Copiar link", no "Copiar".
- Una acción conserva el mismo nombre en todo el flujo: el botón "Guardar en
  favoritos" produce el aviso "Guardado en favoritos".
- **Nada de lenguaje de culpa ni de pérdida como contenido principal.** Los
  números sobre lo que quedó afuera se presentan como estado del sistema y
  siempre con la salida al lado: si 87 ofertas piden un inglés más alto que el
  tuyo, ese dato vive en Métricas y viene acompañado del link a Mi perfil para
  cambiar el nivel declarado. No se muestra arriba de la lista de trabajos.
- Los errores explican qué pasó y cómo arreglarlo. No piden disculpas ni son
  vagos.
- Las pantallas vacías dicen qué va a aparecer ahí y qué puede hacer la persona
  ahora mismo. Nunca cuentan un estado de ánimo ni celebran el vacío.
- El estado del sistema se escribe en lenguaje humano y relativo: "Última
  búsqueda: hoy 16:30 · Próxima: 23:59". No "cron ejecutado", no "hace 2 min",
  no nombres de archivo ni de script en el cuerpo del texto.
- Nombrá las cosas como las entiende la persona: "sin mirar", "apliqué",
  "descarté", "ya no está". No "unreviewed", no "estado 0".

## Components

**Botones** — un solo primario por pantalla, y es la acción que la persona vino
a hacer: aplicar a la oferta, generar el link, guardar el perfil. Secundario
para la alternativa real de ese mismo momento. Ghost para acciones de
mantenimiento que no compiten: archivar, marcar como caída, limpiar filtros.
Nunca dos primarios enfrentados: dos botones del mismo peso obligan a decidir
antes de leer.

**Cards de oferta** — es el componente central de la app y el que más disciplina
necesita. En su estado por defecto muestra: puntaje, título, empresa, metadatos,
etiquetas de tecnología, el motivo del ajuste en una línea, y **una sola acción
primaria: "Apliqué"**. Al lado, en secundario, "No apliqué". Nada más visible.

El bloque de motivo —el desplegable de razones y el campo de texto libre—
aparece recién cuando se marca "No apliqué", expandiéndose dentro de la misma
card. "Ya no está" y los links auxiliares ("Mensaje para escribirle", "Consejo
para el CV") viven en un menú de tres puntos en la esquina, no en la superficie.
La regla es dura: **más de dos controles visibles por oferta es un error de
diseño.** Una vez aplicada, la card pierde el glass, baja a `surface` plano y
muestra una etiqueta de éxito con texto.

**Cards en general** — se usan para agrupar cosas que se comparan entre sí o que
se accionan como unidad. Un formulario largo va en un panel `surface`, no
troceado en cards idénticas. Trocear todo el contenido en cards iguales es el
default genérico y aplana la jerarquía.

**Inputs** — label arriba siempre visible, en `text-secondary`. El placeholder
muestra un ejemplo de formato, nunca repite el label ni sustituye instrucciones.
El texto de ayuda va debajo en `text-tertiary`, limitado a 72 caracteres de
ancho, y explica la consecuencia de la elección, no la sintaxis obvia. Si la
ayuda supera tres líneas, lo que sobra pasa a un desplegable "Cómo funciona esto"
en lugar de crecer hacia abajo. El error reemplaza al texto de ayuda, no se
suma.

**Pills de filtro** — son el conmutador de estado de la lista de trabajos ("Sin
marcar", "Apliqué", "Descarté", "Archivadas", "Todas"). El contador va dentro
del pill en mono y `text-tertiary`, siempre presente incluso en cero. El activo
se marca con borde índigo y superficie elevada, nunca con relleno índigo pleno:
un pill relleno de color de acción se confunde con un botón.

**Pestañas** — solo para Jobs y Publicaciones dentro de LinkedIn URLs. Activa se
marca con borde inferior de 2px y texto primario. No usar pestañas para nada
que sea filtro; para eso están los pills.

**Bloque de URL generada** — la URL se muestra completa en mono sobre
`background`, con quiebre de línea y sin truncar. El botón de copiar es el
primario de esa pantalla. Guardar en favoritos es secundario. La persona tiene
que poder verificar el link antes de usarlo: nunca esconder la URL detrás de un
botón.

**Métricas** — cuadrícula de valores arriba, y debajo los desgloses en tablas de
dos columnas. Acá sí van los números sobre lo que quedó afuera, con la
explicación de por qué y el link a la sección donde se cambia. El valor va en
`display`, el label debajo en `text-tertiary`, y el label nunca es más grande
que el valor.

**Modales** — solo para acciones destructivas irreversibles y confirmación de
borrado de perfil. Aplicar, descartar, archivar y guardar links no interrumpen
nunca: se resuelven en línea con feedback de toast.

**Toasts** — 4 segundos, abajo a la derecha, uno a la vez. Se avisan las
acciones cuyo resultado no es visible en pantalla: link copiado, perfil
guardado, favorito agregado. No se avisa lo que ya se ve: si la card cambió de
estado, el toast es redundante.

**Navegación** — el ítem activo lleva superficie elevada y texto primario; los
demás, texto secundario. Los labels de grupo son `caption` en `text-tertiary`,
sentence case. El estado del sistema al pie es parte del sidebar, no un widget
suelto.

**Tablas** — densidad apretada, cabecera sin fondo y separada por un borde,
filas divididas por `border-subtle`. Los números van en mono a la derecha, el
texto a la izquierda. Orden por defecto: lo más reciente o lo más alto primero.
Sin rayado alterno de filas.

**Estados obligatorios de todo componente interactivo:** default, hover, focus
visible, active, disabled, loading, error, empty. El focus visible usa siempre
`focus-ring` con 2px y offset, y nunca se elimina el outline sin reemplazarlo.

## Do's and Don'ts

**Hacer**

- Usar únicamente valores de los tokens. Cero hex sueltos, cero px arbitrarios.
- Referenciar tokens semánticos, no primitivos, dentro de los componentes.
- Emitir todo como variables CSS (`var(--color-action)`, `var(--spacing-md)`) en
  una hoja de estilos servida por la app. No hay build step, no hay Tailwind, no
  hay clases utilitarias generadas.
- Mantener los tres niveles de texto separados. Todo texto de ayuda va en
  `text-tertiary`.
- Foco de teclado visible en todo lo interactivo.
- Gastar la audacia en un solo lugar: el vidrio esmerilado del sidebar y de las
  cards de oferta, más el glow índigo en hover del botón primario. El resto
  disciplinado.
- Cargar Inter y JetBrains Mono como archivos locales servidos por la app, con
  fallback a la pila del sistema. Sin llamadas a CDN externos.

**No hacer**

- No inventar colores, tamaños ni radios fuera de la escala.
- No usar el mismo border-radius en todo sin importar la jerarquía.
- No poner la misma sombra gris suave debajo de cada elemento.
- No aplicar el efecto de vidrio a más de tres tipos de componente. Si todo es
  vidrio, nada se destaca.
- No usar gradientes como decoración.
- No usar eyebrows en ALL CAPS con letter-spacing encima de cada título.
- No unir metadatos con puntos medios ("A · B · C") dentro de las cards; usar
  etiquetas separadas. El punto medio se reserva para la línea de estado del
  sistema.
- No usar un negro tintado (#0B0B0B, #111) en lugar del token de fondo.
- No agregar "→" al final del texto de links y botones.
- No usar marcadores numerados (01 / 02 / 03) salvo que el contenido sea
  realmente una secuencia.
- No usar monoespaciada para labels chicos que no son datos.
- **No mostrar un recuento de ofertas inalcanzables arriba de la lista de
  trabajos.** Ese dato vive en Métricas, con su explicación y su salida.
- **No mostrar más de dos controles simultáneos por card de oferta.** El motivo
  de descarte se despliega bajo demanda; el resto va al menú de tres puntos.
- **No usar `danger` ni ningún rojo para estados neutrales** como "sin mirar",
  "sin aplicar" o "descartada". Rojo es error o destrucción, nada más.
- No enfrentar dos botones del mismo peso visual para la misma decisión (hoy
  "Apliqué" verde y "No apliqué" rojo compiten y ninguno gana).
- No usar el color de acción como relleno de un pill de filtro: se confunde con
  un botón.
- No dejar que el texto de ayuda de los formularios crezca a lo ancho de la
  columna ni pase de tres líneas.
- No poner indicadores en vivo, contadores que corren, badges de alerta ni
  puntos pulsantes. Ni siquiera para el estado del scraper.
- No nombrar archivos, scripts ni comandos en el cuerpo de la interfaz. Si hay
  que ejecutar algo, es un botón con nombre humano.
- No agregar un light mode. Si hace falta, se discute y se agregan tokens; no se
  improvisa con `filter: invert`.

## Agent Guide

Instrucciones directas para el agente de código:

1. Leé este archivo completo antes de escribir cualquier UI.
2. Los tokens del front matter son normativos. Si un valor no está acá,
   preguntá; no lo inventes.
3. Emití `var(--token)` desde una hoja de estilos servida por la app. Nunca un
   valor literal, nunca estilos inline con hex o px.
4. Antes de terminar, verificá contra la sección "Do's and Don'ts" y corregí lo
   que la incumpla. Listá explícitamente qué reglas verificaste.
5. Si un componente necesita un valor que no existe, proponé agregarlo a los
   tokens en lugar de improvisarlo inline.
6. Ante cualquier duda de jerarquía, resolvé a favor del Principio 1: una
   decisión por vez.

**Prompt de arranque sugerido:**

> Leé DESIGN.md. Construí <COMPONENTE> siguiendo sus tokens y reglas.
> Usá solo valores referenciados de los tokens. Al terminar, listá qué
> reglas de "Do's and Don'ts" verificaste.