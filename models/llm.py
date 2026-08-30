import ollama

from config.config import FAST_MODEL, MAIN_MODEL


def generate(
    prompt: str,
    model: str = MAIN_MODEL
) -> str:
    """
    Generate text using a local Ollama model.

    Args:
        prompt: The user's prompt.
        model: Ollama model to use.

    Returns:
        Generated response as a string.
    """

    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]


def simple_generate(prompt: str) -> str:
    """
    Generate a response using Qwen3 1.7B.
    """

    return generate(
        prompt,
        FAST_MODEL
    )


def complex_generate(prompt: str) -> str:
    """
    Generate a response using Qwen3 4B.
    """

    return generate(
        prompt,
        MAIN_MODEL
    )