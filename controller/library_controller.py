"""
Controller for node registry operations.

Wraps the global ``node_registry`` model and provides a clean API for
views to query and manipulate registered nodes.
"""

from typing import Callable, List, Set

from sciplex_core.model.library_model import library_model
from sciplex_core.model.node_model import NodeModel


class LibraryController:
    """
    Mediates between library views and the underlying ``LibraryModel``.

    Provides read-only queries and mutation operations for registered nodes.
    """

    def __init__(self):
        self._model = library_model

    # ------------------------------------------------------------------
    # Read-only queries
    # ------------------------------------------------------------------

    def get_node_names(self) -> List[str]:
        """Return a list of all registered node names (built-in + custom)."""
        return self._model.get_library_item_names()

    def get_node_names_by_category(self, library_name: str) -> List[str]:
        """Return node names filtered by library (legacy name kept for compatibility)."""
        return self._model.get_library_item_names_by_library(library_name)

    def get_categories(self) -> Set[str]:
        """Return the set of all library names (legacy alias), excluding hidden."""
        return {c for c in self._model.get_library_names() if not str(c).startswith("_")}

    def get_node_icon(self, node_name: str) -> str:
        """
        Return the icon name for a given node.
        """
        return self._model.get_library_item_icon(node_name)

    def get_library_item(self, node_name: str):
        """
        Return the library item for a given node name.

        Returns None if the node is not registered.
        """
        return self._model.get_library_item(node_name)

    def delete_node(self, node_name: str, base_dir: str = None) -> bool:
        """
        Delete a custom node from the registry and its source file.

        Args:
            node_name: Name of the node to delete
            base_dir: Base directory for Sciplex (to find library files)

        Returns True if the node was deleted, False if it wasn't found or couldn't be deleted.
        """
        import glob
        import os
        from pathlib import Path

        library_item = self._model.get_library_item(node_name)
        if not library_item:
            return False

        # Only allow deletion of Custom or Generated nodes
        category = getattr(library_item, "library_name", None)
        if category not in ("Custom", "Generated"):
            return False

        # Find and delete the source file
        if base_dir is None:
            base_dir = os.path.join(Path.home(), "Sciplex")

        # Look for the file in the category folder
        category_dir = os.path.join(base_dir, "libraries", category)
        if os.path.exists(category_dir):
            # Try exact match first
            exact_file = os.path.join(category_dir, f"{node_name}.py")
            if os.path.exists(exact_file):
                try:
                    os.remove(exact_file)
                except Exception as e:
                    print(f"Warning: Could not delete file {exact_file}: {e}")
            else:
                # Try pattern match (for timestamped files like func_name_1234567890.py)
                pattern = os.path.join(category_dir, f"{node_name}_*.py")
                for filepath in glob.glob(pattern):
                    try:
                        os.remove(filepath)
                    except Exception as e:
                        print(f"Warning: Could not delete file {filepath}: {e}")

        # Deregister from the model
        self._model.deregister(node_name)
        return True

    def register_custom_node(
        self, node_name: str, library_name: str, node_factory: Callable[[], NodeModel]
    ) -> None:
        """
        Register a new custom node in the registry.

        Note: The node_factory should return a NodeModel instance.
        """
        from sciplex_core.model.library_model import LibraryItem
        # Create a library item from the factory
        # We need to call the factory to get the node model to extract its properties
        node_model = node_factory()
        library_item = LibraryItem(
            function_name=node_name,
            library_name=library_name,
            icon=getattr(node_model, 'icon', 'python'),
            execute_fn=getattr(node_model, 'execute_fn', None),
            parameters=getattr(node_model, 'parameters', {}),
            inputs=getattr(node_model, 'inputs', []),
            outputs=getattr(node_model, 'outputs', [])
        )
        self._model.register(node_name, library_item)

    def delete_category(self, library_name: str) -> int:
        """
        Delete a library and all its nodes from the registry.

        Returns the number of nodes removed.
        """
        return self._model.remove_library(library_name)

