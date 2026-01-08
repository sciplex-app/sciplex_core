"""
Graph -> Python code exporter.

Goal:
- Export the current graph as a runnable, readable Python script.
- Include library loading/imports for the node libraries used in the graph.

Notes:
- Uses simple import statements like "from library import Function"
- Script nodes embed their function source code directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ExportedPython:
    code: str
    warnings: list[str]


_IDENT_RE = re.compile(r"[^0-9a-zA-Z_]+")


def _sanitize_identifier(name: str) -> str:
    s = (name or "node").strip()
    s = _IDENT_RE.sub("_", s)
    s = s.strip("_")
    if not s:
        s = "node"
    if s[0].isdigit():
        s = f"n_{s}"
    return s


def _py_literal(value: Any) -> str:
    """Best-effort literal formatting for generated code."""
    try:
        import numpy as np  # type: ignore
    except Exception:  # pragma: no cover
        np = None
    try:
        import pandas as pd  # type: ignore
    except Exception:  # pragma: no cover
        pd = None

    if np is not None and isinstance(value, np.ndarray):
        return repr(value.tolist())
    if pd is not None and isinstance(value, (pd.DataFrame, pd.Series)):
        # Can't reasonably inline these; keep a placeholder.
        return "None  # TODO: parameter was a pandas object at export time"
    return repr(value)


def _group_by_library(nodes: Iterable) -> dict[str, set[str]]:
    """
    Returns mapping: library_name -> {function_name, ...}
    Skips script nodes and internal libraries.
    """
    out: dict[str, set[str]] = {}
    for node in nodes:
        if getattr(node, "is_script", False):
            continue
        lib = getattr(node, "library_name", None) or getattr(node, "category", None) or ""
        if not lib or str(lib).startswith("_"):
            continue
        out.setdefault(str(lib), set()).add(str(getattr(node, "title", "Unknown")))
    return out


def export_graph_to_python_code(scene_model, base_dir: str | None = None) -> ExportedPython:
    """
    Export a SceneModel's graph to Python code.

    Args:
        scene_model: SceneModel instance (must have `.graph` and optionally `.imported_libraries`)
        base_dir: SceneController.base_dir, used only for fallback paths.
    """
    graph = getattr(scene_model, "graph", None)
    if graph is None:
        return ExportedPython(code="# No graph found.\n", warnings=["No graph found."])

    nodes = list(getattr(graph, "nodes", []) or [])
    edges = list(getattr(graph, "edges", []) or [])

    warnings: list[str] = []

    # Determine execution order (best effort)
    ordered_nodes = None
    try:
        graph.topological_sort()
        ordered_nodes = list(getattr(graph, "sorted_nodes", None) or [])
    except Exception:
        ordered_nodes = None
    if not ordered_nodes:
        ordered_nodes = nodes
        warnings.append("Graph is not a DAG or could not be topologically sorted; using insertion order.")

    libs_used = _group_by_library(ordered_nodes)

    # Build library_name -> module_name mapping from imported_libraries
    # Extract module names from library paths (e.g., "data.py" -> "data")
    # The key is the library name from nodes, value is the module name from the file path
    lib_module_names: dict[str, str] = {}
    imported = list(getattr(scene_model, "imported_libraries", []) or [])
    for p in imported:
        try:
            import os
            # Get the filename without extension as the module name
            module_name = os.path.splitext(os.path.basename(p))[0]
            # Try to match this path to a library name used in the graph
            # For paths like "default/data.py", the library name from nodes might be "default" or "data"
            # We'll use the module name (filename) as the default
            # Check if any library name from nodes matches this path
            for lib_name in libs_used.keys():
                # If library name matches the module name or is in the path
                if lib_name == module_name or lib_name in p:
                    lib_module_names[lib_name] = module_name
                    break
            # Also add direct mapping by module name
            lib_module_names[module_name] = module_name
        except Exception:
            continue

    # Create stable, non-conflicting variable names for outputs.
    # We intentionally avoid bare function names like `LoadCSV` so that
    # we never shadow imported callables (e.g. `from mylib import LoadCSV`).
    #
    # Instead, we generate names like `LoadCSV_1`, `LoadCSV_2`, etc. per node
    # title, and for multi-output nodes: `LoadCSV_1_1`, `LoadCSV_1_2`, ...
    used_names: set[str] = set()
    title_counts: dict[str, int] = {}

    # Map output socket id -> python variable name
    socket_var: dict[str, str] = {}
    node_out_vars: dict[str, list[str]] = {}

    for node in ordered_nodes:
        outs = list(getattr(node, "output_sockets", []) or [])
        raw_title = str(getattr(node, "title", "node"))
        title_key = _sanitize_identifier(raw_title) or "node"

        # Increment per-title counter to provide stable suffixes: _1, _2, ...
        idx_for_title = title_counts.get(title_key, 0) + 1
        title_counts[title_key] = idx_for_title

        # Base name for this node instance, e.g. LoadCSV_1
        base = f"{title_key}_{idx_for_title}"

        # Ensure global uniqueness in case of unusual title collisions
        while base in used_names:
            idx_for_title += 1
            title_counts[title_key] = idx_for_title
            base = f"{title_key}_{idx_for_title}"
        used_names.add(base)

        if not outs:
            node_out_vars[node.id] = []
            continue

        if len(outs) == 1:
            # Single-output node: use the node-level base, e.g. LoadCSV_1
            v = base
            socket_var[outs[0].id] = v
            node_out_vars[node.id] = [v]
        else:
            # Multi-output node: append an index, e.g. MyNode_1_1, MyNode_1_2
            vars_: list[str] = []
            for idx, sock in enumerate(outs, start=1):
                v = f"{base}_{idx}"
                # Guard against rare collisions
                while v in used_names:
                    idx += 1
                    v = f"{base}_{idx}"
                used_names.add(v)
                socket_var[sock.id] = v
                vars_.append(v)
            node_out_vars[node.id] = vars_

    # Build node_id -> incoming connections by input socket name (and varargs list)
    incoming_kw: dict[str, dict[str, str]] = {n.id: {} for n in ordered_nodes}
    incoming_varargs: dict[str, list[str]] = {n.id: [] for n in ordered_nodes}

    for e in edges:
        try:
            end_sock = e.end_socket
            start_sock = e.start_socket
            end_node = e.end_node
            if end_node.id not in incoming_kw:
                continue
            value_expr = socket_var.get(start_sock.id)
            if not value_expr:
                continue
            if getattr(end_sock, "name", None) == "*":
                incoming_varargs[end_node.id].append(value_expr)
            else:
                incoming_kw[end_node.id][end_sock.name] = value_expr
        except Exception:
            continue

    # Script node sources
    script_sources: dict[str, str] = {}
    for node in ordered_nodes:
        if not getattr(node, "is_script", False):
            continue
        params = getattr(node, "parameters", {}) or {}
        fn_attr = params.get("function")
        code = getattr(fn_attr, "value", None) if fn_attr is not None else None
        if code and isinstance(code, str):
            script_sources[node.title] = code.strip() + "\n"
        else:
            warnings.append(f"Script node '{node.title}' had no function source code.")

    lines: list[str] = []
    lines.append("# Generated by Sciplex (graph export)\n\n")

    if warnings:
        lines.append("# Warnings:\n")
        for w in warnings:
            lines.append(f"# - {w}\n")
        lines.append("\n")

    # Simple imports - one import statement per library
    if libs_used:
        lines.append("# --- Imports ---\n")
        for lib_name in sorted(libs_used.keys()):
            # Get module name (default to library name if not found)
            module_name = lib_module_names.get(lib_name, lib_name)
            # Get all function names used from this library
            functions = sorted(libs_used[lib_name])
            if functions:
                # Create import statement: from module import Function1, Function2, ...
                fn_list = ", ".join(functions)
                lines.append(f"from {module_name} import {fn_list}\n")
        lines.append("\n")

    # Script function definitions
    if script_sources:
        lines.append("# --- Script node functions ---\n")
        for fn_name, fn_src in script_sources.items():
            lines.append(fn_src.rstrip() + "\n\n")

    # Emit execution (script-like, no function wrapper)
    lines.append("# --- Graph execution ---\n")

    for node in ordered_nodes:
        fn_name = str(getattr(node, "title", "Unknown"))
        params = getattr(node, "parameters", {}) or {}
        kwargs_parts: list[str] = []

        # Inputs (as kwargs, matching NodeModel.execute semantics)
        for sock in getattr(node, "input_sockets", []) or []:
            if sock.name == "*":
                continue
            if sock.name in incoming_kw.get(node.id, {}):
                kwargs_parts.append(f"{sock.name}={incoming_kw[node.id][sock.name]}")
            else:
                # keep export runnable-ish: use None placeholders
                kwargs_parts.append(f"{sock.name}=None  # TODO: connect input")

        # Parameters (exclude script source parameter)
        for k, attr in params.items():
            if k == "function":
                continue
            try:
                val = getattr(attr, "value", None)
            except Exception:
                val = None
            kwargs_parts.append(f"{k}={_py_literal(val)}")

        args_prefix = ""
        va = incoming_varargs.get(node.id) or []
        if va:
            args_prefix = ", ".join(va)

        call_parts = []
        if args_prefix:
            call_parts.append(args_prefix)
        if kwargs_parts:
            call_parts.append(", ".join(kwargs_parts))
        call = f"{fn_name}({', '.join(call_parts)})"

        out_vars = node_out_vars.get(node.id, [])
        if not out_vars:
            lines.append(f"{call}\n")
        elif len(out_vars) == 1:
            lines.append(f"{out_vars[0]} = {call}\n")
        else:
            lhs = ", ".join(out_vars)
            lines.append(f"{lhs} = {call}\n")

    return ExportedPython(code="".join(lines), warnings=warnings)

