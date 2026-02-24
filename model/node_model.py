from dataclasses import dataclass

from sciplex_core.model.base import BaseModel
from sciplex_core.model.socket_model import LEFT, RIGHT, SocketModel

READY = 0
FAILED = -1
EXECUTED = 1


@dataclass
class InputOutputInfo:
    name: str
    description: str
    data_type: any


class NodeAttribute:
    def __init__(
        self,
        value=None,
    ):
        self.value = value

    def serialize(self):
        return {
            "value": self.value,
        }

    @classmethod
    def deserialize(cls, data):
        return cls(
            value=data.get("value"),
        )


class NodeModel(BaseModel):
    """
    Model for a node in the graph.

    Pure data model - controllers mutate this model and emit events.
    Models should not call back into controllers.
    """

    def __init__(
        self,
        icon="icon",
        title="NodeTitle",
        parameters=None,
        inputs=None,
        outputs=None,
        is_script=False,
        library_name: str = None,
    ):
        BaseModel.__init__(self)
        self.title = title
        self.parameters = parameters if parameters is not None else {}
        self.inputs = list(inputs) if inputs is not None else []
        self.outputs = list(outputs) if outputs is not None else []
        self.executed = False
        self.failed = False
        self.icon = icon
        self.pos_x = None
        self.pos_y = None
        self.is_selected = False
        self.is_script = is_script  # True for inline script nodes
        self.library_name = library_name
        self.hide_for_presentation = False  # Hide in presentation mode
        # Size for resizable nodes (e.g., Display nodes)
        self.width = None  # Width in pixels
        self.height = None  # Height in pixels
        self._init_sockets()

    def clear(self):
        for socket in self.output_sockets + self.input_sockets:
            socket.clear()

    @property
    def execute_fn(self):
        # Check if execute function was set directly (for internal nodes)
        if hasattr(self, '_execute_fn'):
            return self._execute_fn

        # Special handling for Script nodes - compile from stored code
        if self.is_script and "function" in self.parameters:
            return self._get_script_function()

        from sciplex_core.model.library_model import library_model
        library_item = library_model.get_library_item(self.title)
        if library_item is None:
            return None
        return library_item.execute_fn

    def _get_script_function(self):
        """Compile and return the function from the script code parameter."""
        import numpy as np
        import pandas as pd

        from sciplex import workspace, llm

        code = self.parameters.get("function")
        if not code or not code.value:
            return None

        code_str = code.value.strip()
        if not code_str:
            return None

        # Create execution namespace with common imports (llm for agent nodes)
        namespace = {
            "pd": pd,
            "np": np,
            "workspace": workspace,
            "llm": llm,
            "__builtins__": __builtins__,
        }

        try:
            # Try to import optional modules
            try:
                import sklearn
                namespace["sklearn"] = sklearn
            except ImportError:
                pass

            # Execute the code to define the function
            exec(code_str, namespace)

            # Find the function (first callable that's not a builtin)
            for name, obj in namespace.items():
                if callable(obj) and not name.startswith("_") and name not in ("pd", "np", "plt", "sklearn"):
                    return obj

            return None
        except Exception as e:
            print(f"Error compiling script: {e}")
            return None

    @property
    def description(self):
        # Script nodes have custom descriptions
        if self.is_script:
            func = self._get_script_function()
            if func and func.__doc__:
                return func.__doc__.split('\n')[0].strip()
            return "Custom script node"

        from sciplex_core.model.library_model import library_model
        library_item = library_model.get_library_item(self.title)
        if library_item:
            return library_item.description
        return ""

    @property
    def category(self):
        """Get the node's library name (legacy alias)."""
        if self.library_name:
            return self.library_name
        from sciplex_core.model.library_model import library_model
        library_item = library_model.get_library_item(self.title)
        if library_item:
            return library_item.library_name
        return "Custom"

    def _init_sockets(self):
        """
        Initialize input and output sockets from the node's input/output definitions.

        NOTE: Docstring parsing is kept here for initialization, but could be moved
        to a factory in the future for better MVC separation.
        """
        self.input_sockets = []
        self.output_sockets = []

        # Create input sockets
        new_inputs = []
        for i in self.inputs:
            if isinstance(i, tuple):
                socket_name, data_type = i
            else:
                socket_name, data_type = i.name, i.data_type
            input_socket = SocketModel(
                node=self, name=socket_name, position=LEFT, data_type=data_type
            )
            input_socket.parse_from_node_description()
            self.input_sockets.append(input_socket)
            new_inputs.append(
                InputOutputInfo(
                    name=socket_name,
                    description=input_socket.description,
                    data_type=data_type,
                )
            )
        self.inputs = new_inputs

        # Create output sockets
        new_outputs = []
        for o in self.outputs:
            if isinstance(o, tuple):
                socket_name, data_type = o
            else:
                socket_name, data_type = o.name, o.data_type
            output_socket = SocketModel(
                node=self, name=socket_name, position=RIGHT, data_type=data_type
            )
            output_socket.parse_from_node_description()
            self.output_sockets.append(output_socket)
            new_outputs.append(
                InputOutputInfo(
                    name=socket_name,
                    description=output_socket.description,
                    data_type=data_type,
                )
            )
        self.outputs = new_outputs

    def set_input_data(self, socket_name, data):
        """Set input data for a socket."""
        for socket in self.input_sockets:
            if socket.name == socket_name:
                socket.set_data(data)
                break


    def update_position(self, x, y):
        self.pos_x = x
        self.pos_y = y

    def detach_edge(self, edge_id):
        removed = False
        for socket in self.input_sockets:
            for edge in list(socket.edges):
                if edge.id == edge_id:
                    socket.edges.remove(edge)
                    removed = True
                    break
            if removed:
                break

        if not removed:
            for socket in self.output_sockets:
                for edge in list(socket.edges):
                    if edge.id == edge_id:
                        socket.edges.remove(edge)
                        removed = True
                        break
                if removed:
                    break


    # Note: save() method has been removed.
    # Use NodeRegistryController.register_custom_node() instead.
    # This method was deprecated and is now fully removed for MVC compliance.

    def serialize(self):
        # Minimal, view-independent snapshot
        return {
            "id": self.id,
            "title": self.title,
            "icon": self.icon,
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
            "subtitle": getattr(self, "subtitle", None),
            "library_name": getattr(self, "library_name", None),
            "is_script": self.is_script,
            "is_selected": self.is_selected,
            "hide_for_presentation": getattr(self, "hide_for_presentation", False),
            "executed": getattr(self, "executed", False),
            "failed": getattr(self, "failed", False),
            "input_sockets": [s.serialize() for s in self.input_sockets],
            "output_sockets": [s.serialize() for s in self.output_sockets],
            # Store only parameter values (keep code for scripts)
            "parameters": {name: attr.value for name, attr in self.parameters.items()},
            # Store size for resizable nodes (e.g., Display nodes)
            "width": getattr(self, "width", None),
            "height": getattr(self, "height", None),
        }

    def __str__(self):
        return f"Node(id={self.id}, name={getattr(self, 'name', 'Unnamed')})"

    @classmethod
    def deserialize(cls, data, restore_id=True):
        """
        Deserialize a NodeModel from dictionary data.

        NOTE: This method accesses node_registry to get the factory function.
        This is acceptable for deserialization as it's a read-only operation
        during object construction. However, custom node updates should be
        handled by NodeController after deserialization.
        """
        title = data.get("title")
        is_script = data.get("is_script", False)
        if not title:
            return None

        # Get factory from registry (read-only operation)
        from sciplex_core.model.library_model import library_model

        # Special handling for Display nodes and Script nodes (internal, not in public library)
        if title == "Display":
            # Create display node directly
            def embedded_display_execute(data):
                """Pass-through function for display - just returns input."""
                return data

            node_model = NodeModel(
                title="Display",
                icon="",
                inputs=[("data", object)],  # Generic input type
                outputs=[],
                library_name="Display",
            )
            node_model._execute_fn = embedded_display_execute
        elif is_script:
            # Create script node directly (not from library lookup)
            from sciplex_core.model.library_model import Attribute
            from sciplex_core.utils.script_node import SCRIPT_DEFAULT_CODE

            # Get function code from serialized parameters, or use default
            params_data = data.get("parameters", {}) or {}
            function_code = params_data.get("function", SCRIPT_DEFAULT_CODE)

            node_model = NodeModel(
                title=title,  # Preserve custom title from serialization
                icon="python",
                parameters={"function": Attribute("codeeditor", value=function_code)},
                inputs=[],
                outputs=[],
                is_script=True,
                library_name="_internal",
            )
        else:
            # Regular library nodes: lookup from library
            library_item = library_model.get_library_item(title)
            if not library_item:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"NodeModel.deserialize: Library item '{title}' not found. "
                    f"Available items: {sorted(list(library_model.get_library_items().keys()))[:20]}..."
                )
                return None
            node_model = library_item.create_node_model()

            # Verify that parameters are Attribute objects (they should be from create_node_model)
            import logging
            logger = logging.getLogger(__name__)
            for param_name, param_attr in node_model.parameters.items():
                if not hasattr(param_attr, 'value') or not hasattr(param_attr, 'widget'):
                    logger.warning(
                        f"NodeModel.deserialize: Parameter '{param_name}' in node '{title}' is not an Attribute object "
                        f"after create_node_model(). Type: {type(param_attr)}"
                    )

        # Restore custom title for script nodes
        if is_script:
            node_model.title = title
            node_model.is_script = True

        # Restore position
        node_model.update_position(data.get("pos_x"), data.get("pos_y"))

        # Restore parameters (values only; widget/options come from library template)
        params_data = data.get("parameters", {}) or {}
        import logging
        logger = logging.getLogger(__name__)

        for name, val in params_data.items():
            if name in node_model.parameters:
                # Ensure the parameter is still an Attribute object with correct widget/options
                # (it should be from library definition, but verify and restore if needed)
                param_attr = node_model.parameters[name]
                if not hasattr(param_attr, 'value') or not hasattr(param_attr, 'widget'):
                    # Parameter lost its Attribute structure - restore from library definition
                    logger.warning(f"Parameter '{name}' lost Attribute structure for node '{title}', restoring from library")
                    if not is_script:
                        # Try to get from library item again
                        library_item = library_model.get_library_item(title if not is_script else "Script")
                        if library_item and name in library_item.parameters:
                            from sciplex_core.model.library_model import Attribute
                            orig_attr = library_item.parameters[name]
                            import copy
                            node_model.parameters[name] = Attribute(
                                widget=orig_attr.widget,
                                value=val,
                                options=copy.deepcopy(orig_attr.options) if orig_attr.options else None,
                                range=orig_attr.range,
                                source=orig_attr.source,
                                extractor=orig_attr.extractor
                            )
                        else:
                            # Fallback: create basic Attribute
                            from sciplex_core.model.library_model import Attribute
                            node_model.parameters[name] = Attribute("text", value=val)
                    else:
                        # Script node - use codeeditor for function, lineedit for others
                        from sciplex_core.model.library_model import Attribute
                        widget_type = "codeeditor" if name == "function" else "lineedit"
                        node_model.parameters[name] = Attribute(widget_type, value=val)
                else:
                    # Parameter is valid Attribute object - just update the value
                    # For script nodes, the "function" parameter needs special handling
                    if is_script and name == "function":
                        if "function" not in node_model.parameters:
                            from sciplex_core.model.library_model import Attribute
                            node_model.parameters["function"] = Attribute("codeeditor", value=val)
                        else:
                            node_model.parameters[name].value = val
                    else:
                        node_model.parameters[name].value = val
            else:
                # Parameter not in template - add it (might be custom parameter for script node)
                from sciplex_core.model.library_model import Attribute
                # Try to infer widget type: if it's code-like, use codeeditor, otherwise lineedit
                widget_type = "codeeditor" if is_script and name == "function" else "lineedit"
                node_model.parameters[name] = Attribute(widget_type, value=val)
                if is_script:
                    logger.debug(f"Added custom parameter '{name}' to script node '{title}'")

        # Restore subtitle
        if data.get("subtitle"):
            node_model.subtitle = data.get("subtitle")

        # Restore hide_for_presentation flag
        node_model.hide_for_presentation = data.get("hide_for_presentation", False)

        # Restore size for Display nodes (if present)
        if title == "Display":
            node_model.width = data.get("width")
            node_model.height = data.get("height")

        # Restore execution state (executed/failed flags) - preserve execution status when copying/pasting
        node_model.executed = data.get("executed", False)
        node_model.failed = data.get("failed", False)

        # For non-script nodes: sockets are already correctly initialized from library definition
        # (with correct data types). Only restore sockets from serialized data for script nodes
        # which may have custom socket definitions.
        if is_script or title == "Display":
            # Script/Display nodes: restore sockets from serialized data (may have custom socket definitions)
            node_model.input_sockets.clear()
            node_model.output_sockets.clear()

            node_model.input_sockets = [
                SocketModel.deserialize(node_model, s, restore_id=restore_id) for s in data.get("input_sockets", [])
            ]
            node_model.output_sockets = [
                SocketModel.deserialize(node_model, s, restore_id=restore_id) for s in data.get("output_sockets", [])
            ]
        else:
            # For non-script nodes: sockets are already correctly initialized from library definition
            # (with correct data types), but we need to restore socket IDs from serialized data
            # so that edges can reconnect properly when restore_id=True
            if restore_id:
                # Create mapping of socket names to serialized socket data
                serialized_input_sockets = {s.get("name"): s for s in data.get("input_sockets", [])}
                serialized_output_sockets = {s.get("name"): s for s in data.get("output_sockets", [])}

                # Restore socket IDs by matching by name
                for socket in node_model.input_sockets:
                    if socket.name in serialized_input_sockets:
                        serialized_socket = serialized_input_sockets[socket.name]
                        if "id" in serialized_socket:
                            socket.id = serialized_socket["id"]
                            # Also restore position if present
                            if "position" in serialized_socket:
                                socket.position = serialized_socket["position"]

                for socket in node_model.output_sockets:
                    if socket.name in serialized_output_sockets:
                        serialized_socket = serialized_output_sockets[socket.name]
                        if "id" in serialized_socket:
                            socket.id = serialized_socket["id"]
                            # Also restore position if present
                            if "position" in serialized_socket:
                                socket.position = serialized_socket["position"]

        # Re-extract socket descriptions from library item docstring (like desktop version)
        # This ensures descriptions are always up-to-date from the library item
        for socket in node_model.input_sockets + node_model.output_sockets:
            socket.parse_from_node_description()

        # Restore ID
        if restore_id and "id" in data:
            node_model.id = data["id"]

        # Note: Custom node update (obj.update()) should be handled by controller
        # after deserialization if needed. This keeps the model focused on data restoration.

        return node_model

    def _get_input_sockets_data(self):
        inputs = {}
        var_args = []
        for socket in self.input_sockets:
            if socket.edges:
                if socket.multiple_edges:
                    for edge in socket.edges:
                        data = edge.start_socket.get_data()
                        var_args.append(data)
                else:
                    edge = socket.edges[0]
                    data = edge.start_socket.get_data()
                    inputs[socket.name] = data
            else:
                inputs[socket.name] = None
        if var_args:
            inputs["*"] = var_args
        return inputs

    def _write_to_output_sockets(self, data):
        if not isinstance(data, tuple):
            data = [data]
        for socket, value in zip(self.output_sockets, data):
            socket.set_data(value)

    def _get_parameters(self):
        return {k: v.value for k, v in self.parameters.items() if k!="function"} # exception is for nodifying functions in python nodes

    def update_parameter(self, key, value, trigger=True):
        if key in self.parameters:
            self.parameters[key].value = value

    def _validate_pylineedit_parameter(self, param_name: str, param_attr) -> None:
        """
        Validate a pylineedit parameter value during execution.

        If the value is still a string (not parsed), it means validation failed earlier.
        We try to parse it again, and if it fails, we raise an error to prevent execution.

        Raises ValueError if the value is invalid.
        """
        if param_attr.widget != "pylineedit":
            return

        value = param_attr.value

        # If value is a string, it might be:
        # 1. A valid string literal that was parsed (e.g., user entered '"abc"' -> string "abc")
        # 2. An invalid expression that couldn't be parsed (e.g., user entered "abc" without quotes)
        #
        # To distinguish, we check if it's a simple string that looks like it should have been
        # a literal. If it's a bare identifier (like "abc"), it's invalid.
        # If it's a quoted string (like '"abc"'), it would have been parsed already.
        #
        # Actually, simpler: if validation failed in update_node_parameter, the raw string
        # is stored. During execution, we try to parse it again. If it's a valid string literal,
        # it will parse successfully and we can update the value. If it fails, we raise an error.

        if isinstance(value, str):
            import ast
            expr_str = value.strip()

            # Try to parse as Python literal first
            try:
                parsed_value = ast.literal_eval(expr_str)
                # If successful, update the value (it was a valid literal that somehow wasn't parsed)
                param_attr.value = parsed_value
                return
            except (ValueError, SyntaxError):
                pass

            # Try to evaluate as expression with workspace variables
            try:
                import numpy as np
                import pandas as pd

                from sciplex_core.utils.functions import SafeEvaluator, variables_registry

                namespace = dict(getattr(variables_registry, "data", {}) or {})
                namespace.update({"pd": pd, "np": np})

                if "=" in expr_str:
                    parts = expr_str.split("=", 1)
                    if len(parts) == 2 and parts[0].strip().isidentifier():
                        expr_str = parts[1].strip()

                tree = ast.parse(expr_str, mode='eval')
                evaluator = SafeEvaluator(namespace)
                parsed_value = evaluator.visit(tree)
                # If successful, update the value
                param_attr.value = parsed_value
                return
            except Exception as expr_error:
                # Both parsing attempts failed - this is an invalid value
                raise ValueError(
                    f"Invalid Python expression for parameter '{param_name}': '{value}'. "
                    f"Expected a Python literal (e.g., True, False, 123, [1,2,3], \"text\") "
                    f"or a valid expression with workspace variables. "
                    f"Error: {str(expr_error)}"
                )

    def execute(self):
        """
        Execute the node's computation function.

        This method performs the actual execution logic:
        - Gathers inputs from input sockets
        - Collects parameters
        - Calls the execution function
        - Writes results to output sockets
        - Updates execution state

        The controller should trigger this method, but the execution logic
        itself resides in the model.

        Raises:
            RuntimeError: If node has no execution function (except Display nodes)
            ValueError: If required inputs are not connected
            ValueError: If pylineedit parameters are invalid
            Exception: Any exception raised by the execution function
        """
        # Special handling for Display nodes - they don't need an execute function
        # They just pass through data for visualization
        is_display_node = (self.title == "Display" or
                          getattr(self, 'library_name', None) == "Display")

        if not self.execute_fn:
            if is_display_node:
                # Display nodes don't need execution - they just visualize input data
                # The data is already in the input socket, so we can skip execution
                self.executed = True
                self.failed = False
                return
            else:
                raise RuntimeError("Node has no execution function.")

        # Validate that all input sockets are connected
        for socket in self.input_sockets:
            if not socket.edges:
                raise ValueError(f"Input '{socket.name}' is not connected.")

        # Validate pylineedit parameters before execution
        for param_name, param_attr in self.parameters.items():
            if param_name != "function":  # Skip function parameter for script nodes
                self._validate_pylineedit_parameter(param_name, param_attr)

        # Gather inputs and parameters
        inputs = self._get_input_sockets_data()
        parameters = self._get_parameters()

        # Handle varargs
        args = []
        if "*" in inputs:
            args = inputs.pop("*")

        kwargs = {**inputs, **parameters}

        # Execute the function
        result = self.execute_fn(*args, **kwargs)

        # Write results to output sockets
        self._write_to_output_sockets(result)

        # Update state
        self.executed = True
        self.failed = False

    def reset(self):
        self.executed = False
        self.failed = False
        for socket in self.output_sockets:
            socket.set_data(None)

    def rebuild_sockets_from_code(self) -> dict:
        """
        Parse the script code and rebuild input/output sockets.

        Returns dict with 'success', 'message', 'function_name'.
        """
        import ast
        import inspect
        import re
        import textwrap
        from typing import get_args, get_type_hints

        code = self.parameters.get("function")
        if not code or not code.value:
            return {"success": False, "message": "No code provided"}

        code_str = code.value.strip()

        # Get the compiled function
        func = self._get_script_function()
        if func is None:
            return {"success": False, "message": "Could not compile function. Check syntax."}

        function_name = func.__name__

        try:
            sig = inspect.signature(func)
            try:
                type_hints = get_type_hints(func)
            except Exception:
                type_hints = {}

            # Parse inputs and parameters
            new_inputs = []
            new_parameters = {}

            from sciplex_core.model.library_model import Attribute

            for name, param in sig.parameters.items():
                param_type = type_hints.get(name, None)

                if param.default is not inspect.Parameter.empty:
                    # Has default → parameter widget
                    widget_type = self._infer_widget_type(param_type)
                    new_parameters[name] = Attribute(widget_type, value=param.default)
                else:
                    # No default → input socket
                    new_inputs.append((name, param_type))

            # Parse outputs from return type (or infer from source)
            return_type = type_hints.get("return", None)
            if return_type is None or return_type is type(None):
                def _infer_return_arity_from_code(src: str, fn_name: str) -> int | None:
                    """
                    Best-effort return arity inference for Script nodes from source code.

                    Rules (match utils.node_factory.get_outputs_info behavior):
                    - No explicit `return` statements -> arity 0 (no outputs)
                    - `return` (no value) -> arity 0
                    - `return x` -> arity 1
                    - `return a, b, c` -> arity N
                    - Multiple returns must agree on arity; otherwise None (don't guess)
                    """
                    try:
                        tree = ast.parse(textwrap.dedent(src))
                    except SyntaxError:
                        return None

                    func_def = next(
                        (
                            n
                            for n in ast.walk(tree)
                            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fn_name
                        ),
                        None,
                    )
                    if func_def is None:
                        return None

                    arities: list[int] = []
                    for n in ast.walk(func_def):
                        if isinstance(n, ast.Return):
                            if n.value is None:
                                arities.append(0)
                            elif isinstance(n.value, ast.Tuple):
                                arities.append(len(n.value.elts))
                            else:
                                arities.append(1)

                    if not arities:
                        return 0

                    unique = sorted(set(arities))
                    if len(unique) != 1:
                        return None
                    return unique[0]

                def _infer_tuple_output_names_from_code(src: str, fn_name: str) -> list[str] | None:
                    """
                    Best-effort: if the function returns a tuple like `return a, b`,
                    infer output socket names from the tuple element expressions.

                    Returns:
                        list[str] | None: names when tuple arity > 1 is confidently inferred;
                        otherwise None (caller should use single "result" output).
                    """
                    try:
                        tree = ast.parse(textwrap.dedent(src))
                    except SyntaxError:
                        return None

                    func_def = next(
                        (
                            n
                            for n in ast.walk(tree)
                            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fn_name
                        ),
                        None,
                    )
                    if func_def is None:
                        return None

                    arities: list[int] = []
                    tuple_returns: list[ast.Tuple] = []
                    for n in ast.walk(func_def):
                        if isinstance(n, ast.Return):
                            if n.value is None:
                                arities.append(0)
                            elif isinstance(n.value, ast.Tuple):
                                arities.append(len(n.value.elts))
                                tuple_returns.append(n.value)
                            else:
                                arities.append(1)

                    if not arities:
                        return None

                    unique = sorted(set(arities))
                    if len(unique) != 1:
                        # Inconsistent branches; do not guess.
                        return None

                    arity = unique[0]
                    if arity <= 1:
                        return None

                    # Prefer names from the first tuple-return statement.
                    t = tuple_returns[0] if tuple_returns else None
                    if t is None or len(t.elts) != arity:
                        return None

                    raw_names: list[str] = []
                    for i, elt in enumerate(t.elts):
                        name: str | None = None
                        if isinstance(elt, ast.Name):
                            name = elt.id
                        elif hasattr(ast, "unparse"):
                            try:
                                name = ast.unparse(elt)
                            except Exception:
                                name = None

                        if not name:
                            name = f"out_{i}"

                        # Sanitize to a friendly socket label
                        name = re.sub(r"[^0-9a-zA-Z_]+", "_", name).strip("_") or f"out_{i}"
                        raw_names.append(name)

                    # Ensure uniqueness
                    seen: set[str] = set()
                    names: list[str] = []
                    for i, n in enumerate(raw_names):
                        base = n
                        k = 2
                        while n in seen:
                            n = f"{base}_{k}"
                            k += 1
                        seen.add(n)
                        names.append(n or f"out_{i}")

                    return names

                arity = _infer_return_arity_from_code(code_str, function_name)
                if arity == 0:
                    new_outputs = []
                elif arity is None:
                    # Conservative fallback: keep previous behavior if we can't infer.
                    new_outputs = [("result", None)]
                elif arity == 1:
                    new_outputs = [("result", None)]
                else:
                    tuple_names = _infer_tuple_output_names_from_code(code_str, function_name)
                    if tuple_names and len(tuple_names) == arity:
                        new_outputs = [(n, None) for n in tuple_names]
                    else:
                        new_outputs = [(f"out_{i}", None) for i in range(arity)]
            elif hasattr(return_type, "__origin__") and return_type.__origin__ is tuple:
                new_outputs = [(f"out_{i}", t) for i, t in enumerate(get_args(return_type))]
            else:
                new_outputs = [("result", return_type)]

            # Keep the 'function' parameter (code editor)
            new_parameters["function"] = self.parameters["function"]

            # Update the node title to the function name
            self.title = function_name

            # Store old socket edges for reconnection attempt
            old_input_edges = {s.name: list(s.edges) for s in self.input_sockets}
            old_output_edges = {s.name: list(s.edges) for s in self.output_sockets}

            # Detach all edges first
            for socket in self.input_sockets + self.output_sockets:
                for edge in list(socket.edges):
                    socket.edges.remove(edge)

            # Update inputs/outputs
            self.inputs = new_inputs
            self.outputs = new_outputs
            self.parameters = new_parameters

            # Reinitialize sockets
            self._init_sockets()

            # Try to reconnect edges with matching names
            for socket in self.input_sockets:
                if socket.name in old_input_edges:
                    for edge in old_input_edges[socket.name]:
                        socket.edges.append(edge)
                        edge.end_socket = socket

            for socket in self.output_sockets:
                if socket.name in old_output_edges:
                    for edge in old_output_edges[socket.name]:
                        socket.edges.append(edge)
                        edge.start_socket = socket

            return {"success": True, "message": "", "function_name": function_name}

        except Exception as e:
            return {"success": False, "message": f"Error parsing function: {str(e)}"}

    def _infer_widget_type(self, type_hint) -> str:
        """Infer widget type from a type hint."""
        if type_hint is None:
            # Untyped defaults: use pythonic parsing so "2" becomes int(2), etc.
            return "pylineedit"

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


