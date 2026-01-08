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

import numbers
from typing import Tuple

import numpy as np
import pandas as pd

from sciplex import nodify, Attribute
from _helpers import assign_name


@nodify(
        icon="table",
        kind=Attribute("combobox", value="Sum", options = ['Sum', 'Mean', 'Max', 'Min', 'Count', 'Std', 'Var']),
        how=Attribute("combobox", value="Columns", options = ['Columns', 'Rows'])
)
def AggregateTable(data, kind: str = "sum", how: str = "Columns"):
    """
    Compute an aggregation for each column or row of the input data.

    Args:
        data (column or table): The input data.
        kind (str): Aggregation function to perform. One of ["Sum", "Mean", "Max", "Min", "Count", "Std", "Var"].
        how (str): How aggregation is performed (along which axis). One of ["Columns", "Rows"].

    Returns:
        column or number: Result of the aggregation.
    """
    axis = 0 if how=="Columns" else 1

    if isinstance(data, pd.DataFrame):
        res = getattr(data, kind.lower())(axis=axis)
    elif isinstance(data, pd.Series):
        res = getattr(data, kind.lower())()
    if isinstance(res, pd.Series):
        res.name=kind
    return res


@nodify(
        icon="cut",
        column=Attribute("combobox", source="data", extractor="dataframe_columns"),
        range=Attribute("pylineedit")

)
def Clip(data, column: str, range: str):
    """
    Clip numerical values to a given range, i.e. limit values to be within the given range.

    Args:
        data (column or table): Input data.
        range (list): The range [min, max] to clip the values to. Can be defined:
            - As numerical values, e.g. [1,3].
            - As variable, e.g. "my_range", where "my_range" is a workspace variable containing the range as list.
            - As a list of variables, e.g. [a, b], where "a" and "b" are workspace variables.
        column (str): The column to clip.

    Returns:
        column or table: The clipped values as separate column in a Table.
    """
    _data = data.copy()
    if isinstance(_data, pd.Series):
        column = _data.name
        _data = _data.to_frame()

    lst = range
    if isinstance(lst, np.ndarray):
        lst = lst.tolist()
    if not isinstance(lst, (list, tuple)) or len(lst) != 2:
        raise ValueError("Length of range has to be a list with two entries.")

    new_col_name = assign_name(_data.columns, column+'_clipped')
    _data[new_col_name] = _data[column].clip(lower=lst[0], upper=lst[1])
    return _data


@nodify(
        icon="concat",
        ignore_index=Attribute("combobox", value = 'True', options=["True", "False"]),
        how=Attribute("combobox", value="Columns", options = ['Columns', 'Rows'])
)
def ConcatTables(data1, data2, ignore_index: str = "False", how: str = "Columns"):
    """
    Concatenate one table with another table, either along rows or columns.

    Args:
        data1 (column or table): The first dataset.
        data2 (column or table): The second dataset.
        ignore_index (bool): If True, index will be ignored.
        how (str): Choose from ["Columns", "Rows"] for concatenation in one of the two directions.

    Returns:
        column or table: The concatenated table.
    """
    axis = 1 if how=="Columns" else 0
    ignore_index = ignore_index=="True" and how=="Rows"
    return pd.concat([data1, data2], axis=axis, ignore_index=ignore_index)


@nodify(
        icon="info"
)
def Describe(data):
    """
    Description of data, visible on output socket (double click).

    Args:
        data (column or table): Input data.

    Returns:
        table: Column-wise description (statistics) of the data.
    """
    if data is None:
        return None
    return data.describe()


@nodify(
        icon= "drop",
        columns=Attribute("checkable-combobox", source="data", extractor="dataframe_columns"),
)
def Drop(data: pd.DataFrame, columns: list):
    """
    Drop selected columns from a table.

    Args:
        data (table): Input data.
        columns (list): Columns to drop.

    Returns:
        column or table: Input data with the columns removed.
    """
    if data is None:
        return None
    columns_to_drop = [c for c in columns if c in data.columns]
    return data.drop(columns=columns_to_drop, axis=1).squeeze(axis=1)


@nodify(
        icon="filter",
        ignore_index=Attribute("combobox", value = 'True', options=["True", "False"])
)
def Filter(data, cond, ignore_index: str = "False"):
    """
    Select rows of a table based on a boolean condition (single column).

    Args:
        data (table): Input data.
        cond (column): Column of booleans of the same length as data.
        ignore_index (bool): If True, filtering works as long as data and cond have the same length. Otherwise they need to have the same index too.

    Returns:
        column or table: The filtered data.
    """
    if not isinstance(cond, pd.Series):
        raise ValueError("Argument 'cond' must have exactly one column only.")
    if not cond.dtype==bool:
        raise TypeError("Argument 'cond' must be boolean.")

    if ignore_index=="True":
        return data[cond.to_numpy()]
    else:
        return data[cond]


