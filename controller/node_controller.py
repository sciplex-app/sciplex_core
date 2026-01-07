"""
Controller for node-specific operations.

Handles node execution, reset, updates, and position management.
Uses EventEmitter for framework-agnostic reactive updates.
"""

import ast
import logging
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import numpy as np
import pandas as pd
import sklearn
from matplotlib.figure import Figure

from sciplex_core.controller.events import EventEmitter, SimpleEventEmitter
from sciplex_core.model.node_model import EXECUTED, FAILED, READY, NodeModel


@dataclass
class NodeOperationResult:
    """Result of a node operation."""
    success: bool
    message: Optional[str] = None
    code: Optional[str] = None


class NodeController:
    """
    Mediates node-specific operations.

    Handles execution, reset, updates, and position management for individual nodes.
    Uses EventEmitter for framework-agnostic reactive updates.
    """

    def __init__(self, node_model: NodeModel, event_emitter: Optional[EventEmitter] = None):
        """
        Initialize the node controller.

        Args:
            node_model: The node model to control
            event_emitter: Event emitter for reactive updates. If None, creates SimpleEventEmitter
        """
        self.node_model = node_model
        self.events = event_emitter if event_emitter is not None else SimpleEventEmitter()

    def execute(self) -> NodeOperationResult:
        """
        Trigger execution of the node's computation function.

        The controller triggers execution, but the actual execution logic
        is performed by NodeModel.execute(). This method handles the result
        and state updates, emitting signals as needed.

        Returns:
            NodeOperationResult indicating success or failure
        """
        try:
            logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
            logger.info(f"Executing node: {self.node_model.id} ({self.node_model.title})")
            
            # Gather inputs and parameters for logging
            inputs = self.node_model._get_input_sockets_data()
            parameters = self.node_model._get_parameters()

            # Handle varargs
            args = []
            if "*" in inputs:
                args = inputs.pop("*")

            kwargs = {**inputs, **parameters}

            # Log execution before executing
            self._log_execution(args, kwargs)

            # Trigger execution in the model (execution logic is in the model)
            self.node_model.execute()

            # Emit success event after execution
            self.on_execute_state_updated(EXECUTED, "")
            
            logger.info(f"Node execution completed: {self.node_model.id} ({self.node_model.title})")

            return NodeOperationResult(success=True)
        except RuntimeError as e:
            # Node has no execution function
            return NodeOperationResult(
                success=False,
                message=str(e),
                code="no_execute_fn",
            )
        except Exception as e:
            # Execution failed - update state and notify
            self.node_model.executed = False
            self.node_model.failed = True
            self.on_execute_state_updated(FAILED, str(e))

            # Log error
            logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
            logger.exception(f"Error executing node: {self.node_model.id} ({self.node_model.title})")

            return NodeOperationResult(
                success=False,
                message=str(e),
                code="error",
            )

    def _log_execution(self, args, kwargs):
        """Log execution details for debugging."""
        arg_descriptions = []
        for input_name, input_value in kwargs.items():
            if isinstance(input_value, pd.DataFrame):
                arg_descriptions.append(
                    f"{input_name}: {input_value.shape}: columns: {input_value.columns}"
                )
            elif isinstance(input_value, pd.Series):
                arg_descriptions.append(
                    f"{input_name}: {input_value.shape}: name: {input_value.name}"
                )
            else:
                arg_descriptions.append(f"{input_name} = {input_value}")

        for arg in args:
            if isinstance(arg, pd.Series):
                arg_descriptions.append(f"Series: {arg.shape}, {arg.name}")
            else:
                arg_descriptions.append("")

        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        logger.info(f"Executing Node {self.node_model.id}")
        logger.info("\t\tInputs:")
        for arg_desc in arg_descriptions:
            logger.info(f"\t\t\t {arg_desc}")
        logger.info("\n")

    # Event emission methods - called by controller after mutations
    def on_execute_state_updated(self, state: int, message: str):
        """Emit event when execution state changes."""
        self.events.emit("execute_state_updated", state, message, node_id=self.node_model.id)

    def on_data_updated(self, data):
        """Emit event when data is updated."""
        self.events.emit("data_updated", data)

    def on_parameter_widget_updated(self, param_name: str, options):
        """Emit event when parameter widget options change."""
        self.events.emit("parameter_widget_updated", param_name, options)

    def on_parsing_failed(self, error_message: str, line_number: int):
        """Emit event when parsing fails."""
        self.events.emit("parsing_failed", error_message, line_number)

    def on_parsing_succeeded(self):
        """Emit event when parsing succeeds."""
        self.events.emit("parsing_succeeded")

    def reset(self) -> None:
        """
        Reset the node to its initial state.

        Clears execution state and data.
        """
        self.node_model.reset()
        # Emit event after reset
        self.on_execute_state_updated(READY, "")

    def clear(self) -> None:
        """
        Clear the node's data and execution state.

        Similar to reset but may have different semantics depending on node type.
        """
        self.node_model.clear()

    def update_position(self, x: float, y: float) -> None:
        """
        Update the node's position in the scene.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        self.node_model.update_position(x, y)

    def extract_function_from_code(self, code: str) -> Tuple[Optional[Callable], Optional[str]]:
        """
        Extract a Python function from code string.

        Parses the code, validates it contains a function definition,
        executes it in a safe namespace, and returns the function and its name.

        Args:
            code: Python code string containing a function definition

        Returns:
            Tuple of (function, function_name) or (None, None) on error.
            Emits parsing_failed or parsing_succeeded signals.
        """
        func_name = "<unknown>"
        try:
            if not code:
                raise ValueError("Code string is empty")

            # Create safe namespace with common imports
            local_ns = {"pd": pd, "Fig": Figure, "np": np, "sklearn": sklearn, "tuple": tuple}

            # Parse AST
            tree = ast.parse(code)

            if not tree.body or not isinstance(tree.body[0], ast.FunctionDef):
                raise ValueError("No function definition found in code.")

            func_name = tree.body[0].name

            # Update model title
            self.node_model.title = func_name

            # Execute code in namespace
            exec(code, local_ns)

            # Get function from namespace
            func = local_ns.get(func_name)
            if callable(func):
                self.on_parsing_succeeded()
                return func, func_name
            else:
                self.node_model.failed = True
                self.on_parsing_failed(f"'{func_name}' is not callable", 0)
                return None, None

        except SyntaxError as e:
            error_message = f"Syntax Error: {e.msg} at line {e.lineno}"
            logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
            logger.error(error_message)
            self.on_parsing_failed(error_message, e.lineno - 1)
            self.node_model.failed = True
            return None, None
        except Exception as e:
            error_message = f"Error extracting function '{func_name}': {e}"
            self.node_model.failed = True
            logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
            logger.exception(error_message)
            self.on_parsing_failed(error_message, 0)
            return None, None

    def set_input_data(self, socket_name: str, data) -> None:
        """
        Set input data for a specific socket.

        Args:
            socket_name: Name of the input socket
            data: Data to set
        """
        self.node_model.set_input_data(socket_name, data)
        # Emit data updated event
        self.on_data_updated(data)
        # Handle input change for business logic (extractors, etc.)
        self.handle_input_changed(socket_name, data)

    def handle_input_changed(self, socket_name: str, data) -> None:
        """
        Handle input data change - applies extractor logic and updates parameter options.

        This method contains business logic that was previously in NodeModel.on_input_changed().

        Args:
            socket_name: Name of the socket that received new data
            data: The new data
        """
        from sciplex_core.utils.ui_updaters import EXTRACTOR_REGISTRY

        # Check if any parameters are sourced from this socket
        for param_name, attr in self.node_model.parameters.items():
            if attr.source == socket_name:
                # Apply extractor if available
                if attr.extractor and attr.extractor in EXTRACTOR_REGISTRY:
                    extractor_func = EXTRACTOR_REGISTRY[attr.extractor]
                    new_options = extractor_func(data)
                    attr.options = new_options

                    # Set default value if none yet
                    if attr.value is None and new_options:
                        attr.value = new_options[0]

                    # Notify view of parameter widget update
                    self.on_parameter_widget_updated(param_name, new_options)

    def set_icon(self, icon: str) -> None:
        """
        Set the node's icon.

        Args:
            icon: Icon identifier
        """
        self.node_model.icon = icon

    def set_selected(self, selected: bool) -> None:
        """
        Set the node's selection state.

        Args:
            selected: Whether the node is selected
        """
        self.node_model.is_selected = selected


