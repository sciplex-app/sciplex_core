"""
This file is part of the Sciplex default library and serves as a reference for creating new nodes.

When you delete default libraries from the workspace, they are automatically restored on the next startup.

Library files that expose functions and are imported into the sidebar become available in the flow. Files whose names start with an underscore (e.g., `_helpers.py`) are skipped.

The following helpers are provided by `sciplex` (you can import them directly and the backend wires this up for you):
- `@nodify`: decorate a function to define a node (see the examples below).
- `Attribute`: describe the widgets that appear in the properties panel.
- `workspace`: a global dictionary for sharing values between nodes (`workspace['foo'] = 2`).

Every Sciplex node is just a Python function. Attributes control widget types in the properties panel, and parameters without defaults map to input sockets while those with defaults become editable parameters.

Type hints are optional. Use extractors when you need to probe incoming data (e.g., pull column names from a dataframe).

Common attribute widgets:
- `lineedit`: text input
- `pylineedit`: Python-style input (lists, expressions, access to globals)
- `spinbox`: integer input
- `doublespinbox`: float input
- `combobox`: dropdown
- `checkable-combobox`: dropdown with multiple selections
- `filepath`: file chooser input
- `filesave`: file chooser output
- `colorpicker`: color picker widget

About figures:
- You can return Matplotlib or Plotly figures from node functions (see `visuals.py` for examples).
"""


import numpy as np
import pandas as pd
from _helpers import (
    evaluate_mathematical_expression,  # _helpers.py can be used but is excluded from the library sidebar
)

from sciplex import Attribute, nodify, workspace


@nodify(
        icon="boolean",
        op=Attribute("combobox", value = "True", options=["True", "False"]),
        )
def Boolean(op: str="True") -> bool:
    """
    Boolean constant (True or False).

    Args:
        op (bool): One of [True, False].

    Returns:
        bool: The selected value.
    """
    return op=="True"


@nodify(
    icon="folder",
    path=Attribute("filepath")
)
def Filepath(path: str) -> str:
    """
    Select a filepath from the file explorer.

    Args:
        path (str): The path.

    Returns:
        str: The selected path as a string (e.g. to be read by other Nodes).
    """
    return path


@nodify(
        icon="dataset",
        name=Attribute("lineedit")
)
def FromWorkspace(name: str = "") -> object:
    """
    Load data from workspace by its variable name.

    Args:
        name (str): Variable name in workspace.

    Returns:
        any: The workspace data.
    """
    if name=="":
        raise ValueError("Please specify a variable name.")
    if name not in workspace:
        raise KeyError(f"'{name}' not in workspace.")
    return workspace[name]


@nodify(
    icon="csv",
    path=Attribute("filepath"),
    delimiter=Attribute("combobox", value = ',', options=[";", ","]),
    encoding = Attribute("combobox", options = ['utf-8', 'utf-8-sig', 'latin1', 'ISO-8859-1', 'cp1252', 'utf-16']),
    has_index = Attribute("combobox", value="False", options=["False", "True"])
)
def LoadCSV(
    path: str,
    delimiter: str = ",",
    encoding: str = "utf-8",
    has_index: str = "False",
) -> pd.DataFrame:
    """
    Load a CSV file.

    Args:
        path (str): The path to the CSV file.
        delimiter (str): Delimiter of the CSV file.
        encoding (str): Encoding for reading the file.
        has_index (bool): If True, the first column of your data is treated as index column.

    Returns:
        table: The loaded data.
    """
    if has_index=="True":
        index_col=0
    else:
        index_col=None
    return pd.read_csv(path, delimiter=delimiter, encoding=encoding, index_col=index_col)


@nodify(
    icon="data_table",
    path=Attribute("filepath")
)
def LoadExcel(path: str) -> pd.DataFrame:
    """
    Load a table from an excel (.xlsx) file.

    Args:
        path (str): The path to the .xlsx file.

    Returns:
        table: The loaded data.
    """
    return pd.read_excel(path)


