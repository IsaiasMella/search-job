"""Los mensajes para el reclutador.

Están calcados de los que Isaías mandó de verdad y con los que lo contactaron,
así que estos tests fijan ESA forma. Antes el módulo imponía "máximo 4 líneas",
que era una opinión de quien lo escribió y no lo que funciona en la práctica.
"""

from datetime import date

from vacantia import mensajes
from vacantia.models import Job

PERFIL = {
    "candidate": {"name": "Isaías Mella", "profile": "AI Engineer"},
    "llm": {},
}
JOB = Job(url="https://x.com/1", title="AI Agent Engineer", company="Jazmín Pérez",
          description="Buscamos AI Agent Engineer con Python, LangChain y LLMs.")

LUNES = date(2026, 9, 7)
MIERCOLES = date(2026, 9, 9)
VIERNES = date(2026, 9, 11)
SABADO = date(2026, 9, 12)


# --- el cierre según el día ------------------------------------------------

def test_el_cierre_cambia_con_el_dia_de_la_semana():
    """Es lo que Isaías escribe a mano según cuándo manda el mensaje."""
    assert mensajes.cierre_del_dia(LUNES) == "buen comienzo de semana"
    assert mensajes.cierre_del_dia(MIERCOLES) == "buen transcurso de semana"
    assert mensajes.cierre_del_dia(VIERNES) == "buen último sprint de la semana"
    assert mensajes.cierre_del_dia(SABADO) == "buen fin de semana"


def test_el_cierre_lo_calcula_el_codigo_y_no_el_modelo(monkeypatch):
    """Un modelo no sabe qué día es hoy: lo inventa y queda mal.

    Por eso el cierre se resuelve antes y se le pasa hecho dentro del prompt.
    """
    capturado = {}
    monkeypatch.setattr(mensajes, "has_llm_credentials", lambda cfg: True)
    monkeypatch.setattr(mensajes, "chat_with_llm",
                        lambda cfg, messages, **k: capturado.setdefault(
                            "p", messages[0]["content"]) and "ok")
    mensajes.generar(JOB, "CV", PERFIL, "dm", hoy=LUNES)
    assert "cierre: buen comienzo de semana" in capturado["p"]


# --- la forma del mensaje --------------------------------------------------

def test_el_dm_tiene_la_lista_de_requisitos_con_tildes():
    """Es el corazón del mensaje: se ve de un vistazo que el candidato encaja."""
    texto = mensajes.molde(JOB, PERFIL, "dm", hoy=MIERCOLES)
    assert texto.count("✔️") >= 3
    assert "cumplo con los requisitos" in texto


def test_el_dm_trae_a_quien_escribirle_el_puesto_y_como_te_presentas():
    texto = mensajes.molde(JOB, PERFIL, "dm", hoy=MIERCOLES)
    assert "Hola Jazmín!!" in texto
    assert "AI Agent Engineer" in texto          # el puesto del aviso
    assert "soy AI Engineer" in texto            # cómo se presenta el candidato
    assert "buen transcurso de semana" in texto


def test_usa_el_nombre_de_pila_y_no_el_apellido():
    """En un DM, "Hola Jazmín Pérez" suena a formulario."""
    texto = mensajes.molde(JOB, PERFIL, "dm")
    assert "Jazmín Pérez" not in texto


def test_sin_saber_quien_publico_no_queda_un_hueco_raro():
    anonimo = Job(url="https://x.com/2", title="Data Scientist", company="")
    texto = mensajes.molde(anonimo, PERFIL, "dm")
    assert "quién publicó" in texto or "nombre de quien" in texto


def test_el_mail_lleva_asunto():
    texto = mensajes.molde(JOB, PERFIL, "mail", hoy=MIERCOLES)
    assert texto.startswith("Asunto: AI Agent Engineer - Isaías Mella")
    assert "CV adjunto" in texto


# --- cuando el modelo no está ----------------------------------------------

def test_los_huecos_que_completa_el_modelo_quedan_marcados():
    """Sin credenciales el molde sale con las llaves puestas: deja claro qué
    falta, que es mejor que un mensaje genérico disfrazado de escrito a mano."""
    texto, con_modelo = mensajes.generar(JOB, "CV", PERFIL, "dm")
    assert con_modelo is False
    assert "{" in texto and "}" in texto


def test_si_el_modelo_falla_devuelve_el_molde(monkeypatch):
    monkeypatch.setattr(mensajes, "has_llm_credentials", lambda cfg: True)

    def explota(*a, **k):
        raise RuntimeError("sin cuota")

    monkeypatch.setattr(mensajes, "chat_with_llm", explota)
    texto, con_modelo = mensajes.generar(JOB, "CV", PERFIL, "dm")
    assert con_modelo is False and "Jazmín" in texto


def test_usa_el_modelo_cuando_hay_credenciales(monkeypatch):
    monkeypatch.setattr(mensajes, "has_llm_credentials", lambda cfg: True)
    monkeypatch.setattr(mensajes, "chat_with_llm",
                        lambda cfg, **k: "Hola Jazmín!!")
    texto, con_modelo = mensajes.generar(JOB, "CV", PERFIL, "dm")
    assert con_modelo is True and texto == "Hola Jazmín!!"


# --- el prompt --------------------------------------------------------------

def test_el_prompt_prohibe_listar_lo_que_el_cv_no_dice(monkeypatch):
    """La regla que más importa: un requisito inventado se cae en la primera
    entrevista y quema el contacto."""
    capturado = {}
    monkeypatch.setattr(mensajes, "has_llm_credentials", lambda cfg: True)
    monkeypatch.setattr(mensajes, "chat_with_llm",
                        lambda cfg, messages, **k: capturado.setdefault(
                            "p", messages[0]["content"]) and "ok")
    mensajes.generar(JOB, "CV con Python y LangChain", PERFIL, "mail")
    prompt = capturado["p"]

    assert "Prohibido listar algo que el CV no diga" in prompt
    assert "Cero adjetivos" in prompt
    assert "Buscamos AI Agent Engineer" in prompt      # el aviso
    assert "CV con Python y LangChain" in prompt       # el CV


def test_el_prompt_le_dice_al_modelo_que_es_lo_que_NO_hace(monkeypatch):
    """El caso real: el CV decía "entrené un modelo de IA" cuando en verdad era
    un RAG, y el mensaje salió ofreciendo Machine Learning.

    Conectar modelos ya entrenados a un producto y entrenarlos son dos oficios
    distintos, y en la entrevista se nota en la primera pregunta. Con el CV
    corregido alcanzaría, pero el `not_suitable` del perfil es la red: dice qué
    no hay que ofrecer aunque el CV mencione algo que suene parecido.
    """
    capturado = {}
    perfil = {
        "candidate": {"name": "Isaías", "headline": "AI Engineer",
                      "not_suitable": "NO entrena modelos ni arma redes neuronales."},
        "llm": {},
    }
    monkeypatch.setattr(mensajes, "has_llm_credentials", lambda cfg: True)
    monkeypatch.setattr(mensajes, "chat_with_llm",
                        lambda cfg, messages, **k: capturado.setdefault(
                            "p", messages[0]["content"]) and "ok")
    mensajes.generar(JOB, "CV con Python", perfil, "dm")
    prompt = capturado["p"]

    assert "LO QUE NO HACE" in prompt
    assert "NO entrena modelos ni arma redes neuronales." in prompt
    assert "NO hace Machine Learning" in prompt        # el ejemplo, en las reglas