@nodify(
        icon="group",
        kind=Attribute("combobox", value="sum", options = ['sum', 'mean', 'max', 'min', 'count', 'std', 'var']),
        columns=Attribute("checkable-combobox", source="data", extractor="dataframe_columns"),
        )
def GroupBy(data: pd.DataFrame, kind: str = "sum", columns: list = []):
    """
    Group a table along columns and perform an operation on the others.

    Args:
        data (table): Input data.
        columns (list): Columns to group by.
        kind (str): Operation to perform.

    Returns:
        table: The table with grouped and aggregated output.
    """
    # Inline check_min_n_columns_present(data, "GroupBy", n=2)
    if isinstance(data, pd.DataFrame):
        if len(data.columns) < 2:
            raise ValueError("Need at least 2 columns for GroupBy.")
    elif isinstance(data, pd.Series):
        raise ValueError("Need at least 2 columns for GroupBy.")
    return getattr(data.groupby(by=columns), kind)().reset_index()


@nodify(
    icon="nans",
    drop=Attribute("combobox", value = "False", options=["True", "False"]),
    fill_val=Attribute("doublespinbox", value=0.0, range=[-1e9, 1e9])
)
def MissingData(data, drop: str = "False", fill_val: float = 0.0):
    """
    Remove or replace NaN values in your data. Dropping NaN values is a row-wise operation.

    Args:
        data (table): Input data containing NaNs.
        drop (boolean): True for dropping, False for filling.
        fill_val (float): Values to fill in for NaNs if drop=False.

    Returns:
        table: Data without NaN values.
    """

    if drop=="True":
        return data.dropna()
    else:
        return data.fillna(value=fill_val)


@nodify(
        icon="pivot",
        columns=Attribute("combobox", source="data", extractor="dataframe_columns"),
        index=Attribute("combobox", source="data", extractor="dataframe_columns"),
        values=Attribute("combobox", source="data", extractor="dataframe_columns"),
)
def Pivot(data: pd.DataFrame, columns: str = None, index: str = None, values: str = None) -> pd.DataFrame:
    """
    Compute a pivot table from input.

    Args:
        data (table): Input data.
        columns (str): Column name used to create new columns.
        index (str): Column name used for new index
        values (str): Column name to compute new values (sum)

    Returns:
        table: The pivot table.
    """
    # Inline check_min_n_columns_present(data, "Pivot", n=3)
    if isinstance(data, pd.DataFrame):
        if len(data.columns) < 3:
            raise ValueError("Need at least 3 columns for Pivot.")
    elif isinstance(data, pd.Series):
        raise ValueError("Need at least 3 columns for Pivot.")
    return data.pivot(columns=columns, index=index, values=values)


@nodify(
        icon="change",
        old_name=Attribute("combobox", source="data", extractor="dataframe_columns"),
        new_name=Attribute("lineedit")
)
def Rename(data, old_name: str = None, new_name: str = ""):
    """
    Rename a column of a table.

    Args:
        data (column or table): Input data.
        old_name (str): The old column name.
        new_name (str): The new name.

    Returns:
        column or table: Data with changed name.
    """
    _data = data.copy()
    if isinstance(_data, pd.Series):
        _data.name = new_name
        return _data
    elif isinstance(_data, pd.DataFrame):
        return _data.rename({old_name: new_name}, axis=1)


@nodify(
        icon= "select",
        columns=Attribute("checkable-combobox", source="data", extractor="dataframe_columns"),
)
def SelectColumns(data, columns: list):
    """
    Select a column or columns of a table.

    Args:
        data (Table): Input data.
        columns (list): Columns to select.

    Returns:
        column or table: Slected column(s).
    """
    if isinstance(data, pd.Series):
        data = data.to_frame()
    return data[columns].squeeze(axis=1)


@nodify(
        icon="shift",
        n=Attribute("spinbox", range=[-int(1e9),int(1e9)])
)
def Shift(data, n: int = 1):
    """
    Shift a table by an integer value.

    Args:
        data (column or table): The input data.
        n (int): The index by  which the data is shifted. Positive values mean shifts to the bottom, negative ones to the top.

    Returns:
        column or table: The shifted data.
    """
    return data.shift(n)


