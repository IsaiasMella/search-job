"""Reparto de horarios entre los perfiles de una misma instalación.

Los límites del plan gratis son de la cuenta, no del perfil: si dos personas de
la misma casa arrancan a la misma hora, se pisan contra el tope por minuto.
"""

import pytest

from vacantia import agenda


def test_el_primer_perfil_usa_los_horarios_decididos():
    assert agenda.horarios_de(0) == ["12:00", "16:30", "23:59"]


def test_cada_perfil_arranca_despues_del_anterior():
    assert agenda.horarios_de(1) == ["12:20", "16:50", "00:19"]
    assert agenda.horarios_de(2) == ["12:40", "17:10", "00:39"]


def test_la_corrida_de_medianoche_da_la_vuelta_al_dia():
    """23:59 + 20 minutos es 00:19 del día siguiente, no 24:19."""
    assert agenda.horarios_de(1)[2] == "00:19"
    assert agenda.horarios_de(6)[2] == "01:59"


def test_ningun_perfil_comparte_horario_con_otro():
    reparto = agenda.plan([f"persona{i}" for i in range(6)])
    horas = [h for horarios in reparto.values() for h in horarios]
    assert len(horas) == len(set(horas))


def test_el_orden_es_alfabetico_y_no_el_del_disco():
    """Así agregar un perfil no le cambia el horario a media familia."""
    reparto = agenda.plan(["zoe", "ana", "mario"])
    assert reparto["ana"] == agenda.horarios_de(0)
    assert reparto["mario"] == agenda.horarios_de(1)
    assert reparto["zoe"] == agenda.horarios_de(2)


def test_con_seis_perfiles_el_ultimo_sigue_entrando_en_el_dia():
    reparto = agenda.plan([f"p{i}" for i in range(6)])
    primera = reparto["p0"][0]
    ultima = reparto["p5"][0]
    assert primera == "12:00" and ultima == "13:40"


def test_sin_perfiles_no_explota():
    assert agenda.plan([]) == {}
    assert "No hay perfiles" in agenda.texto([])


def test_el_texto_lista_a_cada_uno_con_sus_horas():
    salida = agenda.texto(["ana", "mario"])
    assert "ana" in salida and "12:00" in salida
    assert "mario" in salida and "12:20" in salida


@pytest.mark.parametrize("hora,minutos,esperado", [
    ("12:00", 0, "12:00"),
    ("23:50", 20, "00:10"),
    ("00:00", 1440, "00:00"),
])
def test_la_suma_de_minutos_no_se_pasa_de_las_24(hora, minutos, esperado):
    assert agenda._mas_minutos(hora, minutos) == esperado
