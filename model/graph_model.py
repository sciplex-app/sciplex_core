import uuid

import networkx as nx

from sciplex_core.model.base import BaseModel
from sciplex_core.model.edge_model import EdgeModel
from sciplex_core.model.node_model import NodeModel

# Note: GraphModel.execute() creates temporary NodeControllers for execution.
# In a pure MVC architecture, execution orchestration would be in SceneController.
# This is kept here for now to maintain existing functionality.

class GraphModel(BaseModel):
    def __init__(self, nodes=None, edges=None):
        super().__init__()
        self.nodes = list(nodes) if nodes is not None else []
        self.edges = list(edges) if edges is not None else []
        self._nx_graph = None
        self.sorted_nodes = None

    def clear(self):
        self.logger.info(f"Clearing Graph with id: {self.id}")
        self.nodes.clear()  # Use .clear() instead of = []
        self.edges.clear()  # Use .clear() instead of = []
        self.sorted_nodes = None
        self._nx_graph = None

    def build_nx_graph(self):
        # Skip if already built (use cache)
        if self._nx_graph is not None:
            import traceback
            self.logger.warning(
                f"build_nx_graph() called but graph already built. "
                f"Call stack:\n{''.join(traceback.format_stack()[-5:-1])}"
            )
            return
        
        self.logger.info("Building NetworkX Graph.")
        g = nx.DiGraph()
        for node in self.nodes:
            g.add_node(node.id, obj=node)
        for edge in self.edges:
            g.add_edge(
                edge.start_node.id, edge.end_node.id, obj=edge
            )  # for topological sort we're only interested in the node level connection not the socket-level connections
        self._nx_graph = g

    def topological_sort(self):
        if self._nx_graph is None:
            self.build_nx_graph()
        # Only sort if not already cached
        if self.sorted_nodes is not None:
            return
        self.logger.info(f"Sorting Graph :{self.id} topologically.")
        try:
            sorted_node_ids = list(nx.topological_sort(self._nx_graph))
            self.sorted_nodes = [
                self._nx_graph.nodes[n]["obj"] for n in sorted_node_ids
            ]

        except nx.NetworkXUnfeasible:
            self.logger.error("Graph contains cycles, cannot perform topological sort")
            self.sorted_nodes = None
            return None

    def execute_up_to_node(self, target_node):
        """
        Execute nodes up to a target node.
        
        NOTE: This method is deprecated. Use SceneController.execute_up_to_node() instead.
        This method is kept for backward compatibility but will be removed.
        """
        self.logger.warning(
            "GraphModel.execute_up_to_node() is deprecated. "
            "Use SceneController.execute_up_to_node() instead."
        )
        # Delegate to scene controller if available
        if hasattr(self, '_scene_controller_ref'):
            scene_controller = self._scene_controller_ref()
            if scene_controller:
                result = scene_controller.execute_up_to_node(target_node)
                return result
        
        # Fallback: raise error to force migration
        raise RuntimeError(
            "GraphModel.execute_up_to_node() is no longer supported. "
            "Use SceneController.execute_up_to_node() instead."
        )

    def add_node(self, node):
        # Prevent accidental double-add (e.g., controller + view both adding same model)
        if any(getattr(n, "id", None) == getattr(node, "id", None) for n in self.nodes):
            self.logger.warning(f"Skipped duplicate node add: {getattr(node, 'id', None)}")
            return
        self.nodes.append(node)
        # Invalidate cache so graph is rebuilt with new node
        self._nx_graph = None
        self.sorted_nodes = None



    def remove_node(self, node):
        if node in self.nodes:
            # Remove all edges connected to this node
            edges_to_remove = [
                edge for edge in self.edges
                if edge.start_node.id == node.id or edge.end_node.id == node.id
            ]
            for edge in edges_to_remove:
                self.remove_edge(edge)
            
            # Remove the node itself
            self.nodes.remove(node)
            self.sorted_nodes = None
            self._nx_graph = None

    def remove_edge(self, edge):
        if edge in self.edges:
            self.edges.remove(edge)
            # Disconnect edge from sockets to clean up references
            if hasattr(edge, 'disconnect'):
                edge.disconnect()
            self.sorted_nodes = None
            self._nx_graph = None
        for node in self.nodes:
            node.detach_edge(edge.id)


    def add_edge(self, edge):
        self.edges.append(edge)
        # Invalidate cache so graph is rebuilt with new edge
        self._nx_graph = None
        self.sorted_nodes = None

    def is_dag(self):
        # Only build/sort if not already cached
        if self._nx_graph is None:
            self.build_nx_graph()
        if self.sorted_nodes is None:
            self.topological_sort()
        return nx.is_directed_acyclic_graph(self._nx_graph)

    def execute(self):
        """
        Execute all nodes in the graph in topological order.

        NOTE: This method is deprecated. Use SceneController.execute_graph() instead.
        This method is kept for backward compatibility but will be removed.
        Models should not import controllers - this violates MVC separation.
        """
        self.logger.warning(
            "GraphModel.execute() is deprecated. Use SceneController.execute_graph() instead. "
            "This method will be removed in a future version."
        )
        # Delegate to scene controller if available
        if hasattr(self, '_scene_controller_ref'):
            scene_controller = self._scene_controller_ref()
            if scene_controller:
                result = scene_controller.execute_graph()
                if not result.success:
                    raise RuntimeError(result.message or "Graph execution failed")
                return
        
        # Fallback: raise error to force migration
        raise RuntimeError(
            "GraphModel.execute() is no longer supported. "
            "Use SceneController.execute_graph() instead. "
            "This ensures proper MVC separation."
        )

    def serialize(self):
        return {
            "id": self.id,
            "nodes": [nd.serialize() for nd in self.nodes],
            "edges": [nd.serialize() for nd in self.edges],
        }


    def __str__(self):
        node_lines = [f"Node {node.id}: {node.title}" for node in self.nodes]
        edge_lines = [
            f"Edge {edge.id}: {edge.start_node.id} -> {edge.end_node.id}" for edge in self.edges
        ]
        return (
            f"GraphModel(id={self.id}, nodes={len(self.nodes)}, edges={len(self.edges)})\n"
            f"Nodes:\n  " + "\n  ".join(node_lines) + "\n"
            "Edges:\n  " + "\n  ".join(edge_lines)
        )

    @classmethod
    def deserialize(cls, data, restore_id=True):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"GraphModel.deserialize called with restore_id={restore_id}")
        
        if data is None:
            logger.error("GraphModel.deserialize: data is None!")
            raise ValueError("Cannot deserialize GraphModel: data is None")
        
        if not isinstance(data, dict):
            logger.error(f"GraphModel.deserialize: data is not a dict, got {type(data)}")
            raise ValueError(f"Cannot deserialize GraphModel: expected dict, got {type(data)}")
        
        if "nodes" not in data:
            logger.error(f"GraphModel.deserialize: 'nodes' key missing. Keys: {list(data.keys())}")
            raise ValueError(f"Cannot deserialize GraphModel: missing 'nodes' key. Available keys: {list(data.keys())}")
        
        graph = cls()
        if restore_id and "id" in data:
            graph.id = data["id"]
            logger.info(f"Restoring graph ID: {graph.id}")
        else:
            graph.id = str(uuid.uuid4())
            logger.info(f"Generated new graph ID: {graph.id}")

        node_lookup = {}
        nodes_data = data.get("nodes", [])
        logger.info(f"Deserializing {len(nodes_data)} nodes...")
        
        for i, node_data in enumerate(nodes_data):
            try:
                logger.debug(f"Deserializing node {i+1}/{len(nodes_data)}: {node_data.get('title', 'Unknown')}")
                node = NodeModel.deserialize(node_data, restore_id)
                if node:
                    graph.add_node(node)
                    node_lookup[node.id] = node
                    logger.debug(f"Successfully deserialized node: {node.id} ({node.title})")
                else:
                    logger.warning(f"NodeModel.deserialize returned None for node {i+1}: {node_data.get('title', 'Unknown')}")
            except Exception as e:
                logger.exception(f"Error deserializing node {i+1} ({node_data.get('title', 'Unknown')}): {e}")
                raise
        
        logger.info(f"Successfully deserialized {len(node_lookup)} nodes")
        
        edges_data = data.get("edges", [])
        logger.info(f"Deserializing {len(edges_data)} edges...")
        
        edges_created = 0
        for i, edge_data in enumerate(edges_data):
            try:
                start_node_id = edge_data.get("start_node_id")
                end_node_id = edge_data.get("end_node_id")
                
                if start_node_id not in node_lookup:
                    logger.warning(f"Edge {i+1}: start_node_id '{start_node_id}' not found in node_lookup")
                    continue
                if end_node_id not in node_lookup:
                    logger.warning(f"Edge {i+1}: end_node_id '{end_node_id}' not found in node_lookup")
                    continue

                start_node = node_lookup[start_node_id]
                end_node = node_lookup[end_node_id]
                
                start_socket_id = edge_data.get("start_socket_id")
                end_socket_id = edge_data.get("end_socket_id")
                
                # Use next(..., None) to avoid StopIteration
                start_socket = next(
                    (s for s in start_node.output_sockets if s.id == start_socket_id),
                    None
                )
                if start_socket is None:
                    logger.warning(
                        f"Edge {i+1}: start_socket_id '{start_socket_id}' not found in node {start_node_id} ({start_node.title}). "
                        f"Available output socket IDs: {[s.id for s in start_node.output_sockets]}"
                    )
                    continue
                    
                end_socket = next(
                    (s for s in end_node.input_sockets if s.id == end_socket_id),
                    None
                )
                if end_socket is None:
                    logger.warning(
                        f"Edge {i+1}: end_socket_id '{end_socket_id}' not found in node {end_node_id} ({end_node.title}). "
                        f"Available input socket IDs: {[s.id for s in end_node.input_sockets]}"
                    )
                    continue
                
                edge = EdgeModel(start_socket, end_socket)
                if restore_id and "id" in edge_data:
                    edge.id = edge_data["id"]
                graph.add_edge(edge)
                edges_created += 1
                logger.debug(f"Successfully created edge {i+1}: {start_node_id}.{start_socket_id} -> {end_node_id}.{end_socket_id}")
            except Exception as e:
                logger.exception(f"Error deserializing edge {i+1}: {e}")
                # Continue with other edges instead of failing completely
                continue
        
        logger.info(f"Successfully deserialized {edges_created}/{len(edges_data)} edges")
        logger.info(f"GraphModel.deserialize complete: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
        return graph
