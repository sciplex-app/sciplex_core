"""
Centralized library loading utilities.

This module provides all library loading functionality used by both
desktop and web versions. It extracts duplicated code from app.py
and scene_controller.py into a single, reusable module.
"""

import builtins
import importlib.util
import inspect
import logging
import os
import shutil
import sys
from functools import wraps
from typing import Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Default allowed modules for user libraries
# NOTE: Restrictions disabled; kept for potential future use.
DEFAULT_ALLOWED_MODULES = {'numpy', 'pandas', 'sklearn', 'scipy', 'plotly'}


def create_restricted_import(allowed_modules: Set[str], default_dir: Optional[str] = None) -> Callable:
    """
    Previously returned a restricted __import__ to sandbox user libraries.
    Restrictions are now disabled; we return the original import.
    """
    return builtins.__import__


def infer_widget_from_type(type_hint) -> str:
    """
    Infer widget type from a Python type hint.

    Args:
        type_hint: A Python type annotation

    Returns:
        Widget type string for the UI
    """
    if type_hint is None:
        return "lineedit"

    type_name = getattr(type_hint, "__name__", str(type_hint))

    if type_hint is bool or type_name == "bool":
        return "toggle"
    elif type_hint is int or type_name == "int":
        return "spinbox"
    elif type_hint is float or type_name == "float":
        return "doublespinbox"
    elif type_hint is str or type_name == "str":
        return "lineedit"
    else:
        return "lineedit"


def auto_register_function(func: Callable, library_name: str) -> None:
    """
    Auto-register a plain Python function as a node.

    Analyzes the function signature to determine:
    - Args with defaults → parameters (widgets)
    - Args without defaults → inputs (sockets)
    - Return annotation → outputs (sockets)

    Args:
        func: The Python function to register
        library_name: Name of the library this function belongs to
    """
    from typing import get_args, get_type_hints

    from sciplex_core.model.library_model import Attribute, LibraryItem, library_model

    sig = inspect.signature(func)

    try:
        type_hints = get_type_hints(func, func.__globals__, func.__globals__)
    except Exception:
        type_hints = {}

    parameters = {}
    inputs = []

    for name, param in sig.parameters.items():
        param_type = type_hints.get(name, None)

        if param.default is not inspect.Parameter.empty:
            # Has default value → parameter
            widget_type = infer_widget_from_type(param_type)
            parameters[name] = Attribute(widget_type, value=param.default)
        else:
            # No default → input socket
            inputs.append((name, param_type))

    # Get output types from return annotation (or infer from source)
    return_type = type_hints.get("return", None)
    if return_type is None:
        # Infer return arity from source when un-annotated
        from sciplex_core.utils.node_factory import get_outputs_info
        output_types = get_outputs_info(func)
        outputs = [(f"out_{i}", t) for i, t in enumerate(output_types)]
    elif hasattr(return_type, "__origin__") and return_type.__origin__ is tuple:
        outputs = [(f"out_{i}", t) for i, t in enumerate(get_args(return_type))]
    else:
        outputs = [("out_0", return_type)]

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    library_item = LibraryItem(
        function_name=func.__name__,
        library_name=library_name,
        icon="python",
        execute_fn=wrapper,
        parameters=parameters,
        inputs=inputs,
        outputs=outputs
    )
    library_model.register(func.__name__, library_item)


