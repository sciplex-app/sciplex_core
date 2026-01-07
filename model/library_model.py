from typing import Callable, Optional

from docstring_parser import parse

from sciplex_core.model.node_model import NodeModel


class Attribute:

    def __init__(
        self,
        widget,
        value=None,
        options=None,
        range=None,
        source=None,
        extractor=None,
    ):
        self.widget = widget
        self.value = value
        self.options = options
        self.range = range
        self.source = source
        self.extractor = extractor

    def serialize(self):
        return {
            "widget": str(self.widget),
            "value": self.value,
            "options": self.options,
            "range": self.range,
            "source": self.source,
            "extractor": self.extractor,
        }

    @classmethod
    def deserialize(cls, data):
        return cls(
            widget=data.get("widget"),
            value=data.get("value"),
            options=data.get("options"),
            range=data.get("range"),
            source=data.get("source"),
            extractor=data.get("extractor"),
        )


class LibraryItem:
    def __init__(
        self,
        function_name: str,
        library_name: str,
        icon: str,
        execute_fn: Optional[Callable],
        parameters: Optional[dict],
        inputs: Optional[list],
        outputs: list,
    ):
        """
        Represents a single function/node inside a library (.py file).

        library_name mirrors the file name (without extension). UI can prettify it
        (e.g., "machine_learning" -> "Machine Learning").
        """
        self.function_name = function_name
        self.library_name = library_name
        self.icon = icon
        self.execute_fn = execute_fn
        self.parameters = parameters
        self.inputs = inputs
        self.outputs = outputs
        self.description = self.extract_description()

    def extract_description(self):
        if self.execute_fn and self.execute_fn.__doc__:
            docstring = parse(self.execute_fn.__doc__)
            return docstring.short_description
        return ""

    def create_node_model(self):
        import copy
        # Deep copy parameters so each node instance has its own copy
        params_copy = {
            name: Attribute(
                widget=attr.widget,
                value=copy.deepcopy(attr.value),
                options=copy.deepcopy(attr.options) if attr.options else None,
                range=attr.range,
                source=attr.source,
                extractor=attr.extractor
            )
            for name, attr in (self.parameters or {}).items()
        }
        return NodeModel(
            icon=self.icon,
            title=self.function_name,
            parameters=params_copy,
            inputs=list(self.inputs) if self.inputs else [],
            outputs=list(self.outputs) if self.outputs else [],
            is_script=(self.function_name == "Script"),
            library_name=self.library_name,
        )


class LibraryModel:
    def __init__(self):
        self.data = {}

    def register(self, function_name, library_item):
        self.data[function_name] = library_item

    def deregister(self, function_name):
        if function_name in self.data.keys():
            del self.data[function_name]

    def get_library_item(self, function_name):
        if function_name in self.data.keys():
            return self.data[function_name]
        return None

    def get_library_item_names(self):
        return list(self.data.keys())

    def get_library_items(self):
        return self.data

    def get_library_item_names_by_library(self, library_name):  # meh
        return [
            function_name
            for function_name, node_registry_item in self.get_library_items().items()
            if node_registry_item.library_name == library_name
        ]

    def get_library_item_icon(self, function_name):
        return self.get_library_item(function_name).icon  # TBD really REALLY bad

    def get_library_names(self):
        return set(
            library_item.library_name for library_item in self.get_library_items().values()
        )

    def remove_library(self, library_name: str) -> int:
        """
        Remove all items belonging to the given library.

        Returns the number of items removed.
        """
        items_to_remove = [
            name for name, item in self.data.items()
            if item.library_name == library_name
        ]
        for name in items_to_remove:
            del self.data[name]
        return len(items_to_remove)

library_model = LibraryModel()