@nodify(
        icon="sort",
        by=Attribute("checkable-combobox", source="data", extractor="dataframe_columns"),
        order=Attribute("combobox", value="ascending", options = ['ascending', 'descending'])
)
def Sort(data, by: list = [], order: str = "ascending"):
    """
    Sort a table by column values.

    Args:
        data (column or table): Input data.
        by (list): List of columns to sort by.
        order (str): One of ["ascending", "descending"] for the sorting order.

    Returns:
        column or table: The sorted data.
    """
    ascending = order=="ascending"
    if isinstance(data, pd.Series):
        return data.sort_values(ascending=ascending)
    elif isinstance(data, pd.DataFrame):
        return data.sort_values(by=by, ascending=ascending)


@nodify(
        icon="split",
        cols1=Attribute("checkable-combobox", source="data", extractor="dataframe_columns"),
        cols2=Attribute("checkable-combobox", source="data", extractor="dataframe_columns"),
)
def SplitTable(data: pd.DataFrame, cols1: list = [], cols2: list = []) -> Tuple:
    """
    Create two tables from one table by splitting columns.

    Args:
        data (table): Input data.
        cols1 (list): Names of columns for first output.
        cols2 (list): Names of columns for second output.

    Returns:
        column or table: First table.
        column or table: Second table.
    """
    return (data[cols1], data[cols2])


@nodify(
        icon="switch"
)
def Switch(cond, y_true, y_false):
    """
    Element-wise if-else statement. Outputs y_True if cond is True, otherwise y_False.
    Notes:
        - If cond is a column, then y_True and y_False also have to be columns of the same size.
        - If cond contains numerical data, anything unequal to zero is considered True.

    Args:
        cond (column or number): Column containing boolean(s) or a single boolean.
        y_true (column or number): Return values if cond==True, element wise for cond as Column.
        y_false (column or number): Return if cond==False, element wise for cond as Column.

    Returns:
        column or number: Evaluated result.
    """
    # Inline check_max_n_columns_present(y_true, "Switch", n=1)
    if isinstance(y_true, pd.DataFrame):
        if len(y_true.columns) > 1:
            raise ValueError("Need at least 1 columns for Switch.")

    # Inline check_max_n_columns_present(y_false, "Switch", n=1)
    if isinstance(y_false, pd.DataFrame):
        if len(y_false.columns) > 1:
            raise ValueError("Need at least 1 columns for Switch.")

    if isinstance(cond, bool):
        res = y_true if cond else y_false
    else:
        if not (isinstance(cond, pd.Series) and isinstance(y_true, pd.Series) and isinstance(y_false, pd.Series)):
            raise TypeError("If 'cond' is a column, the other inputs also have to be columns.")

        res=pd.Series(np.where(cond, y_true, y_false))
    if isinstance(res, pd.Series):
        res.name="switch"
    return res


@nodify(
        icon="square",
        bins=Attribute("pylineedit"),
        column=Attribute("combobox", source="data", extractor="dataframe_columns"),
        align=Attribute("combobox", value="left", options = ['left', 'center', 'right']),
        clip=Attribute("combobox", value="True", options = ['True', 'False'])
)
def ValuesToBins(data, bins: str = "", column: str = "", align: str = "left", clip: str = "True") -> pd.DataFrame:
    """
    Convert numerical data of a column to bins.

    Args:
        data (column or table): The input data.
        column (str): The column name for which binning shall be performed.
        bins (list or str): The bins for the binning. Can be defined through:
            - As numerical values, e.g. [1,2,3].
            - As variable, e.g. "my_bins", where "my_bins" is a workspace variable containing a list.
            - As a list of variables, e.g. [a, b, c], where a, b, c are workspace variables.
        align (str): Return values can equal "left", "center" or "right" edge of bin intervals.
        clip (bool): If True, values are clipped to range defined by bins prior to binning.

    Returns:
        table: The original data with an additional column with binned values.
    """
    _data=data.copy()
    if isinstance(_data, pd.Series):
        column = _data.name
        _data = _data.to_frame()

    if bins is None or bins == "":
        bin_values = np.linspace(_data[column].min(), _data[column].max(), 10)
    else:
        bin_values = bins

    if isinstance(bin_values, numbers.Number):
        if isinstance(bin_values, int):
            bin_values = np.linspace(_data[column].min(), _data[column].max(), bin_values)
        else:
            raise TypeError("If bin_values is a number, it has to be an integer.")

    if align=="left":
        labels=bin_values[:-1]
    elif align=="right":
        labels=bin_values[1:]
    elif align=="center":
        labels=[(bin_values[i]+bin_values[i+1])/2 for i in range(len(bin_values)-1)]
    else:
        return None

    new_col_name = assign_name(_data.columns, column+'_binned')

    if clip=="True":
        _data[new_col_name] = pd.cut(_data[column].clip(lower=bin_values[0], upper=bin_values[-1]), bins=bin_values, labels=labels).astype(float)
    else:
        _data[new_col_name] = pd.cut(_data[column], bins=bin_values, labels=labels).astype(float)
    return _data
