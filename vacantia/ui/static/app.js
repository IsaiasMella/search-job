// El JavaScript de la pantalla.
//
// Lo que hay acá es lo poco que htmx no cubre: que el motivo sea obligatorio al
// descartar, el menú de tres puntos, y copiar al portapapeles. Todo lo demás
// anda sin JavaScript propio: el bloque de motivo y el menú son `<details>`,
// que se abren solos, y las actualizaciones de pantalla las hace htmx.
//
// El error del motivo se muestra al lado del campo, y no con un cartel modal
// del navegador: ese cartel tapa la pantalla, hay que sacarlo antes de poder
// escribir, y no deja ver cuál de las ofertas lo pidió cuando hay veinte en la
// lista. El servidor lo valida igual en `_post_feedback`, así que esto es
// comodidad y no la garantía.


function marcarBien(form) {
  var campo = form.querySelector('input[name=motivo]');
  var error = form.querySelector('.error-motivo');
  var select = form.querySelector('select[name=motivo_clave]');
  [campo, select].forEach(function (el) {
    if (!el) { return; }
    el.classList.remove('mal');
    el.removeAttribute('aria-invalid');
  });
  if (error) { error.classList.remove('visible'); }
}

// Alcanza con CUALQUIERA de los dos: elegir un motivo de la lista, o
// escribirlo. No hay opción "Otro motivo" en el desplegable a propósito —
// obligaba a abrirlo, bajar hasta "Otro" y recién ahí escribir, tres pasos de
// más justo cuando ya tenías la mano en el teclado.
function descartar(boton) {
  var form   = boton.closest('form');
  var select = form.querySelector('select[name=motivo_clave]');
  var campo  = form.querySelector('input[name=motivo]');
  var error  = form.querySelector('.error-motivo');
  if ((select && select.value) || (campo && campo.value.trim())) {
    marcarBien(form);
    return true;
  }
  var flojo = select || campo;
  flojo.classList.add('mal');
  flojo.setAttribute('aria-invalid', 'true');
  if (error) { error.classList.add('visible'); }
  flojo.focus();
  return false;
}

// Volver al mismo lugar de la lista después de marcar una oferta.
//
// Marcar es un POST que redirige a un GET (si no, recargar reenviaría el
// formulario), y el navegador abre esa página nueva arriba de todo. Con 40
// ofertas eso significa que después de marcar la número 30 hay que volver a
// bajar hasta ahí. Se guarda dónde estabas justo antes de enviar y se vuelve
// al llegar; la clave se consume una sola vez, así un F5 posterior no te
// mueve.
var CLAVE_SCROLL = 'vacantia:scroll';

function recordarScroll() {
  try { sessionStorage.setItem(CLAVE_SCROLL, String(window.scrollY)); } catch (e) {}
}

function volverAlScroll() {
  var y;
  try {
    y = sessionStorage.getItem(CLAVE_SCROLL);
    sessionStorage.removeItem(CLAVE_SCROLL);
  } catch (e) { return; }
  if (y === null) { return; }
  // 'instant' y no 'smooth': ya estabas ahí, no es un viaje.
  window.scrollTo({ top: parseInt(y, 10) || 0, behavior: 'instant' });
}

// Lo mismo, pero para la columna del constructor de LinkedIn.
//
// Ahí la página entera no scrollea: scrollea cada columna por dentro. Armar la
// búsqueda es un GET, o sea una recarga, y la columna vuelve arriba: si venías
// eligiendo abajo de todo, cada intento te devolvía al principio del
// formulario. Se guarda dónde estabas y se vuelve, igual que en la lista.
var CLAVE_TALLER = 'vacantia:taller';

function elLado() { return document.querySelector('.taller > .controles'); }

function recordarTaller() {
  var col = elLado();
  if (!col) { return; }
  try { sessionStorage.setItem(CLAVE_TALLER, String(col.scrollTop)); } catch (e) {}
}

function volverAlTaller() {
  var col = elLado(), y;
  if (!col) { return; }
  try {
    y = sessionStorage.getItem(CLAVE_TALLER);
    sessionStorage.removeItem(CLAVE_TALLER);
  } catch (e) { return; }
  if (y === null) { return; }
  col.scrollTop = parseInt(y, 10) || 0;
}

// El menú de tres puntos se cierra al tocar afuera. Sin esto quedan tres menús
// abiertos tapando la lista y hay que cerrarlos de a uno.
function cerrarMenus(salvo) {
  document.querySelectorAll('details.menu[open]').forEach(function (m) {
    if (m !== salvo) { m.removeAttribute('open'); }
  });
}

// Una columna que scrollea recorta lo que se le sale, y el menú de la última
// guardada se abre justo contra el borde de abajo. Al abrirlo se lo trae a la
// vista; 'nearest' mueve lo mínimo, así que si ya entraba no mueve nada.
function menuALaVista(menu) {
  var panel = menu.querySelector('.panel');
  if (panel && panel.scrollIntoView) {
    panel.scrollIntoView({ block: 'nearest', behavior: 'instant' });
  }
}

