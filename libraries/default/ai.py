"""
AI / Agent nodes for Sciplex.

Requires Sciplex Platform (sciplex_core_ext) so that `llm` is available.
Use prompt/system_prompt as parameters (Properties panel) or wire text into inputs.
"""

from sciplex import Attribute, nodify, llm


@nodify(
    icon="agent",
    system_prompt=Attribute("textarea", value="You are a helpful assistant."),
)
def LLM_Agent(
    prompt: str,
    context: str = "",
    system_prompt: str = "You are a helpful assistant.",
) -> str:
    """
    Call the LLM with a prompt and optional context. Set system prompt in the Properties panel.

    Args:
        prompt: Main user message (wire text or type in panel if you add it as a parameter).
        context: Optional extra context (e.g. second text or data summary).
        system_prompt: System instruction for the model (Properties panel).

    Returns:
        str: The model's text response.
    """
    text_prompt = str(prompt) if prompt is not None else ""
    if context:
        text_prompt += "\n\nContext:\n" + str(context)
    if not text_prompt.strip():
        raise ValueError("LLM Agent: prompt is empty. Wire text into the prompt input or set it in the node.")
    return llm.generate(text_prompt, system_prompt=system_prompt or "You are a helpful assistant.")


@nodify(icon="generate_report")
def GenerateReport(data) -> None:
    """
    Dummy node: one input, no output. Use as a sink for report generation workflows.

    Args:
        data: Input data (e.g. table, text, or figure) to consume.
    """
    pass


@nodify(icon="human_feedback")
def HumanFeedback(data):
    """
    Dummy node: one input, one output. Placeholder for human-in-the-loop feedback.

    Args:
        data: Input data (e.g. agent output) to pass through.

    Returns:
        The same data (pass-through).
    """
    return data


@nodify(icon="model")
def LoadModel():
    """
    Dummy node: no input, one output. Placeholder for loading a model.

    Returns:
        Dummy placeholder (replace with real model loading later).
    """
    return None


@nodify(icon="measurement")
def GetMeasurement():
    """
    Dummy node: no input, one output. Placeholder for fetching measurement data.

    Returns:
        Dummy placeholder (replace with real measurement data later).
    """
    return None


@nodify(icon="item_list")
def ItemList():
    """
    Dummy node: no input, one output. Placeholder for an item list.

    Returns:
        Dummy placeholder (replace with real list later).
    """
    return None


@nodify(icon="read_pdf")
def ReadPDF():
    """
    Dummy node: no input, one output. Placeholder for reading a PDF.

    Returns:
        Dummy placeholder (replace with real PDF content later).
    """
    return None


@nodify(icon="knowledge_store")
def KnowledgeStore():
    """
    Dummy node: no input, one output. Placeholder for a knowledge store.

    Returns:
        Dummy placeholder (replace with real store/handle later).
    """
    return None


@nodify(icon="agent")
def TextAgent(text):
    """
    Dummy node: one input, one output. Placeholder for a text agent.

    Args:
        text: Input text.

    Returns:
        Pass-through (replace with real agent logic later).
    """
    return text


@nodify(icon="agent")
def MatchingAgent(input_a, input_b):
    """
    Dummy node: two inputs, one output. Placeholder for a matching agent.

    Args:
        input_a: First input.
        input_b: Second input.

    Returns:
        Dummy placeholder (replace with real matching result later).
    """
    return None


@nodify(icon="item_list")
def ProductItems(data):
    """
    Dummy node: one input, one output. Placeholder for product items.

    Args:
        data: Input data (e.g. list or table).

    Returns:
        Pass-through (replace with real product items logic later).
    """
    return data


@nodify(icon="report")
def SummaryNode(data) -> None:
    """
    Dummy node: one input, no output. Placeholder for a summary/report sink.

    Args:
        data: Input data to consume (e.g. summary or report content).
    """
    pass


@nodify(icon="agent")
def InterpretationAgent(data):
    """
    Dummy node: one input, one output. Placeholder for an interpretation agent.

    Args:
        data: Input data (e.g. text or measurement to interpret).

    Returns:
        Pass-through (replace with real interpretation logic later).
    """
    return data


@nodify(icon="find_outlier")
def FindOutlier(data, config):
    """
    Dummy node: two inputs, one output. Placeholder for outlier detection.

    Args:
        data: Input data (e.g. table or series).
        config: Configuration (e.g. threshold or method).

    Returns:
        Dummy placeholder (replace with real outlier indices or mask later).
    """
    return None
