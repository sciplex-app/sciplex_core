"""
Controller layer for the Qt application.

Controllers sit between the Qt views in ``view/`` and the data models in
``model/``. They encapsulate application logic and I/O so that widgets
can focus on presentation and user interaction.

Controller hierarchy:
- SceneController: High-level scene/graph operations
- NodeController: Node-specific operations (execute, reset, update)
- EdgeController: Edge validation and management
- SettingsController: Application settings and theme
- ExplorerController: Project file management
- LibraryController: Node library queries and management
"""


