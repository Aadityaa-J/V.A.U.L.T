from typing import Optional

from models.llm import (
    simple_generate,
    complex_generate
)

from models.router import classify_task
from models.vision import analyze_image


def generate(
    prompt: str,
    image_path: Optional[str] = None
) -> str:
    """
    Common V.A.U.L.T AI interface.

    Automatically selects the appropriate model
    based on the task type.

    Simple  -> Qwen3 1.7B
    Complex -> Qwen3 4B
    Visual  -> Qwen3-VL 2B
    """

    task_type = classify_task(
        prompt,
        image_path
    )

    print(f"[Inference] Task type: {task_type}")

    # --------------------------------
    # SIMPLE TASK
    # --------------------------------
    if task_type == "simple":
        print("[Inference] Using Qwen3 1.7B")

        return simple_generate(
            prompt
        )

    # --------------------------------
    # COMPLEX TASK
    # --------------------------------
    if task_type == "complex":
        print("[Inference] Using Qwen3 4B")

        return complex_generate(
            prompt
        )

    # --------------------------------
    # VISUAL TASK
    # --------------------------------
    if task_type == "visual":

        if image_path is None:
            raise ValueError(
                "Visual task requires an image_path."
            )

        print("[Inference] Using Qwen3-VL 2B")

        return analyze_image(
            image_path,
            prompt
        )

    # --------------------------------
    # UNKNOWN TASK
    # --------------------------------
    raise ValueError(
        f"Unknown task type: {task_type}"
    )