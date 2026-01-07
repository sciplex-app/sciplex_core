import numbers
import operator
import re

import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator

from sciplex import nodify, Attribute, workspace
from _helpers import assign_name, evaluate_mathematical_expression


@nodify(
        icon="arithm",
        op=Attribute("combobox", value = "+", options=["+", "-", "x", "/"])
)
def Arithmetic(x, y, op: str = "+"):
    """
    Calculate an arithmetic operation between two inputs.  Element-wise for tabular input.

    Args:
        x (numeric): First input.
        y (numeric): Second input.
        op (str): Arithmetic operation to be performed. One of [+,-,x,/].

    Returns:
        numeric: The result.
    """

    ops = {
        '+': [operator.add, "sum"],
        '-': [operator.sub, "difference"],
        'x': [operator.mul, "product"],
        '/': [operator.truediv, "quotient"]
    }

    if (isinstance(x, pd.DataFrame) and isinstance(y, pd.Series)) or (isinstance(y, pd.DataFrame) and isinstance(x, pd.Series)):
        raise ValueError("Cannot add/subtract/multiply/divide tables with columns.")
    res = ops[op][0](x,y)
    if isinstance(res, pd.Series):
        res.name=ops[op][1]
    return res


@nodify(
        icon="corr"
)
def Correlation(data):
    """
    Compute the correlation matrix of the data. Matrix is visible on the output socket (double click).

    Args:
        data (table): I nput data. Needs >1 columns.

    Returns:
        table: The correlation matrix.
    """
    # Inline check_min_n_columns_present(data, "Correlation", n=2)
    if isinstance(data, pd.DataFrame):
        if len(data.columns) < 2:
            raise ValueError("Need at least 2 columns for Correlation.")
    elif isinstance(data, pd.Series):
        if 1 < 2:
            raise ValueError("Need at least 2 columns for Correlation.")
    return data.corr()


@nodify(
        icon="cumsum"
)
def Cumsum(data):
    """
    Compute the cumulative sum of the input data.

    Args:
        data (column or table): Input data

    Returns:
        column or table: Cumulative sum along the index.
    """
    return data.cumsum()


@nodify(
        n=Attribute("spinbox", value=1, range=(-int(1e9), int(1e9))),
        icon="diff"
        )
def Diff(data, n: int = 1):
    """
    Compute the difference between consecutive elements. Note that the first n values of the result are returned as NaN.

    Args:
        data (column or table): Input data.
        n (int): Step size.

    Returns:
        column or table: Entry i corresponds to result[i]=data[i]-data[i-n].
    """
    return data.diff(n)


@nodify(
        icon="function",
        expr = Attribute("lineedit")
        )
def Function(x, expr: str = ""):
    """
    Applies a one-dimensional function. Input can be a number, column or table (element-wise evaluation) . Allowed functions: log, sqrt, abs, exp, sin, cos, tan, sinh, cosh, tanh. Enter the indepndent variable as "x" in the input expression ('expr').

    Args:
        x (numeric): Input data.
        expr (str): formula, argument is defined as "x", e.g. "2*x" or "y=3*x".

    Returns:
        numeric: the computed result
    """

    var_name, result = evaluate_mathematical_expression(expr, x)

    # Assign name if result is a Series
    if isinstance(result, pd.Series):
        result.name = var_name
    return result


@nodify(
        icon="function",
        op = Attribute("combobox", options=["exp", "log", "sqrt", "abs", "sin", "cos", "tan", "sinh", "cosh", "tanh"])
        )
