import ollama


FAST_MODEL = "qwen3:1.7b"
MAIN_MODEL = "qwen3:4b"


def generate(prompt: str, model: str = MAIN_MODEL) -> str:
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