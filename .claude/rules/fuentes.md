---
paths:
  - "vacantia/sources/**"
  - "vacantia/ui/linkedin_urls.py"
---

# Fuentes de ofertas y direcciones de búsqueda

- **Términos de búsqueda:** salen siempre de `config.terminos_de_busqueda(perfil, propios)`. Si una fuente los arma por su cuenta, deja afuera las palabras clave de los CV.
- **Topes:** las fuentes rotan los términos por día y tienen tope por corrida (`max_searches`, `max_queries`). Sumar términos reparte la cobertura entre días; no multiplica pedidos. No saques esos topes: cada pedido cuesta plata (TinyFish) o arriesga un bloqueo (LinkedIn, Indeed).
- **Parámetros de un portal o de LinkedIn:** verificarlos contra el sitio antes de darlos por buenos, y dejar escrito en el docstring qué se probó y cuándo. Sin eso, una búsqueda que devuelve cero parece "no hay ofertas".
- **LinkedIn URLs (`ui/linkedin_urls.py`):**
  - Las exclusiones van con un `NOT` por término. `NOT (a OR b)` devuelve cero.
  - En Publicaciones, el texto no puede pasar de `TOPE_KEYWORDS = 110` caracteres.
- **Probar sin gastar:** para ver qué trae una fuente se usa `--dry-run`, que gasta llamadas reales. Pedí permiso antes.
