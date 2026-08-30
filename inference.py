from typing import Optional

from models.llm import generate as llm_generate


def generate(
    prompt: str,
    model: Optional[str] = None
) -> str:
    """
    Common interface for local AI text generation.

    Other parts of V.A.U.L.T can use this function
    without directly interacting with Ollama.
    """

    if model is None:
        return llm_generate(prompt)

    return llm_generate(
        prompt,
        model
    )