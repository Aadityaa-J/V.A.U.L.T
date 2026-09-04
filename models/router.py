from typing import Optional

from config.config import (
    FAST_MODEL,
    MAIN_MODEL,
    VISION_MODEL,
)


# ---------------------------------------------------------
# Task classification
# ---------------------------------------------------------

def classify_task(
    prompt: str,
    image_path: Optional[str] = None
) -> str:
    """
    Classify a request for model selection.

    Returns one of:

        simple
        complex
        visual
        classification
        extraction
        document
        coding
        engineering
    """

    # -----------------------------------------------------
    # Image requests
    # -----------------------------------------------------

    if image_path:
        return "visual"

    prompt_lower = prompt.lower().strip()

    # -----------------------------------------------------
    # Document tasks
    # -----------------------------------------------------

    document_keywords = [
        "document",
        "file",
        "read document",
        "read file",
        "summarize document",
        "summarize file",
        "search document",
        "search file",
        "document info",
        "text file",
        "markdown",
        "csv file",
        "json file",
    ]

    for keyword in document_keywords:
        if keyword in prompt_lower:
            return "document"

    # -----------------------------------------------------
    # Coding tasks
    # -----------------------------------------------------

    coding_keywords = [
        "python",
        "code",
        "program",
        "function",
        "script",
        "debug",
        "bug",
        "software",
        "algorithm",
        "write code",
        "execute code",
        "run python",
    ]

    for keyword in coding_keywords:
        if keyword in prompt_lower:
            return "coding"

    # -----------------------------------------------------
    # Engineering tasks
    # -----------------------------------------------------

    engineering_keywords = [
        "calculate",
        "calculation",
        "engineering",
        "multiply",
        "multiplied",
        "divide",
        "addition",
        "subtract",
        "force",
        "pressure",
        "velocity",
        "acceleration",
        "voltage",
        "current",
        "power",
        "torque",
        "stress",
        "strain",
    ]

    for keyword in engineering_keywords:
        if keyword in prompt_lower:
            return "engineering"

    # -----------------------------------------------------
    # Extraction tasks
    # -----------------------------------------------------

    extraction_keywords = [
        "extract",
        "extract text",
        "get the text",
        "read the text",
        "transcribe",
        "transcription",
        "list the text",
        "copy the text",
        "ocr",
    ]

    for keyword in extraction_keywords:
        if keyword in prompt_lower:
            return "extraction"

    # -----------------------------------------------------
    # Classification tasks
    # -----------------------------------------------------

    classification_keywords = [
        "classify",
        "classification",
        "categorize",
        "category",
        "which type",
        "what type",
        "identify the type",
        "label this",
    ]

    for keyword in classification_keywords:
        if keyword in prompt_lower:
            return "classification"

    # -----------------------------------------------------
    # Complex reasoning tasks
    # -----------------------------------------------------

    complex_keywords = [
        "analyze",
        "analyse",
        "compare",
        "evaluate",
        "reason",
        "explain why",
        "why does",
        "why is",
        "root cause",
        "failure analysis",
        "diagnose",
        "diagnosis",
        "optimization",
        "optimize",
        "derive",
        "design",
        "architecture",
        "debugging",
        "trade-off",
        "tradeoff",
        "step by step",
    ]

    for keyword in complex_keywords:
        if keyword in prompt_lower:
            return "complex"

    # -----------------------------------------------------
    # Default
    # -----------------------------------------------------

    return "simple"


# ---------------------------------------------------------
# Model selection
# ---------------------------------------------------------

def select_model(task_type: str) -> str:
    """
    Select the appropriate local model.

    Agent task types and model task types are both supported.
    """

    # -----------------------------------------------------
    # Fast model tasks
    # -----------------------------------------------------

    if task_type in {
        "simple",
        "classification",
        "extraction",
        "document",
    }:
        return FAST_MODEL

    # -----------------------------------------------------
    # Main reasoning model tasks
    # -----------------------------------------------------

    if task_type in {
        "complex",
        "coding",
        "engineering",
    }:
        return MAIN_MODEL

    # -----------------------------------------------------
    # Vision model
    # -----------------------------------------------------

    if task_type == "visual":
        return VISION_MODEL

    raise ValueError(
        f"Unknown task type: {task_type}"
    )


# ---------------------------------------------------------
# Router
# ---------------------------------------------------------

def route(
    prompt: str,
    image_path: Optional[str] = None
) -> str:
    """
    Determine which local model should handle a request.

    Returns the selected Ollama model name.
    """

    task_type = classify_task(
        prompt,
        image_path
    )

    model = select_model(task_type)

    print(f"[Router] Task type: {task_type}")
    print(f"[Router] Selected model: {model}")

    return model