import numbers
from typing import Union

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import PathPatch, Polygon, Rectangle

# Note: matplotlib backend is set by desktop/app.py (QtAgg) or web backend (Agg)
# No need to set it here - keeps code consistent between desktop and web

from sciplex import nodify, Attribute


@nodify(icon="barchart",
        title=Attribute("lineedit", value="Bar Plot"),
        x=Attribute("combobox", source="data", extractor="dataframe_columns_with_index"),
        y=Attribute("checkable-combobox", source="data", extractor="dataframe_columns"),
        stacked=Attribute("combobox", options=["True", "False"]),
        orientation=Attribute("combobox", options=["Vertical", "Hoizontal"]),
        color=Attribute("colorpicker")
)
def Bar(data, title: str="Bar Plot", color: str="#2F4F4F", x: str=None, y: list=[], stacked: str="True", orientation: str="Vertical") -> Figure:
    """
    Create a simple bar plot.

    Args:
        data (column or table): Input data.
        title (str): Title of the plot.
        color (str): Color for plotting.
        x (str): Name of x-column to plot.
        y (list): Names of y-columns to plot.
        stacked (bool): If True, box plots for different.
        orientation (str): One of ['Vertical', 'Horizontal'].

    Returns:
        fig: Created figure. Can be used as input for Plot and ToSubplot nodes.
    """
    if isinstance(data, pd.Series):
        plot_data = data.to_frame()
    else:
        plot_data = data.copy()
    fig, ax = plt.subplots(1,1)
    stacked = stacked == "True"
    kind = "bar" if orientation=="Vertical" else "barh"
    if x=="index":
        x=None
    if len(y) > 1:
        color=None
    plot_data.plot(x=x, y=y, ax=ax, stacked=stacked, kind=kind, color=color)
    ax.set_title(title)
    ax.grid()
    fig.tight_layout()

    return fig