@nodify(
        icon="data_array",
        name=Attribute("lineedit"),
        start=Attribute("doublespinbox", value=0.0, range=[-1e9, 1e9]),
        stop=Attribute("doublespinbox", value=0.0, range=[-1e9, 1e9]),
        step=Attribute("doublespinbox", value=0.0, range=[-1e9, 1e9])
)
def Range(
    name: str = "",
    start: float = 0.0,
    stop: float = 1.0,
    step: float = 0.1,
) -> pd.Series:
    """
    Create an evenly spaced 1-dimensional array (as column).

    Args:
        name (str): Name, used as variable name or name of the output column.
        start (float): Start value.
        stop (float): Stop value.
        step (float): Step value.

    Returns:
        column: The created range.
    """
    a = np.arange(start, stop, step)
    res = pd.Series(a)
    if name !="":
        res.name=name
    else:
        res.name="values"
    return res


@nodify(
        icon="function",
        start=Attribute("doublespinbox", value=0.0, range=[-1e9, 1e9]),
        stop=Attribute("doublespinbox", value=0.0, range=[-1e9, 1e9]),
        step=Attribute("doublespinbox", value=0.0, range=[-1e9, 1e9]),
        expr = Attribute("lineedit", value="y=x")
        )
def RangeFunction(
    expr: str = "y=x",
    start: float = 0.0,
    stop: float = 1.0,
    step: float = 0.1,
) -> pd.DataFrame:
    """
    Creates a range and applies a function to it. Allowed functions: log, sqrt, abs, exp, sin, cos, tan, sinh, cosh, tanh.

    Args:
        start (float): Start value.
        stop (float): Stop value.
        step (float): Step value.
        expr (str): Formula, argument is defined as "x", e.g. "2*x" or "y=3*x".

    Returns:
        table: Two columns containing the range and computed values.
    """
    x = np.arange(start, stop, step)
    var_name, values = evaluate_mathematical_expression(expr, x)
    df = pd.DataFrame({"x": x, var_name: values})
    return df


@nodify(
    icon="csv",
    path=Attribute("filesave"),
    index=Attribute("combobox", value = "False", options=["False", "True"])
)
def SaveCSV(data, path: str, index: str = "False") -> None:
    """
    Save data in a CSV file.

    Args:
        data (column or table): The input data.
        path (str): Filepath to write to (already resolved to workspace if needed by backend).
        index (bool): If index shall be saved or not.
    """
    save_index = index=="True"

    # Ensure .csv extension
    if path and not path.endswith('.csv'):
        path = path + '.csv'

    data.to_csv(path, index=save_index)


@nodify(
    icon="data_table",
    path=Attribute("filesave"),
    index=Attribute("combobox", value = "False", options=["False", "True"])
)
def SaveExcel(data, path: str, index: str = "False") -> None:
    """
    Save data to an excel (.xlsx) file.

    Args:
        data (column or table): The input data.
        path (str): Filepath to write to (already resolved to workspace if needed by backend).
        index (bool): If index shall be saved or not.
    """
    save_index = index=="True"

    # Ensure .xlsx extension
    if path and not path.endswith('.xlsx'):
        path = path + '.xlsx'

    data.to_excel(path, index=save_index)


@nodify(
        icon="save",
        name=Attribute("lineedit")
)
def ToWorkspace(data, name: str = "") -> None:
    """
    Save input to workspace.

    Args:
        data (any): Input data.
        name (str): Name in workspace.
    """
    workspace[name] = data


@nodify(
        icon="input",
        val=Attribute("pylineedit", value=0.0)
        )
def Value(val=0.0) -> object:
    """
    Define a constant (numeric, boolean, string) or array based on user input. Use True or False for boolean. You can also use workspace variable names to load their values from workspace.

    Args:
        val (float, str, list or bool): The value. If you enter the name of a workspace variable, this node outputs its value.

    Returns:
        any: The value.
    """
    return val
