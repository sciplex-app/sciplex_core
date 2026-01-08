from pathlib import Path

from sciplex_core.controller.scene_controller import SceneController


def test_create_new_project_initializes_graph(tmp_path):
    base_dir = tmp_path / "workspace"
    project_path = base_dir / "projects" / "example.sciplex"

    controller = SceneController(base_dir=str(base_dir))

    result = controller.create_new_project(str(project_path))

    assert result.success
    assert project_path.exists()
    assert controller.model.graph is not None

