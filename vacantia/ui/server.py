"""Servidor local de la UI. Sólo biblioteca estándar.

    python -m vacantia.ui              # levanta y abre el navegador
    python -m vacantia.ui --port 9000 --sin-navegador

Escucha **únicamente en 127.0.0.1**: no es accesible desde otra máquina de la
red ni desde internet, y por eso no tiene login. Lee y escribe los mismos
archivos que el motor.
"""

import argparse
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

from vacantia.log import get_logger
from vacantia.ui import corrida, data, estilos, formulario, render

logger = get_logger()

PUERTO = 8756
HOST = "127.0.0.1"


#: Lo que sirve la app además del HTML: {ruta: (content-type, cómo se lee)}.
#:
#: El cuerpo se pide con una función y no se guarda en una constante para que
#: se lea del disco en cada pedido. Editar un `.css` y ver el cambio con F5, sin
#: reiniciar el servidor, es la mitad de la razón por la que el CSS dejó de ser
#: un string de Python.
_ESTATICOS = {
    "/estilos.css": ("text/css; charset=utf-8",
                     lambda: estilos.hoja().encode("utf-8")),
    "/app.js": ("text/javascript; charset=utf-8",
                lambda: render.estatico("app.js").encode("utf-8")),
    "/htmx.min.js": ("text/javascript; charset=utf-8",
                     lambda: render.estatico("htmx.min.js").encode("utf-8")),
}


