"""`use_search: false` por empresa: la careers page se lee igual, la búsqueda
por dominio (que es la cara, ~3s serial cada una) no se hace.

Las empresas se arman acá y no se leen del `companies.json` del repo: esa lista
es de la persona que usa esta copia y cambia en cada máquina. Un test que
dependía de las empresas de Isaías fallaba en cuanto otra persona cargaba las
suyas, con el código sano.
"""

import json

from vacantia.sources.careers import CareersPagesSource

CONFIG = {"type": "careers", "api_key": "x", "companies_file": "companies.json"}

EMPRESAS = [
    {"name": "Con búsqueda", "careers_url": "https://a.com/jobs", "search_domain": "a.com"},
    {"name": "Sin búsqueda", "careers_url": "https://b.com/jobs", "search_domain": "b.com",
     "use_search": False},
]


def test_una_empresa_con_la_busqueda_apagada_se_sigue_cargando(tmp_path, monkeypatch):
    """El flag apaga la búsqueda por dominio, no la empresa entera."""
    (tmp_path / "companies.json").write_text(json.dumps(EMPRESAS), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    cargadas = CareersPagesSource(CONFIG, {})._load_companies()
    assert [c["name"] for c in cargadas] == ["Con búsqueda", "Sin búsqueda"]


def test_discover_from_search_saltea_las_apagadas(monkeypatch):
    src = CareersPagesSource(CONFIG, {})
    consultadas = []
    monkeypatch.setattr(
        CareersPagesSource, "_search_domain",
        lambda self, name, domain: consultadas.append(name) or set(),
    )
    src._discover_from_search(EMPRESAS, {c["name"]: set() for c in EMPRESAS})
    assert consultadas == ["Con búsqueda"]


def test_la_careers_page_de_las_apagadas_se_sigue_leyendo(monkeypatch):
    src = CareersPagesSource(CONFIG, {})
    pedidas = []
    monkeypatch.setattr(
        CareersPagesSource, "_fetch_links",
        lambda self, urls: pedidas.extend(urls) or {},
    )
    src._discover_from_careers_pages(EMPRESAS)
    assert "https://b.com/jobs" in pedidas