@nodify(
        icon="boxplot",
        title=Attribute("lineedit", value="My Plot"),
        color=Attribute("colorpicker"),
        columns=Attribute("checkable-combobox", source="data", extractor="dataframe_columns"),
        by=Attribute("combobox", source="data", extractor="dataframe_columns"),
        group=Attribute("combobox", value="False", options=["True", "False"])
)
def Box(data, title: str="Box Plot", color: str="#2F4F4F", columns: list=[], by: str=None, group: str="False") -> Figure:
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
        fig: Created figure. Can be used as input for Plot and ToSubplot nodes.
    """
    if isinstance(data, pd.Series):
        plot_data = data.to_frame()
    else:
        plot_data = data.copy()

    fig, ax = plt.subplots(1,1)

    if columns == []:
        columns=None
    if group=="True":
        plot_data.boxplot(column=columns, by=by, ax=ax, patch_artist=True, color=color)
    else:
        plot_data.boxplot(column=columns, ax=ax, patch_artist=True, color=color)

    ax.set_title(title)
    ax.grid()
    fig.tight_layout()

    return fig


@nodify(icon="histogram",
        title=Attribute("lineedit", value="My Plot"),
        color=Attribute("colorpicker"),
        y=Attribute("combobox", source="data", extractor="dataframe_columns"),
        bins=Attribute("pylineedit", value=10),
        normalize=Attribute("combobox", value="False", options=["True", "False"]),
        label=Attribute("lineedit", value="")
)
def Histogram(
    data,
    title: str = "My Plot",
    color: str = "#2F4F4F",
    y: str = None,
    bins=10,
    normalize: str = "False",
    label: str = "",
) -> Figure:
    """
    Create a histogram.

    Args:
        data (column or table): Input data.
        title (str): Title of the plot.
        color (str): Color for plotting.
        y (str): Column to plot.
        bins (list or str): The bins for the binning. Can be defined through:
            - As numerical values, e.g. [1,2,3].
            - As variable, e.g. "my_bins", where "my_bins" is a workspace variable containing a list.
            - As a list of variables, e.g. [a, b, c], where a, b, c are workspace variables.

    Returns:
        fig: Created figure. Can be used as input for Plot and ToSubplot nodes.
    """
    if isinstance(data, pd.Series):
        plot_data = data.to_frame()
    else:
        plot_data = data.copy()

    if bins is None or bins == "":
        bin_values = np.linspace(plot_data[y].min(), plot_data[y].max(), 10)
    else:
        bin_values = bins

    if isinstance(bin_values, numbers.Number):
        if isinstance(bin_values, int):
            bin_values = np.linspace(plot_data[y].min(), plot_data[y].max(), bin_values)
        else:
            raise TypeError("If bin_values is a number, it has to be an integer.")

    normalize = normalize=="True"
    if label=="":
        label=None
    fig, ax = plt.subplots(1,1)
    ax.hist(plot_data[y], bins=bin_values, color=color, density=normalize, label=label)
    ax.set_title(title)
    ax.grid()
    ax.legend()
    fig.tight_layout()
    return fig


@nodify(icon="Line",
        title=Attribute("lineedit", value="My Plot"),
        color=Attribute("colorpicker"),
        x=Attribute("combobox", source="data", extractor="dataframe_columns_with_index"),
        y=Attribute("combobox", source="data", extractor="dataframe_columns"),
        linewidth=Attribute("doublespinbox", value=10, range=(0, 100)),
        linestyle=Attribute("combobox", value='-', options=[' ', '-', '--', '-.', ':']),
        marker=Attribute("combobox", value="", options=["",".","o","x","+"]),
        markersize=Attribute("doublespinbox", value=5.0, range=(0, 1000)),
        label=Attribute("lineedit", value=""),
)
def Line(data, title: str = "My Plot", color: str="#2F4F4F", x: str=None, y: str=None, linestyle: str="-", linewidth: float=1.0, marker: str="", markersize: float=5.0, label: str="") -> Figure:
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
        fig: Created figure. Can be used as input for Plot and ToSubplot nodes.
    """
    if isinstance(data, pd.Series):
        plot_data = data.to_frame()
    else:
        plot_data = data.copy()
    if x=="index":
        x=None
    if label=="":
        label=None

    fig, ax = plt.subplots(1,1)
    plot_data.plot(x=x, y=y, ax=ax, color=color, linestyle=linestyle, label=label, linewidth=linewidth, marker=marker, markersize=markersize)

    ax.grid()
    fig.tight_layout()
    return fig