class Handler(BaseHTTPRequestHandler):
    server_version = "vacantia"

    # --- utilidades -----------------------------------------------------

    def _responder(self, cuerpo: bytes, tipo="text/html; charset=utf-8", codigo=200,
                   extra: dict | None = None, cache: str = "no-store") -> None:
        extra = extra or {}
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        # Las páginas nunca se cachean: leen archivos que cambian solos. Lo que
        # sí es inmutable (las fuentes) pasa su propio valor.
        self.send_header("Cache-Control", cache)
        for clave, valor in extra.items():
            self.send_header(clave, valor)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(cuerpo)

    def _html(self, texto: str, codigo=200) -> None:
        self._responder(texto.encode("utf-8"), codigo=codigo)

    def _redirigir(self, ruta: str, ancla: str = "", **params) -> None:
        destino = f"{ruta}?{urlencode(params)}" if params else ruta
        # La ancla va después del querystring: sin ella, agregar un CV te
        # devolvía al principio de Mi perfil y el CV nuevo quedaba fuera de vista.
        if ancla:
            destino += f"#{ancla}"
        self.send_response(303)
        self.send_header("Location", destino)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _form(self) -> dict:
        """El cuerpo de un POST como {campo: valor}. Los repetidos se pisan:
        ningún campo del formulario es multivaluado."""
        largo = int(self.headers.get("Content-Length") or 0)
        if largo <= 0:
            return {}
        crudo = self.rfile.read(largo).decode("utf-8", errors="replace")
        return {k: v[-1] for k, v in parse_qs(crudo, keep_blank_values=True).items()}

    def _perfil_pedido(self, params: dict) -> str | None:
        """El perfil del querystring, o el primero que haya. None si no hay ninguno."""
        disponibles = data.perfiles()
        pedido = (params.get("perfil") or [""])[0]
        if pedido in disponibles:
            return pedido
        return disponibles[0] if disponibles else None

    def _pagina(self, titulo, cuerpo, perfil, tab, codigo=200) -> None:
        # El estado del sistema (cuándo buscó, cuándo vuelve, qué ventana cubre)
        # viaja en TODAS las páginas: vive al pie de la barra lateral y tiene
        # que estar siempre, no sólo en Trabajos.
        self._html(render.pagina(titulo, cuerpo, perfil, data.perfiles(), tab,
                                 estado=data.estado_del_sistema(perfil)), codigo)

    def _sin_perfiles(self, params: dict) -> None:
        """Instalación recién estrenada, o se borró el último perfil: no hay a
        quién mostrarle nada. Los carteles sí, que dicen qué se borró."""
        cuerpo = formulario.render_sin_perfiles(_mensajes(params))
        self._html(render.pagina("Empezar", cuerpo, "", [], "configuracion"))

    # --- GET ------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802  (lo impone BaseHTTPRequestHandler)
        url = urlparse(self.path)
        params = parse_qs(url.query)
        ruta = url.path.rstrip("/") or "/"

        if ruta == "/":
            return self._redirigir("/trabajos")
        if ruta.startswith("/fuentes/"):
            return self._get_fuente(ruta)
        if ruta in _ESTATICOS:
            return self._get_estatico(ruta)

        perfil = self._perfil_pedido(params)
        if perfil is None:
            return self._sin_perfiles(params)

        try:
            if ruta == "/trabajos":
                return self._get_trabajos(perfil, params)
            if ruta == "/datos":
                return self._get_datos(perfil, params)
            if ruta == "/configuracion":
                return self._get_configuracion(perfil, params)
            if ruta == "/mensajes":
                return self._get_mensajes(perfil, params)
            if ruta == "/consejo":
                return self._get_consejo(perfil, params)
            if ruta == "/estadisticas":
                return self._estadisticas(perfil, params)
            if ruta == "/linkedin":
                return self._get_linkedin(perfil, params)
            if ruta == "/corrida":
                return self._get_corrida(perfil, params)
        except FileNotFoundError as e:
            return self._pagina("Error", render.avisos([("error", str(e))]), perfil,
                                "trabajos", 404)
        except Exception as e:          # que un bug no deje la página en blanco
            logger.exception("[ui] Error sirviendo GET %s", self.path)
            return self._pagina("Error", render.avisos([("error", f"Algo falló: {e}")]),
                                perfil, "trabajos", 500)

        self._html("<h1>404</h1>", 404)

    def _get_estatico(self, ruta: str) -> None:
        """La hoja de estilos y los dos scripts, servidos como archivos.

        **Nunca se cachean.** Es a propósito: son archivos que se editan mientras
        se trabaja, y un caché acá significa tocar el CSS, apretar F5 y no ver
        el cambio. La app corre en la misma máquina que el navegador, así que
        volver a mandar 75 KB no cuesta nada medible.

        htmx se sirve **desde acá y no desde un CDN**, por la misma razón que
        las fuentes: la máquina puede estar sin internet, y una pantalla que
        depende de una descarga externa para que anden los botones es una
        pantalla rota.
        """
        tipo, cuerpo = _ESTATICOS[ruta]
        self._responder(cuerpo(), tipo=tipo, cache="no-store")

    def _get_fuente(self, ruta: str) -> None:
        """Inter y JetBrains Mono, servidas por la app y no por un CDN.

        La máquina puede estar sin internet, y una fuente que tarda tres
        segundos en llegar es una pantalla que parpadea al abrir. Si los
        archivos no están, `estilos` ni siquiera declara las `@font-face` y todo
        cae en la pila del sistema: esta ruta no se llega a pedir.

        Sólo sirve los nombres de la lista blanca de `estilos.FUENTES`: nada de
        armar el path con lo que venga en la URL.
        """
        pedido = ruta.rsplit("/", 1)[-1]
        if pedido not in {archivo for archivo, _, _ in estilos.FUENTES}:
            return self._html("<h1>404</h1>", 404)
        archivo = estilos.FUENTES_DIR / pedido
        if not archivo.exists():
            return self._html("<h1>404</h1>", 404)
        # Un año de caché: el nombre del archivo no cambia y el contenido tampoco.
        self._responder(archivo.read_bytes(), tipo="font/woff2",
                        cache="public, max-age=31536000, immutable")

    def _get_trabajos(self, perfil: str, params: dict) -> None:
        ver = (params.get("ver") or ["pendientes"])[0]
        if ver not in dict(render.FILTROS):
            ver = "pendientes"
        # Por defecto no se esconde nada: filtrar por fecha sin que nadie lo
        # haya pedido haría desaparecer avisos sin explicación. El botón está
        # a la vista y con el número puesto.
        desde = (params.get("desde") or ["todo"])[0]
        if desde not in data.RANGOS:
            desde = "todo"
        try:
            pedida = int((params.get("p") or ["1"])[0])
        except ValueError:
            pedida = 1
        mensajes = _mensajes(params)
        ofertas, pagina, paginas = data.ofertas(perfil, ver, desde, pedida)

        # El cartel de arriba cambia según la pestaña, así que sólo se calcula
        # el que se va a mostrar: leer el historial entero para armar un gráfico
        # que no se dibuja es trabajo tirado en cada carga de página.
        periodo = (params.get("apliq") or [""])[0] or data.PERIODO_POR_DEFECTO
        aplicadas = descartadas = None
        if ver in ("pendientes", "aplicadas"):
            # Parado en Apliqué el número tiene que ser el de la lista de abajo:
            # las contadas a mano desde un posteo de LinkedIn no están ahí, y un
            # cartel más grande que la lista se lee como un error.
            aplicadas = data.aplicadas_en(perfil, periodo,
                                          solo_de_la_lista=(ver == "aplicadas"))
        elif ver == "descartadas":
            descartadas = data.descartadas_en(perfil, periodo)

        cuerpo = render.trabajos(
            perfil, ofertas, data.contar_ofertas(perfil, desde),
            ver, mensajes, desde,
            conteo_fecha=data.contar_por_fecha(perfil, ver),
            marca=data.marca_de_cambio(perfil),
            pagina=pagina, paginas=paginas,
            viejas={d: len(data.viejas_sin_marcar(perfil, d)) for d in (7, 14, 30)},
            corriendo=corrida.esta_corriendo(),
            revision=data.resumen_revision(perfil),
            aplicadas=aplicadas, descartadas=descartadas,
        )
        self._pagina("Trabajos", cuerpo, perfil, "trabajos")

    def _get_corrida(self, perfil: str, params: dict) -> None:
        """El cartel del pie de la barra lateral, recién armado.

        Es lo único que la pantalla se pregunta sola, y contesta dos cosas en un
        solo pedido: en qué etapa va la búsqueda, y si entraron ofertas desde
        que la persona abrió la página.

        `marca` y `pend` son cómo estaba el historial **al abrir**, y los manda
        el navegador de vuelta en cada pedido. El servidor no se guarda nada: si
        se abren dos pestañas, cada una compara contra su propio momento.

        Devuelve un pedazo de HTML y no un JSON a propósito. El HTML lo arma
        `render` como el resto de la pantalla, con las mismas reglas y los
        mismos tests; un JSON obligaría a tener una segunda copia del texto y
        del marcado adentro del JavaScript, que es de donde venimos.
        """
        estado = data.estado_del_sistema(perfil)
        marca_al_abrir = (params.get("marca") or [""])[0]
        try:
            pendientes_al_abrir = int((params.get("pend") or ["0"])[0])
        except ValueError:
            pendientes_al_abrir = 0

        # Si el historial cambió, y cuántas entraron desde que se abrió. Son dos
        # preguntas distintas: puede cambiar sin que suba el número (entraron
        # veinte y las filtró a todas, o estás marcando desde otra pestaña), y
        # ahí igual hay que avisar que lo que estás mirando ya no es lo que hay.
        #
        # La diferencia y no el total: "entraron 211 ofertas" cuando entraron 3
        # es peor que no decir nada.
        cambio = bool(marca_al_abrir) and estado.get("marca") != marca_al_abrir
        nuevas = int(estado.get("pendientes") or 0) - pendientes_al_abrir if cambio else 0

        self._html(render.corrida_estado(
            perfil, estado.get("paso") or {}, marca_al_abrir, pendientes_al_abrir,
            nuevas=nuevas, cambio=cambio))

    def _get_mensajes(self, perfil: str, params: dict, con_llm: bool = False) -> None:
        """Los moldes para escribirle a quien publicó. Con `con_llm`, se los
        completa el modelo leyendo el aviso y el CV (cuesta una llamada)."""
        from vacantia import mensajes as mensajes_mod

        url = (params.get("url") or [""])[0]
        oferta = data.buscar_oferta(perfil, url)
        if oferta is None:
            return self._redirigir("/trabajos", perfil=perfil,
                                   error="No encontré esa oferta en el historial.")

        datos = data.leer_perfil(perfil)
        job = data.como_job(oferta)
        avisos_: list[tuple[str, str]] = []
        if con_llm:
            textos, escrito = data.mensajes_con_llm(perfil, job)
            avisos_.append(("ok", "Mensajes completados con IA.") if escrito else
                           ("error", "No pude usar el modelo — quedan los moldes para "
                                     "completar a mano."))
        else:
            textos = {t: mensajes_mod.molde(job, datos, t) for t in mensajes_mod.TIPOS}
            escrito = False
        cv_usado = (data.cv_para_oferta(perfil, oferta, datos)
                    if len(data.cvs_con_texto(datos)) > 1 else None)
        cuerpo = render.mensajes(perfil, oferta, textos, escrito, avisos_,
                                 cv_usado=cv_usado)
        self._pagina("Mensajes", cuerpo, perfil, "trabajos")

    def _get_consejo(self, perfil: str, params: dict, con_llm: bool = False) -> None:
        """Qué reordenar del CV para este aviso. La lista de palabras faltantes
        sale gratis; el consejo escrito cuesta una llamada al modelo."""
        from vacantia import consejo as consejo_mod

        url = (params.get("url") or [""])[0]
        oferta = data.buscar_oferta(perfil, url)
        if oferta is None:
            return self._redirigir("/trabajos", perfil=perfil,
                                   error="No encontré esa oferta en el historial.")

        datos = data.leer_perfil(perfil)
        job = data.como_job(oferta)
        # Las palabras que faltan se buscan en el CV que conviene mandar para ESTA
        # oferta, no en el primero: con dos CV, comparar contra el equivocado
        # marca como faltante justo lo que el otro CV sí tiene.
        cv_usado = data.cv_para_oferta(perfil, oferta, datos)
        faltantes = consejo_mod.faltan_en_el_cv(job, cv_usado["texto"])

        texto, escrito = "", False
        avisos_: list[tuple[str, str]] = []
        if con_llm:
            texto, escrito = data.consejo_con_llm(perfil, job)
            if not escrito:
                avisos_.append(("error", "No pude usar el modelo — te queda igual "
                                         "la lista de palabras que faltan."))
        varios = len(data.cvs_con_texto(datos)) > 1
        cuerpo = render.consejo(perfil, oferta, faltantes, texto, escrito, avisos_,
                                cv_usado=cv_usado if varios else None)
        self._pagina("Consejo", cuerpo, perfil, "trabajos")

    def _get_datos(self, perfil: str, params: dict) -> None:
        cuerpo = formulario.render_datos(perfil, data.leer_perfil(perfil), _mensajes(params),
                                         cv_elegido=(params.get("cv") or [""])[0])
        self._pagina("Mi perfil", cuerpo, perfil, "datos")

    def _get_configuracion(self, perfil: str, params: dict) -> None:
        cuerpo = formulario.render_configuracion(perfil, data.leer_perfil(perfil),
                                                 _mensajes(params))
        self._pagina("Configuración", cuerpo, perfil, "configuracion")

    def _estadisticas(self, perfil: str, params: dict) -> None:
        """Los contadores que antes competían con la lista por el mismo lugar."""
        desde = (params.get("desde") or ["todo"])[0]
        if desde not in data.RANGOS:
            desde = "todo"
        cuerpo = render.estadisticas(perfil, data.estadisticas(perfil, desde),
                                     desde, _mensajes(params),
                                     salud=corrida.salud(),
                                     puntajes=data.distribucion_de_puntajes(perfil),
                                     habilidades=data.habilidades_pedidas(perfil, desde))
        self._pagina("Métricas", cuerpo, perfil, "estadisticas")

    def _get_linkedin(self, perfil: str, params: dict) -> None:
        """Las direcciones de búsqueda de LinkedIn, en dos pestañas.

        **Publicaciones** es la que se abre por defecto: es la que cubre el
        hueco que el scraper no puede tapar, los posteos del muro que nunca
        llegan a la pestaña de empleos.

        El constructor es un `<form method=get>`, así que lo elegido viaja en
        estos mismos parámetros y la URL de la pantalla queda compartible.
        """
        from vacantia.ui import linkedin_urls

        tab = linkedin_urls.tipo_de((params.get("tab") or ["publicaciones"])[0])
        if tab == "jobs":
            elegido, url = self._armar_jobs(params)
        else:
            elegido, url = self._armar_publicaciones(params)

        cuerpo = render.linkedin(
            perfil, tab, _mensajes(params), elegido=elegido, url=url,
            guardados=linkedin_urls.favoritos(perfil, tab),
            # Los puestos salen de las palabras clave del perfil: un solo lugar
            # donde se agregan y se sacan, y no dos que se desincronizan.
            puestos=linkedin_urls.puestos_de(data.leer_perfil(perfil)),
            apliques={"pendientes": linkedin_urls.pendientes(perfil, tab),
                      "confirmadas": len(linkedin_urls.postulaciones(perfil, tab))})
        self._pagina("LinkedIn URLs", cuerpo, perfil, "linkedin")

    @staticmethod
    def _armar_jobs(params: dict) -> tuple[dict, str]:
        """Lo elegido en el constructor de Jobs, y la dirección que sale."""
        from vacantia.ui import linkedin_urls

        elegido = {
            "puestos": params.get("puesto") or [],
            "tambien": (params.get("tambien") or [""])[0].strip(),
            "sin_junior": bool(params.get("sin_junior")),
            "donde": (params.get("donde") or ["argentina"])[0],
            "modalidades": params.get("modalidad") or [],
            "niveles": params.get("nivel") or [],
            "cuando": (params.get("cuando") or ["24h"])[0],
            "orden": (params.get("orden") or ["recientes"])[0],
            "pocos": bool(params.get("pocos")),
            "sencilla": bool(params.get("sencilla")),
        }
        if not elegido["puestos"]:
            return elegido, ""
        fuera = linkedin_urls.EXCLUIR_JOBS if elegido["sin_junior"] else ()
        texto = linkedin_urls.armar_boolean_jobs(elegido["puestos"], elegido["tambien"],
                                                 fuera)
        return elegido, linkedin_urls.armar_url_jobs(
            texto, elegido["donde"], elegido["modalidades"], elegido["niveles"],
            elegido["cuando"], elegido["orden"], elegido["pocos"], elegido["sencilla"])

    @staticmethod
    def _armar_publicaciones(params: dict) -> tuple[dict, str]:
        """Lo elegido en el constructor de Publicaciones, y la dirección que sale."""
        from vacantia.ui import linkedin_urls

        idioma = (params.get("idioma") or ["es"])[0]
        gatillos = {
            "es": linkedin_urls.GATILLOS_ES,
            "en": linkedin_urls.GATILLOS_EN,
        }.get(idioma, linkedin_urls.GATILLOS_ES + linkedin_urls.GATILLOS_EN)

        elegido = {
            "puestos": params.get("puesto") or [],
            "lugares": params.get("lugar") or [],
            "idioma": idioma,
            "sin_junior": bool(params.get("sin_junior")),
            "cuando": (params.get("cuando") or ["24h"])[0],
            "orden": (params.get("orden") or ["recientes"])[0],
            "de_quien": (params.get("de_quien") or ["todos"])[0],
        }
        # La URL se arma sólo si la persona eligió algo. Al abrir la pantalla
        # por primera vez no hay nada que mostrar todavía, y una dirección
        # armada sola sería una que nadie pidió.
        url = ""
        if elegido["puestos"]:
            fuera = linkedin_urls.EXCLUIR if elegido["sin_junior"] else ()
            texto = linkedin_urls.armar_boolean(
                elegido["puestos"], gatillos, elegido["lugares"], fuera)
            url = linkedin_urls.armar_url(texto, elegido["cuando"],
                                          elegido["orden"], elegido["de_quien"])
            # Si el texto no entraba, se recortó: la pantalla lo dice.
            entraron = linkedin_urls.que_entro(
                elegido["puestos"], gatillos, elegido["lugares"], fuera)
            elegido["pedidos"] = {"gatillos": len(gatillos), "excluir": len(fuera)}
            elegido["entraron"] = entraron
        return elegido, url

    # --- POST -----------------------------------------------------------

    def do_POST(self) -> None:  # noqa: N802
        ruta = urlparse(self.path).path.rstrip("/") or "/"
        form = self._form()
        perfil = form.get("perfil", "")

        try:
            if ruta == "/feedback":
                return self._post_feedback(form)
            if ruta == "/datos":
                mensajes = formulario.aplicar_datos(perfil, form)
                # Volver al CV que estaba a la vista. Sin esto, guardar te devolvía
                # siempre al primero y el que estabas editando quedaba escondido.
                volver = {"cv": form["cv_elegido"]} if form.get("cv_elegido") else {}
                return self._redirigir("/datos", perfil=perfil, ok=_resumen(mensajes),
                                       **volver)
            if ruta == "/configuracion":
                mensajes = formulario.aplicar_configuracion(perfil, form)
                return self._redirigir("/configuracion", perfil=perfil,
                                       ok=_resumen(mensajes))
            if ruta == "/mensajes":
                return self._get_mensajes(perfil, {"url": [form.get("url", "")]},
                                          con_llm=True)
            if ruta == "/consejo":
                return self._get_consejo(perfil, {"url": [form.get("url", "")]},
                                         con_llm=True)
            if ruta == "/buscar":
                return self._post_buscar(form)
            if ruta == "/linkedin-favorito":
                return self._post_linkedin_favorito(form)
            if ruta == "/linkedin-apliques":
                return self._post_linkedin_apliques(form, self.path)
            if ruta == "/revisar-filtro":
                return self._post_revisar_filtro(form)
            if ruta == "/archivar":
                return self._post_archivar(form)
            if ruta == "/archivar-viejas":
                return self._post_archivar_viejas(form)
            if ruta == "/cv-nuevo":
                # Primero se guarda lo que estaba escrito, después se agrega.
                mensajes = formulario.aplicar_datos(perfil, form)
                cv_id = data.agregar_cv(perfil)
                return self._redirigir(
                    "/datos", ancla=f"cv-{cv_id}", perfil=perfil, cv=cv_id,
                    ok=f"{_resumen(mensajes)} Agregué un CV vacío: ponele nombre, qué "
                       "buscar con él y pegá el texto. Mientras esté vacío no cuenta.")
            if ruta == "/cv-borrar":
                # Llega sólo desde la confirmación de "Borrar este CV".
                mensajes = formulario.aplicar_datos(perfil, form)
                borrado = data.borrar_cv(perfil, form.get("cv_borrar", ""))
                if borrado:
                    return self._redirigir(
                        "/datos", ancla="mis-cv", perfil=perfil,
                        ok=f"{_resumen(mensajes)} Borré el CV «{borrado}».")
                return self._redirigir("/datos", ancla="mis-cv", perfil=perfil,
                                       error="Tiene que quedar al menos un CV.")
            if ruta == "/perfil-nuevo":
                nuevo = data.crear_perfil(form.get("nombre", ""))
                return self._redirigir(
                    "/datos", perfil=nuevo,
                    ok=f"Perfil '{nuevo}' creado. Completá el CV y los datos, y guardá.",
                )
            if ruta == "/perfil-borrar":
                return self._post_borrar_perfil(form)
        except (ValueError, FileNotFoundError) as e:
            return self._redirigir(_pantalla_del_post(ruta), perfil=perfil, error=str(e))
        except Exception as e:
            logger.exception("[ui] Error procesando POST %s", self.path)
            return self._redirigir(_pantalla_del_post(ruta), perfil=perfil,
                                   error=f"Algo falló: {e}")

        self._html("<h1>404</h1>", 404)

    def _post_borrar_perfil(self, form: dict) -> None:
        """Llega sólo desde la confirmación de "Borrar este perfil".

        El nombre sale del botón que se apretó y no del campo escondido: es el
        que estaba escrito en la confirmación que la persona leyó.

        Se vuelve a Configuración del primer perfil que quede, porque desde ahí
        se borró. Si no queda ninguno, la misma dirección sin perfil cae en la
        bienvenida.
        """
        nombre = form.get("perfil_borrar", "")
        tarea = data.borrar_perfil(nombre)
        avisos_ = {"ok": f"Borré el perfil «{nombre}» con todo."}
        if tarea == "no-estaba":
            avisos_["ok"] += " No tenía búsqueda programada en esta computadora."
        elif tarea == "fallo":
            avisos_["error"] = (
                f"No pude sacar su búsqueda programada. Abrí el Programador de "
                f"tareas de Windows y borrá «{data.TAREA_PROGRAMADA.format(nombre)}» "
                f"a mano: si queda, va a intentar buscar para un perfil que ya no existe.")
        quedan = data.perfiles()
        if quedan:
            return self._redirigir("/configuracion", perfil=quedan[0], **avisos_)
        return self._redirigir("/configuracion", **avisos_)

    def _post_buscar(self, form: dict) -> None:
        """Buscar ahora, sin esperar al horario programado.

        Corre en un proceso aparte: la búsqueda tarda minutos y el servidor
        atiende de a un pedido, así que hacerla acá adentro dejaría la pantalla
        congelada. Se vuelve enseguida a donde estabas, y cuando entren ofertas
        el vigilante que ya existe avisa solo.
        """
        perfil = form.get("perfil", "")
        arranco, mensaje = corrida.arrancar(perfil)

        # Desde el botón de la barra lateral: vuelve el cartel ya en "buscando"
        # y la página no se mueve. Era una recarga completa para cambiar tres
        # palabras, y encima te devolvía arriba de la lista.
        if self.headers.get("HX-Request"):
            try:
                pendientes = int(form.get("pend", "0"))
            except ValueError:
                pendientes = 0
            return self._html(render.corrida_estado(
                perfil, corrida.progreso(), form.get("marca", ""), pendientes))

        # Sin htmx (el botón grande del estado vacío) sigue el camino de
        # siempre: POST, redirección y GET, que es lo que evita que recargar
        # vuelva a disparar la búsqueda.
        clave = "ok" if arranco else "error"
        return self._redirigir("/trabajos", perfil=perfil, **{clave: mensaje})

    def _post_linkedin_favorito(self, form: dict) -> None:
        """Guardar o sacar una búsqueda de la libreta.

        No lleva toast: el favorito aparece (o desaparece) de la lista de abajo,
        y avisar lo que ya se ve es ruido.
        """
        from vacantia.ui import linkedin_urls

        perfil = form.get("perfil", "")
        url = form.get("url", "").strip()
        volver = {"perfil": perfil, "tab": linkedin_urls.tipo_de(form.get("tab", ""))}

        if form.get("borrar"):
            if not linkedin_urls.borrar_favorito(perfil, url):
                return self._redirigir("/linkedin", **volver,
                                       error="Esa búsqueda ya no estaba guardada.")
            return self._redirigir("/linkedin", **volver)

        paso = linkedin_urls.guardar_favorito(perfil, form.get("nombre", ""), url)
        if paso == "invalida":
            return self._redirigir("/linkedin", **volver,
                                   error="Esa dirección no es una búsqueda de "
                                         "LinkedIn, ni de publicaciones ni de empleos.")
        if paso == "repetida":
            # No es un error de la persona: la búsqueda ya está donde la fue a
            # buscar. Se dice con qué nombre, que es el dato que falta para
            # encontrarla en la lista.
            como = linkedin_urls.guardada_como(perfil, url)
            return self._redirigir("/linkedin", **volver,
                                   ok=f"Esa búsqueda ya estaba guardada, "
                                      f"como «{como}».")
        self._redirigir("/linkedin", **volver)

    #: Lo único que se acepta de vuelta en el `volver` del contador. Ese valor
    #: vuelve del navegador y termina en un header `Location`: se rearma desde
    #: cero con las claves conocidas en vez de reenviarlo tal cual.
    _CLAVES_DEL_ARMADOR = ("perfil", "tab", "puesto", "lugar", "idioma",
                           "sin_junior", "cuando", "orden", "de_quien",
                           # las de Jobs
                           "tambien", "donde", "modalidad", "nivel", "pocos",
                           "sencilla")

    def _post_linkedin_apliques(self, form: dict, camino: str) -> None:
        """Sumar o restar una postulación hecha desde un posteo de LinkedIn.

        No hay ninguna oferta que marcar: estas postulaciones no entraron por el
        scraper y no están en el historial. Por eso se cuentan a mano acá, y por
        eso suman al contador grande de Trabajos, que es el mismo trabajo.

        Son dos pasos: el más y el menos mueven un anotador que todavía no
        cuenta para nada, y *Confirmar* lo pasa al contador de Trabajos y lo
        deja en cero. Un número que sube y nunca vuelve a cero no se puede
        confirmar ni corregir.

        Se vuelve a la misma pantalla con la misma búsqueda armada: anotar no
        puede costarte la dirección que acabás de construir.
        """
        from vacantia.ui import linkedin_urls

        perfil = form.get("perfil", "")
        # Cada pestaña tiene su anotador. La pestaña llega en el campo escondido
        # del constructor, que viaja con el POST de los botones.
        tipo = linkedin_urls.tipo_de(form.get("tab", ""))
        aviso = None
        if form.get("confirmar"):
            cuantas = linkedin_urls.confirmar_pendientes(perfil, tipo)
            if cuantas:
                total = len(linkedin_urls.postulaciones(perfil, tipo))
                una = "postulación" if cuantas == 1 else "postulaciones"
                desde = "búsquedas de empleos" if tipo == "jobs" else "posteos"
                aviso = (f"Sumaste {cuantas} {una} al contador de Trabajos. "
                         f"Van {total} desde {desde} de LinkedIn.")
        elif form.get("menos"):
            linkedin_urls.restar_pendiente(perfil, tipo)
        else:
            linkedin_urls.sumar_pendiente(perfil, tipo)

        crudo = parse_qs(urlparse(camino).query).get("volver", [""])[0]
        vuelta = [(k, v) for k, vs in parse_qs(crudo).items()
                  if k in self._CLAVES_DEL_ARMADOR for v in vs]
        vuelta = vuelta or [("perfil", perfil), ("tab", tipo)]
        # Confirmar es el único de los tres que deja rastro: el más y el menos
        # se ven en el número mismo, y avisar lo que ya se ve es ruido.
        if aviso:
            vuelta.append(("ok", aviso))
        self.send_response(303)
        self.send_header("Location", f"/linkedin?{urlencode(vuelta)}")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _post_revisar_filtro(self, form: dict) -> None:
        """¿El filtro automático acertó con esta oferta, o se equivocó?

        Las tres respuestas la sacan de la pestaña Filtradas. La diferencia es
        que "mal" además la devuelve a Sin marcar, porque si el filtro se
        equivocó la oferta sigue estando y todavía se le puede aplicar.

        "motivo" es la del medio: la oferta no tenía que llegarte, pero el
        filtro la atribuyó mal. Se queda afuera, como "bien", y se anota aparte.
        """
        perfil = form.get("perfil", "")
        url = form.get("url", "").strip()
        revision = form.get("revision", "")
        volver = {"ver": "filtradas", "desde": form.get("desde", "todo"),
                  "p": form.get("p", "1")}

        oferta = data.buscar_oferta(perfil, url) or {}
        titulo = (oferta.get("scored_title") or oferta.get("title") or "")[:70]
        if not data.revisar_filtro(perfil, url, revision):
            return self._redirigir("/trabajos", perfil=perfil, **volver,
                                   error="No encontré esa oferta en el historial.")
        if revision == "mal":
            aviso = (f"«{titulo}» vuelve a Sin marcar." if titulo
                     else "Vuelve a Sin marcar.")
        elif revision == "motivo":
            aviso = (f"Anotado: «{titulo}» estaba bien sacada, con el motivo mal."
                     if titulo else "Anotado: bien sacada, con el motivo mal.")
        else:
            aviso = (f"Bien descartada: «{titulo}»." if titulo
                     else "Bien descartada.")
        self._redirigir("/trabajos", perfil=perfil, **volver, ok=aviso)

    def _post_archivar(self, form: dict) -> None:
        """Una sola oferta: el aviso ya no está, o quedó viejo.

        No pide motivo y no toca `aplicado`: archivar no es descartar. Ver
        `State.archivar`.
        """
        perfil = form.get("perfil", "")
        url = form.get("url", "").strip()
        volver = {"ver": form.get("ver", "pendientes"),
                  "desde": form.get("desde", "todo"), "p": form.get("p", "1")}
        archivar = form.get("archivar", "1") != "0"

        oferta = data.buscar_oferta(perfil, url) or {}
        titulo = (oferta.get("scored_title") or oferta.get("title") or "")[:70]
        if not data.archivar(perfil, [url], archivar):
            return self._redirigir("/trabajos", perfil=perfil, **volver,
                                   error="No encontré esa oferta en el historial.")
        que = "Archivada" if archivar else "De vuelta en la lista"
        self._redirigir("/trabajos", perfil=perfil, **volver,
                        ok=f"{que}: «{titulo}»." if titulo else f"{que}.")

    def _post_archivar_viejas(self, form: dict) -> None:
        """Todas las que pasaron cierta antigüedad, de una."""
        perfil = form.get("perfil", "")
        desde = form.get("desde", "todo")
        try:
            dias = int(form.get("dias", "14"))
        except ValueError:
            dias = 14

        urls = data.viejas_sin_marcar(perfil, dias)
        cuantas = data.archivar(perfil, urls) if urls else 0
        if not cuantas:
            return self._redirigir("/trabajos", perfil=perfil, desde=desde,
                                   ok=f"No había ninguna de más de {dias} días.")
        self._redirigir(
            "/trabajos", perfil=perfil, desde=desde,
            ok=f"Archivadas {cuantas} de más de {dias} días. Están en la pestaña "
               f"Archivadas y se pueden devolver.",
        )

    def _post_feedback(self, form: dict) -> None:
        perfil = form.get("perfil", "")
        ver = form.get("ver", "pendientes")
        # El rango de fechas viaja en el formulario y vuelve en el redirect:
        # sin esto, marcar una oferta te devolvía a la lista completa y había
        # que volver a elegir el filtro después de cada clic.
        desde = form.get("desde", "todo")
        pagina = form.get("p", "1")
        url = form.get("url", "").strip()
        aplicado = form.get("aplicado") == "si"
        motivo = form.get("motivo", "").strip()
        # Cuál de los motivos del desplegable. Se valida contra el catálogo:
        # lo que venga de afuera no decide qué se guarda.
        claves = {c for c, _, _ in data.MOTIVOS}
        motivo_clave = form.get("motivo_clave", "").strip()
        motivo_clave = motivo_clave if motivo_clave in claves else ""

        # Alcanza con cualquiera de los dos: un motivo del desplegable, o texto
        # libre. El campo de texto está siempre a la vista y es opcional.
        if not aplicado and not motivo and not motivo_clave:
            return self._redirigir(
                "/trabajos", perfil=perfil, ver=ver, desde=desde, p=pagina,
                error="Para descartar una oferta, elegí un motivo o escribilo.",
            )
        # El título se busca ANTES de guardar, para poder nombrarla en el aviso:
        # "Guardado." no alcanza cuando hay dos ofertas de 90 pegadas y no se
        # ve cuál desapareció de la lista.
        oferta = data.buscar_oferta(perfil, url) or {}
        titulo = (oferta.get("scored_title") or oferta.get("title") or "")[:70]

        ok = data.guardar_feedback(perfil, url, aplicado, motivo, motivo_clave)
        if ok:
            que = "Aplicaste a" if aplicado else "Descartaste"
            aviso = f"{que} «{titulo}»." if titulo else "Guardado."
            self._redirigir("/trabajos", perfil=perfil, ver=ver, desde=desde, p=pagina,
                            ok=aviso)
        else:
            self._redirigir("/trabajos", perfil=perfil, ver=ver, desde=desde, p=pagina,
                            error="No encontré esa oferta en el historial.")

    # --- ruido ----------------------------------------------------------

    #: Lo que no se anota en el registro aunque se pida mil veces.
    #:
    #: El cartel de la corrida pregunta cada 2 segundos mientras busca. Sin
    #: esto son 1800 líneas por hora y por pestaña abierta, en el mismo archivo
    #: del que sale el panel "Cómo viene funcionando": el registro se infla y
    #: encontrar un error de verdad ahí adentro se vuelve imposible.
    _SIN_REGISTRAR = ("/corrida", "/estilos.css", "/app.js", "/htmx.min.js")

    def log_message(self, formato, *args):
        """Al log del proyecto, no a stderr: con pythonw no hay consola."""
        linea = formato % args
        if any(f" {ruta}" in linea for ruta in self._SIN_REGISTRAR):
            return
        logger.debug("[ui] " + linea)