def Expression(x, op: str = "exp"):
    """
    Applies one of the specified functions to the input data. Allowed functions: [log, sqrt, abs, exp, sin, cos, tan, sinh, cosh, tanh].

    Args:
        x (numeric): Input data
        op (str): Function to apply to input data.

    Returns:
        numeric: the computed result
    """

    funcs = {
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
    return funcs[op](x)


@nodify(icon = "map1d",
        x_column=Attribute("combobox", source="data", extractor="dataframe_columns"),
        map_data=Attribute("pylineedit"),
        x_support=Attribute("pylineedit"),
        clip=Attribute("combobox", value = "False", options=["True", "False"])
        )
def Interp1D(data, x_column: str = "", map_data: str = "", x_support: str = "", clip: str = "True"):
    """
    Perform a linear interpolation in one dimension (1D map).

    Args:
        data (table, column or number): Input data.
        x_column (str): Name of column for input data. Only relevant if data is a Table.
        map_data (str): Map values. Can be defined as list (e.g. [1,2,3]) or as the name of a workspace variable.
        x_support (str): Support values. Can be defined as list (e.g. [1,2,3]) or as the name of a workspace variable.
        clip (bool): If True, values are clipped prior to interpolation to the support range.

    Returns:
        table: Table with input data and a column with the resulting interpolated values.
    """
    if map_data is None or map_data == "":
        raise ValueError("Please specify 'map_data' (e.g. [1,2,3] or a workspace variable).")
    if x_support is None or x_support == "":
        raise ValueError("Please specify 'x_support' (e.g. [0,1,2] or a workspace variable).")

    x_support_arr = np.array(x_support, dtype=float)
    map_data_arr = np.array(map_data, dtype=float)
    interp = RegularGridInterpolator((x_support_arr,), map_data_arr)

    if isinstance(data, pd.Series):
        x_data = data.values
        _data = data.to_frame()
    elif isinstance(data, numbers.Number):
        _data = pd.DataFrame({'data': [data]})
        x_data = _data["data"].values
    elif isinstance(data, pd.DataFrame):
        _data = data.copy()
        x_data = _data[x_column].values

    if clip=="True":
        x_data=np.clip(x_data, np.min(x_support_arr), np.max(x_support_arr))

    col_name = assign_name(_data.columns, "interp1d")
    _data[col_name] = interp(x_data)

    return _data


@nodify(icon = "map2d",
        x_column=Attribute("combobox", source="data", extractor="dataframe_columns"),
        y_column=Attribute("combobox", source="data", extractor="dataframe_columns"),
        map_data=Attribute("pylineedit"),
        x_support=Attribute("pylineedit"),
        y_support=Attribute("pylineedit"),
        clip=Attribute("combobox", value = "False", options=["True", "False"]),
        )
def Interp2D(
    data,
    x_column: str = "",
    y_column: str = "",
    map_data: str = "",
    x_support: str = "",
    y_support: str = "",
    clip: str = "True",
):
    """
    Perform a linear interpolation in two dimensions (2D map).

    Args:
        data (table, list or array): Input data.
        x_column (str): Name of column for input data in x-direction. Only relevant if data is a Table.
        y_column (str): Name of column for input data in y-direction. Only relevant if data is a Table.
        map_data (str): Map values. Can be defined as list (e.g. [[1,2,3], [4,5,6]]) or as the name of a workspace variable.
        x_support (str): Support values in x-direction. Can be defined as list (e.g. [1,2,3]) or as the name of a workspace variable.
        y_support (str): Support values in y-direction. Can be defined as list (e.g. [2,3]) or as the name of a workspace variable.
        clip (bool): If True, values are clipped prior to interpolation to the support range.

    Returns:
        table: Original Data with an additional column with interpolated values.
    """
    if map_data is None or map_data == "":
        raise ValueError("Please specify 'map_data' (e.g. [[1,2],[3,4]] or a workspace variable).")
    if x_support is None or x_support == "":
        raise ValueError("Please specify 'x_support' (e.g. [0,1,2] or a workspace variable).")
    if y_support is None or y_support == "":
        raise ValueError("Please specify 'y_support' (e.g. [0,1,2] or a workspace variable).")

    x_support_arr = np.array(x_support, dtype=float)
    y_support_arr = np.array(y_support, dtype=float)
    map_data_arr = np.array(map_data, dtype=float).T
    interp = RegularGridInterpolator((x_support_arr, y_support_arr), map_data_arr)

    if isinstance(data, (np.ndarray, list)):
        _data = pd.DataFrame(columns=["x", "y"], data=[data])
        x_column = "x"
        y_column = "y"
    else:
        _data = data.copy()

    x_data = _data[x_column]
    y_data = _data[y_column]

    if clip=="True":
        x_data=np.clip(x_data, np.min(x_support_arr), np.max(x_support_arr))
        y_data=np.clip(y_data, np.min(y_support_arr), np.max(y_support_arr))
    col_name = assign_name(_data.columns, "interp2d")
    _data[col_name]=interp(pd.concat([x_data, y_data], axis=1).values)
    return _data


@nodify(
        icon="logical",
        op=Attribute("combobox", value = "AND", options=["AND", "OR", "XOR"]),

)
def Logical(x, y, op: str = "AND"):
    """
    Compute a logical operation. Select one of ['AND', 'OR', 'XOR'].

    Args:
        x (bool): The first input.
        y (bool): The second input.
        op (str): The operation to perform.

    Returns:
        bool: The result of the logical operation. Element-wise for Tables.
    """
    if op=="AND":
        res=x&y
    elif op=="OR":
        res=x|y
    elif op=="XOR":
        res=x^y

    if isinstance(res, pd.Series):
        res.name=op.lower()
    return res


@nodify(
        icon="MaxMin",
        op=Attribute("combobox", value = "Max", options=["Max", "Min"])
)
def MaxMin(x, y, op: str = "Max"):
    """
    Returns the (element-wise) Max / Min for the two inputs.

    Args:
        x (numeric): The first input.
        y (numeric): The second input.

    Returns:
        numeric: The (element-wise) Max / Min.
    """
    if op=="Max":
        res = np.maximum(x,y)
    else:
        res = np.minimum(x,y)
    if isinstance(res, pd.Series):
        res.name = op
        res.index = x.index
    return res


@nodify(
        icon="not"
)
def Not(data):
    """
    Element-wise NOT operation.

    Args:
        data (bool): Data containing solely booleans.

    Returns:
        bool: Inverted booleans.
    """
    if isinstance(data, pd.DataFrame):
        res = ~data
    elif isinstance(data, numbers.Number):
        res=not data
    return res


@nodify(
        icon="rel",
        op=Attribute("combobox", value = ">", options=[">", ">=", "==", "!=", "<", "<="])

)
def Relation(x, y, op: str = ">"):
    """
    Compute a relational operation between x and y.

    Args:
        x (numeric): First input.
        y (numeric): Second input.
        op (str): one of [">", ">=", "==", "!=", "<", "<="]

    Returns:
        numeric: The result of the comparison.
    """

    ops = {
        '==': [operator.eq, "e1"],
        '!=': [operator.ne, "ne"],
        '<': [operator.lt, "lt"],
        '<=': [operator.le, "le"],
        '>': [operator.gt, "gt"],
        '>=': [operator.ge, "ge"],
    }

    if op not in ops:
        raise ValueError(f"Unsupported relation: {op}")
    res=ops[op][0](x, y)
    if isinstance(res, pd.Series):
        res.name=ops[op][1]
    return  res


@nodify(icon = "roll",
        kind=Attribute("combobox", value='mean', options=['mean', 'sum', 'max', 'min', 'var']),
        n=Attribute("spinbox")
)
def Rolling(data, kind: str = "mean", n: int = 1):
    """
    Compute a basic operation over a rolling window.

    Args:
        data (column or table): Input data.
        n (int): Window size of the operation.
        kind (str): What to calculate, one of ["mean", "sum", "max", "min", "var"]

    Returns:
        column or table: The resulting Table.

    """
    if kind=='mean':
        return data.rolling(n).mean()
    elif kind=='sum':
        return data.rolling(n).sum()
    elif kind=='max':
        return data.rolling(n).max()
    elif kind=='min':
        return data.rolling(n).min()
    elif kind=='var':
        return data.rolling(n).var()
    elif kind=='std':
        return data.rolling(n).std()


@nodify(
        icon="TableFormula",
        formula = Attribute("lineedit")
)
def TableCalc(data, formula: str):
    """
    Calculates a formula based on the columns of the table. Column names and workspace variables will be regognized (column names are priorized over similar workspace variables).
    Allowed functions: log, sqrt, abs, exp, sin, cos, tan, sinh, cosh, tanh

    Args:
        data (column or table): The table to calculate something from.
        formula (str): Formula to calculate, e.g. "y=2*x" or "x^2"

    Returns:
        table: Table with a new column
    """
    if isinstance(data, pd.Series):
        data=data.to_frame()
    # find left hand side of equation
    plain_formula = formula
    formula = formula.replace("^", "**")
    match = re.match(r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=', formula)
    varname_assigned = True
    try:
        assigned_var = match.group(1)
    except Exception:
        assigned_var = assign_name(data.columns, "f")
        formula = assigned_var + "=" + formula
        varname_assigned = False

    # Allowed functions
    allowed_functions = ["log", "sqrt", "abs", "exp", "sin", "cos", "tan", "sinh", "cosh", "tanh"]

    for func in allowed_functions:
        formula = re.sub(rf'\b{func}\b', func, formula, flags=re.IGNORECASE)

    # pattern for extraction
    pattern = r'^[\w\s\=\+\-\*/\(\)\.]+$'

    # Check if expression is ok
    expressions = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', formula)
    column_names = data.columns.tolist()
    variables = list(workspace.keys())
    functions_ok = all(func in allowed_functions+column_names+[assigned_var]+variables for func in expressions)

    if not re.match(pattern, formula) or not functions_ok:
        raise ValueError('Expressions has errors')
    local_dict = {k: workspace[k] for k in workspace.keys()}
    for c in data.columns:
        local_dict[c] = data[c]
    df_res = pd.eval(formula, local_dict=local_dict, engine="numexpr", target=data)
    # df_res = data.eval(formula, engine = 'numexpr', local_dict=variables_registry.data)
    if not varname_assigned:
        df_res.rename({assigned_var: plain_formula}, axis=1, inplace=True)
    return df_res
