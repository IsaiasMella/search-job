---
paths:
  - "tests/**"
  - "conftest.py"
---

# Tests

- **Fixture `sitio`** (`tests/test_ui.py`): arma una instalación de juguete en `tmp_path`, hace `monkeypatch.chdir` y levanta el servidor en un puerto libre. Devuelve `(base_url, tmp_path)`. Los helpers `get` y `post` de ese archivo los reusan los demás tests.
- **Nunca leer datos reales del repo:** nada de `profiles/<persona>.json`, `resume/`, `companies*.json` ni `state/`. Esos archivos cambian en cada máquina, y un test que depende de ellos falla en otra computadora aunque el código esté bien. Armá los datos en `tmp_path`.
- **El modelo nunca se llama de verdad:** `monkeypatch.setattr(scoring, "chat_with_llm", falso)`. Tampoco la red ni `subprocess`.
- **CSS y JavaScript:** los tests que los miran leen el archivo de disco en el momento, con `estilos.CSS` y `render.JS`.
- **Si un test falla después de un cambio,** primero entendé qué protege: el docstring de cada test explica el incidente que lo motivó. No lo "arregles" para que pase sin saber eso.
