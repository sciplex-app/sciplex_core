import ast
import inspect
import os
import textwrap
from functools import wraps
from typing import get_args, get_type_hints

import pandas as pd

from sciplex_core.model.library_model import LibraryItem, library_model


def _infer_return_arity_from_source(func) -> int | None:
    """
    Best-effort: infer how many values the function returns by scanning its AST.

    Rules:
    - No explicit `return` statements -> arity 0 (no output sockets)
    - `return` (no value) -> arity 0
    - `return x` -> arity 1
    - `return a, b, c` -> arity N
    - Multiple returns must agree on arity; otherwise raise ValueError.

    Returns:
        int | None: inferred arity, or None if source code is unavailable.
    """
    try:
        src = inspect.getsource(func)
    except Exception:
        return None

    src = textwrap.dedent(src)

    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None

    func_def = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func.__name__:
            func_def = node
            break

    if func_def is None:
        return None

    arities: list[int] = []
    for node in ast.walk(func_def):
        if isinstance(node, ast.Return):
            if node.value is None:
                arities.append(0)
            elif isinstance(node.value, ast.Tuple):
                arities.append(len(node.value.elts))
            else:
                arities.append(1)

    if not arities:
        return 0

    unique = sorted(set(arities))
    if len(unique) > 1:
        raise ValueError(
            f"Function '{func.__name__}' has inconsistent return arity across branches: {unique}. "
            "Please make all return statements return the same number of values (e.g. always `return x` "
            "or always `return a, b`)."
        )

    return unique[0]


def get_outputs_info(func):
    sig = inspect.signature(func)
    ret = sig.return_annotation

    if (
        ret is inspect.Signature.empty
        or ret is None
        or ret is type(None)
    ):
        # No return annotation: infer outputs from return statements if possible.
        arity = _infer_return_arity_from_source(func)
        if arity is None:
            # Conservative fallback: keep old behavior (no outputs) if we cannot inspect source.
            return []
        return [None] * arity

    # Explicitly handle tuple types
    if hasattr(ret, '__origin__') and ret.__origin__ is tuple:
        return list(get_args(ret))

    #args = get_args(ret)

    #if args:
    #    return list(args)

    return [ret]


def type_error_clear(msg):
    replacements = {
        # pandas types
        "<class 'pandas.core.series.Series'>": "Column",
        "pandas.core.series.Series": "Column",
        "<class 'pandas.core.frame.DataFrame'>": "Table",
        "pandas.core.frame.DataFrame": "Table",

        # numeric types
        "numbers.Number": "Number",
        "<class 'int'>": "Int",
        "<class 'float'>": "float",

        # generic typing
        "typing.Union": "one of ",

        # other common types
        "<class 'str'>": "String",
        "<class 'bool'>": "Boolean",
        "<class 'list'>": "List",
        "<class 'tuple'>": "Tuple",
        "<class 'dict'>": "Dictionary",
        "<class 'NoneType'>": "None",
        "numpy.ndarray": "array"
    }

    for old, new in replacements.items():
        msg = msg.replace(old, new)
    return msg


def nodify(
    icon="icon",
    **widget_overrides,
):
    def decorator(func):
        sig = inspect.signature(func)
        user_params = {}
        inputs = []
        type_hints = get_type_hints(func)
        for name, param in sig.parameters.items():
            param_type = type_hints.get(name, None)
            if name in widget_overrides:
                user_params[name] = widget_overrides[name]
                user_params[name].value = (
                    param.default if param.default is not param.empty else None
                )
            else:
                if param.kind == inspect.Parameter.VAR_POSITIONAL:
                    inputs.append(("*", None))
                else:
                    inputs.append((name, param_type))

        output_types = get_outputs_info(func)
        outputs = [
            (f"out_{i}", typ) for i, typ in enumerate(output_types)
        ]

        hints = get_type_hints(func)

        @wraps(func)  # preserves name, docstring, annotations, etc.
        def wrapper(*args, **kwargs):
            bound_args = dict(zip(func.__code__.co_varnames, args))
            bound_args.update(kwargs)

            # check argument types
            for name, expected_type in hints.items():
                if name == 'return':
                    continue
                if name in bound_args and not isinstance(bound_args[name], expected_type):
                    error_message = f"Argument '{name}' expected {expected_type}, got {type(bound_args[name])}"
                    raise TypeError(type_error_clear(error_message))

            new_args = []
            # loop through positional arguments
            for arg in args:
                if isinstance(arg, pd.DataFrame):
                    if arg.shape[1] == 1:
                        new_args.append(arg.iloc[:, 0])  # convert to Series
                    else:
                        new_args.append(arg)
                else:
                    new_args.append(arg)

            # also process keyword arguments
            new_kwargs = {}
            for k, v in kwargs.items():
                if isinstance(v, pd.DataFrame) and v.shape[1] == 1:
                    new_kwargs[k] = v.iloc[:, 0]
                else:
                    new_kwargs[k] = v

            result = func(*new_args, **new_kwargs)

            return result

        module = inspect.getmodule(func)
        file_based_library = None
        if module and getattr(module, "__file__", None):
            file_based_library = os.path.splitext(os.path.basename(module.__file__))[0]
        # Allow loader to override via module attribute
        library_name = getattr(module, "__sciplex_library_name__", None) or file_based_library

        library_item = LibraryItem(
            function_name=func.__name__,
            library_name=library_name,
            icon=icon,
            execute_fn=wrapper,
            parameters=user_params,
            inputs=inputs,
            outputs=outputs,
        )
        library_model.register(func.__name__, library_item)

        return wrapper

    return decorator
