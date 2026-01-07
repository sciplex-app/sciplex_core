import ast
import json
import logging
import os
import sys
from dataclasses import dataclass
from typing import Optional, Tuple

import networkx as nx

from sciplex_core.controller.clipboard_interface import ClipboardInterface, QtClipboard
from sciplex_core.controller.edge_controller import EdgeController
from sciplex_core.controller.events import EventEmitter, SimpleEventEmitter
from sciplex_core.controller.node_controller import NodeController
from sciplex_core.model.graph_model import GraphModel
from sciplex_core.model.library_model import library_model
from sciplex_core.model.scene_annotation_model import SceneAnnotationModel
from sciplex_core.model.scene_model import SceneModel
from sciplex_core.model.socket_model import SocketModel
try:
    from sciplex_core_ext.utils.llm.prompts import socket_hint
except ImportError:
    socket_hint = None


@dataclass
class SceneOperationResult:
    """Simple result object for scene controller operations."""

    success: bool
    message: Optional[str] = None
    code: Optional[str] = None
    data: Optional[object] = None


class SceneController:
    """
    Mediates between the scene-related views (e.g. ``SceneView``) and the
    underlying ``SceneModel`` / ``GraphModel``.

    The controller owns the model and emits events for view updates.
    Views connect to these events and update themselves reactively.
    """

    def __init__(
        self,
        base_dir: str,
        event_emitter: Optional[EventEmitter] = None,
        clipboard: Optional[ClipboardInterface] = None
    ):
        """
        Initialize the scene controller.

        Args:
            base_dir: Base directory for application data
            event_emitter: Event emitter for reactive updates. If None, creates SimpleEventEmitter
            clipboard: Clipboard interface for copy/paste. If None, creates QtClipboard
        """
        self.model: SceneModel = SceneModel()
        self.base_dir = base_dir
        self._has_been_modified = False

        self.events = event_emitter if event_emitter is not None else SimpleEventEmitter()
        self.clipboard = clipboard if clipboard is not None else QtClipboard()
        
        # Initialize logger
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Set reference to this controller on the graph model
        # This allows GraphModel.execute() to delegate to SceneController
        # (for backward compatibility during migration)
        self._update_graph_controller_ref()
    
    def _update_graph_controller_ref(self):
        """Update the graph model's reference to this controller."""
        import weakref
        if self.model.graph:
            self.model.graph._scene_controller_ref = weakref.ref(self)

    def on(self, event_name: str, callback):
        """Register a callback for an event. Framework-agnostic."""
        self.events.on(event_name, callback)

    def emit(self, event_name: str, *args, **kwargs):
        """Emit an event. Framework-agnostic."""
        self.events.emit(event_name, *args, **kwargs)

    def disconnect(self, event_name: str, callback=None):
        """Disconnect a callback from an event."""
        self.events.disconnect(event_name, callback)

    # ------------------------------------------------------------------
    # Basic state queries
    # ------------------------------------------------------------------
    def is_modified(self) -> bool:
        """Return whether the current scene has unsaved changes."""
        return self._has_been_modified

    def set_modified(self, modified: bool) -> None:
        """Set the modified flag."""
        self._has_been_modified = modified

    # ------------------------------------------------------------------
    # Project / file operations
    # ------------------------------------------------------------------
    def create_new_project(self, save_path: str) -> SceneOperationResult:
        """
        Create a new, empty project file at ``save_path`` and load it into
        the current scene.
        """
        try:
            if os.path.exists(save_path):
                return SceneOperationResult(
                    success=False,
                    message="Project file already exists.",
                    code="file_exists",
                )

            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # Initialize a fresh scene and write it to disk.
            self.model.filepath = save_path
            self.model.graph = GraphModel()
            self._update_graph_controller_ref()
            self.model.scene_annotations = []
            initial_scene = self.model.serialize()
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(initial_scene, f, indent=2)

            # Emit events
            self._has_been_modified = False
            self.emit("scene_cleared")
            self.emit("project_created", save_path)

            return SceneOperationResult(success=True)

        except Exception as exc:
            return SceneOperationResult(
                success=False,
                message=str(exc),
                code="error",
            )

    def open_project(self, path: str) -> SceneOperationResult:
        """
        Open an existing project file and load it into the scene.
        Auto-imports any libraries that were saved with the project.
        """
        if not os.path.isfile(path):
            return SceneOperationResult(
                success=False,
                message="Project file not found.",
                code="not_found",
            )

        try:
            # First, read the JSON to get library paths BEFORE deserializing nodes
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Auto-import libraries before loading the graph
            imported_libraries = data.get("imported_libraries", [])
            missing_libraries = []
            import_errors = []

            for lib_path in imported_libraries:
                result = self._import_library(lib_path)
                if not result["success"]:
                    if result["code"] == "not_found":
                        missing_libraries.append(lib_path)
                    else:
                        import_errors.append(f"{lib_path}: {result['message']}")

            # Now load the project (libraries are registered, nodes can be found)
            self.model.load_from_file(path)
            self._update_graph_controller_ref()  # Set controller ref on loaded graph
            self._has_been_modified = False

            # After loading, update custom nodes via their controllers
            if self.model.graph:
                for node_model in self.model.graph.nodes:
                    NodeController(node_model)
                    # Note: update() method was removed, so we skip this for now
                        # Custom nodes should be handled differently

            # Emit events for view to update
            self.emit("scene_cleared")
            self.emit("project_opened", path)

            # Return with warnings if there were issues
            if missing_libraries or import_errors:
                warnings = []
                if missing_libraries:
                    warnings.append(f"Missing libraries: {', '.join(missing_libraries)}")
                if import_errors:
                    warnings.append(f"Import errors: {'; '.join(import_errors)}")
                return SceneOperationResult(
                    success=True,
                    message="; ".join(warnings),
                    code="warnings",
                )

        except Exception as exc:  # pragma: no cover - defensive
            return SceneOperationResult(
                success=False,
                message=str(exc),
                code="error",
            )

        return SceneOperationResult(success=True)

    def _import_library(self, filepath: str) -> dict:
        """
        Import a Python library file and register its nodes.

        Uses LibraryLoader from sciplex_core.utils for actual loading.
        Returns dict with success, message, code.
        """
        from sciplex_core.utils.library_loader import LibraryLoader

        if not os.path.isfile(filepath):
            return {"success": False, "message": "File not found", "code": "not_found"}

        try:
            # Use LibraryLoader for actual import
            loader = LibraryLoader(self.base_dir)
            result = loader.load_library_file(filepath)

            # Track successfully imported libraries for serialization
            if result.get("success"):
                self.add_imported_library(filepath)

            return result

        except Exception as e:
            return {"success": False, "message": str(e), "code": "error"}

    # ------------------------------------------------------------------
    # Script node creation (internal, not from library list)
    # ------------------------------------------------------------------
    def create_script_node(self, scene_pos) -> SceneOperationResult:
        """
        Create a Script node model at the given scene position.
        Script nodes are not shown in the library; they are added via context menu.
        """
        from sciplex_core.model.library_model import Attribute
        from sciplex_core.model.node_model import NodeModel

        try:
            # Internal script template (kept out of user-facing libraries)
            from sciplex_core.utils.script_node import SCRIPT_DEFAULT_CODE
        except Exception:
            SCRIPT_DEFAULT_CODE = "def my_function(data):\\n    return data"

        node_model = NodeModel(
            title="Script",
            icon="python",
            parameters={"function": Attribute("codeeditor", value=SCRIPT_DEFAULT_CODE)},
            inputs=[],
            outputs=[],
            is_script=True,
            library_name="Script",
        )

        # Build sockets from default code
        build_result = node_model.rebuild_sockets_from_code()
        if not build_result["success"]:
            return SceneOperationResult(
                success=False,
                message=build_result["message"],
                code="build_error",
            )

        # Position is set by the view when it adds the NodeView.
        node_model.update_position(scene_pos[0], scene_pos[1])
        self._has_been_modified = True

        return SceneOperationResult(success=True, data=node_model)

    def generate_node_from_socket_data(
        self,
        socket_model: SocketModel,
        user_prompt: str,
        schema_info: Optional[dict] = None,
        scene_pos: Tuple[float, float] = (0, 0),
    ) -> SceneOperationResult:
        """
        Generate a new node from LLM based on socket data.
        
        This method handles the complete flow:
        1. Get data from socket
        2. Build enhanced prompt with schema
        3. Generate code via LLM
        4. Create node from code
        5. Connect edge from source socket to new node
        
        Args:
            socket_model: The output socket model containing the data
            user_prompt: User's natural language prompt
            schema_info: Optional schema information (columns, dtypes, etc.)
            scene_pos: Position where the new node should be created
            
        Returns:
            SceneOperationResult with success status and any error messages
        """
        import logging
        import os
        
        logger = logging.getLogger("sciplex.llm")
        
        # Get data from socket
        data = socket_model.get_data()
        
        # If no data, try to execute source node
        if data is None and socket_model.node:
            node_controller = NodeController(socket_model.node)
            node_controller.execute()
            data = socket_model.get_data()
        
        if data is None:
            return SceneOperationResult(
                success=False,
                message="No data available. Please execute the source node first.",
                code="no_data",
            )
        
        # Build enhanced prompt with schema information
        enhanced_prompt = self._build_llm_prompt_from_data(user_prompt, schema_info, data)
        
        # Check for API key
        if not os.getenv("GEMINI_API_KEY"):
            return SceneOperationResult(
                success=False,
                message="GEMINI_API_KEY environment variable is not set.",
                code="no_api_key",
            )
        
        # Generate code using LLM (requires sciplex_core_ext)
        try:
            from sciplex_core_ext.utils.llm.gemini import generate_code_with_gemini_flash
        except ImportError:
            return SceneOperationResult(
                success=False,
                message="LLM extension not installed. Install sciplex_core_ext for this feature.",
                code="llm_extension_missing",
            )

        try:
            logger.info("Generating node code from LLM (prompt_len=%d)", len(enhanced_prompt))
            code = generate_code_with_gemini_flash(enhanced_prompt)
            
            if not code:
                return SceneOperationResult(
                    success=False,
                    message="Failed to generate code from LLM.",
                    code="llm_generation_failed",
                )
            
            logger.info("LLM code generated successfully (code_len=%d)", len(code))
            
            # Create node from code
            result = self.build_graph_from_python_code(code, scene_pos)
            
            if not result.success:
                return result
            
            # Connect edge from source socket to the first newly created node
            # Find the newly created nodes
            graph = self.model.graph
            if graph and graph.nodes:
                # Get the last node (should be the one we just created)
                created_node = graph.nodes[-1]
                
                if created_node.input_sockets:
                    target_socket = created_node.input_sockets[0]
                    
                    # Validate and create edge
                    edge_result = self.validate_and_create_edge(socket_model, target_socket)
                    
                    if edge_result.success and edge_result.data:
                        edge_model = edge_result.data
                        self.add_edge_model(edge_model)
                        
                        # Emit signal for edge view creation (view will handle the visual connection)
                        # We store the edge model and socket info for the view to pick up
                        result.data = {
                            "edge_model": edge_model,
                            "source_socket_model": socket_model,
                            "target_socket_model": target_socket,
                            "created_node": created_node,
                        }
                        
                        return SceneOperationResult(
                            success=True,
                            message="Node generated and connected successfully.",
                            data=result.data,
                        )
                    else:
                        return SceneOperationResult(
                            success=False,
                            message=f"Node created but edge connection failed: {edge_result.message}",
                            code="edge_connection_failed",
                        )
            
            return SceneOperationResult(
                success=True,
                message="Node generated successfully.",
                data=result.data,
            )
            
        except Exception as e:
            logger.exception("Failed to generate node from data")
            return SceneOperationResult(
                success=False,
                message=f"Failed to generate node: {str(e)}",
                code="exception",
            )
    
    def _build_llm_prompt_from_data(
        self, user_prompt: str, schema_info: Optional[dict], data
    ) -> str:
        """
        Build an enhanced prompt that includes schema information for LLM.
        """
        if socket_hint:
            return socket_hint(schema_info, user_prompt)
        return user_prompt

    def add_imported_library(self, filepath: str) -> None:
        """Add a library path to the list of imported libraries."""
        if filepath not in self.model.imported_libraries:
            self.model.imported_libraries.append(filepath)
            self._has_been_modified = True

    # ------------------------------------------------------------------
    # Edit / execution operations
    # ------------------------------------------------------------------
    def undo(self) -> None:
        """
        Request undo operation.

        Note: The view's History object handles the actual undo/redo stack.
        This method is called by the view when undo is requested.
        The view's history.restoreHistoryStamp() will call restore_from_history_snapshot().
        """
        # History is managed by the view - this is just a placeholder
        # The actual undo is handled by view.history.undo()
        pass

    def redo(self) -> None:
        """
        Request redo operation.

        Note: The view's History object handles the actual undo/redo stack.
        This method is called by the view when redo is requested.
        The view's history.restoreHistoryStamp() will call restore_from_history_snapshot().
        """
        # History is managed by the view - this is just a placeholder
        # The actual redo is handled by view.history.redo()
        pass

    def delete_selection(self) -> None:
        """
        Request deletion of selected items.

        Note: Selection deletion is handled by the view via deleteSelected().
        This method is kept for API compatibility but doesn't need to do anything
        since the view handles selection deletion directly.
        """
        # View handles this directly via deleteSelected()
        pass

    def execute_graph(self) -> SceneOperationResult:
        """
        Execute all nodes in the graph in topological order.
        
        This method orchestrates graph execution. It was moved from GraphModel
        to maintain proper MVC separation (models should not import controllers).
        
        Checks that the graph is a DAG (directed acyclic graph) before execution.
        
        Returns:
            SceneOperationResult indicating success or failure
        """
        graph = self.model.graph
        if not graph:
            return SceneOperationResult(
                success=False,
                message="No graph to execute.",
                code="no_graph",
            )
        
        self.logger.info(f"Executing graph: {graph.id}")
        
        # Check if graph is a DAG (this will build graph if needed, but uses cache)
        if not graph.is_dag():
            return SceneOperationResult(
                success=False,
                message="Please check for cycles and ensure the graph is directed and acyclic.",
                code="not_dag",
            )
        
        # Only build/sort if not already cached (is_dag() may have built it)
        if graph._nx_graph is None:
            graph.build_nx_graph()
        if graph.sorted_nodes is None:
            graph.topological_sort()
        
        if graph.sorted_nodes is None:
            return SceneOperationResult(
                success=False,
                message="Graph contains cycles, cannot execute.",
                code="cycle_detected",
            )
        
        # Execute nodes through controllers
        # Use existing controller from view if available, otherwise create temporary one
        for node in graph.sorted_nodes:
            # Check if node has an existing controller (from view)
            if hasattr(node, '_controller_ref'):
                node_controller_ref = node._controller_ref()
                if node_controller_ref is not None:
                    # Use existing controller (may be Qt adapter or core controller)
                    node_controller = node_controller_ref
                else:
                    # Weak reference was garbage collected, create new controller with event emitter
                    node_controller = NodeController(node, event_emitter=self.events)
            else:
                # No existing controller, create temporary one with event emitter
                node_controller = NodeController(node, event_emitter=self.events)
            
            result = node_controller.execute()
            if not result.success:
                return SceneOperationResult(
                    success=False,
                    message=f"Node execution failed: {result.message}",
                    code=result.code or "node_execution_failed",
                )
        
        return SceneOperationResult(success=True, message="Graph executed successfully.")

    def execute_up_to_node(self, node_model) -> SceneOperationResult:
        """
        Execute nodes up to a target node in topological order.
        
        This method orchestrates partial graph execution. It was moved from GraphModel
        to maintain proper MVC separation.
        
        Args:
            node_model: The target node to execute up to
            
        Returns:
            SceneOperationResult indicating success or failure
        """
        graph = self.model.graph
        if not graph:
            return SceneOperationResult(
                success=False,
                message="No graph to execute.",
                code="no_graph",
            )
        
        self.logger.info(f"Executing up to node: {node_model.id}")
        
        # Only build graph if not already cached
        if graph._nx_graph is None:
            graph.build_nx_graph()

        try:
            if node_model.id not in graph._nx_graph:
                return SceneOperationResult(
                    success=False,
                    message=f"Node {node_model.id} not in graph, cannot execute.",
                    code="node_not_in_graph",
                )

            # Check node execution mode setting
            from sciplex_core.model.settings_model import settings
            execution_mode = settings.get_node_execution_mode()
            
            if execution_mode == "single node":
                # Only execute the target node, not its ancestors
                sorted_nodes = [node_model]
            else:
                # Execute node and all ancestors (default behavior)
                ancestors = nx.ancestors(graph._nx_graph, node_model.id)
                ancestors.add(node_model.id)

                subgraph = graph._nx_graph.subgraph(ancestors)

                sorted_node_ids = list(nx.topological_sort(subgraph))

                sorted_nodes = [graph._nx_graph.nodes[n]["obj"] for n in sorted_node_ids]

            # Execute nodes through controllers
            for node in sorted_nodes:
                # Check if node has an existing controller (from view)
                if hasattr(node, '_controller_ref'):
                    node_controller_ref = node._controller_ref()
                    if node_controller_ref is not None:
                        node_controller = node_controller_ref
                    else:
                        # Weak reference was garbage collected, create new controller with event emitter
                        node_controller = NodeController(node, event_emitter=self.events)
                else:
                    # No existing controller, create temporary one with event emitter
                    node_controller = NodeController(node, event_emitter=self.events)
                
                result = node_controller.execute()
                if not result.success:
                    return SceneOperationResult(
                        success=False,
                        message=f"Node execution failed: {result.message}",
                        code=result.code or "node_execution_failed",
                    )

            return SceneOperationResult(success=True, message="Execution completed successfully.")

        except nx.NetworkXUnfeasible:
            return SceneOperationResult(
                success=False,
                message="Graph contains cycles, cannot perform topological sort",
                code="cycle_detected",
            )
        except nx.NetworkXError as e:
            return SceneOperationResult(
                success=False,
                message=f"Error during graph execution: {e}",
                code="networkx_error",
            )
        """
        Execute the graph up to the given ``node_model``.
        """
        try:
            if not self.model.graph:
                return SceneOperationResult(
                    success=False,
                    message="No graph to execute.",
                    code="no_graph",
                )

            result = self.execute_up_to_node(node_model)
            return result
        except Exception as exc:  # pragma: no cover - defensive
            return SceneOperationResult(
                success=False,
                message=str(exc),
                code="error",
            )


    def reset_all_nodes(self) -> None:
        """
        Reset all nodes in the current graph to their initial state.
        Also clears the global variables registry.
        """
        if self.model.graph:
            for node in self.model.graph.nodes:
                # Prefer existing controller so connected views get the reset signal
                node_controller = None
                controller_ref = getattr(node, "_controller_ref", None)
                if controller_ref:
                    node_controller = controller_ref()

                # Fallback to a temporary controller if no view/controller is attached
                if node_controller is None:
                    node_controller = NodeController(node)

                node_controller.reset()

        # Clear global variables registry
        try:
            from sciplex_core.utils.functions import variables_registry
            variables_registry.clear()
        except ImportError:
            pass  # Gracefully handle if not available

    def execute_node(self, node_model) -> SceneOperationResult:
        """
        Execute a single node.

        Args:
            node_model: The NodeModel to execute

        Returns:
            SceneOperationResult indicating success or failure
        """
        # Create controller for execution with event emitter
        # Note: If a view exists for this node, it will have its own controller
        # that will also receive the execution signal. This is fine - both
        # controllers will work, but the view's controller is what matters for UI updates.
        node_controller = NodeController(node_model, event_emitter=self.events)
        result = node_controller.execute()

        if result.success:
            return SceneOperationResult(success=True)
        else:
            return SceneOperationResult(
                success=False,
                message=result.message,
                code=result.code,
            )

    def update_node(self, node_model) -> SceneOperationResult:
        """
        Update a node (e.g., re-parse custom code).

        Args:
            node_model: The NodeModel to update

        Returns:
            SceneOperationResult indicating success or failure
        """
        # NodeController.update() is a no-op - custom nodes are handled through library system
        # No action needed here
        return SceneOperationResult(success=True)

    def save_node_to_library(self, node_model, library_name: str, is_new: bool) -> SceneOperationResult:
        """
        Persist a Script node into a library .py file and register it.
        Library name maps to the file name (without extension).
        """
        try:
            if not node_model.is_script:
                return SceneOperationResult(
                    success=False,
                    message="Only Script nodes can be saved to a library.",
                    code="not_script",
                )

            func_code = node_model.parameters.get("function").value if node_model.parameters else None
            if not func_code or "def " not in func_code:
                return SceneOperationResult(
                    success=False,
                    message="No valid function code found.",
                    code="no_code",
                )

            # Extract function name from code
            func_name = node_model.title or "script_function"
            try:
                tree = ast.parse(func_code)
                func_def = next((n for n in tree.body if isinstance(n, ast.FunctionDef)), None)
                if func_def:
                    func_name = func_def.name
            except SyntaxError:
                pass  # fallback to node title

            # Guard against duplicate function names already registered
            if library_model.get_library_item(func_name) is not None:
                return SceneOperationResult(
                    success=False,
                    message=f"Node name '{func_name}' already exists. Choose a different name.",
                    code="name_conflict",
                )

            libraries_dir = os.path.join(self.base_dir, "libraries")
            os.makedirs(libraries_dir, exist_ok=True)

            filename = f"{library_name}.py" if not library_name.endswith(".py") else library_name
            filepath = os.path.join(libraries_dir, filename)

            header = (
                "# Auto-generated by Sciplex Script node\n"
                "import pandas as pd\n"
                "import numpy as np\n"
                "import matplotlib.pyplot as plt\n"
                "import sklearn\n\n"
            )

            if not os.path.exists(filepath):
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(header)
                    f.write(func_code.strip() + "\n")
            else:
                with open(filepath, "a", encoding="utf-8") as f:
                    f.write("\n\n")
                    f.write(f"# Added from Script node '{node_model.title}'\n")
                    f.write(func_code.strip() + "\n")

            # Import/reload the library so nodes are registered
            import_result = self._import_library(filepath)
            if not import_result.get("success", False):
                return SceneOperationResult(
                    success=False,
                    message=import_result.get("message", "Failed to import library."),
                    code=import_result.get("code", "import_error"),
                )

            # Track imported library
            self.add_imported_library(filepath)

            return SceneOperationResult(
                success=True,
                message=f"Saved function '{func_name}' to {filename}.",
                data={"function_name": func_name, "filepath": filepath},
            )

        except Exception as exc:
            return SceneOperationResult(
                success=False,
                message=str(exc),
                code="error",
            )

    def clear_scene(self) -> None:
        """
        Clear the entire scene (graph and annotations).

        This clears the model state and emits an event for the view to update.
        """
        if self.model:
            self.model.clear()
        self._has_been_modified = False
        self.emit("scene_cleared")

    def update_node_position(self, node_model, x: float, y: float) -> None:
        """
        Update a node's position in the scene.

        Args:
            node_model: The NodeModel to update
            x: New X coordinate
            y: New Y coordinate
        """
        from sciplex_core.controller.node_controller import NodeController
        node_controller = NodeController(node_model)
        node_controller.update_position(x, y)
        self._has_been_modified = True

    def store_history(self, description: str, set_modified: bool = False) -> None:
        """
        Request history storage. View's history object handles the actual storage.

        Args:
            description: Human-readable label for the operation
            set_modified: Whether to mark the scene as modified
        """
        if set_modified:
            self._has_been_modified = True
        self.emit("history_stored", description, set_modified)

    def restore_from_history_snapshot(self, history_stamp: dict) -> None:
        """
        Restore the scene to a previous state from a history stamp.

        This deserializes the snapshot into the model and emits an event
        for the view to re-render and restore selection.
        """
        import logging

        log = logging.getLogger("sciplex.history")

        # ------------------------------------------------------------------
        # IMPORTANT: History snapshots are intentionally "lightweight" and do
        # not serialize socket runtime data (which can be huge: DataFrames, arrays).
        #
        # However, for common UX actions like moving nodes and undo/redo of that move,
        # users expect already-executed nodes to keep their outputs.
        #
        # So we keep a best-effort in-memory cache keyed by (node_id, socket_name)
        # across history restores, and reattach it after deserialization.
        # This keeps the app responsive and avoids bloating the history JSON.
        # ------------------------------------------------------------------
        runtime_cache: dict[str, dict] = {}
        try:
            if getattr(self.model, "graph", None) and getattr(self.model.graph, "nodes", None):
                for node in self.model.graph.nodes:
                    runtime_cache[str(node.id)] = {
                        "executed": bool(getattr(node, "executed", False)),
                        "failed": bool(getattr(node, "failed", False)),
                        "outputs": {s.name: s.get_data() for s in getattr(node, "output_sockets", [])},
                    }
        except Exception:
            # Never fail history restore due to caching
            runtime_cache = {}

        # Deserialize the snapshot into the model
        if "snapshot" in history_stamp:
            self.model.deserialize(history_stamp["snapshot"], restore_id=True)

        # Re-attach runtime outputs where possible (best-effort)
        try:
            if runtime_cache and getattr(self.model, "graph", None) and getattr(self.model.graph, "nodes", None):
                restored = 0
                for node in self.model.graph.nodes:
                    cached = runtime_cache.get(str(node.id))
                    if not cached:
                        continue

                    # Restore node execution flags (not part of serialization)
                    node.executed = cached.get("executed", False)
                    node.failed = cached.get("failed", False)

                    # Restore outputs by socket name; use set_data() so edges propagate
                    outputs = cached.get("outputs", {})
                    for socket in getattr(node, "output_sockets", []):
                        if socket.name in outputs:
                            socket.set_data(outputs[socket.name])
                    restored += 1

                log.info(
                    "History restore (%s): reattached runtime outputs for %s nodes",
                    history_stamp.get("desc", "unknown"),
                    restored,
                )
        except Exception as exc:
            log.warning("History restore: failed to reattach runtime outputs: %s", exc)

        # Emit event for view to handle rendering and selection restoration
        self.emit("history_restored", history_stamp)

    def paste_graph_data(self, data: dict, mouse_scene_position) -> SceneOperationResult:
        """
        Paste graph data (nodes and edges) into the scene at the given position.

        This handles deserializing nodes and edges, calculating offsets based on
        mouse position, and emitting events for the view layer to create visuals.
        The controller only works with models - views subscribe to events.
        """
        try:
            from sciplex_core.model.node_model import NodeModel

            # Track created nodes for edge creation (model.id -> model)
            created_node_models = {}

            # Handle annotations if present
            if "annotations" in data and len(data["annotations"]) > 0:
                ann_data_list = data["annotations"]
                minx = min(ann_data["pos_x"] for ann_data in ann_data_list)
                maxx = max(ann_data["pos_x"] for ann_data in ann_data_list)
                miny = min(ann_data["pos_y"] for ann_data in ann_data_list)
                maxy = max(ann_data["pos_y"] for ann_data in ann_data_list)
                bbox_center_x = (minx + maxx) / 2
                bbox_center_y = (miny + maxy) / 2

                mouse_x, mouse_y = mouse_scene_position
                offset_x = mouse_x - bbox_center_x
                offset_y = mouse_y - bbox_center_y

                for ann_data in ann_data_list:
                    ann_model = SceneAnnotationModel.deserialize(ann_data, restore_id=False)
                    orig_x = ann_data["pos_x"]
                    orig_y = ann_data["pos_y"]
                    new_x = orig_x + offset_x
                    new_y = orig_y + offset_y
                    ann_model.set_position(new_x, new_y)
                    self.add_annotation_model(ann_model)

                    # Emit event with model data - view layer creates the visual
                    self.emit("annotation_model_created", ann_model)

            # Normalize clipboard/graph payloads
            graph_data = None
            if "graph" in data and isinstance(data["graph"], dict):
                graph_data = data["graph"]
            elif "nodes" in data and "edges" in data:
                graph_data = {"nodes": data.get("nodes", []), "edges": data.get("edges", [])}

            # Handle graph nodes and edges
            if graph_data and "nodes" in graph_data:
                node_data_list = graph_data["nodes"]
                if len(node_data_list) > 0:
                    # Calculate bounding box center for offset
                    minx = min(node_data["pos_x"] for node_data in node_data_list)
                    maxx = max(node_data["pos_x"] for node_data in node_data_list)
                    miny = min(node_data["pos_y"] for node_data in node_data_list)
                    maxy = max(node_data["pos_y"] for node_data in node_data_list)
                    bbox_center_x = (minx + maxx) / 2
                    bbox_center_y = (miny + maxy) / 2

                    # Calculate offset to center nodes around mouse position
                    mouse_x, mouse_y = mouse_scene_position
                    offset_x = mouse_x - bbox_center_x
                    offset_y = mouse_y - bbox_center_y

                    # Map old socket IDs to new socket models for edge creation
                    old_to_new_socket = {}

                    # Deserialize and add nodes
                    for node_data in node_data_list:
                        # Store old socket IDs and names before deserialization creates new ones
                        # Map by name for non-script nodes, by position for script nodes
                        old_input_sockets = {s.get("name"): s.get("id") for s in node_data.get("input_sockets", [])}
                        old_output_sockets = {s.get("name"): s.get("id") for s in node_data.get("output_sockets", [])}

                        import logging
                        logger = logging.getLogger(__name__)
                        print(f"[PASTE] About to deserialize node: title={node_data.get('title')}, parameters={node_data.get('parameters', {})}")
                        logger.info(f"[PASTE] About to deserialize node: title={node_data.get('title')}, parameters={node_data.get('parameters', {})}")
                        
                        node_model = NodeModel.deserialize(node_data, restore_id=False)
                        
                        if node_model:
                            params_after = {name: attr.value for name, attr in node_model.parameters.items()}
                            print(f"[PASTE] Deserialized node ID: {node_model.id}, parameters after deserialize: {params_after}")
                            logger.info(f"[PASTE] Deserialized node ID: {node_model.id}, parameters after deserialize: {params_after}")
                        if node_model is None:
                            continue

                        # Calculate new position
                        orig_x = node_data["pos_x"]
                        orig_y = node_data["pos_y"]
                        new_x = orig_x + offset_x
                        new_y = orig_y + offset_y
                        node_model.update_position(new_x, new_y)

                        self.add_node_model(node_model)
                        created_node_models[node_model.id] = node_model

                        # Map old socket IDs to new socket models by name (more robust than by position)
                        for socket in node_model.input_sockets:
                            old_id = old_input_sockets.get(socket.name)
                            if old_id:
                                old_to_new_socket[old_id] = socket
                        for socket in node_model.output_sockets:
                            old_id = old_output_sockets.get(socket.name)
                            if old_id:
                                old_to_new_socket[old_id] = socket

                        # Emit event with model - view layer creates the visual
                        self.emit("node_model_created", node_model)

                    # Deserialize and add edges
                    if "edges" in graph_data:
                        for edge_data in graph_data["edges"]:
                            start_socket_id = edge_data.get("start_socket_id")
                            end_socket_id = edge_data.get("end_socket_id")

                            # Look up new socket models from old IDs
                            start_socket_model = old_to_new_socket.get(start_socket_id)
                            end_socket_model = old_to_new_socket.get(end_socket_id)

                            if start_socket_model and end_socket_model:
                                # Validate and create edge through controller
                                edge_result = self.validate_and_create_edge(start_socket_model, end_socket_model)
                                if edge_result.success and edge_result.data:
                                    edge_model = edge_result.data
                                    # Emit event with model - view layer creates the visual
                                    self.emit("edge_model_created", edge_model)

            return SceneOperationResult(success=True)

        except Exception as exc:
            return SceneOperationResult(
                success=False,
                message=str(exc),
                code="error",
            )

    def copy_selection(self, selected_items: list) -> SceneOperationResult:
        """
        Serialize the current selection and store it in the application
        clipboard as JSON text.

        Args:
            selected_items: List of selected view items (from view)

        Currently enforces the existing restriction that only a single item
        may be copied at a time.
        """
        # Collect selected nodes directly from the view items to avoid duplicates
        selected_node_ids = set()
        selected_nodes = []
        selected_edges = []

        for item in selected_items:
            model = getattr(item, "model", None)
            # Node views carry input_sockets/output_sockets; use that to detect nodes
            if model and hasattr(model, "input_sockets") and hasattr(model, "output_sockets"):
                if model.id not in selected_node_ids:
                    selected_node_ids.add(model.id)
                    selected_nodes.append(model)

        # Include only edges whose endpoints are both in the selected node set
        if self.model.graph:
            for edge in self.model.graph.edges:
                if (
                    edge.start_node.id in selected_node_ids
                    and edge.end_node.id in selected_node_ids
                ):
                    selected_edges.append(edge)

        from sciplex_core.model.graph_model import GraphModel
        graph_data = GraphModel(nodes=selected_nodes, edges=selected_edges).serialize()

        payload = {"graph": graph_data}
        str_data = json.dumps(payload, indent=4)
        self.clipboard.set_text(str_data)

        return SceneOperationResult(success=True)

    def paste_from_clipboard(self, mouse_scene_position: Tuple[float, float]) -> SceneOperationResult:
        """
        Read text from the clipboard and paste it into the scene.

        Handles two types of content:
        1. JSON data (serialized nodes/edges) - pastes as graph elements
        2. Python function code - creates a new node from the function

        Args:
            mouse_scene_position: Tuple of (x, y) representing mouse position in scene coordinates
        """
        raw_data = self.clipboard.get_text()

        if not raw_data or not raw_data.strip():
            return SceneOperationResult(
                success=False,
                message="Clipboard is empty.",
                code="empty_clipboard",
            )

        # First, try to parse as JSON (existing node/edge copy-paste)
        try:
            data = json.loads(raw_data)
            # If it's valid JSON with graph/nodes/edges, paste it as graph data
            if isinstance(data, dict) and (
                "graph" in data or "nodes" in data or "edges" in data
            ):
                result = self.paste_graph_data(data, mouse_scene_position)
                if not result.success:
                    return result
                self._has_been_modified = True
                return SceneOperationResult(success=True)
        except (ValueError, json.JSONDecodeError):
            pass  # Not JSON, try Python code

        # Try to interpret as Python function code
        script_result = self._create_node_from_python_code(raw_data, mouse_scene_position)
        if script_result.code != "not_function":
            return script_result

        return SceneOperationResult(
            success=False,
            message="Clipboard does not contain valid node data or Python function code.",
            code="invalid_clipboard",
        )

    # ------------------------------------------------------------------
    # Python code -> Graph (MVP)
    # ------------------------------------------------------------------
    def build_graph_from_python_code(
        self, code: str, origin_pos: Tuple[float, float]
    ) -> SceneOperationResult:
        """
        Build a subgraph from a Python code block.

        MVP supports:
        - Multiple function definitions: ``def foo(...): ...``
        - A simple top-level pipeline of calls, e.g.::

              a = foo(x)
              b = bar(a)
              baz(b)

        Behavior:
        - Creates a Script node for user-defined functions that are called
        - Creates a library node for already-registered functions
        - Connects edges based on variable flow between assignments/calls
        """
        if not code or not code.strip():
            return SceneOperationResult(
                success=False, message="No code provided.", code="empty_code"
            )

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return SceneOperationResult(
                success=False, message=f"Syntax error: {exc}", code="syntax_error"
            )

        # Extract function defs (name -> def source). Use lineno/end_lineno so we
        # get only the function block (not the whole file).
        lines = code.splitlines(True)
        func_defs = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                if getattr(node, "lineno", None) and getattr(node, "end_lineno", None):
                    func_defs[node.name] = "".join(
                        lines[node.lineno - 1 : node.end_lineno]
                    )

        # Extract a simple top-level pipeline of calls
        def _call_name(call_node: ast.Call) -> Optional[str]:
            fn = call_node.func
            if isinstance(fn, ast.Name):
                return fn.id
            return None

        def _name_if_simple(expr) -> Optional[str]:
            return expr.id if isinstance(expr, ast.Name) else None

        steps = []
        for stmt in tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.Import, ast.ImportFrom)):
                continue

            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                fn = _call_name(stmt.value)
                if not fn:
                    continue

                # Support both single assignment:  out = foo(...)
                # and tuple unpacking:            out1, out2 = foo(...)
                target = stmt.targets[0]
                target_var = target.id if isinstance(target, ast.Name) else None
                target_vars = None
                if isinstance(target, (ast.Tuple, ast.List)):
                    vars_ = []
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            vars_.append(elt.id)
                    if vars_:
                        target_vars = vars_
                pos_args = [_name_if_simple(a) for a in stmt.value.args]
                kw_args = {
                    kw.arg: _name_if_simple(kw.value)
                    for kw in stmt.value.keywords
                    if kw.arg is not None
                }
                steps.append(
                    {
                        "fn": fn,
                        "target": target_var,
                        "targets": target_vars,
                        "pos_args": pos_args,
                        "kw_args": kw_args,
                    }
                )
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                fn = _call_name(stmt.value)
                if not fn:
                    continue
                pos_args = [_name_if_simple(a) for a in stmt.value.args]
                kw_args = {
                    kw.arg: _name_if_simple(kw.value)
                    for kw in stmt.value.keywords
                    if kw.arg is not None
                }
                steps.append(
                    {"fn": fn, "target": None, "pos_args": pos_args, "kw_args": kw_args}
                )

        if not steps:
            # If user provided only function definitions, still build disconnected nodes.
            if func_defs:
                from typing import List

                from sciplex_core.model.library_model import Attribute
                from sciplex_core.model.node_model import NodeModel

                ox, oy = origin_pos
                x_spacing = 320
                y_spacing = 180

                created_nodes: List[NodeModel] = []
                for idx, (fn_name, fn_src) in enumerate(func_defs.items()):
                    node_model = NodeModel(
                        title="Script",
                        icon="python",
                        parameters={"function": Attribute("codeeditor", value=fn_src)},
                        inputs=[],
                        outputs=[],
                        is_script=True,
                        library_name="_internal",
                    )
                    build_result = node_model.rebuild_sockets_from_code()
                    if not build_result.get("success", False):
                        return SceneOperationResult(
                            success=False,
                            message=build_result.get("message", f"Failed to build '{fn_name}'."),
                            code="build_error",
                        )

                    # Simple grid layout
                    node_model.update_position(
                        ox + (idx % 3) * x_spacing,
                        oy + (idx // 3) * y_spacing,
                    )
                    self.add_node_model(node_model)

                    # Emit event with model - view layer creates the visual
                    self.emit("node_model_created", node_model)

                    created_nodes.append(node_model)

                self._has_been_modified = True
                return SceneOperationResult(
                    success=True,
                    message=f"Built {len(created_nodes)} node(s) from function definitions.",
                    data={"nodes": len(created_nodes), "edges": 0},
                )

            return SceneOperationResult(
                success=False,
                message="No callable pipeline found. Add top-level calls like `x = foo(y)` or provide at least one function definition.",
                code="no_steps",
            )

        from sciplex_core.model.library_model import Attribute, library_model
        from sciplex_core.model.node_model import NodeModel

        ox, oy = origin_pos
        x_spacing = 280
        y_spacing = 160

        created = []  # [{step, model}]

        # Create node models
        for idx, step in enumerate(steps):
            fn = step["fn"]

            if fn in func_defs:
                node_model = NodeModel(
                    title="Script",
                    icon="python",
                    parameters={"function": Attribute("codeeditor", value=func_defs[fn])},
                    inputs=[],
                    outputs=[],
                    is_script=True,
                    library_name="_internal",
                )
                build_result = node_model.rebuild_sockets_from_code()
                if not build_result.get("success", False):
                    return SceneOperationResult(
                        success=False,
                        message=build_result.get("message", f"Failed to build '{fn}'."),
                        code="build_error",
                    )
            else:
                lib_item = library_model.get_library_item(fn)
                if not lib_item:
                    return SceneOperationResult(
                        success=False,
                        message=f"Unknown function '{fn}'. Define it in the code or register it as a node.",
                        code="unknown_function",
                    )
                node_model = lib_item.create_node_model()

            node_model.update_position(ox + idx * x_spacing, oy + idx * y_spacing)
            self.add_node_model(node_model)

            # Emit event with model - view layer creates the visual
            self.emit("node_model_created", node_model)

            created.append({"step": step, "model": node_model})

        # Track produced variables -> (node_model, output_index)
        produced_by = {}
        for item in created:
            step = item["step"]
            targets = step.get("targets")
            if targets:
                for out_idx, var_name in enumerate(targets):
                    produced_by[var_name] = (item["model"], out_idx)
            else:
                target = step.get("target")
                if target:
                    produced_by[target] = (item["model"], 0)

        # Helpers for wiring
        def _output_socket(producer_model: NodeModel, out_index: int = 0) -> Optional[SocketModel]:
            outs = getattr(producer_model, "output_sockets", []) or []
            if not outs:
                return None
            if 0 <= out_index < len(outs):
                return outs[out_index]
            return outs[0]

        def _input_socket_for(node_model: NodeModel, param_name: Optional[str], pos_index: Optional[int]) -> Optional[SocketModel]:
            if param_name:
                return next((s for s in node_model.input_sockets if s.name == param_name), None)
            if pos_index is not None and pos_index < len(node_model.input_sockets):
                return node_model.input_sockets[pos_index]
            if len(node_model.input_sockets) == 1:
                return node_model.input_sockets[0]
            return None

        # Create edges
        for item in created:
            step = item["step"]
            node_model = item["model"]

            # Positional args
            for i, var in enumerate(step.get("pos_args") or []):
                if not var or var not in produced_by:
                    continue
                producer, out_idx = produced_by[var]
                start_socket_model = _output_socket(producer, out_idx)
                end_socket_model = _input_socket_for(node_model, None, i)
                if not start_socket_model or not end_socket_model:
                    continue

                edge_result = self.validate_and_create_edge(start_socket_model, end_socket_model)
                if not (edge_result.success and edge_result.data):
                    continue
                edge_model = edge_result.data
                self.add_edge_model(edge_model)

                # Emit event with model - view layer creates the visual
                self.emit("edge_model_created", edge_model)

            # Keyword args
            for param_name, var in (step.get("kw_args") or {}).items():
                if not var or var not in produced_by:
                    continue
                producer, out_idx = produced_by[var]
                start_socket_model = _output_socket(producer, out_idx)
                end_socket_model = _input_socket_for(node_model, param_name, None)
                if not start_socket_model or not end_socket_model:
                    continue

                edge_result = self.validate_and_create_edge(start_socket_model, end_socket_model)
                if not (edge_result.success and edge_result.data):
                    continue
                edge_model = edge_result.data
                self.add_edge_model(edge_model)

                # Emit event with model - view layer creates the visual
                self.emit("edge_model_created", edge_model)

        self._has_been_modified = True
        return SceneOperationResult(
            success=True,
            message=f"Built graph with {len(created)} node(s) from code.",
            data={"nodes": len(created)},
        )

    def _create_node_from_python_code(self, code: str, mouse_scene_position: Tuple[float, float]) -> SceneOperationResult:
        """
        Create a Script node from pasted Python function code.

        Creates a Script node, sets the code as parameter, and builds it.
        """
        import ast

        # Ensure there's at least one function definition
        try:
            tree = ast.parse(code)
            func_def = next((n for n in tree.body if isinstance(n, ast.FunctionDef)), None)
            if not func_def:
                return SceneOperationResult(
                    success=False,
                    message="Clipboard code does not contain a function definition.",
                    code="not_function",
                )
        except SyntaxError as exc:
            return SceneOperationResult(
                success=False,
                message=f"Syntax error in function code: {exc}",
                code="syntax_error",
            )

        # Create a Script node (try library first, then internal fallback)
        result = self.create_node_model("Script")
        if result.success:
            node_model = result.data
        else:
            from sciplex_core.model.library_model import Attribute
            from sciplex_core.model.node_model import NodeModel
            try:
                from sciplex_core.libraries.default.machine_learning import SCRIPT_DEFAULT_CODE
            except Exception:
                SCRIPT_DEFAULT_CODE = "def my_function(data):\n    return data"
            node_model = NodeModel(
                title="Script",
                icon="python",
                parameters={"function": Attribute("codeeditor", value=SCRIPT_DEFAULT_CODE)},
                inputs=[],
                outputs=[],
                is_script=True,
                library_name="Script",
            )

        # Set the pasted code as the function parameter
        node_model.parameters["function"].value = code.strip()

        # Build the script (parse code and create sockets)
        build_result = node_model.rebuild_sockets_from_code()
        if not build_result["success"]:
            return SceneOperationResult(
                success=False,
                message=build_result["message"],
                code="build_error",
            )

        # Position; the view will add the node model to the graph when it creates the NodeView
        node_model.update_position(mouse_scene_position[0], mouse_scene_position[1])

        self._has_been_modified = True

        function_name = build_result.get("function_name", "Script")
        return SceneOperationResult(
            success=True,
            message=f"Created script node '{function_name}' from pasted code.",
            data={"function_name": function_name, "node_model": node_model}
        )

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------
    def create_node_model(self, node_name: str) -> SceneOperationResult:
        """
        Construct a new NodeModel instance for the given registered node name.

        The actual view object (NodeView / DisplayNodeView / CustomDisplayNodeView)
        is created on the UI side; this method is responsible only for
        resolving and instantiating the underlying model.
        """
        library_item = library_model.get_library_item(node_name)
        if library_item is None:
            return SceneOperationResult(success=False, message=f"Unknown node type '{node_name}'.", code="unknown_node")

        node_model = library_item.create_node_model()
        return SceneOperationResult(success=True, data=node_model)

    def add_node_model(self, node_model) -> None:
        """Add a node model to the current graph."""
        if not self.model.graph:
            self.model.graph = GraphModel()
            self._update_graph_controller_ref()
        self.model.graph.add_node(node_model)

    def remove_node_model(self, node_model) -> None:
        """Remove a node model from the current graph, if present."""
        if self.model.graph:
            self.model.graph.remove_node(node_model)

    def add_edge_model(self, edge_model) -> None:
        """Add an edge model to the current graph."""
        if not self.model.graph:
            self.model.graph = GraphModel()
            self._update_graph_controller_ref()
        self.model.graph.add_edge(edge_model)

    def remove_edge_model(self, edge_model) -> None:
        """Remove an edge model from the current graph."""
        if self.model.graph:
            self.model.graph.remove_edge(edge_model)

    def add_annotation_model(self, annotation_model) -> None:
        """Add an annotation to the scene model."""
        self.model.add_scene_annotation(annotation_model)

    def remove_annotation_model(self, annotation_model) -> None:
        """Remove an annotation from the scene model."""
        self.model.remove_annotation(annotation_model)

    # ------------------------------------------------------------------
    # Edge validation and creation
    # ------------------------------------------------------------------

    def validate_and_create_edge(
        self, source_socket_model: SocketModel, target_socket_model: SocketModel
    ) -> SceneOperationResult:
        """
        Validate that two sockets can be connected and create an EdgeModel if valid.

        Delegates to EdgeController for validation logic.
        """
        edge_controller = EdgeController()
        result = edge_controller.validate_connection(source_socket_model, target_socket_model)

        if result.success:
            return SceneOperationResult(success=True, data=result.data)
        else:
            return SceneOperationResult(
                success=False,
                message=result.message,
                code=result.code,
            )

    # ------------------------------------------------------------------
    # Save operations
    # ------------------------------------------------------------------

    def save_current_project(self, project_name: Optional[str] = None, node_positions: Optional[list] = None) -> SceneOperationResult:
        """
        Save the current project to disk.

        If ``project_name`` is provided and the current filepath is empty,
        creates a new project file. Otherwise saves to the existing filepath.

        Args:
            project_name: Optional project name for new projects
            node_positions: Optional list of (node_model, x, y) tuples to update positions
        """
        # Update node positions if provided
        if node_positions:
            for node_model, x, y in node_positions:
                self.update_node_position(node_model, x, y)

        # Allow saving even if no graph exists; serialize will emit graph=None
        if not self.model.graph:
            self.model.graph = None

        # Determine save path
        if project_name:
            save_path = os.path.join(
                self.base_dir, "data", "user", "projects", f"{project_name}.json"
            )
            self.model.filepath = save_path
        elif not self.model.filepath:
            return SceneOperationResult(
                success=False,
                message="No filepath set and no project name provided.",
                code="no_filepath",
            )
        else:
            save_path = self.model.filepath

        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # Check if file exists (for new projects)
            if project_name and os.path.exists(save_path):
                return SceneOperationResult(
                    success=False,
                    message=f"Project '{project_name}' already exists.",
                    code="file_exists",
                )

            # Serialize and save the full scene (graph + annotations)
            scene_data = self.model.serialize()
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(scene_data, f, indent=2)

            self._has_been_modified = False

            return SceneOperationResult(success=True, data=save_path)

        except Exception as exc:
            return SceneOperationResult(
                success=False,
                message=str(exc),
                code="error",
            )

    def save_current_project_overwrite(
        self, project_name: str, node_positions: Optional[list] = None
    ) -> SceneOperationResult:
        """
        Save the current project, overwriting an existing file if it exists.

        This is used when the user explicitly confirms they want to overwrite.

        Args:
            project_name: Project name
            node_positions: Optional list of (node_model, x, y) tuples to update positions
        """
        # Update node positions if provided
        if node_positions:
            for node_model, x, y in node_positions:
                self.update_node_position(node_model, x, y)

        # Allow saving even if no graph exists; serialize will emit graph=None
        if not self.model.graph:
            self.model.graph = None

        save_path = os.path.join(
            self.base_dir, "data", "user", "projects", f"{project_name}.json"
        )
        self.model.filepath = save_path

        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # Serialize and save the full scene (graph + annotations)
            scene_data = self.model.serialize()
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(scene_data, f, indent=2)

            self._has_been_modified = False

            return SceneOperationResult(success=True, data=save_path)

        except Exception as exc:
            return SceneOperationResult(
                success=False,
                message=str(exc),
                code="error",
            )

    # ------------------------------------------------------------------
    # Export operations
    # ------------------------------------------------------------------
    def export_graph_as_python_code(self) -> SceneOperationResult:
        """
        Export the current graph as a Python script.

        Returns:
            SceneOperationResult with data={"code": str, "warnings": list[str]}
        """
        try:
            from sciplex_core.utils.graph_export import export_graph_to_python_code

            exported = export_graph_to_python_code(self.model, base_dir=self.base_dir)
            return SceneOperationResult(
                success=True,
                data={"code": exported.code, "warnings": exported.warnings},
            )
        except Exception as exc:
            return SceneOperationResult(
                success=False,
                message=str(exc),
                code="export_error",
            )




