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
- You can return Plotly figures from node functions (see `visuals.py` for examples).
"""

import numbers
from typing import Union

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from sciplex import Attribute, nodify


@nodify(icon="barchart",
        title=Attribute("lineedit", value="Bar Plot"),
        x=Attribute("combobox", source="data", extractor="dataframe_columns_with_index"),
        y=Attribute("checkable-combobox", source="data", extractor="dataframe_columns"),
        stacked=Attribute("combobox", options=["True", "False"]),
        orientation=Attribute("combobox", options=["Vertical", "Horizontal"]),
        color=Attribute("colorpicker", value="#06E4A8")
)
def Bar(data, title: str="Bar Plot", color: str="#06E4A8", x: str=None, y: list=[], stacked: str="True", orientation: str="Vertical") -> go.Figure:
    """
    Create a simple bar plot.

    Args:
        data (column or table): Input data.
        title (str): Title of the plot.
        color (str): Color for plotting.
        x (str): Name of x-column to plot.
        y (list): Names of y-columns to plot.
        stacked (bool): If True, bars are stacked.
        orientation (str): One of ['Vertical', 'Horizontal'].

    Returns:
        fig: Created Plotly figure. Can be used as input for Plot and ToSubplot nodes.
    """
    if isinstance(data, pd.Series):
        plot_data = data.to_frame()
    else:
        plot_data = data.copy()

    is_stacked = stacked == "True"
    is_horizontal = orientation == "Horizontal"

    # Handle x-axis
    if x == "index" or x is None:
        x_values = plot_data.index if hasattr(plot_data, 'index') else range(len(plot_data))
    else:
        x_values = plot_data[x] if x in plot_data.columns else plot_data.index

    # Create figure
    fig = go.Figure()

    # Determine number of series to plot
    y_columns = y if y else [plot_data.columns[0]] if len(plot_data.columns) > 0 else []
    num_series = len(y_columns)

    # If multiple y columns, use Plotly's auto color palette (don't specify marker_color)
    # If single y column, use the specified color
    if num_series > 1:
        # Multiple series: use auto colors
        for col in y_columns:
            if col in plot_data.columns:
                fig.add_trace(go.Bar(
                    x=x_values if not is_horizontal else plot_data[col],
                    y=plot_data[col] if not is_horizontal else x_values,
                    name=col,
                    orientation='h' if is_horizontal else 'v',
                    # No marker_color specified - Plotly will use default color palette
                ))
    else:
        # Single y column: use specified color
        y_col = y_columns[0] if y_columns else plot_data.columns[0]
        if y_col in plot_data.columns:
            fig.add_trace(go.Bar(
                x=x_values if not is_horizontal else plot_data[y_col],
                y=plot_data[y_col] if not is_horizontal else x_values,
                name=y_col,
                orientation='h' if is_horizontal else 'v',
                marker_color=color,
            ))

    # Update layout
    fig.update_layout(
        title=title,
        barmode='stack' if is_stacked else 'group',
        xaxis_title=x if x and x != "index" else None,
        yaxis_title=y[0] if len(y) == 1 else None,
        showlegend=len(y) > 1,
        template='plotly_white',
    )
    # Enable grid (Plotly requires separate x/y axis updates)
    fig.update_xaxes(showgrid=True)
    fig.update_yaxes(showgrid=True)

    return fig


@nodify(
        icon="boxplot",
        title=Attribute("lineedit", value="My Plot"),
        color=Attribute("colorpicker", value="#06E4A8"),
        columns=Attribute("checkable-combobox", source="data", extractor="dataframe_columns"),
        by=Attribute("combobox", source="data", extractor="dataframe_columns"),
        group=Attribute("combobox", value="False", options=["True", "False"])
)
def Box(data, title: str="Box Plot", color: str="#06E4A8", columns: list=[], by: str=None, group: str="False") -> go.Figure:
    """
    Create a simple box plot.

    Args:
        data (column or table): Input data.
        title (str): Title of the plot.
        color (str): Color for plotting.
        columns (list): Columns to plot. If empty, all columns are plotted.
        by (str): Column to groupby.
        group (bool): If True, data is grouped by 'by' column.

    Returns:
        fig: Created Plotly figure. Can be used as input for Plot and ToSubplot nodes.
    """
    if isinstance(data, pd.Series):
        plot_data = data.to_frame()
    else:
        plot_data = data.copy()

    fig = go.Figure()

    if columns == []:
        columns = list(plot_data.select_dtypes(include=[np.number]).columns)

    if group == "True" and by and by in plot_data.columns:
        # Group by column
        for group_name, group_data in plot_data.groupby(by):
            for col in columns:
                if col in group_data.columns:
                    fig.add_trace(go.Box(
                        y=group_data[col],
                        name=f"{col} ({group_name})",
                        marker_color=color,
                    ))
    else:
        # No grouping
        for col in columns:
            if col in plot_data.columns:
                fig.add_trace(go.Box(
                    y=plot_data[col],
                    name=col,
                    marker_color=color,
                ))

    fig.update_layout(
        title=title,
        template='plotly_white',
        showlegend=True,
    )

    return fig


@nodify(icon="histogram",
        title=Attribute("lineedit", value="My Plot"),
        color=Attribute("colorpicker", value="#06E4A8"),
        y=Attribute("combobox", source="data", extractor="dataframe_columns"),
        bins=Attribute("pylineedit", value=10),
        normalize=Attribute("combobox", value="False", options=["True", "False"]),
        label=Attribute("lineedit", value="")
)
def Histogram(
    data,
    title: str = "My Plot",
    color: str = "#06E4A8",
    y: str = None,
    bins=10,
    normalize: str = "False",
    label: str = "",
) -> go.Figure:
    """
    Create a histogram.

    Args:
        data (column or table): Input data.
        title (str): Title of the plot.
        color (str): Color for plotting.
        y (str): Column to plot.
        bins (int, list, or str): The bins for the binning. Can be:
            - An integer: number of bins
            - A list/array: custom bin edges, e.g. [1,2,3]
            - A string: variable name containing bins
        normalize (str): "True" to normalize, "False" for count.

    Returns:
        fig: Created Plotly figure. Can be used as input for Plot and ToSubplot nodes.
    """
    if isinstance(data, pd.Series):
        plot_data = data.to_frame()
    else:
        plot_data = data.copy()

    # Get the data column to plot
    if y and y in plot_data.columns:
        hist_data = plot_data[y]
    else:
        # Use first column if y is not specified or not found
        hist_data = plot_data.iloc[:, 0]
        y = plot_data.columns[0] if len(plot_data.columns) > 0 else None

    # Handle bins parameter
    if bins is None or bins == "":
        # Default: 10 bins
        num_bins = 10
        use_custom_bins = False
    elif isinstance(bins, numbers.Number):
        # Integer number of bins
        if isinstance(bins, int) and bins > 0:
            num_bins = bins
            use_custom_bins = False
        else:
            raise TypeError("If bins is a number, it must be a positive integer.")
    elif isinstance(bins, (list, np.ndarray, tuple)):
        # Custom bin edges
        if len(bins) > 1:
            bin_edges = np.array(bins)
            use_custom_bins = True
        else:
            raise ValueError("Custom bins must have at least 2 edges.")
    else:
        # Try to convert string to number
        try:
            num_bins = int(float(bins))
            use_custom_bins = False
        except (ValueError, TypeError):
            raise TypeError(f"bins must be an integer, list of bin edges, or convertible to integer. Got: {type(bins)}")

    is_normalized = normalize == "True"
    hist_label = label if label else (y if y else "Value")

    # Set histnorm value (Plotly accepts: None, 'percent', 'probability', 'density', 'probability density')
    histnorm_value = 'probability density' if is_normalized else None

    fig = go.Figure()

    if use_custom_bins:
        # For custom bins, we need to compute the histogram manually
        # and use a bar chart, since Plotly's Histogram doesn't directly support custom bin edges
        counts, bin_edges = np.histogram(hist_data, bins=bin_edges)

        # Calculate bin centers for x-axis
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # Normalize if requested
        if is_normalized:
            # Probability density: normalize so area = 1
            bin_widths = np.diff(bin_edges)
            counts = counts.astype(float) / (counts.sum() * bin_widths)
            y_title = 'Probability Density'
        else:
            y_title = 'Count'

        # Use bar chart for custom bins
        fig.add_trace(go.Bar(
            x=bin_centers,
            y=counts,
            name=hist_label,
            marker_color=color,
            width=[bin_edges[i+1] - bin_edges[i] for i in range(len(bin_edges)-1)],
        ))
    else:
        # Use Plotly's Histogram for automatic or number-of-bins binning
        fig.add_trace(go.Histogram(
            x=hist_data,
            nbinsx=num_bins,
            name=hist_label,
            marker_color=color,
            histnorm=histnorm_value,
        ))
        y_title = 'Probability Density' if is_normalized else 'Count'

    fig.update_layout(
        title=title,
        xaxis_title=y if y else "Value",
        yaxis_title=y_title,
        template='plotly_white',
        showlegend=bool(label),
    )

    return fig


@nodify(icon="line",
        title=Attribute("lineedit", value="My Plot"),
        color=Attribute("colorpicker", value="#06E4A8"),
        x=Attribute("combobox", source="data", extractor="dataframe_columns_with_index"),
        y=Attribute("combobox", source="data", extractor="dataframe_columns"),
        linewidth=Attribute("doublespinbox", value=1.0, range=(0, 100)),
        linestyle=Attribute("combobox", value='-', options=[' ', '-', '--', '-.', ':']),
        marker=Attribute("combobox", value="", options=["",".","o","x","+"]),
        markersize=Attribute("doublespinbox", value=5.0, range=(0, 1000)),
        label=Attribute("lineedit", value=""),
)
def Line(data, title: str = "My Plot", color: str="#06E4A8", x: str=None, y: str=None, linestyle: str="-", linewidth: float=1.0, marker: str="", markersize: float=5.0, label: str="") -> go.Figure:
    """
    Create a simple line plot. For multi-line plots, use MultiLine Node.

    Args:
        data (column or table): Input data.
        title (str): Title of the plot.
        color (str): Color for plotting.
        x (str): Name of x-column to plot.
        y (str): Names of y-column to plot.
        linestyle (str): Style of the line.
        linewidth (float): Width of line.
        marker (str): Marker style.
        markersize (float): Size of marker, if marker is not empty.
        label (str): Label of curve.

    Returns:
        fig: Created Plotly figure. Can be used as input for Plot and ToSubplot nodes.
    """
    if isinstance(data, pd.Series):
        plot_data = data.to_frame()
    else:
        plot_data = data.copy()

    if x == "index":
        x = None

    # Get x values
    if x is None:
        x_values = plot_data.index if hasattr(plot_data, 'index') else range(len(plot_data))
    else:
        x_values = plot_data[x] if x in plot_data.columns else plot_data.index

    # Get y values - use first column if y is None or not found
    if y and y in plot_data.columns:
        y_values = plot_data[y]
    else:
        if len(plot_data.columns) > 0:
            y_values = plot_data.iloc[:, 0]
            y = plot_data.columns[0]  # Update y for label
        else:
            raise ValueError("No data columns available for line plot")

    # Map linestyle to Plotly dash
    dash_map = {
        '-': None,  # solid
        '--': 'dash',
        '-.': 'dashdot',
        ':': 'dot',
        ' ': None,  # no line (handled by mode)
    }
    line_dash = dash_map.get(linestyle, None)

    # Map marker style
    marker_symbol_map = {
        '.': 'circle',
        'o': 'circle',
        'x': 'x',
        '+': 'cross',
    }
    marker_symbol = marker_symbol_map.get(marker, None) if marker else None

    # Determine mode based on linestyle and marker
    has_line = linestyle != ' '  # Space means no line
    if has_line and marker_symbol:
        mode = 'lines+markers'
    elif has_line:
        mode = 'lines'
    elif marker_symbol:
        mode = 'markers'
    else:
        mode = 'markers'  # Fallback to markers if both are disabled

    fig = go.Figure()

    # Build trace parameters
    trace_params = {
        'x': x_values,
        'y': y_values,
        'mode': mode,
        'name': label if label else (y if y else "Value"),
    }

    # Add line parameters only if line is enabled
    if has_line:
        trace_params['line'] = dict(
            color=color,
            width=linewidth,
            dash=line_dash,
        )

    # Add marker parameters only if marker is enabled
    if marker_symbol:
        trace_params['marker'] = dict(
            symbol=marker_symbol,
            size=markersize,
            color=color,
        )

    fig.add_trace(go.Scatter(**trace_params))

    fig.update_layout(
        title=title,
        xaxis_title=x if x else "Index",
        yaxis_title=y if y else "Value",
        template='plotly_white',
        showlegend=bool(label),
    )

    return fig


@nodify(icon="scatter",
        title=Attribute("lineedit", value="My Plot"),
        color=Attribute("colorpicker", value="#06E4A8"),
        x=Attribute("combobox", source="data", extractor="dataframe_columns"),
        y=Attribute("combobox", source="data", extractor="dataframe_columns"),
        markersize=Attribute("spinbox", value=20, range=(0, 1000)),
        marker=Attribute("combobox", options=[".","o","x","+"]),
        label=Attribute("lineedit", value="")
)
def Scatter(data, title: str = "My Plot", color: str="#06E4A8", x: str=None, y: str=None, marker: str=".", markersize: int=20, label: str="") -> go.Figure:
    """
    Create a simple scatter plot.

    Args:
        data (column or table): Input data.
        title (str): Title of the plot.
        color (str): Color for plotting.
        x (str): Name of x-column to plot.
        y (str): Names of y-column to plot.
        marker (str): Marker style.
        markersize (float): Size of marker, if marker is not empty.

    Returns:
        fig: Created Plotly figure. Can be used as input for Plot and ToSubplot nodes.
    """
    if isinstance(data, pd.Series):
        plot_data = data.to_frame()
    else:
        plot_data = data.copy()

    # Handle x values - use index if x is None or not found
    if x and x in plot_data.columns:
        x_values = plot_data[x]
    else:
        x_values = plot_data.index if hasattr(plot_data, 'index') else range(len(plot_data))

    # Handle y values - use first column if y is None or not found
    if y and y in plot_data.columns:
        y_values = plot_data[y]
    else:
        if len(plot_data.columns) > 0:
            y_values = plot_data.iloc[:, 0]
            y = plot_data.columns[0]  # Update y for label
        else:
            raise ValueError("No data columns available for scatter plot")

    # Map marker style
    marker_symbol_map = {
        '.': 'circle',
        'o': 'circle',
        'x': 'x',
        '+': 'cross',
    }
    marker_symbol = marker_symbol_map.get(marker, 'circle')

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_values,
        y=y_values,
        mode='markers',
        name=label if label else (y if y else "Value"),
        marker=dict(
            symbol=marker_symbol,
            size=markersize,
            color=color,
        ),
    ))

    fig.update_layout(
        title=title,
        xaxis_title=x if x else "Index",
        yaxis_title=y if y else "Value",
        template='plotly_white',
        showlegend=bool(label),
    )

    return fig


@nodify(
        icon="poly",
        title=Attribute("lineedit", value="My Plot")
)
def Plot(*figures, title: str = "My Plot") -> go.Figure:
    """
    Combine multiple Plotly Figures into a single figure.

    Supports line plots, scatter plots, bar plots, histograms, and boxplots.
    """
    if not figures:
        return go.Figure()

    # Create new figure
    fig = go.Figure()

    # Add all traces from all input figures
    for fig_input in figures:
        if isinstance(fig_input, go.Figure):
            for trace in fig_input.data:
                fig.add_trace(trace)

    # Use layout from first figure, but update title
    if figures and isinstance(figures[0], go.Figure):
        fig.update_layout(figures[0].layout)

    fig.update_layout(title=title)

    return fig


@nodify(
        icon="plot2",
        x=Attribute("combobox", source="data", extractor="dataframe_columns_with_index"),
        y=Attribute("checkable-combobox", source="data", extractor="dataframe_columns_with_index"),
        title=Attribute("lineedit"),
        subplots=Attribute("combobox", value="True", options = ["True", "False"]),
        positions=Attribute("lineedit")
)
def MultiLine(data: Union[pd.Series, pd.DataFrame], x: str=None, y: list=[], title: str="Plot Title", subplots: str="False", positions: str="") -> go.Figure:
    """
    Create multi-row subplots with line or scatter plot.

    Args:
        data (Table): Input data
        x (str): Name of x-column
        y (list): List of columns for y-axis
        title (str): Title of plot
        subplots (str): If "True", every y-value is plotted in a separate subplot
        positions (str): List of subplot positions to control what is plotted in which subplot.
                         For each of the selected columns in y. Used if subplots="True".
                         Must have same length as selected columns. Can be a Python list string like "[1, 2, 3]".

    Returns:
        fig: Created Plotly figure. Can be used as input for Plot and ToSubplot nodes.
    """
    if isinstance(data, pd.Series):
        plot_data = data.to_frame()
    else:
        plot_data = data.copy()

    if not y:
        raise ValueError("At least one y column must be selected")

    if x == "index":
        x = None

    use_subplots = subplots == "True"

    # Parse positions if provided
    use_positions = False
    position_list = []
    if positions and positions.strip():
        try:
            # Try to evaluate as Python expression (supports workspace variables)
            from _helpers import evaluate_mathematical_expression
            # If it's a string representation of a list, parse it
            if positions.strip().startswith('['):
                # Simple parsing for list strings
                import ast
                position_list = ast.literal_eval(positions)
            else:
                # Try as workspace variable or expression
                _, position_list = evaluate_mathematical_expression(positions, None)
                if not isinstance(position_list, list):
                    position_list = [position_list]
        except Exception:
            # Fallback: treat as comma-separated values
            position_list = [int(p.strip()) for p in positions.split(',') if p.strip()]

        if len(position_list) == len(y):
            use_positions = True

    # Get x values
    if x is None:
        x_values = plot_data.index if hasattr(plot_data, 'index') else range(len(plot_data))
    else:
        x_values = plot_data[x] if x in plot_data.columns else plot_data.index

    if use_subplots:
        # Create subplots - one for each y column
        n_subplots = len(y)
        fig = make_subplots(
            rows=n_subplots,
            cols=1,
            shared_xaxes=True,
            subplot_titles=y,
            vertical_spacing=0.05,
        )

        for i, column in enumerate(y):
            if column in plot_data.columns:
                row_idx = position_list[i] if use_positions and i < len(position_list) else (i + 1)
                if row_idx < 1 or row_idx > n_subplots:
                    row_idx = i + 1

                fig.add_trace(
                    go.Scatter(
                        x=x_values,
                        y=plot_data[column],
                        mode='lines',
                        name=column,
                        showlegend=False,
                    ),
                    row=row_idx,
                    col=1,
                )

        fig.update_layout(
            title_text=title,
            template='plotly_white',
        )
    else:
        # Single plot with multiple lines
        fig = go.Figure()

        for col in y:
            if col in plot_data.columns:
                fig.add_trace(go.Scatter(
                    x=x_values,
                    y=plot_data[col],
                    mode='lines',
                    name=col,
                ))

        fig.update_layout(
            title=title,
            template='plotly_white',
            showlegend=True,
        )

    return fig


@nodify(
        icon="subplot",
        row_index = Attribute("spinbox", value=1, range=(0, 15)),
        col_index = Attribute("spinbox", value=1, range=(0, 15))

)
def ToSubplot(fig: go.Figure, row_index: int=1, col_index: int=1) -> list:
    """
    Create a subplot from a figure. Connect multiple of this kind of node to a CombineFigures Node.

    Args:
        fig (fig): Figure, e.g. output of a Line Node.
        row_index (int): Row index in subplot.
        col_index (int): Column index in subplot.

    Returns:
        subplot object: Input for CombineFiguress node.
    """
    return [fig, (row_index, col_index)]


@nodify(
        icon="grid",
        title=Attribute("lineedit", value="My Figure")
)
def CombineFiguress(*subplots: list, title: str = "My Figure") -> go.Figure:
    """
    Combine multiple Plotly figures into a single figure with subplots.

    Args
        subplots : List of lists [fig, (i_row, i_col)]

    Returns
        fig : Figure containing the subplots
    """
    if not subplots:
        return go.Figure()

    # Determine max rows and columns
    max_row = max(pos[0] for _, pos in subplots if isinstance(pos, (list, tuple)) and len(pos) >= 2)
    max_col = max(pos[1] for _, pos in subplots if isinstance(pos, (list, tuple)) and len(pos) >= 2)

    # Create subplot figure
    fig = make_subplots(
        rows=max_row,
        cols=max_col,
        subplot_titles=[f"Subplot ({pos[0]}, {pos[1]})" for _, pos in subplots if isinstance(pos, (list, tuple))],
    )

    # Add traces from each figure to its designated subplot
    for fig_input, (row, col) in subplots:
        if isinstance(fig_input, go.Figure):
            for trace in fig_input.data:
                fig.add_trace(trace, row=row, col=col)

    fig.update_layout(
        title_text=title,
        template='plotly_white',
    )

    return fig