document.addEventListener('DOMContentLoaded', function () {
  volverAlScroll();
  volverAlTaller();
  // Para los envíos que sí pasan por 'submit': archivar, y marcar cuando la
  // animación está apagada por prefers-reduced-motion.
  document.querySelectorAll('form.acciones').forEach(function (form) {
    form.addEventListener('submit', recordarScroll);
  });
  document.querySelectorAll('form.armador').forEach(function (form) {
    form.addEventListener('submit', recordarTaller);
  });
  document.querySelectorAll('details.menu').forEach(function (m) {
    m.addEventListener('toggle', function () { if (m.open) { menuALaVista(m); } });
  });
  document.addEventListener('click', function (ev) {
    var dentro = ev.target.closest ? ev.target.closest('details.menu') : null;
    cerrarMenus(dentro);
  });
});

// Marcar una oferta: se la ve irse antes de que la página se recargue.
//
// El servidor sigue haciendo todo el trabajo; esto es sólo para que se note
// CUÁL se fue. Con dos ofertas de 90 pegadas, la página vuelve y la lista se
// ve igual: no hay forma de saber a cuál le diste.
//
// Sin JavaScript el botón envía el formulario como siempre, y quien pidió
// menos movimiento tampoco espera la animación.
function marcar(boton, esDescarte) {
  if (esDescarte && !descartar(boton)) { return false; }
  var tarjeta = boton.closest('.oferta');
  var quieto = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!tarjeta || quieto) { return true; }

  // `form.submit()` no manda el botón apretado, así que se agrega a mano:
  // sin esto el servidor no sabría si fue "apliqué" o "no apliqué".
  var form = boton.closest('form');
  var oculto = document.createElement('input');
  oculto.type = 'hidden';
  oculto.name = boton.name;
  oculto.value = boton.value;
  form.appendChild(oculto);

  tarjeta.classList.add('yendose');
  // OJO: `form.submit()` NO dispara el evento 'submit', así que el listener de
  // más abajo no alcanza y hay que guardar la posición a mano. Es exactamente
  // lo que hacía que después de marcar volvieras arriba de todo.
  recordarScroll();
  setTimeout(function () { form.submit(); }, 220);
  return false;
}

// Copiar la URL armada al portapapeles, y avisar que se copió.
//
// Es el único caso de toast de la app, y está porque el resultado NO se ve: el
// portapapeles es invisible. Guardar un favorito no lleva toast, porque el
// favorito aparece en la lista y avisar lo que ya se ve es ruido.
//
// Sin `navigator.clipboard` (pasa si la página no es segura) se cae a
// seleccionar el texto, que deja el Ctrl+C a un paso.
function copiar(boton, url) {
  var listo = function () { avisar('Link copiado'); };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(listo, function () { seleccionar(boton); });
  } else {
    seleccionar(boton);
  }
  return false;
}

function seleccionar(boton) {
  var bloque = boton.closest('section, li');
  var texto = bloque && bloque.querySelector('.url-generada');
  if (!texto) { return; }
  var rango = document.createRange();
  rango.selectNodeContents(texto);
  var sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(rango);
  avisar('Seleccionada: apretá Ctrl+C');
}

// El toast: 4 segundos, abajo a la derecha, uno solo a la vez. El anterior se
// reemplaza en vez de apilarse, que es lo que convierte un aviso en un estorbo.
var TOAST_TIMER = null;

function avisar(texto) {
  var toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = 'toast';
    toast.setAttribute('role', 'status');
    document.body.appendChild(toast);
  }
  toast.textContent = texto;
  toast.classList.add('visible');
  if (TOAST_TIMER) { clearTimeout(TOAST_TIMER); }
  TOAST_TIMER = setTimeout(function () { toast.classList.remove('visible'); }, 4000);
}

// El aviso de que entraron ofertas ya NO se maneja acá.
//
// Era un `setInterval` que le pedía un JSON al servidor cada 20 segundos y
// escribía el cartel a mano. Ahora lo trae el cartel de la corrida del pie de
// la barra lateral, en el mismo pedido con el que pregunta en qué etapa va la
// búsqueda: el servidor manda el aviso ya armado y htmx lo pone en su lugar con
// `hx-swap-oob`. Un reloj en vez de dos, y el texto se arma donde se arma todo
// el resto del HTML.
//
// Lo que NO cambió, porque sigue siendo lo correcto: **no recarga sola**. Si
// alguien está escribiendo el motivo de un descarte, una recarga se lo borra.
// Avisa, y decide la persona.

// Mis CV, en Mi perfil: se ve un CV por vez y se cambia con el desplegable.
//
// Los otros CV no se sacan del formulario, sólo se esconden: así lo que
// escribiste en uno y todavía no guardaste sigue ahí cuando volvés, y al
// guardar se mandan todos. El campo escondido `cv_elegido` viaja con el
// formulario para que, después de guardar, la pantalla vuelva a este mismo CV.
//
// Sin JavaScript no hay desplegable y se ven todos, uno abajo del otro.
function elegirCv(id) {
  document.querySelectorAll('.mis-cv .grilla.cv').forEach(function (bloque) {
    bloque.classList.toggle('activo', bloque.id === 'cv-' + id);
  });
  var campo = document.querySelector('input[name=cv_elegido]');
  if (campo) { campo.value = id; }
}
