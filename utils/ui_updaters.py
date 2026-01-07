from typing import Union

import pandas as pd


def get_dataframe_columns(data: pd.DataFrame) -> list[str]:
    """Extracts column names from a DataFrame."""
    if isinstance(data, pd.DataFrame):
        return data.columns.tolist()
    elif isinstance(data, pd.Series):
        return [data.name]
    return []


def get_dataframe_columns_with_index(data: Union[pd.Series, pd.DataFrame]) -> list[str]:
    """Extracts column names from a DataFrame."""
    if isinstance(data, pd.DataFrame):
        return ["index"] + data.columns.tolist()
    elif isinstance(data, pd.Series):
        return ["index", data.name]
    return []

# The registry that maps a string name to the function
EXTRACTOR_REGISTRY = {
    "dataframe_columns": get_dataframe_columns,
    "dataframe_columns_with_index": get_dataframe_columns_with_index
}
