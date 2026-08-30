"""Regla de Bahía Blanca: ubicación y modalidad evaluadas juntas.

Remoto en cualquier lado, o presencial/híbrido en la ciudad del perfil.
"""

from vacantia.filters import apply_filters, passes_place
from vacantia.models import Job

BB = {"country": "Argentina", "city": "", "home_city": "Bahía Blanca"}
SOLO_REMOTO = ["remote"]


def job(**kw) -> Job:
    base = dict(url="https://x.com/jobs/1", title="Data Scientist", company="ACME")
    return Job(**{**base, **kw})


def test_presencial_en_la_ciudad_del_perfil_entra_aunque_pidan_solo_remoto():
    j = job(work_mode="onsite", city="Bahía Blanca", country="Argentina")
    ok, why, _ = passes_place(j, BB, SOLO_REMOTO)
    assert ok, why


def test_hibrido_en_la_ciudad_del_perfil_tambien_entra():
    j = job(work_mode="hybrid", city="Bahia Blanca", country="Argentina")
    assert passes_place(j, BB, SOLO_REMOTO)[0]


def test_presencial_en_otra_ciudad_se_descarta():
    j = job(work_mode="onsite", city="Buenos Aires", country="Argentina")
    ok, why, etiqueta = passes_place(j, BB, SOLO_REMOTO)
    assert not ok and etiqueta == "work_mode"


def test_presencial_sin_ciudad_en_el_aviso_no_se_asume_local():
    """Si el aviso no dice la ciudad, no se supone que sea la de uno: si no,
    todo presencial sin ciudad entraría como local."""
    j = job(work_mode="onsite", city="", country="Argentina")
    assert not passes_place(j, BB, SOLO_REMOTO)[0]


def test_remoto_en_otro_pais_pasa():
    """Remoto en cualquier lado: la ubicación no filtra."""
    j = job(work_mode="remote", city="Madrid", country="España")
    assert passes_place(j, BB, SOLO_REMOTO)[0]


def test_remote_anywhere_false_vuelve_a_filtrar_por_pais():
    cfg = {**BB, "remote_anywhere": False}
    j = job(work_mode="remote", city="Madrid", country="España")
    ok, why, etiqueta = passes_place(j, cfg, SOLO_REMOTO)
    assert not ok and etiqueta == "location"


def test_remoto_se_descarta_si_el_perfil_no_quiere_remoto():
    j = job(work_mode="remote", country="Argentina")
    ok, _, etiqueta = passes_place(j, BB, ["onsite"])
    assert not ok and etiqueta == "work_mode"


def test_sin_home_city_se_comporta_como_antes():
    cfg = {"country": "Argentina", "city": ""}
    j = job(work_mode="onsite", city="Bahía Blanca", country="Argentina")
    assert not passes_place(j, cfg, SOLO_REMOTO)[0]


def test_city_sola_alcanza_como_ciudad_del_perfil():
    cfg = {"country": "Argentina", "city": "Bahía Blanca"}
    j = job(work_mode="onsite", city="Bahía Blanca", country="Argentina")
    assert passes_place(j, cfg, SOLO_REMOTO)[0]


def test_presencial_local_pero_en_otro_pais_se_descarta():
    """Homónimos: 'Córdoba' está en Argentina y en España."""
    cfg = {"country": "Argentina", "home_city": "Córdoba"}
    j = job(work_mode="onsite", city="Córdoba", country="España")
    assert not passes_place(j, cfg, SOLO_REMOTO)[0]


def test_modalidad_sin_dato_sigue_pasando():
    """Lo que el aviso no dice, no filtra."""
    j = job(work_mode="", city="", country="Argentina")
    assert passes_place(j, BB, SOLO_REMOTO)[0]


def test_apply_filters_cuenta_la_local_como_aceptada():
    perfil = {"filters": {"location": BB, "work_modes": SOLO_REMOTO}}
    jobs = [
        job(url="https://x.com/1", work_mode="onsite", city="Bahía Blanca", country="Argentina"),
        job(url="https://x.com/2", work_mode="onsite", city="Rosario", country="Argentina"),
    ]
    kept, stats = apply_filters(jobs, perfil)
    assert [j.url for j in kept] == ["https://x.com/1"]
    assert stats.dropped == 1 and stats.by_reason["work_mode"] == 1
