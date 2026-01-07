from sciplex_core.model.library_model import Attribute, LibraryItem, library_model

# Default template for new script nodes
SCRIPT_DEFAULT_CODE = '''def my_function(data):
    """
    Write your function here. Use type hints:

    def process(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
        return df.head(n)

    - Parameters with defaults → editable widgets
    - Parameters without defaults → input sockets
    - Return type → output socket(s)

    Workspace variables:
        workspace["a"] = 2
        xs = np.arange(0, 1, 0.1)
        workspace["xs"] = xs
        ys = workspace["xs"]

    Available: np, pd, plt, sklearn, workspace
    """
    return data
'''


def register_script_node():
    """
    Register the Script node into the library model under a hidden
    internal category so it is available for creation but not shown
    in the public library list.
    """
    # Build minimal parameters for script nodes
    params = {"function": Attribute("codeeditor", value=SCRIPT_DEFAULT_CODE)}

    # Script nodes compile their code at runtime, so execute_fn is None
    library_item = LibraryItem(
        function_name="Script",
        library_name="_internal",
        icon="python",
        execute_fn=None,
        parameters=params,
        inputs=[],
        outputs=[],
    )
    library_model.register("Script", library_item)

