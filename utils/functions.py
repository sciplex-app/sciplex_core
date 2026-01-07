import ast
import keyword
import operator
import re

import numpy as np
import pandas as pd

__all__ = [
    "variables_registry",
    "extract_variable_definitions_simple",
    "expression_to_numerical_full",
    ]


class VariablesRegistry:
    """A registry for variables."""
    def __init__(self):
        """Initializes the VariablesRegistry."""
        self.data = {}

    def clear(self):
        self.data={}

    def register(self, var_name, var):
        """Registers a variable.

        Args:
            var_name (str): The name of the variable.
            var: The variable to register.
        """
        if keyword.iskeyword(var_name):
            raise ValueError(f"Variable name {var_name} is a Python keyword. Choose another name.")
        if not var_name.isidentifier():
            raise ValueError(f"'{var_name}' is not a valid Python variable name.")
        self.data[var_name] = var

    def register_dict(self, var_dict):
        """Registers a dictionary of variables.

        Args:
            var_dict (dict): A dictionary of variables to register.
        """
        for k, v in var_dict.items():
            self.register(k, v)

    def get_variable(self, var_name):
        """Gets a variable.

        Args:
            var_name (str): The name of the variable.

        Returns:
            The variable.
        """
        return self.data[var_name]


variables_registry = VariablesRegistry()


class SafeEvaluator(ast.NodeVisitor):
    def __init__(self, namespace=None):
        self.namespace = namespace or {}

    def visit(self, node):
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        elif isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.List):
            return [self.visit(el) for el in node.elts]
        elif isinstance(node, ast.Tuple):
            return tuple(self.visit(el) for el in node.elts)
        elif isinstance(node, ast.Dict):
            return {self.visit(k): self.visit(v) for k, v in zip(node.keys, node.values)}
        elif isinstance(node, ast.Name):
            if node.id in self.namespace:
                return self.namespace[node.id]
            else:
                raise ValueError(f"Name '{node.id}' is not allowed")
        elif isinstance(node, ast.Attribute):
            value = self.visit(node.value)
            return getattr(value, node.attr)
        elif isinstance(node, ast.Call):
            func = self.visit(node.func)
            args = [self.visit(arg) for arg in node.args]
            kwargs = {kw.arg: self.visit(kw.value) for kw in node.keywords}
            return func(*args, **kwargs)
        elif isinstance(node, ast.UnaryOp):
            ops = {ast.UAdd: operator.pos, ast.USub: operator.neg}
            if type(node.op) in ops:
                return ops[type(node.op)](self.visit(node.operand))
            else:
                raise ValueError(f"Unsupported unary operator: {node.op}")
        elif isinstance(node, ast.BinOp):  # <-- NEW: binary arithmetic
            ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.FloorDiv: operator.floordiv,
                ast.Mod: operator.mod,
                ast.Pow: operator.pow
            }
            if type(node.op) in ops:
                left = self.visit(node.left)
                right = self.visit(node.right)
                return ops[type(node.op)](left, right)
            else:
                raise ValueError(f"Unsupported binary operator: {node.op}")
        else:
            raise ValueError(f"Unsupported AST node type: {type(node).__name__}")

def expression_to_numerical_full(expr_str):
    """
    Evaluate an expression string using AST with a controlled namespace.
    Supports literals, lists, tuples, dicts, and calls to allowed names.
    """
    namespace = {"pd": pd, "np": np}
    try:
        tree = ast.parse(expr_str, mode='eval')
        evaluator = SafeEvaluator(namespace)
        return evaluator.visit(tree)
    except Exception as e:
        raise ValueError(f"Failed to evaluate expression '{expr_str}': {e}")


def extract_variable_definitions_simple(text):
    """
    Extract variables from Python-like text and remove unnecessary whitespace.
    Handles multi-line definitions with brackets.

    Returns:
        list of tuples: [(variable_name, compact_expression), ...]
    """
    # Remove newlines but keep spaces so we can split definitions
    text_no_newlines = ' '.join(text.splitlines())

    # Regex: match variable name, =, then expression until next variable or end
    pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+?)(?=\s*[a-zA-Z_][a-zA-Z0-9_]*\s*=|$)'
    matches = re.findall(pattern, text_no_newlines)

    compacted = []
    for var, expr in matches:
        # Remove unnecessary spaces except inside strings (simplified)
        expr_no_spaces = re.sub(r'\s+', '', expr)
        compacted.append((var, expr_no_spaces))

    return compacted


# Note: Node libraries are now loaded dynamically from ~/Sciplex/libraries/
# by Application._load_node_libraries() on startup.
# This allows users to view and modify node definitions.
