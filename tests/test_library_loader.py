from importlib import resources

from sciplex_core.model.library_model import library_model
from sciplex_core.utils.library_loader import LibraryLoader, auto_register_function


def test_setup_libraries_folder_copies_defaults(tmp_path):
    base_dir = tmp_path / "workspace"
    loader = LibraryLoader(str(base_dir))
    source_dir = resources.files("sciplex_core.libraries.default")

    loader.setup_libraries_folder(str(source_dir))

    default_dir = base_dir / "libraries" / "default"
    assert default_dir.exists()
    assert (default_dir / "data.py").exists()


def test_auto_register_function_registers_parameters_inputs_outputs():
    def add_one(value: int, offset: int = 1) -> int:
        return value + offset

    auto_register_function(add_one, library_name="testlib")
    item = library_model.get_library_item("add_one")

    try:
        assert item is not None
        assert item.library_name == "testlib"
        assert list(item.inputs) == [("value", int)]
        assert "offset" in item.parameters
        assert item.parameters["offset"].value == 1
        assert item.outputs == [("out_0", int)]
    finally:
        library_model.deregister("add_one")

