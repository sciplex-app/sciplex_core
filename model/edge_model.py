from sciplex_core.model.base import BaseModel


class EdgeModel(BaseModel):
    def __init__(self, start_socket=None, end_socket=None):
        super().__init__()

        self._start_socket = None
        self._end_socket = None

        self.start_socket = start_socket
        self.end_socket = end_socket
        self.is_selected = False

    @property
    def start_socket(self):
        return self._start_socket

    @start_socket.setter
    def start_socket(self, socket):
        self._start_socket = socket
        if socket and self not in socket.edges:
            socket.edges.append(self)

    @property
    def end_socket(self):
        return self._end_socket

    @end_socket.setter
    def end_socket(self, socket):
        self._end_socket = socket
        if socket and self not in socket.edges:
            socket.edges.append(self)

    @property
    def start_node(self):
        return self.start_socket.node

    @property
    def end_node(self):
        return self.end_socket.node


    def __str__(self):
        return f"Edge(id={self.id}, from={self.start_node.id}, to={self.end_node.id})"

    def disconnect(self):
        if self in self.start_socket.edges:
            self.start_socket.edges.remove(self)
        if self in self.end_socket.edges:
            self.end_socket.edges.remove(self)

    def serialize(self):
        return {
            "id": self.id,
            "start_node_id": self.start_node.id,
            "end_node_id": self.end_node.id,
            "start_socket_id": self.start_socket.id,
            "end_socket_id": self.end_socket.id,
        }
