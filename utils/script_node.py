from sciplex_core.model.library_model import Attribute, LibraryItem, library_model

# Default template for new script nodes
SCRIPT_DEFAULT_CODE = '''def my_function(data, i: int=2):
    """
    Write your function(s) or code here.

    - Parameters with defaults → editable widgets (available in properties panel of each node)
    - Parameters without defaults → input sockets
    - Return → output socket(s)

    If you use type hints for input sockets and return types, connecting nodes with incosistent types will result in an error.

    You can use global variables to store data in a flow. To view it, click on the "Workspace" button in the toolbar.

    Example workspace variables:
        workspace["a"] = 2
        workspace["xs"] = np.arange(0, 1, 0.1)

    """
    return i*data
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

