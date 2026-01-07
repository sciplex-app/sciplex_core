from sciplex_core.model.base import BaseModel

LEFT = 1
TOP = 2
RIGHT = 3
BOTTOM = 4


class SocketModel(BaseModel):
    def __init__(self, node=None, name="", position=None, description="", data_type=None):
        super().__init__()
        self.name = name
        self.node = node
        self.pos_x = None
        self.pos_y = None
        self.position = position
        self.edges = []
        self.multiple_edges = True if name == "*" else False  # TBD: mehhh
        self.data = None
        self.description = description
        self.description_type = ""
        self.data_type = data_type

    def set_data(self, data):
        self.data = data
        if self.node and self.node.outputs and self in self.node.output_sockets:
            for edge in self.edges:
                if edge.end_socket and edge.end_socket.node:
                    # Use controller to set input data so extractors are triggered
                    end_node_model = edge.end_socket.node
                    if hasattr(end_node_model, '_controller_ref'):
                        controller_ref = end_node_model._controller_ref
                        if controller_ref:
                            node_controller = controller_ref()
                            if node_controller:
                                node_controller.set_input_data(edge.end_socket.name, data)
                                continue
                    # Fallback to model if controller not available
                    edge.end_socket.node.set_input_data(edge.end_socket.name, data)


    def clear(self):
        self.set_data(None)
        self.edges.clear()

    def trigger_node_execution(self):
        """
        Trigger execution of the parent node up to this socket's node.

        NOTE: This method is deprecated. Execution should be triggered through
        SceneController.execute_up_to_node() instead. This method is kept for
        backward compatibility but will be removed.
        """
        # Try to get scene controller from graph
        if hasattr(self.node, 'graph') and hasattr(self.node.graph, '_scene_controller_ref'):
            scene_controller_ref = self.node.graph._scene_controller_ref
            if scene_controller_ref:
                scene_controller = scene_controller_ref()
                if scene_controller:
                    scene_controller.execute_up_to_node(self.node)
                    return
        
        # Fallback: use deprecated method with warning
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "SocketModel.trigger_node_execution() is deprecated. "
            "Use SceneController.execute_up_to_node() instead."
        )
        # This will raise an error if graph doesn't have scene controller ref
        self.node.graph.execute_up_to_node(self.node)

    def get_data(self):
        return self.data

    def add_edge(self, edge):
        if edge not in self.edges:
            self.edges.append(edge)

    def remove_edge(self, edge):
        if edge in self.edges:
            self.edges.remove(edge)

    def parse_from_node_description(self):
        if self.node and self.node.execute_fn is not None:
            import inspect

            from docstring_parser import parse

            docstring = parse(self.node.execute_fn.__doc__)
            sig = inspect.signature(self.node.execute_fn)

            if self.position == LEFT:
                param = sig.parameters.get(self.name)
                if param:
                    param_doc = next((p for p in docstring.params if p.arg_name == self.name), None)
                    self.description = param_doc.description if param_doc else ""
                    self.description_type = param_doc.type_name if param_doc else ""
            else:
                returns_text = docstring.returns.description if docstring.returns else ""
                lines = [line.strip() for line in returns_text.splitlines() if line.strip()]

                type_text = docstring.returns.type_name if docstring.returns and docstring.returns.type_name else ""
                type_lines = [line.strip() for line in type_text.splitlines() if line.strip()]

                try:
                    socket_descr = lines[int(self.name.split("_")[1])]
                    if ":" in socket_descr:
                        descr = socket_descr.split(":")
                        self.description = descr[1]
                        self.description_type = descr[0]
                    else:
                        self.description = socket_descr
                        self.description_type = type_lines[int(self.name.split("_")[1])]
                except Exception:
                    self.description = ""
                    self.description_type = ""



    def get_position(self):
        if self.pos_x is not None and self.pos_y is not None:
            return (self.pos_x, self.pos_y)
        return None

    def serialize(self):
        # Ensure data_type is JSON-serializable; convert any non-primitive to string
        dt = self.data_type
        if isinstance(dt, type):
            dt = dt.__name__
        elif dt is not None and not isinstance(dt, (str, int, float, bool)):
            dt = str(dt)
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "data_type": dt,
        }

    @classmethod
    def deserialize(cls, node, serialized, restore_id=True):
        obj = super().deserialize(serialized, restore_id)
        obj.node = node
        return obj