class LibraryLoader:
    """
    Handles loading Python library files and registering their nodes.

    This class provides a unified interface for loading libraries that
    can be used by both desktop and web versions.
    """

    def __init__(self, base_dir: str, allowed_modules: Optional[Set[str]] = None):
        """
        Initialize the library loader.

        Args:
            base_dir: Base directory for application data (e.g., ~/Sciplex)
            allowed_modules: Set of allowed module names for sandboxing.
                           Defaults to DEFAULT_ALLOWED_MODULES.
        """
        self.base_dir = base_dir
        self.allowed_modules = allowed_modules or DEFAULT_ALLOWED_MODULES
        self.loaded_library_files: List[str] = []

    @property
    def libraries_dir(self) -> str:
        """Get the libraries directory path."""
        return os.path.join(self.base_dir, "libraries")

    @property
    def default_dir(self) -> str:
        """Get the default libraries directory path."""
        return os.path.join(self.libraries_dir, "default")

    def setup_libraries_folder(self, source_dir: str) -> None:
        """
        Set up the libraries folder structure and copy default node files.

        Args:
            source_dir: Source directory containing default library files
        """
        os.makedirs(self.default_dir, exist_ok=True)

        # Files to copy (exclude __init__.py, __pycache__, and tutorial.py)
        node_files = ["_helpers.py", "data.py", "math.py", "transform.py", "visuals.py", "machine_learning.py"]

        for filename in node_files:
            source_path = os.path.join(source_dir, filename)
            dest_path = os.path.join(self.default_dir, filename)

            if os.path.exists(source_path):
                # Always update to ensure latest version
                if not os.path.exists(dest_path) or \
                   os.path.getmtime(source_path) > os.path.getmtime(dest_path):
                    shutil.copy2(source_path, dest_path)

        # Remove legacy files that shouldn't be in user libraries
        for legacy_file in ["tutorial.py", "helpers.py"]:
            legacy_path = os.path.join(self.default_dir, legacy_file)
            if os.path.exists(legacy_path):
                try:
                    os.remove(legacy_path)
                except OSError:
                    pass

    def load_all_libraries(self, include_tutorials: bool = False, tutorial_source_path: Optional[str] = None) -> None:
        """
        Load all node libraries from the libraries folder.

        This loads:
        - All .py files in libraries/default/ (built-in nodes)
        - All .py files directly in libraries/ (user libraries)
        - All .py files in any subfolder of libraries/

        Args:
            include_tutorials: Whether to load tutorial nodes
            tutorial_source_path: Path to tutorial.py source file
        """
        if not os.path.exists(self.libraries_dir):
            return

        # Ensure directories are in sys.path
        if self.default_dir not in sys.path:
            sys.path.insert(0, self.default_dir)

        files_to_load = []

        # Load default/ folder first (built-in nodes)
        if os.path.exists(self.default_dir):
            for filename in sorted(os.listdir(self.default_dir)):
                if filename == "tutorial.py":
                    continue  # Never load from user libraries
                if filename.endswith(".py") and not filename.startswith("_"):
                    file_path = os.path.join(self.default_dir, filename)
                    files_to_load.append(file_path)
                    self.loaded_library_files.append(file_path)

        # Load other subfolders and root .py files
        for item in sorted(os.listdir(self.libraries_dir)):
            item_path = os.path.join(self.libraries_dir, item)

            if item == "default":
                continue

            if os.path.isfile(item_path) and item.endswith(".py") and not item.startswith("_"):
                files_to_load.append(item_path)
                self.loaded_library_files.append(item_path)
            elif os.path.isdir(item_path) and not item.startswith("_"):
                for filename in sorted(os.listdir(item_path)):
                    if filename.endswith(".py") and not filename.startswith("_"):
                        file_path = os.path.join(item_path, filename)
                        files_to_load.append(file_path)
                        self.loaded_library_files.append(file_path)

        # Load each file
        for filepath in files_to_load:
            self.load_library_file(filepath)

        # Load tutorials from source if enabled
        if include_tutorials and tutorial_source_path and os.path.exists(tutorial_source_path):
            self.load_library_file(tutorial_source_path)

    def load_library_file(self, filepath: str) -> Dict:
        """
        Load a single library file and register its nodes.

        Args:
            filepath: Path to the Python library file

        Returns:
            Dict with 'success', 'message', 'code' keys
        """
        from sciplex_core.model.library_model import library_model

        if not os.path.isfile(filepath):
            return {"success": False, "message": "File not found", "code": "not_found"}

        library_name = os.path.splitext(os.path.basename(filepath))[0]

        try:
            # Generate unique module name
            import time
            unique_module_name = f"sciplex_lib_{library_name}_{int(time.time() * 1000)}"

            spec = importlib.util.spec_from_file_location(unique_module_name, filepath)
            if spec is None or spec.loader is None:
                return {"success": False, "message": "Could not load module", "code": "load_error"}

            module = importlib.util.module_from_spec(spec)
            setattr(module, "__sciplex_library_name__", library_name)
            sys.modules[unique_module_name] = module

            spec.loader.exec_module(module)

            # Auto-register plain functions (those without @nodify)
            for name in dir(module):
                if name.startswith("_"):
                    continue
                obj = getattr(module, name)
                if callable(obj) and hasattr(obj, "__module__") and obj.__module__ == unique_module_name:
                    if library_model.get_library_item(name) is None:
                        auto_register_function(obj, library_name)

            return {"success": True, "message": "", "code": "ok"}

        except Exception as e:
            logger.warning(f"Failed to load library {filepath}: {e}")
            return {"success": False, "message": str(e), "code": "error"}

    def load_tutorial_library(self, tutorial_source_path: str) -> None:
        """Load tutorial.py from source and register its nodes."""
        if os.path.exists(tutorial_source_path):
            self.load_library_file(tutorial_source_path)

    def unload_tutorial_library(self) -> None:
        """Unregister all tutorial nodes from the library model."""
        from sciplex_core.model.library_model import library_model

        tutorial_items = [
            name for name, item in library_model.get_library_items().items()
            if item.library_name == "tutorial"
        ]

        for name in tutorial_items:
            library_model.deregister(name)

