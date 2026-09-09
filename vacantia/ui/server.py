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

    def _redirigir(self, ruta: str, **params) -> None:
        destino = f"{ruta}?{urlencode(params)}" if params else ruta
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

    def _sin_perfiles(self) -> None:
        """Instalación recién estrenada: no hay a quién mostrarle nada."""
        cuerpo = formulario.render_sin_perfiles()
        self._html(render.pagina("Empezar", cuerpo, "", [], "datos"))

    # --- GET ------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802  (lo impone BaseHTTPRequestHandler)
        url = urlparse(self.path)
        params = parse_qs(url.query)
        ruta = url.path.rstrip("/") or "/"

        if ruta == "/":
            return self._redirigir("/trabajos")
        if ruta.startswith("/fuentes/"):
            return self._get_fuente(ruta)

        perfil = self._perfil_pedido(params)
        if perfil is None:
            return self._sin_perfiles()

        try:
            if ruta == "/trabajos":
                return self._get_trabajos(perfil, params)
            if ruta == "/datos":
                return self._get_datos(perfil, params)
            if ruta == "/mensajes":
                return self._get_mensajes(perfil, params)
            if ruta == "/consejo":
                return self._get_consejo(perfil, params)
            if ruta == "/estadisticas":
                return self._estadisticas(perfil, params)
            if ruta == "/linkedin":
                return self._get_linkedin(perfil, params)
            if ruta == "/novedades":
                return self._get_novedades(perfil)
        except FileNotFoundError as e:
            return self._pagina("Error", render.avisos([("error", str(e))]), perfil,
                                "trabajos", 404)
        except Exception as e:          # que un bug no deje la página en blanco
            logger.exception("[ui] Error sirviendo GET %s", self.path)
            return self._pagina("Error", render.avisos([("error", f"Algo falló: {e}")]),
                                perfil, "trabajos", 500)

        self._html("<h1>404</h1>", 404)

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
        cuerpo = render.trabajos(
            perfil, ofertas, data.contar_ofertas(perfil, desde),
            ver, mensajes, desde,
            conteo_fecha=data.contar_por_fecha(perfil, ver),
            marca=data.marca_de_cambio(perfil),
            pagina=pagina, paginas=paginas,
            viejas={d: len(data.viejas_sin_marcar(perfil, d)) for d in (7, 14, 30)},
            corriendo=corrida.esta_corriendo(),
        )
        self._pagina("Trabajos", cuerpo, perfil, "trabajos")

    def _get_novedades(self, perfil: str) -> None:
        """¿Entraron ofertas desde que se abrió la página? JSON, para el poll.

        Deliberadamente NO recarga la pantalla sola: si alguien está escribiendo
        el motivo de un descarte, una recarga se lo borra. Se avisa y decide la
        persona.
        """
        import json as _json

        cuerpo = _json.dumps({
            "marca": data.marca_de_cambio(perfil),
            "pendientes": data.contar_ofertas(perfil).get("pendientes", 0),
        }).encode("utf-8")
        self._responder(cuerpo, tipo="application/json")

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
        cuerpo = render.mensajes(perfil, oferta, textos, escrito, avisos_)
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
        cv = data.leer_cv(datos)
        faltantes = consejo_mod.faltan_en_el_cv(job, cv)

        texto, escrito = "", False
        avisos_: list[tuple[str, str]] = []
        if con_llm:
            texto, escrito = data.consejo_con_llm(perfil, job)
            if not escrito:
                avisos_.append(("error", "No pude usar el modelo — te queda igual "
                                         "la lista de palabras que faltan."))
        cuerpo = render.consejo(perfil, oferta, faltantes, texto, escrito, avisos_)
        self._pagina("Consejo", cuerpo, perfil, "trabajos")

    def _get_datos(self, perfil: str, params: dict) -> None:
        cuerpo = formulario.render(perfil, data.leer_perfil(perfil), _mensajes(params))
        self._pagina("Mi perfil", cuerpo, perfil, "datos")

    def _estadisticas(self, perfil: str, params: dict) -> None:
        """Los contadores que antes competían con la lista por el mismo lugar."""
        desde = (params.get("desde") or ["todo"])[0]
        if desde not in data.RANGOS:
            desde = "todo"
        cuerpo = render.estadisticas(perfil, data.estadisticas(perfil, desde),
                                     desde, _mensajes(params),
                                     salud=corrida.salud())
        self._pagina("Métricas", cuerpo, perfil, "estadisticas")

    def _get_linkedin(self, perfil: str, params: dict) -> None:
        """Las direcciones de búsqueda de LinkedIn, en dos pestañas.

        Jobs es la que se abre por defecto: es la que cubre el hueco más grande,
        los avisos publicados hoy que ningún buscador indexó todavía.
        """
        tab = (params.get("tab") or ["jobs"])[0]
        cuerpo = render.linkedin(perfil, tab, _mensajes(params))
        self._pagina("LinkedIn URLs", cuerpo, perfil, "linkedin")

    # --- POST -----------------------------------------------------------

    def do_POST(self) -> None:  # noqa: N802
        ruta = urlparse(self.path).path.rstrip("/") or "/"
        form = self._form()
        perfil = form.get("perfil", "")

        try:
            if ruta == "/feedback":
                return self._post_feedback(form)
            if ruta == "/datos":
                mensajes = formulario.aplicar(perfil, form)
                return self._redirigir("/datos", perfil=perfil, ok=_resumen(mensajes))
            if ruta == "/mensajes":
                return self._get_mensajes(perfil, {"url": [form.get("url", "")]},
                                          con_llm=True)
            if ruta == "/consejo":
                return self._get_consejo(perfil, {"url": [form.get("url", "")]},
                                         con_llm=True)
            if ruta == "/buscar":
                return self._post_buscar(form)
            if ruta == "/archivar":
                return self._post_archivar(form)
            if ruta == "/archivar-viejas":
                return self._post_archivar_viejas(form)
            if ruta == "/perfil-nuevo":
                nuevo = data.crear_perfil(form.get("nombre", ""))
                return self._redirigir(
                    "/datos", perfil=nuevo,
                    ok=f"Perfil '{nuevo}' creado. Completá el CV y los datos, y guardá.",
                )
        except (ValueError, FileNotFoundError) as e:
            return self._redirigir("/datos", perfil=perfil, error=str(e))
        except Exception as e:
            logger.exception("[ui] Error procesando POST %s", self.path)
            return self._redirigir("/datos", perfil=perfil, error=f"Algo falló: {e}")

        self._html("<h1>404</h1>", 404)

    def _post_buscar(self, form: dict) -> None:
        """Buscar ahora, sin esperar al horario programado.

        Corre en un proceso aparte: la búsqueda tarda minutos y el servidor
        atiende de a un pedido, así que hacerla acá adentro dejaría la pantalla
        congelada. Se vuelve enseguida a donde estabas, y cuando entren ofertas
        el vigilante que ya existe avisa solo.
        """
        perfil = form.get("perfil", "")
        arranco, mensaje = corrida.arrancar(perfil)
        clave = "ok" if arranco else "error"
        return self._redirigir("/trabajos", perfil=perfil, **{clave: mensaje})

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

    def log_message(self, formato, *args):
        """Al log del proyecto, no a stderr: con pythonw no hay consola."""
        logger.debug("[ui] " + formato % args)


def _mensajes(params: dict) -> list[tuple[str, str]]:
    """Los carteles viajan por querystring porque después de un POST se
    redirige (patrón POST-redirect-GET: si no, recargar reenvía el formulario)."""
    salida = []
    for clase, clave in (("ok", "ok"), ("error", "error")):
        for texto in params.get(clave, []):
            if texto:
                salida.append((clase, texto))
    return salida


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
