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
    Classify a request into:

        simple
        complex
        visual
        classification
        extraction

    If an image is supplied, the request is visual.
    """

    # -----------------------------------------------------
    # Image requests always go to the vision model
    # -----------------------------------------------------

    if image_path:
        return "visual"

    prompt_lower = prompt.lower().strip()

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
        "calculate",
        "design",
        "architecture",
        "debug",
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
    Select the appropriate local model for a task type.
    """

    if task_type in {
        "simple",
        "classification",
        "extraction",
    }:
        return FAST_MODEL

    if task_type == "complex":
        return MAIN_MODEL

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

    Returns:
        The selected Ollama model name.
    """

    task_type = classify_task(
        prompt,
        image_path
    )

    model = select_model(task_type)

    print(f"[Router] Task type: {task_type}")
    print(f"[Router] Selected model: {model}")

    return model