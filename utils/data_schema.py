"""
Utility functions for extracting schema information from data objects.

This module provides functions to extract metadata about data structures,
primarily for pandas DataFrames.
"""

from typing import Optional

import pandas as pd


def extract_dataframe_schema(df: pd.DataFrame) -> dict:
    """
    Extract schema information from a pandas DataFrame.

    Args:
        df: The pandas DataFrame to analyze

    Returns:
        Dictionary containing:
        - columns: List of column names
        - dtypes: Dictionary mapping column names to data types
        - shape: Tuple of (rows, columns)
        - sample: List of dictionaries representing first few rows
    """
    if df is None or df.empty:
        return {"columns": [], "dtypes": {}, "shape": (0, 0), "sample": None}

    # Get column names and dtypes
    columns = df.columns.tolist()
    dtypes = {col: str(df[col].dtype) for col in columns}

    # Get sample data (first few rows)
    sample_size = min(5, len(df))
    sample = df.head(sample_size).to_dict('records') if sample_size > 0 else None

    return {
        "columns": columns,
        "dtypes": dtypes,
        "shape": df.shape,
        "sample": sample,
    }


def extract_schema_from_data(data) -> Optional[dict]:
    """
    Extract schema information from various data types.

    Currently supports:
    - pandas.DataFrame
    - pandas.Series (converted to DataFrame)

    Args:
        data: The data object to analyze

    Returns:
        Schema dictionary or None if not supported
    """
    if isinstance(data, pd.DataFrame):
        return extract_dataframe_schema(data)
    elif isinstance(data, pd.Series):
        # Convert Series to DataFrame for schema extraction
        df = data.to_frame() if data.name else data.to_frame(name='value')
        return extract_dataframe_schema(df)

    return None

