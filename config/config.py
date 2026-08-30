import os


# Ollama server
OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://localhost:11434"
)


# Qwen3 1.7B - lightweight model
FAST_MODEL = os.getenv(
    "FAST_MODEL",
    "qwen3:1.7b"
)


# Qwen3 4B - more capable model
MAIN_MODEL = os.getenv(
    "MAIN_MODEL",
    "qwen3:4b"
)


# Qwen3-VL 2B - vision model
VISION_MODEL = os.getenv(
    "VISION_MODEL",
    "qwen3-vl:2b"
)


# Nomic - embeddings model
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "nomic-embed-text"
)