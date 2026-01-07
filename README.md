# sciplex-core

Core models, controllers, utilities, and default node libraries for Sciplex visual programming (desktop, server, and web variants). Packaged for reuse as a PyPI library.

## Installation

Python 3.11+ is required.

```bash
pip install sciplex-core
```

For local development:

```bash
pip install -e ".[dev]"
```

## Quick start

```python
from pathlib import Path
from importlib.resources import files

from sciplex_core.controller.scene_controller import SceneController
from sciplex_core.utils.library_loader import LibraryLoader

# Where user libraries and projects will be stored
base_dir = Path.home() / "Sciplex"
base_dir.mkdir(parents=True, exist_ok=True)

# Copy packaged default libraries into the user's workspace and load them
default_lib_source = files("sciplex_core.libraries.default")
loader = LibraryLoader(str(base_dir))
loader.setup_libraries_folder(str(default_lib_source))
loader.load_all_libraries()

# Create a scene controller and initialize a project
controller = SceneController(base_dir=str(base_dir))
controller.create_new_project(str(base_dir / "projects" / "example.sciplex"))
```

## Authoring nodes

Users can build custom node libraries with the public API exposed via `sciplex`:

```python
from sciplex import Attribute, nodify, workspace

@nodify(icon="function", scale=Attribute("doublespinbox", value=1.0))
def Scale(table, scale: float = 1.0):
    return table * scale

# Share data across nodes
workspace["my_df"] = ...
```

Functions decorated with `@nodify` gain inputs/outputs from type hints and register themselves with the runtime library model.

## Package structure

- `controller/` — Scene, node, edge, and library controllers plus event/clipboard abstractions.
- `model/` — Graph, node, edge, socket, settings, and annotation data models.
- `utils/` — Shared utilities including `library_loader`, node factory helpers, graph export, and icon helpers.
- `libraries/default/` — Packaged data, transform, math, visuals, and ML nodes (auto-copied into user workspaces).
- `libraries/internal/` — Internal helpers (e.g., matplotlib-based visuals).
- `assets/` — Application icons (see `icons_credits.txt`).
- `sciplex/` — Public API surface for library authors (`Attribute`, `nodify`, `workspace`).

## Optional features

LLM-assisted node generation hooks into `sciplex_core_ext` (not bundled). Set `GEMINI_API_KEY` and install the extension to enable these methods; otherwise they safely return informative errors.

## Development & testing

- Format/lint: `ruff check .`
- Tests: `pytest`
- Build wheel/sdist: `python -m build`

## License

MIT

