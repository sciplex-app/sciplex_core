
from sciplex_core.model.base import BaseModel


class CodeEditorModel(BaseModel):
    """
    Model for code editor.

    Pure data model with no UI framework dependencies.
    """

    def __init__(self):
        super().__init__()
        self.text = None
        self.fn = None
        self.fn_name = None

    def get_fn(self):
        return self.fn

    def set_fn(self, fn):
        self.fn = fn

    def set_text(self, text):
        self.text = text

    def get_text(self):
        return self.text
