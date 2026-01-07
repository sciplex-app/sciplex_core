import json
import uuid

from sciplex_core.model.base import BaseModel
from sciplex_core.model.graph_model import GraphModel
from sciplex_core.model.scene_annotation_model import SceneAnnotationModel


class SceneModel(BaseModel):
    def __init__(self):
        super().__init__()
        self.filepath = ""
        self.graph = None
        self.scene_annotations = []
        self.imported_libraries = []  # List of file paths to imported Python libraries

    def serialize(self, only_selection=False):
        base_data = super().serialize()
        # Remove internal list to avoid duplicate/unused key in output
        base_data.pop("scene_annotations", None)
        # Avoid persisting absolute file path in serialized project data
        base_data.pop("filepath", None)

        serialized_ids = set()
        serialized_annotations = []
        selected_nodes = []
        selected_edges = []

        for annotation in self.scene_annotations:
            if not only_selection or annotation.is_selected:
                serialized_annotations.append(annotation.serialize())
                serialized_ids.add(annotation.id)

        if self.graph:
            if only_selection:
                for node in self.graph.nodes:
                    if node.is_selected and node.id not in serialized_ids:
                        selected_nodes.append(node)
                        serialized_ids.add(node.id)

                for edge in self.graph.edges:
                    if edge.is_selected and edge.id not in serialized_ids:
                        selected_edges.append(edge)
                        serialized_ids.add(edge.id)

                subgraph = GraphModel(nodes=selected_nodes, edges=selected_edges)
                graph_data = subgraph.serialize()

            else:
                graph_data = self.graph.serialize()

        else:
            # Handle the case where there is no graph with a distinct id
            graph_data = {"id": str(uuid.uuid4()), "nodes": [], "edges": []}

        # Build output dict with desired key order (imported_libraries first for readability)
        if only_selection:
            data = base_data
            data["graph"] = graph_data
            data["annotations"] = serialized_annotations
        else:
            # Order keys: id, imported_libraries, then the rest
            data = {"id": self.id}
            data["imported_libraries"] = self.imported_libraries
            # add remaining base fields except id
            for k, v in base_data.items():
                if k in ("id",):
                    continue
                data[k] = v
            data["graph"] = graph_data
            data["annotations"] = serialized_annotations

        return data

    def add_node(self, node):
        if not self.graph:
            self.graph = GraphModel()
        self.graph.add_node(node)
        return self.graph

    def add_edge(self, edge):
        # no verification because you can't create an edge without having a node in the scene anyway (which means that a graph has already been created)
        self.graph.add_edge(edge)
        return self.graph

    def add_scene_annotation(self, scene_annotation):
        self.logger.info("Adding Scene Annotation")
        self.scene_annotations.append(scene_annotation)

    def deserialize(self, data, node_lookup={}, restore_id=False):
        self.logger.info(f"SceneModel.deserialize called with restore_id={restore_id}")
        self.clear()
        self.filepath = data.get("filepath", "")
        self.scene_annotations = [
            SceneAnnotationModel.deserialize(a) for a in data.get("annotations", [])
        ]
        self.imported_libraries = data.get("imported_libraries", [])

        # Handle both formats:
        # 1. Full scene format: { "graph": {...}, "annotations": [...] }
        # 2. Graph-only format: { "nodes": [...], "edges": [...] }
        if "graph" in data:
            self.logger.info("Found 'graph' key, deserializing GraphModel...")
            graph_data = data["graph"]
            if graph_data is None:
                self.logger.error("'graph' key exists but value is None!")
                self.graph = None
            elif not isinstance(graph_data, dict):
                self.logger.error(f"'graph' key exists but value is not a dict: {type(graph_data)}")
                self.graph = None
            elif "nodes" not in graph_data:
                self.logger.error(f"'graph' dict missing 'nodes' key. Keys: {list(graph_data.keys())}")
                self.graph = None
            else:
                try:
                    self.graph = GraphModel.deserialize(graph_data, restore_id=restore_id)
                    self.logger.info(f"GraphModel deserialized successfully. Nodes: {len(self.graph.nodes)}, Edges: {len(self.graph.edges)}")
                except Exception as e:
                    self.logger.exception(f"Error deserializing GraphModel: {e}")
                    self.graph = None
                    raise
        elif "nodes" in data:
            # Graph-only format (saved by controller)
            self.logger.info("Found 'nodes' key (graph-only format), deserializing GraphModel...")
            try:
                self.graph = GraphModel.deserialize(data, restore_id=restore_id)
                self.logger.info(f"GraphModel deserialized successfully. Nodes: {len(self.graph.nodes)}, Edges: {len(self.graph.edges)}")
            except Exception as e:
                self.logger.exception(f"Error deserializing GraphModel: {e}")
                self.graph = None
                raise
        else:
            self.logger.warning("Neither 'graph' nor 'nodes' key found. Setting graph to None.")
            self.graph = None

    def load_from_file(self, filename):
        self.logger.info(f"Loading data from: {filename}")
        try:
            with open(filename, "r") as file:
                raw_data = file.read()
            data = json.loads(raw_data)
            self.logger.info(f"JSON parsed successfully. Keys: {list(data.keys())}")

            # Add filepath to data for deserialize
            data["filepath"] = filename
            if "annotations" not in data:
                data["annotations"] = []

            # Check if graph key exists
            if "graph" in data:
                self.logger.info(f"Graph key found in data. Graph keys: {list(data['graph'].keys()) if isinstance(data.get('graph'), dict) else 'Not a dict'}")
            elif "nodes" in data:
                self.logger.info("Graph key not found, but 'nodes' key found (graph-only format)")
            else:
                self.logger.warning("Neither 'graph' nor 'nodes' key found in data!")

            # deserialize modifies self in place (restore_id=True to preserve socket IDs for edge linking)
            self.logger.info("Calling deserialize...")
            self.deserialize(data, restore_id=True)
            self.logger.info(f"Deserialize complete. Graph is {'None' if self.graph is None else f'GraphModel with {len(self.graph.nodes)} nodes'}")
        except Exception as e:
            self.logger.exception(f"Error During File Loading: {e}")
            # Re-raise to allow caller to handle
            raise

    def save_to_file(self, filename):
        self.logger.info(f"Writing data to: {filename}")
        try:
            with open(filename, "w") as file:
                file.write(json.dumps(self.serialize(), indent=4))
        except Exception:
            self.logger.exception("Error During File Saving.")

    def clear(self):
        self.filename = None
        if self.graph:
            self.graph.clear()
        self.graph = None
        self.scene_annotations = []
        self.imported_libraries = []

    def remove_node(self, node_model):
        if node_model in self.graph.nodes:
            self.graph.remove_node(node_model)

    def remove_edge(self, edge_model):
        if edge_model in self.graph.edges:
            self.graph.remove_edge(edge_model)

    def remove_annotation(self, annotation_model):
        """Remove an annotation model from the scene."""
        if annotation_model in self.scene_annotations:
            self.scene_annotations.remove(annotation_model)



