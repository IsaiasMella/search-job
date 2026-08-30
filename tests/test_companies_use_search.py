"""`use_search: false` por empresa: la careers page se lee igual, la búsqueda
por dominio (que es la cara, ~3s serial cada una) no se hace."""

import json
from pathlib import Path

from vacantia.sources.careers import CareersPagesSource

CONFIG = {"type": "careers", "api_key": "x", "companies_file": "companies.json"}

SIN_RESULTADOS = {
    "Mercado Libre", "Mutt Data", "Ualá", "Despegar",
    "Naranja X", "Banco Galicia", "Swiss Medical Group",
}


def test_las_empresas_que_nunca_devolvieron_nada_tienen_la_busqueda_apagada():
    empresas = json.loads(Path("companies.json").read_text(encoding="utf-8"))
    apagadas = {c["name"] for c in empresas if c.get("use_search") is False}
    assert SIN_RESULTADOS <= apagadas


def test_discover_from_search_saltea_las_apagadas(monkeypatch):
    src = CareersPagesSource(CONFIG, {})
    consultadas = []
    monkeypatch.setattr(
        CareersPagesSource, "_search_domain",
        lambda self, name, domain: consultadas.append(name) or set(),
    )
    empresas = [
        {"name": "Con búsqueda", "search_domain": "a.com"},
        {"name": "Sin búsqueda", "search_domain": "b.com", "use_search": False},
    ]
    src._discover_from_search(empresas, {c["name"]: set() for c in empresas})
    assert consultadas == ["Con búsqueda"]


def test_la_careers_page_de_las_apagadas_se_sigue_leyendo():
    """El flag apaga la búsqueda por dominio, no la empresa entera."""
    empresas = json.loads(Path("companies.json").read_text(encoding="utf-8"))
    apagadas = [c for c in empresas if c.get("use_search") is False]
    assert apagadas and all(c.get("careers_url") for c in apagadas)
