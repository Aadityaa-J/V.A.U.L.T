from pathlib import Path

import ollama

from config.config import VISION_MODEL


def analyze_image(
    image_path: str,
    prompt: str
) -> str:
    """
    Analyze an image using the local Qwen3-VL model.

    Args:
        image_path: Path to the image.
        prompt: Instruction for the vision model.

    Returns:
        Generated response from Qwen3-VL.
    """

    # Expand ~ and convert to Path
    path = Path(image_path).expanduser()

    # Validate image path
    if not path.exists():
        raise FileNotFoundError(
            f"Image not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Image path is not a file: {path}"
        )

    print(f"[Vision] Using model: {VISION_MODEL}")
    print(f"[Vision] Image: {path}")

    # Send image to Ollama
    response = ollama.chat(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [str(path)]
            }
        ]
    )

    # Get message object
    message = response.get("message")

    if message is None:
        raise RuntimeError(
            "Ollama returned no message."
        )

    # ---------------------------------------------------------
    # Qwen3-VL may put its answer in either:
    #
    #   message.content
    #
    # or
    #
    #   message.thinking
    #
    # We support both.
    # ---------------------------------------------------------

    content = message.get("content", "")

    thinking = message.get("thinking", "")

    # Prefer normal content
    result = content.strip() if content else ""

    # If content is empty, use thinking as fallback
    if not result and thinking:
        result = thinking.strip()

    # Remove <think>...</think> wrapper if present
    if result.startswith("<think>"):
        result = result[len("<think>"):]

    if "</think>" in result:
        result = result.split("</think>", 1)[1]

    result = result.strip()

    if not result:
        raise RuntimeError(
            "Qwen3-VL returned an empty response."
        )

    return result