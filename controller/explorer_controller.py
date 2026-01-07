import os
from pathlib import Path
from typing import List


class ExplorerController:
    """
    Controller for the project explorer.

    Encapsulates filesystem access (listing and deleting project files) so the
    view can stay focused on presentation and user interaction.
    """

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = Path(base_dir) if base_dir is not None else Path.home() / "Sciplex"
        self.projects_path = self.base_dir / "data" / "user" / "projects"

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def list_projects(self) -> List[str]:
        """Return all project filenames (e.g. ``['myproject.json', ...]``)."""
        if not self.projects_path.exists():
            return []

        return sorted(
            [
                name
                for name in os.listdir(self.projects_path)
                if (self.projects_path / name).is_file()
            ]
        )

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------
    def delete_project(self, filename: str) -> None:
        """Delete the given project file if it exists."""
        filepath = self.projects_path / filename
        if filepath.exists():
            filepath.unlink()


