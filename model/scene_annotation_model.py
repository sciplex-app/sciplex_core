import uuid

from sciplex_core.model.base import BaseModel


class SceneAnnotationModel(BaseModel):
    def __init__(
        self,
        text="Type Here ...",
        pos_x=None,
        pos_y=None,
        width=None,
        height=None,
        is_selected=False,
    ):
        super().__init__()
        self.text = text
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.width = width
        self.height = height
        self.is_selected = is_selected

    def set_position(self, pos_x, pos_y):
        self.pos_x = pos_x
        self.pos_y = pos_y

    def set_dimensions(self, width, height):
        self.width = width
        self.height = height

    def set_text(self, text):
        self.text = text

    def get_text(self):
        return self.text

    def serialize(self):
        return {
            "text": self.text,
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
            "width": self.width,
            "height": self.height,
            "is_selected": "true" if self.is_selected else "false",
        }

    @classmethod
    def deserialize(cls, data, restore_id):
        obj = cls(
            text=data.get("text"),
            pos_x=data.get("pos_x"),
            pos_y=data.get("pos_y"),
            width=data.get("width"),
            height=data.get("height"),
            is_selected=True if data.get("is_selected") else False,
        )

        if restore_id:
            obj.id = data["id"]
        else:
            obj.id = str(uuid.uuid4())

        return obj
