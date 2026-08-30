from models.llm import generate


response = generate(
    "Explain what a centrifugal pump is in two sentences.",
    model="qwen3:4b"
)

print(response)