import json
import os
from pathlib import Path

from sciplex_core.model.base import BaseModel
from sciplex_core.model.library_model import Attribute

home = os.path.join(Path.home(), "Sciplex")


class SettingsModel(BaseModel):
    """
    Model for application settings.

    Pure data model with no UI framework dependencies.
    Controllers mutate this model and emit events for views to react to.
    """

    def __init__(self):
        BaseModel.__init__(self)
        self.base_dir = home
        self.config = {
            "scene": {
                "label": "Scene",
                "elements": {
                    "Socket Annotation": Attribute(widget="toggle", value=True)
                },
            },
            "Display": {
                "label": "Display",
                "elements": {
                    "Edge Type": Attribute(
                        widget="combobox", value="edgy", options=["edgy", "smooth"]
                    ),
                }
            },
            "Execution": {
                "label": "Execution",
                "elements": {
                    "Node execution": Attribute(
                        widget="combobox", value="node and all ancestors", options=["single node", "node and all ancestors"]
                    )
                }
            },
            "Library": {
                "label": "Library",
                "elements": {
                    "Show Tutorials": Attribute(widget="toggle", value=False),
                },
            },
            "AI Assistant": {
                "label": "AI Assistant",
                "elements": {
                    "Context Mode": Attribute(
                        widget="combobox",
                        value="Private",
                        options=["Private", "Full"]
                    ),
                },
            },
        }
        self.colors = {
            # don't nest further or you'll have to update set_stylesheet
            "dark": {
                "general": {
                    "primary": "#111",
                    "secondary": "#06E4A8",
                    "tertiary": "#010101",
                    "quaternary": "#F8FAFC",
                    "pentenary": "#00000000",
                    "registry_border": "#FFFFFF",
                    "borderColor": "#333",
                    "hoverColor": "#3D3D3D",
                    "lineEditColor": "#1a1a1a",
                },
                "button": {
                    "textColor": "#1A1A1A",
                    "backgroundColor": "#06E4A8",
                    "borderColor": "#000000",
                },
                "scene": {"backgroundColor": "#121212", "gridColor": "#2F2F2F"},
                "node": {
                    "backgroundColor": "#2A2A2A",
                    "executedColor": "#0CB85D",
                    "failedColor": "#B80C09",
                    "readyColor": "#1A1A1A",
                    "textColor": "#E0E0E0",
                    "borderColor": "#6C6A6A",
                    "borderSelectedColor": "#06E4A8",
                },
                "codeeditor": {
                    "textEditorBgColor": "#1E1E1E",
                    "textEditorSideBarColor": "#343434",
                    "textEditorCaretLineColor": "#3D3D3D",
                    "textEditorCaretColor": "#FFFFFF",
                    "textColor": "#FFFFFF",
                    "syntaxKeyword": "#C586C0",
                    "syntaxString": "#CE9178",
                    "syntaxComment": "#6A9955",
                    "syntaxNumber": "#B5CEA8",
                    "syntaxOperator": "#D4D4D4",
                    "syntaxFunction": "#DCDCAA",
                    "syntaxClass": "#4EC9B0",
                    "syntaxIdentifier": "#9CDCFE",
                    "braceMatchBgColor": "#A8A6A6",
                },
                "edge": {
                    "color": "#6C6C6C",
                    "colorSelected": "#06E4A8",
                    "colorDragging": "#B6C0B6",
                },
                "inputSocket": {"color": "#E0E0E0"},
                "outputSocket": {"color": "#E0E0E0"},
            },
            "light": {
                "general": {
                    "primary": "#fffefa",
                    "secondary": "#06E4A8",
                    "tertiary": "#F5F5F5",
                    "borderColor": "#d9d9d9",
                },
                "button": {
                    "textColor": "#1A1A1A",
                    "backgroundColor": "#06E4A8",
                    "borderColor": "#000000",
                },
                "scene": {"backgroundColor": "#FFFFFF", "gridColor": "#D0D0D0"},
                "node": {
                    "backgroundColor": "#ffffff",
                    "executedColor": "#0CB85D",
                    "failedColor": "#B80C09",
                    "textColor": "#1A1A1A",
                    "readyColor": "#FFFFFF",
                    "borderColor": "",
                    "borderSelectedColor": "#06E4A8",
                },
                "edge": {
                    "color": "#1A1A1A",
                    "colorSelected": "#06E4A8",
                    "colorDragging": "#5D5D5D",
                },
                "codeeditor": {
                    "textEditorBgColor": "#FFFFFF",
                    "textEditorSideBarColor": "#f0f0f0",
                    "textEditorCaretLineColor": "#0CB85D",
                    "textEditorCaretColor": "#000000",
                    "textColor": "#000000",
                    "syntaxKeyword": "#06E4A8",
                    "syntaxString": "#A3E4D7",
                    "syntaxComment": "#6A9955",
                    "syntaxNumber": "#B5CEA8",
                    "syntaxOperator": "#D4D4D4",
                    "syntaxFunction": "#795E26",
                    "syntaxClass": "#267F99",
                    "syntaxIdentifier": "#001080",
                    "braceMatchBgColor": "#E0E0E0",
                },
                "inputSocket": {"color": "#4B4B4B"},
                "outputSocket": {"color": "#06E4A8"},
            },
        }
        self._dark_theme = True

    def get_stylesheet_path(self):
        theme_name = "dark" if self._dark_theme else "light"
        filename = f"{theme_name}_style.qss.template"
        # Go up from core/model/ to project root (two levels up)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(
            project_root,
            "assets",
            "css",
            filename,
        )

    def get_stylesheet(self, colors_data=None):
        stylesheet_path = self.get_stylesheet_path()
        with open(stylesheet_path, "r") as f:
            stylesheet = f.read()

        current_colors = colors_data if colors_data is not None else self.colors
        theme_colors = (
            current_colors["dark"] if self._dark_theme else current_colors["light"]
        )

        for category in theme_colors:
            for key, value in theme_colors[category].items():
                placeholder = f"{{{{{category}.{key}}}}}"
                stylesheet = stylesheet.replace(placeholder, value)
        return stylesheet

    def update_color(self, theme, category, key, value):
        if (
            theme in self.colors
            and category in self.colors[theme]
            and key in self.colors[theme][category]
        ):
            self.colors[theme][category][key] = value
            # Note: Events are emitted by controller after mutation, not by model
            self.save()

    def update_parameter(self, g, k, v):
        if g in self.colors and k in self.colors[g]:
            self.colors[g][k] = v
            # Note: Events are emitted by controller after mutation, not by model
        elif g in self.config and k in self.config[g]["elements"]:
            self.config[g]["elements"][k].value = v
            # Note: Events are emitted by controller after mutation, not by model
        self.save()

    def get_edge_type(self):
        return self.config["Display"]["elements"]["Edge Type"].value
    
    def get_node_execution_mode(self):
        return self.config["Execution"]["elements"]["Node execution"].value
    
    def get_llm_context_mode(self):
        """Get the LLM context mode: 'Private' or 'Full'."""
        try:
            return self.config["AI Assistant"]["elements"]["Context Mode"].value
        except KeyError:
            return "Private"  # Default to private

    def is_dark_theme_enabled(self):
        return self._dark_theme

    def get_initial_stylesheet(self):
        return self.get_stylesheet()

    def save(self):
        config_path = os.path.join(self.base_dir, "data", "user", "settings.json")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self.serialize(), f, indent=4, ensure_ascii=False)
        # Note: Events are emitted by controller after save if needed, not by model

    def serialize(self):
        base = super().serialize()
        base["config"] = {}

        for section_key, section_data in self.config.items():
            elements = {
                label: attr.serialize()
                for label, attr in section_data["elements"].items()
            }
            base["config"][section_key] = {
                "label": section_data["label"],
                "elements": elements,
            }

        return base

    @classmethod
    def deserialize(cls, serialized: dict):
        obj = cls.__new__(cls)
        cls.__init__(obj)

        # Start with default config, then update with loaded values
        config = obj.config.copy()
        
        # Update with serialized values (merges with defaults)
        for section_key, section_data in serialized.get("config", {}).items():
            if section_key in config:
                # Update existing section
                for label, attr_data in section_data["elements"].items():
                    if label in config[section_key]["elements"]:
                        # Update existing attribute
                        config[section_key]["elements"][label] = Attribute.deserialize(attr_data)
                    else:
                        # Add new attribute to existing section
                        config[section_key]["elements"][label] = Attribute.deserialize(attr_data)
            else:
                # Add new section
                config[section_key] = {
                    "label": section_data["label"],
                    "elements": {
                        label: Attribute.deserialize(attr_data)
                        for label, attr_data in section_data["elements"].items()
                    },
                }
        
        # Remove LLM section if it exists (no longer wanted)
        if "llm" in config:
            del config["llm"]
        
        obj.config = config
        obj._dark_theme = True
        # Font settings removed - no longer used in main app
        obj._init_logger()
        return obj


config_path = os.path.join(SettingsModel().base_dir, "data", "user", "settings.json")
if os.path.exists(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    settings = SettingsModel.deserialize(data)
else:
    settings = SettingsModel()
