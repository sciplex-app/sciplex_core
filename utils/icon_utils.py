"""
Utility functions for icon path resolution.

Separates library node icons (public, in libraries/icons/) from UI icons (internal, in assets/icons).
"""
import os
from pathlib import Path
from typing import Optional

from sciplex_core.model.settings_model import settings


def get_library_icon_path(icon_name: str, variant: str = "_black") -> Optional[str]:
    """
    Get the path to a library node icon.
    
    Checks libraries/icons/ first (for shared/custom icons), then falls back to assets/icons.
    
    Args:
        icon_name: Base name of the icon (e.g., "csv", "scatter")
        variant: Icon variant suffix (e.g., "_black", ""). Defaults to "_black".
    
    Returns:
        Full path to the icon file if found, None otherwise.
    """
    base_dir = settings.base_dir
    # Icons are stored alongside libraries in libraries/icons/
    libraries_icons_dir = os.path.join(base_dir, "libraries", "icons")
    
    # Calculate assets/icons path (go up from core/utils/icon_utils.py to project root)
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    assets_icons_dir = os.path.join(project_root, "assets", "icons")
    
    # Try libraries/icons first (for shared/custom icons)
    icon_filename = f"{icon_name}{variant}.png"
    library_icon_path = os.path.join(libraries_icons_dir, icon_filename)
    if os.path.exists(library_icon_path):
        return library_icon_path
    
    # Fallback to assets/icons
    assets_icon_path = os.path.join(assets_icons_dir, icon_filename)
    if os.path.exists(assets_icon_path):
        return assets_icon_path
    
    return None


def get_ui_icon_path(icon_name: str) -> Optional[str]:
    """
    Get the path to a UI icon (toolbar, buttons, etc.).
    
    Always uses assets/icons (internal icons).
    
    Args:
        icon_name: Name of the icon file (with or without .png extension)
    
    Returns:
        Full path to the icon file if found, None otherwise.
    """
    if not icon_name.endswith(".png"):
        icon_name = f"{icon_name}.png"
    
    # Calculate assets/icons path (go up from core/utils/icon_utils.py to project root)
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    assets_icons_dir = os.path.join(project_root, "assets", "icons")
    
    icon_path = os.path.join(assets_icons_dir, icon_name)
    if os.path.exists(icon_path):
        return icon_path
    
    return None


def initialize_library_icons():
    """
    Copy default library node icons from assets/icons to libraries/icons.
    
    This makes default libraries self-contained and shareable.
    Icons are stored alongside library .py files in libraries/icons/.
    """
    base_dir = settings.base_dir
    # Icons are stored alongside libraries in libraries/icons/
    libraries_icons_dir = Path(base_dir) / "libraries" / "icons"
    
    # Calculate assets/icons path (go up from core/utils/icon_utils.py to project root)
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    assets_icons_dir = project_root / "assets" / "icons"
    
    # Create libraries icons directory if it doesn't exist
    libraries_icons_dir.mkdir(parents=True, exist_ok=True)
    
    # List of icons used by default library nodes (extracted from @nodify decorators)
    default_library_icons = {
        # data.py
        "boolean", "folder", "dataset", "list", "csv", "data_table", "number",
        "data_array", "function", "save", "input",
        # visuals.py
        "barchart", "boxplot", "histogram", "Line", "scatter", "poly", "plot2",
        "subplot", "grid",
        # math.py
        "arithm", "corr", "cumsum", "diff", "logical", "MaxMin", "not", "rel",
        "map1d", "map2d", "roll", "TableFormula",
        # machine_learning.py
        "score", "table", "decisiontree", "encoder", "transform", "linreg",
        "predict", "randomforest", "split", "xgboost",
        # transform.py
        "cut", "add_row", "info", "bin", "filter", "group", "nans", "pivot",
        "change", "select", "shift", "sort", "switch", "square",
    }
    
    # Copy icons (both regular and _black variants)
    copied_count = 0
    for icon_name in default_library_icons:
        for variant in ["", "_black"]:
            icon_filename = f"{icon_name}{variant}.png"
            src = assets_icons_dir / icon_filename
            dst = libraries_icons_dir / icon_filename
            
            # Only copy if source exists and destination doesn't
            if src.exists() and not dst.exists():
                try:
                    import shutil
                    shutil.copy2(str(src), str(dst))
                    copied_count += 1
                except Exception as e:
                    print(f"Warning: Could not copy icon {icon_filename}: {e}")
    
    if copied_count > 0:
        print(f"Initialized {copied_count} library icons in {libraries_icons_dir}")