def _mensajes(params: dict) -> list[tuple[str, str]]:
    """Los carteles viajan por querystring porque después de un POST se
    redirige (patrón POST-redirect-GET: si no, recargar reenvía el formulario)."""
    salida = []
    for clase, clave in (("ok", "ok"), ("error", "error")):
        for texto in params.get(clave, []):
            if texto:
                salida.append((clase, texto))
    return salida


def _pantalla_del_post(ruta: str) -> str:
    """Adónde vuelve un POST que falló: a la pantalla del formulario que lo mandó.

    Crear y borrar perfiles viven en Configuración. Volver a Mi perfil con el
    error de un nombre inválido mostraba el cartel lejos del campo que había que
    corregir.
    """
    if ruta in ("/configuracion", "/perfil-nuevo", "/perfil-borrar"):
        return "/configuracion"
    return "/datos"


def _resumen(mensajes: list[tuple[str, str]]) -> str:
    return " ".join(t for _, t in mensajes) or "Guardado."


def serve(puerto: int = PUERTO, abrir: bool = True) -> None:
    servidor = ThreadingHTTPServer((HOST, puerto), Handler)
    url = f"http://localhost:{puerto}"
    logger.info(f"[ui] Servidor local en {url}  (Ctrl+C para cortar)")
    if abrir:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        logger.info("[ui] Cerrado.")
    finally:
        servidor.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m vacantia.ui", description="La pantalla local de vacantia."
    )
    parser.add_argument("--port", "-p", type=int, default=PUERTO)
    parser.add_argument("--sin-navegador", action="store_true",
                        help="No abrir el navegador solo.")
    args = parser.parse_args(argv)
    try:
        serve(args.port, abrir=not args.sin_navegador)
    except OSError as e:
        logger.error(
            f"No pude levantar el servidor en el puerto {args.port}: {e}\n"
            "Puede que ya esté abierto en otra ventana: probá entrar a "
            f"http://localhost:{args.port}"
        )
        return 1
    return 0


__all__ = ["serve", "main", "Handler", "PUERTO"]
