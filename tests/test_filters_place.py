"""Regla de Bahía Blanca: ubicación y modalidad evaluadas juntas.

Las tres ideas que la definen:

- el país filtra siempre, también al remoto (Argentina es enorme y el remoto de
  Buenos Aires suele ser para todo el país; el de México, sólo para México);
- la ciudad filtra sólo presencial e híbrido;
- presencial en las ciudades de uno entra aunque el perfil pida sólo remoto.
"""

from vacantia.filters import apply_filters, home_cities, passes_place
from vacantia.models import Job

# El perfil de Isaías: busca en Argentina, va en persona sólo a Bahía Blanca.
BB = {"country": "Argentina", "city": "Bahía Blanca"}
SOLO_REMOTO = ["remote"]


def job(**kw) -> Job:
    base = dict(url="https://x.com/jobs/1", title="Data Scientist", company="ACME")
    return Job(**{**base, **kw})


# --- el país filtra siempre -------------------------------------------------

def test_un_remoto_argentino_entra():
    j = job(work_mode="remote", city="Buenos Aires", country="Argentina")
    ok, why, _ = passes_place(j, BB, SOLO_REMOTO)
    assert ok, why


def test_un_remoto_de_otro_pais_se_descarta():
    """Un remoto de México suele ser remoto PARA México: por cuestiones legales
    de contratación no toman a alguien de Argentina."""
    j = job(work_mode="remote", city="CDMX", country="Mexico")
    ok, why, etiqueta = passes_place(j, BB, SOLO_REMOTO)
    assert not ok and etiqueta == "location" and "Mexico" in why


def test_un_remoto_que_no_dice_de_donde_es_pasa():
    """Lo que el aviso no dice, no filtra."""
    j = job(work_mode="remote", country="")
    assert passes_place(j, BB, SOLO_REMOTO)[0]


def test_con_el_pais_vacio_entra_el_remoto_del_mundo():
    """País vacío en el perfil = worldwide."""
    cfg = {"country": "", "city": "Bahía Blanca"}
    j = job(work_mode="remote", city="Madrid", country="España")
    assert passes_place(j, cfg, SOLO_REMOTO)[0]


def test_remote_anywhere_vuelve_al_comportamiento_viejo():
    cfg = {**BB, "remote_anywhere": True}
    j = job(work_mode="remote", city="Madrid", country="España")
    assert passes_place(j, cfg, SOLO_REMOTO)[0]


def test_el_pais_tambien_filtra_al_presencial():
    j = job(work_mode="onsite", city="Madrid", country="España")
    ok, _, etiqueta = passes_place(j, BB, ["remote", "onsite"])
    assert not ok and etiqueta == "location"


# --- la ciudad filtra sólo lo presencial ------------------------------------

def test_un_remoto_de_otra_ciudad_del_pais_entra():
    """Es el caso que más importa: Buenos Aires y Córdoba publican remoto para
    todo el país. Descartarlo por ciudad sería perder la mayoría de las buenas."""
    j = job(work_mode="remote", city="Córdoba", country="Argentina")
    assert passes_place(j, BB, SOLO_REMOTO)[0]


def test_presencial_en_la_ciudad_de_uno_entra_aunque_pidan_solo_remoto():
    j = job(work_mode="onsite", city="Bahía Blanca", country="Argentina")
    ok, why, _ = passes_place(j, BB, SOLO_REMOTO)
    assert ok, why


def test_hibrido_en_la_ciudad_de_uno_tambien_entra():
    j = job(work_mode="hybrid", city="Bahia Blanca", country="Argentina")
    assert passes_place(j, BB, SOLO_REMOTO)[0]


def test_presencial_en_otra_ciudad_se_descarta():
    j = job(work_mode="onsite", city="Buenos Aires", country="Argentina")
    ok, _, etiqueta = passes_place(j, BB, SOLO_REMOTO)
    assert not ok and etiqueta == "work_mode"


