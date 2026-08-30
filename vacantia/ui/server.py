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
from vacantia.ui import data, formulario, render

logger = get_logger()

PUERTO = 8756
HOST = "127.0.0.1"


class Handler(BaseHTTPRequestHandler):
    server_version = "vacantia"

    # --- utilidades -----------------------------------------------------

    def _responder(self, cuerpo: bytes, tipo="text/html; charset=utf-8", codigo=200,
                   extra: dict | None = None) -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        for clave, valor in (extra or {}).items():
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
        self._html(render.pagina(titulo, cuerpo, perfil, data.perfiles(), tab), codigo)

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

        perfil = self._perfil_pedido(params)
        if perfil is None:
            return self._sin_perfiles()

        try:
            if ruta == "/trabajos":
                return self._get_trabajos(perfil, params)
            if ruta == "/datos":
                return self._get_datos(perfil, params)
            if ruta == "/cv.pdf":
                return self._get_cv_pdf(perfil)
        except FileNotFoundError as e:
            return self._pagina("Error", render.avisos([("error", str(e))]), perfil,
                                "trabajos", 404)
        except Exception as e:          # que un bug no deje la página en blanco
            logger.exception("[ui] Error sirviendo GET %s", self.path)
            return self._pagina("Error", render.avisos([("error", f"Algo falló: {e}")]),
                                perfil, "trabajos", 500)

        self._html("<h1>404</h1>", 404)

    def _get_trabajos(self, perfil: str, params: dict) -> None:
        ver = (params.get("ver") or ["pendientes"])[0]
        if ver not in dict(render.FILTROS):
            ver = "pendientes"
        mensajes = _mensajes(params)
        cuerpo = render.trabajos(
            perfil, data.ofertas(perfil, ver), data.contar_ofertas(perfil), ver, mensajes
        )
        self._pagina("Trabajos", cuerpo, perfil, "trabajos")

    def _get_cv_pdf(self, perfil: str) -> None:
        """El CV en PDF, como descarga. Si algo falla, se vuelve a Trabajos con
        el motivo escrito: un navegador mostrando un PDF roto no explica nada."""
        from vacantia import pdf as pdf_mod

        datos = data.leer_perfil(perfil)
        cv = data.leer_cv(datos)
        if not cv.strip():
            return self._redirigir(
                "/trabajos", perfil=perfil,
                error="Todavía no cargaste el CV. Está en la pestaña Mis datos.",
            )
        try:
            contenido = pdf_mod.cv_a_pdf(cv, f"CV {perfil}")
        except ImportError:
            return self._redirigir(
                "/trabajos", perfil=perfil,
                error="Falta la librería fpdf2. Volvé a correr instalar.bat.",
            )
        nombre = pdf_mod.nombre_archivo(perfil)
        self._responder(contenido, tipo="application/pdf",
                        extra={"Content-Disposition": f'attachment; filename="{nombre}"'})

    def _get_datos(self, perfil: str, params: dict) -> None:
        cuerpo = formulario.render(perfil, data.leer_perfil(perfil), _mensajes(params))
        self._pagina("Mis datos", cuerpo, perfil, "datos")

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

    def _post_feedback(self, form: dict) -> None:
        perfil = form.get("perfil", "")
        ver = form.get("ver", "pendientes")
        url = form.get("url", "").strip()
        aplicado = form.get("aplicado") == "si"
        motivo = form.get("motivo", "").strip()

        if not aplicado and not motivo:
            return self._redirigir(
                "/trabajos", perfil=perfil, ver=ver,
                error="Para descartar una oferta hace falta escribir el motivo.",
            )
        ok = data.guardar_feedback(perfil, url, aplicado, motivo)
        if ok:
            self._redirigir("/trabajos", perfil=perfil, ver=ver,
                            ok="Guardado." if aplicado else "Guardado con el motivo.")
        else:
            self._redirigir("/trabajos", perfil=perfil, ver=ver,
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
