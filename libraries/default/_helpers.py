"""
Sciplex Helper Functions

This module provides helper functions for users creating custom node libraries.
These functions are exposed to users and can be imported in custom libraries.

Note: This file is copied to ~/Sciplex/libraries/default/_helpers.py along with other default library files.
The _ prefix excludes it from being loaded as a node library, but it can still be imported.

Usage:
    from _helpers import assign_name, evaluate_mathematical_expression, MLModel, MLTransform
"""

import ast

import numpy as np

# Import workspace from sciplex for evaluate_mathematical_expression
# This import will work when libraries are loaded as sciplex is available
from sciplex import workspace


def assign_name(column_names, base_name):
    """Assigns a unique name to a column.

    Args:
        column_names (list): A list of column names.
        base_name (str): The base name for the column.

    Returns:
        str: A unique name for the column.
    """
    i = 0
    proposed_name = base_name
    if proposed_name in column_names:
        while True:
            proposed_name = base_name + '_' + str(i)
            if proposed_name in column_names:
                i += 1
            else:
                break
    return proposed_name


class MLModel:
    """Machine Learning Model container."""
    def __init__(self, name, model, features, targets):
        self.name = name
        self.model = model
        self.features = features
        self.targets = targets


class MLTransform:
    """Machine Learning Transform container."""
    def __init__(self, name, transform, features):
        self.name = name
        self.transform = transform
        self.features = features


def evaluate_mathematical_expression(expr, x):
    """Evaluate a mathematical expression with variable support.

    Args:
        expr (str): The mathematical expression to evaluate.
        x: The input variable 'x' for the expression.

    Returns:
        tuple: (variable_name, result) where variable_name is the name if
               expression was in form "name=expr", otherwise "function".
    """
    allowed_funcs = {
        'log': np.log,
        'sqrt': np.sqrt,
        'abs': np.abs,
        'exp': np.exp,
        'sin': np.sin,
        'cos': np.cos,
        'tan': np.tan,
        'sinh': np.sinh,
        'cosh': np.cosh,
        'tanh': np.tanh,
    }
    expr = expr.replace("^", "**")
    expr_lst = expr.split("=")
    if len(expr_lst) > 2:
        raise ValueError("Invalid expression")
    else:
        expr = expr_lst[-1]

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Pow):
                return left**right
            raise TypeError(f"Unsupported binary operator: {type(node.op)}")
        elif isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            if isinstance(node.op, ast.USub):
                return -operand
            raise TypeError(f"Unsupported unary operator: {type(node.op)}")
        elif isinstance(node, ast.Name):
            if node.id == 'x':
                return x
            elif node.id in workspace:
                return workspace[node.id]
            else:
                raise ValueError(f"Unknown variable: {node.id}")
        elif isinstance(node, ast.Call):
            func_name = node.func.id
            if func_name not in allowed_funcs:
                raise ValueError(f"Function '{func_name}' not allowed.")
            args = [_eval(arg) for arg in node.args]
            return allowed_funcs[func_name](*args)
        else:
            raise TypeError(f"Unsupported expression node: {type(node)}")

    result = _eval(ast.parse(expr, mode='eval').body)

    if len(expr_lst) == 2:
        var_name = expr_lst[0]
    else:
        var_name = "function"

    return var_name, result


# Note: variables_registry is not exposed - users should use workspace from sciplex instead
__all__ = [
    "assign_name",
    "evaluate_mathematical_expression",
    "MLModel",
    "MLTransform",
]

