"""
Sciplex Public API

This module provides a clean interface for users creating custom node libraries.

Usage:
    from sciplex import nodify, Attribute, workspace
    from sciplex import llm  # for agent nodes (available in Sciplex Platform)
"""

from sciplex_core.model.library_model import Attribute
from sciplex_core.utils.functions import variables_registry
from sciplex_core.utils.node_factory import nodify

try:
    from sciplex_core_ext.utils.llm import llm
except ImportError:

    class _LLMUnavailable:
        """Placeholder when sciplex_core_ext is not installed (e.g. core-only install)."""

        def generate(self, prompt: str, system_prompt=None, **kwargs) -> str:
            raise RuntimeError(
                "LLM helper is only available when running in Sciplex Platform. "
                "Install sciplex_platform (or sciplex_core_ext) to use llm.generate() in nodes."
            )

    llm = _LLMUnavailable()


class _WorkspaceProxy:
    """
    Public, user-friendly proxy for Sciplex "workspace" variables.

    Intended usage inside custom libraries:
        from sciplex import workspace
        workspace["a"] = 2
        x = workspace["a"]
    """

    def __getitem__(self, key: str):
        if not isinstance(key, str):
            raise TypeError("Workspace key must be a string (e.g. workspace['a']).")
        if key not in variables_registry.data:
            raise KeyError(f"'{key}' not in workspace.")
        return variables_registry.get_variable(key)

    def __setitem__(self, key: str, value):
        if not isinstance(key, str):
            raise TypeError("Workspace key must be a string (e.g. workspace['a']).")
        variables_registry.register(key, value)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and key in variables_registry.data

    def keys(self):
        return list((variables_registry.data or {}).keys())

    def get(self, key: str, default=None):
        try:
            return self[key]
        except KeyError:
            return default


# Singleton proxy instance users can import.
workspace = _WorkspaceProxy()

__all__ = [
    "nodify",
    "Attribute",
    "workspace",
    "llm",
]

