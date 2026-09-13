"""Cada perfil con su propio archivo de empresas.

Isaías y papá compartían `companies.json`. El 12/9/2026 se guardó el perfil de
papá y su lista reemplazó a la de Isaías: se perdieron 10 empresas y la fuente
de empresas dejó de revisar cualquier página. Estos tests fijan que no vuelva a
pasar, por los dos lados:

* Un perfil nuevo nace con su propio archivo.
* Si igual dos perfiles apuntan al mismo, el que guarda pasa a tener el suyo, y
  la lista del otro no se toca.
"""

import json

from vacantia.ui import data

from tests.test_ui import post, sitio  # noqa: F401


def _papa_comparte_el_archivo_de_test(tmp):
    """Un segundo perfil con la configuración de antes: el mismo companies.json."""
    perfil = json.loads((tmp / "profiles" / "test.json").read_text(encoding="utf-8"))
    perfil["name"] = "papa"
    (tmp / "profiles" / "papa.json").write_text(json.dumps(perfil), encoding="utf-8")


def test_un_perfil_nuevo_nace_con_su_propio_archivo_de_empresas(sitio):
    _, tmp = sitio
    data.crear_perfil("maria")
    assert data.ruta_companies(data.leer_perfil("maria")).name == "companies-maria.json"
    assert data.otros_perfiles_con_las_mismas_empresas(
        "maria", data.leer_perfil("maria")) == []


def test_guardar_un_perfil_que_comparte_no_pisa_la_lista_del_otro(sitio):
    base, tmp = sitio
    _papa_comparte_el_archivo_de_test(tmp)
    antes = (tmp / "companies.json").read_text(encoding="utf-8")

    post(base, "/datos", {"perfil": "papa", "keywords": "QHSE",
                          "empresas": "Techint | https://careers.techint.com | techint.com"})

    # La lista del otro perfil quedó intacta, byte por byte.
    assert (tmp / "companies.json").read_text(encoding="utf-8") == antes
    # Y papá tiene la suya, con lo que cargó.
    papa = data.leer_perfil("papa")
    assert data.ruta_companies(papa).name == "companies-papa.json"
    assert [c["name"] for c in data.leer_companies(papa)] == ["Techint"]
    assert data.otros_perfiles_con_las_mismas_empresas("papa", papa) == []


def test_sin_otro_perfil_en_el_mismo_archivo_no_se_separa_nada(sitio):
    base, tmp = sitio
    post(base, "/datos", {"perfil": "test", "keywords": "Python",
                          "empresas": "ACME | https://acme.com/jobs | acme.com"})
    assert data.ruta_companies(data.leer_perfil("test")).name == "companies.json"
