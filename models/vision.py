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

    # ---------------------------------------------------------
    # 1. Expand ~ and convert path to Path object
    # ---------------------------------------------------------
    path = Path(image_path).expanduser()

    # ---------------------------------------------------------
    # 2. Validate image path
    # ---------------------------------------------------------
    if not path.exists():
        raise FileNotFoundError(
            f"Image not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Image path is not a file: {path}"
        )

    # ---------------------------------------------------------
    # 3. Log model and image information
    # ---------------------------------------------------------
    print(f"[Vision] Using model: {VISION_MODEL}")
    print(f"[Vision] Image: {path}")

    # ---------------------------------------------------------
    # 4. Send image to Ollama
    # ---------------------------------------------------------
    response = ollama.chat(
    model=VISION_MODEL,
    messages=[
        {
            "role": "system",
            "content": (
                "You are a document OCR engine.\n"
                "Your ONLY task is to transcribe visible text from the image.\n\n"
                "RULES:\n"
                "1. Return ONLY text visible in the image.\n"
                "2. Do NOT describe the image.\n"
                "3. Do NOT summarize.\n"
                "4. Do NOT explain your reasoning.\n"
                "5. Do NOT add missing or guessed text.\n"
                "6. Preserve the original order of the text.\n"
                "7. Preserve headings, paragraphs, lists, dates, numbers, "
                "course codes and punctuation.\n"
                "8. If a word is unclear, make your best visual transcription "
                "but do not invent surrounding content.\n"
                "9. Never say 'Wait', 'Let's check', 'I can see', "
                "'This image contains', or similar commentary.\n"
            )
        },
        {
            "role": "user",
            "content": (
                "Transcribe ALL visible text in this document from TOP to BOTTOM. "
                "Do not stop early. Return ONLY the transcription."
            ),
            "images": [str(path)]
        }
    ],
    think=False,
    options={
        "temperature": 0,
        "num_predict": 4096
    }
)

    # ---------------------------------------------------------
    # 5. Get message object
    #
    # Ollama can return a ChatResponse containing a Message
    # object. We handle both object and dictionary formats.
    # ---------------------------------------------------------
    message = None

    if hasattr(response, "message"):
        message = response.message

    elif isinstance(response, dict):
        message = response.get("message")

    if message is None:
        raise RuntimeError(
            "Ollama returned no message."
        )

    # ---------------------------------------------------------
    # 6. Extract content and thinking
    #
    # Depending on the Ollama response format, these can be
    # attributes of a Message object or dictionary values.
    # ---------------------------------------------------------
    content = ""
    thinking = ""

    if isinstance(message, dict):
        content = message.get("content", "") or ""
        thinking = message.get("thinking", "") or ""

    else:
        content = getattr(message, "content", "") or ""
        thinking = getattr(message, "thinking", "") or ""

    # ---------------------------------------------------------
    # 7. Prefer normal response content
    # ---------------------------------------------------------
    result = content.strip()

    # ---------------------------------------------------------
    # 8. Fallback to thinking only if content is empty
    #
    # Some Qwen models may place their response in the
    # thinking field.
    # ---------------------------------------------------------
    if not result and thinking:
        result = thinking.strip()

    # ---------------------------------------------------------
    # 9. Remove <think>...</think> wrapper if present
    # ---------------------------------------------------------
    if result.startswith("<think>"):
        result = result[len("<think>"):].strip()

    if "</think>" in result:
        result = result.split("</think>", 1)[1].strip()

    # ---------------------------------------------------------
    # 10. Final validation
    # ---------------------------------------------------------
    if not result:
        raise RuntimeError(
            "Qwen3-VL returned an empty response."
        )

    # ---------------------------------------------------------
    # 11. Return final answer
    # ---------------------------------------------------------
    return result