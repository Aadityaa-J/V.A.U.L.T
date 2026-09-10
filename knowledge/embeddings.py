"""
Embedding utilities for V.A.U.L.T.

Embeddings are generated locally through Ollama rather than through
SentenceTransformers/Hugging Face.

Configured model:
    EMBEDDING_MODEL (defaults to nomic-embed-text)

This keeps the RAG stack local:

    document -> chunks -> Ollama embedding -> ChromaDB
"""

from __future__ import annotations

from typing import Iterable

import ollama

try:
    from config.config import EMBEDDING_MODEL, OLLAMA_HOST
except ImportError:
    # Safe defaults for direct execution/imports.
    EMBEDDING_MODEL = "nomic-embed-text"
    OLLAMA_HOST = "http://localhost:11434"


MODEL_NAME = EMBEDDING_MODEL
OLLAMA_URL = OLLAMA_HOST

_client: ollama.Client | None = None


def get_ollama_client() -> ollama.Client:
    """Return a lazily initialized Ollama client."""
    global _client

    if _client is None:
        _client = ollama.Client(host=OLLAMA_URL)

    return _client


def _extract_embeddings(response) -> list[list[float]]:
    """
    Extract embeddings from the response returned by Ollama.

    Ollama's Python client returns an object that exposes an `embeddings`
    attribute for the embedding endpoint. A dictionary response is also
    accepted for compatibility with different client versions.
    """
    embeddings = getattr(response, "embeddings", None)

    if embeddings is None and isinstance(response, dict):
        embeddings = response.get("embeddings")

    if embeddings is None:
        raise RuntimeError(
            "Ollama did not return an 'embeddings' field."
        )

    return [
        [float(value) for value in embedding]
        for embedding in embeddings
    ]


def get_embedding_model() -> str:
    """Return the configured local Ollama embedding model name."""
    return MODEL_NAME


def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    """
    Generate embeddings for multiple text chunks using Ollama.

    Parameters
    ----------
    texts:
        Iterable of text strings.

    Returns
    -------
    list[list[float]]
        One embedding vector per input text.
    """
    text_list = [str(text) for text in texts]

    if not text_list:
        return []

    client = get_ollama_client()

    try:
        response = client.embed(
            model=MODEL_NAME,
            input=text_list,
        )
    except AttributeError:
        # Compatibility fallback for older Ollama Python clients.
        vectors: list[list[float]] = []

        for text in text_list:
            response = client.embeddings(
                model=MODEL_NAME,
                prompt=text,
            )

            embedding = getattr(response, "embedding", None)

            if embedding is None and isinstance(response, dict):
                embedding = response.get("embedding")

            if embedding is None:
                raise RuntimeError(
                    "Ollama did not return an 'embedding' field."
                )

            vectors.append([float(value) for value in embedding])

        return vectors
    except Exception as exc:
        raise RuntimeError(
            f"Failed to generate embeddings with Ollama model "
            f"'{MODEL_NAME}': {exc}"
        ) from exc

    embeddings = _extract_embeddings(response)

    if len(embeddings) != len(text_list):
        raise RuntimeError(
            "Ollama returned a different number of embeddings than "
            "the number of input texts."
        )

    return embeddings


def embed_query(query: str) -> list[float]:
    """
    Generate one embedding vector for a RAG search query.
    """
    if not query or not query.strip():
        raise ValueError("Embedding query cannot be empty.")

    client = get_ollama_client()

    try:
        response = client.embed(
            model=MODEL_NAME,
            input=query,
        )

        embeddings = _extract_embeddings(response)

        if not embeddings:
            raise RuntimeError(
                "Ollama returned no embedding for the query."
            )

        return embeddings[0]

    except AttributeError:
        # Compatibility fallback for older Ollama Python clients.
        try:
            response = client.embeddings(
                model=MODEL_NAME,
                prompt=query,
            )

            embedding = getattr(response, "embedding", None)

            if embedding is None and isinstance(response, dict):
                embedding = response.get("embedding")

            if embedding is None:
                raise RuntimeError(
                    "Ollama did not return an 'embedding' field."
                )

            return [float(value) for value in embedding]

        except Exception as exc:
            raise RuntimeError(
                f"Failed to generate query embedding with Ollama model "
                f"'{MODEL_NAME}': {exc}"
            ) from exc

    except Exception as exc:
        raise RuntimeError(
            f"Failed to generate query embedding with Ollama model "
            f"'{MODEL_NAME}': {exc}"
        ) from exc