def test_presencial_en_otra_ciudad_se_descarta_aunque_acepte_presencial():
    """Con work_modes abierto, lo que lo frena es la ciudad."""
    j = job(work_mode="onsite", city="Rosario", country="Argentina")
    ok, why, etiqueta = passes_place(j, BB, [])
    assert not ok and etiqueta == "location" and "Rosario" in why


def test_presencial_sin_ciudad_en_el_aviso_no_se_asume_local():
    """Si el aviso no dice la ciudad no se supone que sea la de uno: si no, todo
    presencial sin ciudad entraría como local."""
    j = job(work_mode="onsite", city="", country="Argentina")
    assert not passes_place(j, BB, SOLO_REMOTO)[0]


def test_varias_ciudades_para_quien_se_mueve_por_el_conurbano():
    cfg = {"country": "Argentina", "city": ["La Plata", "Buenos Aires", "CABA"]}
    assert passes_place(job(work_mode="onsite", city="La Plata",
                            country="Argentina"), cfg, SOLO_REMOTO)[0]
    assert passes_place(job(work_mode="hybrid", city="CABA",
                            country="Argentina"), cfg, SOLO_REMOTO)[0]
    assert not passes_place(job(work_mode="onsite", city="Mendoza",
                                country="Argentina"), cfg, SOLO_REMOTO)[0]


def test_sin_ciudad_cargada_el_presencial_del_pais_depende_de_work_modes():
    cfg = {"country": "Argentina", "city": ""}
    j = job(work_mode="onsite", city="Mendoza", country="Argentina")
    assert not passes_place(j, cfg, SOLO_REMOTO)[0]      # no acepta presencial
    assert passes_place(j, cfg, ["remote", "onsite"])[0]  # sí lo acepta


# --- modalidad --------------------------------------------------------------

def test_remoto_se_descarta_si_el_perfil_no_quiere_remoto():
    j = job(work_mode="remote", country="Argentina")
    ok, _, etiqueta = passes_place(j, BB, ["onsite"])
    assert not ok and etiqueta == "work_mode"


def test_lo_que_no_aclara_la_modalidad_pasa_si_el_pais_da():
    j = job(work_mode="", city="Rosario", country="Argentina")
    assert passes_place(j, BB, SOLO_REMOTO)[0]


def test_lo_que_no_aclara_la_modalidad_igual_filtra_por_pais():
    j = job(work_mode="", city="Madrid", country="España")
    ok, _, etiqueta = passes_place(j, BB, SOLO_REMOTO)
    assert not ok and etiqueta == "location"


# --- compatibilidad y armado ------------------------------------------------

def test_home_city_sigue_andando_en_los_perfiles_viejos():
    cfg = {"country": "Argentina", "city": "", "home_city": "Bahía Blanca"}
    assert home_cities(cfg) == ["Bahía Blanca"]
    j = job(work_mode="onsite", city="Bahía Blanca", country="Argentina")
    assert passes_place(j, cfg, SOLO_REMOTO)[0]


def test_city_le_gana_a_home_city_cuando_estan_las_dos():
    cfg = {"city": "La Plata", "home_city": "Bahía Blanca"}
    assert home_cities(cfg) == ["La Plata"]


def test_apply_filters_cuenta_bien_lo_que_deja_pasar():
    perfil = {"filters": {"location": BB, "work_modes": SOLO_REMOTO}}
    jobs = [
        job(url="https://x.com/1", work_mode="onsite", city="Bahía Blanca", country="Argentina"),
        job(url="https://x.com/2", work_mode="remote", city="Córdoba", country="Argentina"),
        job(url="https://x.com/3", work_mode="remote", city="Bogotá", country="Colombia"),
        job(url="https://x.com/4", work_mode="onsite", city="Rosario", country="Argentina"),
    ]
    kept, stats = apply_filters(jobs, perfil)
    assert [j.url for j in kept] == ["https://x.com/1", "https://x.com/2"]
    assert stats.by_reason["location"] == 1 and stats.by_reason["work_mode"] == 1