@nodify(icon="scatter",
        title=Attribute("lineedit", value="My Plot"),
        color=Attribute("colorpicker"),
        x=Attribute("combobox", source="data", extractor="dataframe_columns"),
        y=Attribute("combobox", source="data", extractor="dataframe_columns"),
        markersize=Attribute("spinbox", value=20, range=(0, 1000)),
        marker=Attribute("combobox", options=[".","o","x","+"]),
        label=Attribute("lineedit", value="")
)
def Scatter(data, title: str = "My Plot", color: str="#2F4F4F", x: str=None, y: str=None, marker: str=".", markersize: int=20, label: str="") -> Figure:
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
        fig: Created figure. Can be used as input for Plot and ToSubplot nodes.
    """
    if isinstance(data, pd.Series):
        plot_data = data.to_frame()
    else:
        plot_data = data.copy()
    if label=="":
        label=None
    fig, ax = plt.subplots(1,1)
    plot_data.plot(x=x, y=y, ax=ax, kind='scatter', c=color, marker=marker, s=markersize, label=label)
    ax.set_title(title)
    ax.grid()
    fig.tight_layout()
    return fig


@nodify(
        icon="poly",
        title=Attribute("lineedit", value="My Plot")
)
def Plot(*figures, title: str = "My Plot") -> Figure:
    """
    Combine multiple matplotlib Figures into a single figure.

    Supports line plots, scatter plots, bar plots, histograms, and boxplots.
    """
    fig, ax = plt.subplots()

    for fig_old in figures:
        for ax_old in fig_old.get_axes():

            # --- copy line plots ---
            for line in ax_old.get_lines():
                ax.plot(
                    line.get_xdata(),
                    line.get_ydata(),
                    label=line.get_label(),
                    linestyle=line.get_linestyle(),
                    marker=line.get_marker(),
                    color=line.get_color(),
                    linewidth=line.get_linewidth()
                )

            # --- copy scatter plots ---
            for col in ax_old.collections:
                offsets = col.get_offsets()
                if len(offsets) > 0:
                    sizes = col.get_sizes() if len(col.get_sizes()) > 0 else None
                    ax.scatter(
                        offsets[:, 0],
                        offsets[:, 1],
                        label=col.get_label(),
                        marker=col.get_paths()[0],
                        c=col.get_facecolor(),
                        s=sizes,
                    )

            # --- copy bar/hist patches ---
            for patch in ax_old.patches:
                if isinstance(patch, Rectangle) and patch.get_width() != 0:
                    ax.bar(
                        patch.get_x(),
                        patch.get_height(),
                        width=patch.get_width(),
                        color=patch.get_facecolor(),
                        label=patch.get_label() if patch.get_label() != "_nolegend_" else None,
                        align="edge",
                    )

            # --- copy boxplot components ---

            for child in ax_old.get_children():
                if isinstance(child, (Line2D, PathPatch)):
                    if child in ax_old.lines:
                        continue
                    if isinstance(child, Line2D):
                        ax.add_line(Line2D(
                            child.get_xdata(),
                            child.get_ydata(),
                            color=child.get_color(),
                            linestyle=child.get_linestyle(),
                            marker=child.get_marker(),
                            label=child.get_label() if child.get_label() != "_nolegend_" else None,
                        ))
                    elif isinstance(child, PathPatch):
                        # use Path vertices for box
                        verts = child.get_path().vertices
                        ax.add_patch(Polygon(
                            verts,
                            facecolor=child.get_facecolor(),
                            edgecolor=child.get_edgecolor(),
                            label=child.get_label() if child.get_label() != "_nolegend_" else None,
                        ))

    ax.legend()
    ax.grid()
    ax.set_title(title)
    return fig


@nodify(
        icon="plot2",
        x=Attribute("combobox", source="data", extractor="dataframe_columns_with_index"),
        y=Attribute("checkable-combobox", source="data", extractor="dataframe_columns_with_index"),
        title=Attribute("lineedit"),
        subplots=Attribute("combobox", value="True", options = ["True", "False"]),
        positions=Attribute("lineedit")
)
def MultiLine(data: Union[pd.Series, pd.DataFrame], x: str=None, y: list=[], title: str="Plot Title", subplots: str="False", positions: str="") -> Figure:
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
        fig: Created figure. Can be used as input for Plot and ToSubplot nodes.
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
        except:
            # Fallback: treat as comma-separated values
            position_list = [int(p.strip()) for p in positions.split(',') if p.strip()]
        
        if len(position_list) == len(y):
            use_positions = True
    
    if use_subplots:
        # Create subplots - one for each y column
        n_subplots = len(y)
        fig, axes = plt.subplots(n_subplots, 1, sharex=True, figsize=(8, 4 * n_subplots))
        
        # Handle single subplot case (axes is not a list)
        if n_subplots == 1:
            axes = [axes]
        
        for i, column in enumerate(y):
            if use_positions:
                # Use specified position (1-indexed, convert to 0-indexed for list)
                subplot_idx = position_list[i] - 1
                if subplot_idx < 0 or subplot_idx >= n_subplots:
                    subplot_idx = i
            else:
                subplot_idx = i
            
            ax = axes[subplot_idx]
            
            # Plot the column
            if x is None:
                plot_data.plot(y=[column], ax=ax)
            else:
                plot_data.plot(x=x, y=[column], ax=ax)
            
            ax.set_title(column)
            ax.grid()
            ax.set_ylabel(column)
        
        # Set overall title
        fig.suptitle(title)
        fig.tight_layout(rect=[0, 0, 1, 0.96])  # Leave room for suptitle
    else:
        # Single plot with multiple lines
        fig, ax = plt.subplots(1, 1, figsize=(8, 6))
        
        if x is None:
            plot_data.plot(y=y, ax=ax)
        else:
            plot_data.plot(x=x, y=y, ax=ax)
        
        ax.set_title(title)
        ax.grid()
        ax.legend()
        fig.tight_layout()
    
    return fig


@nodify(
        icon="subplot",
        row_index = Attribute("spinbox", value=1, range=(0, 15)),
        col_index = Attribute("spinbox", value=1, range=(0, 15))

)
def ToSubplot(fig: Figure, row_index: int=1, col_index: int=1) -> list:
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
def CombineFiguress(*subplots: list, title: str = "My Figure") -> Figure:
    """
    Combine multiple Matplotlib figures into a single figure with subplots.

    Args
        subplots : List of lists [fig, (i_row, i_col)]

    Returns
        fig : Figure containing the subplots
    """
    # determine max rows and columns
    max_row = max(pos[0] for _, pos in subplots)
    max_col = max(pos[1] for _, pos in subplots)

    fig_new, axes = plt.subplots(max_row, max_col, squeeze=False)

    # iterate through each figure and its target position
    for fig_old, (row, col) in subplots:
        ax_new = axes[row-1][col-1]  # 0-based indexing

        for ax_old in fig_old.get_axes():

            # --- copy line plots ---
            for line in ax_old.get_lines():
                ax_new.plot(
                    line.get_xdata(),
                    line.get_ydata(),
                    label=line.get_label(),
                    linestyle=line.get_linestyle(),
                    marker=line.get_marker(),
                    color=line.get_color(),
                )

            # --- copy scatter plots ---
            for col_obj in ax_old.collections:
                offsets = col_obj.get_offsets()
                if len(offsets) > 0:
                    sizes = col_obj.get_sizes() if len(col_obj.get_sizes()) > 0 else None
                    ax_new.scatter(
                        offsets[:, 0],
                        offsets[:, 1],
                        label=col_obj.get_label(),
                        marker=col_obj.get_paths()[0],
                        c=col_obj.get_facecolor(),
                        s=sizes,
                    )

            # --- copy bar/hist patches ---
            for patch in ax_old.patches:
                if isinstance(patch, Rectangle) and patch.get_width() != 0:
                    ax_new.bar(
                        patch.get_x(),
                        patch.get_height(),
                        width=patch.get_width(),
                        color=patch.get_facecolor(),
                        label=patch.get_label() if patch.get_label() != "_nolegend_" else None,
                        align="edge",
                    )

            # --- copy boxplot / other components ---
            for child in ax_old.get_children():
                if isinstance(child, (Line2D, PathPatch)):
                    # skip normal plot lines already added
                    if child in ax_old.lines:
                        continue

                    if isinstance(child, Line2D):
                        ax_new.add_line(Line2D(
                            child.get_xdata(),
                            child.get_ydata(),
                            color=child.get_color(),
                            linestyle=child.get_linestyle(),
                            marker=child.get_marker(),
                            label=child.get_label() if child.get_label() != "_nolegend_" else None,
                        ))
                    elif isinstance(child, PathPatch):
                        # convert PathPatch to Polygon
                        verts = child.get_path().vertices
                        ax_new.add_patch(Polygon(
                            verts,
                            facecolor=child.get_facecolor(),
                            edgecolor=child.get_edgecolor(),
                            label=child.get_label() if child.get_label() != "_nolegend_" else None,
                        ))
        ax_new.legend()
        ax_new.grid()

    fig_new.suptitle(title)
    fig_new.tight_layout()
    return fig_new


