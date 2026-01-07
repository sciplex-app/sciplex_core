"""
Controller for edge-specific operations.

Handles edge validation, creation, and management.
"""

from dataclasses import dataclass
from typing import Optional, Union, get_args, get_origin

from sciplex_core.model.edge_model import EdgeModel
from sciplex_core.model.socket_model import SocketModel


@dataclass
class EdgeOperationResult:
    """Result of an edge operation."""
    success: bool
    message: Optional[str] = None
    code: Optional[str] = None
    data: Optional[EdgeModel] = None


class EdgeController:
    """
    Mediates edge-specific operations.

    Handles edge validation, creation, and connection management.
    """

    def __init__(self, edge_model: Optional[EdgeModel] = None):
        self.edge_model = edge_model

    def validate_connection(
        self, source_socket: SocketModel, target_socket: SocketModel
    ) -> EdgeOperationResult:
        """
        Validate that two sockets can be connected.

        Performs all business logic checks:
        - Sockets must be on different positions (input vs output)
        - Cannot connect a node to itself
        - Type compatibility check
        - Target socket capacity check (unless it's a wildcard "*" socket)

        Returns an EdgeOperationResult with success=True and data=edge_model if valid,
        or success=False with an appropriate error message/code.
        """
        # Check socket positions (must be different - input vs output)
        if source_socket.position == target_socket.position:
            return EdgeOperationResult(
                success=False,
                message="Cannot connect sockets on the same side.",
                code="same_position",
            )

        # Cannot connect node to itself
        if source_socket.node.id == target_socket.node.id:
            return EdgeOperationResult(
                success=False,
                message="Cannot connect node with itself.",
                code="self_connection",
            )

        # Type compatibility check
        source_types = source_socket.data_type
        target_types = target_socket.data_type

        source_types_set = (
            set(get_args(source_types))
            if get_origin(source_types) is Union
            else set([source_types])
        )
        target_types_set = (
            set(get_args(target_types))
            if get_origin(target_types) is Union
            else set([target_types])
        )

        type_overlap = source_types_set & target_types_set

        # Check target socket capacity (unless it's a wildcard "*" socket)
        if target_socket.name != "*":
            if target_socket.edges:
                return EdgeOperationResult(
                    success=False,
                    message=f"{target_socket.node.title}'s {target_socket.name} only accepts one input.",
                    code="socket_full",
                )

            # Type mismatch check (allow None types to pass through)
            if (
                not type_overlap
                and target_types_set != {None}
                and source_types_set != {None}
            ):
                return EdgeOperationResult(
                    success=False,
                    message="Data types don't match.",
                    code="type_mismatch",
                )

        # All checks passed - create the edge
        try:
            edge_model = EdgeModel(source_socket, target_socket)
            return EdgeOperationResult(success=True, data=edge_model)
        except Exception as exc:
            return EdgeOperationResult(
                success=False,
                message=str(exc),
                code="error",
            )

    def disconnect(self) -> None:
        """
        Disconnect the edge from its sockets.

        Removes the edge from both start and end socket edge lists.
        """
        if self.edge_model:
            self.edge_model.disconnect()

