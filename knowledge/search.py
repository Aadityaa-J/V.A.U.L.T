"""
Knowledge-base semantic search for V.A.U.L.T.

Retrieval is authorization-aware:

- Global Knowledge Base documents are available to authenticated users.
- User Library documents are available only to their owner.
- A user's private documents are never intentionally exposed to another user.
"""

from .vector_store import search_documents


DEFAULT_DISTANCE_THRESHOLD = 1.3


def search_knowledge(
    query: str,
    top_k: int = 4,
    distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
    user_id=None,
):
    """
    Search V.A.U.L.T.'s knowledge base.

    Retrieval scope:

        user_id is None
            -> Global Knowledge Base only

        user_id is provided
            -> Global Knowledge Base
               +
               current user's private Library

    Parameters
    ----------
    query:
        Natural-language semantic search query.

    top_k:
        Maximum number of results to retrieve.

    distance_threshold:
        Maximum Chroma distance accepted as relevant.

    user_id:
        Authenticated user's ID.

    Returns
    -------
    list[dict]
        Search results containing text, source, page,
        distance, scope, user_id, OCR information, etc.
    """

    if not query or not query.strip():
        return []

    try:
        top_k = int(top_k)
    except (TypeError, ValueError):
        top_k = 4

    top_k = max(1, min(top_k, 20))

    try:
        distance_threshold = float(distance_threshold)
    except (TypeError, ValueError):
        distance_threshold = DEFAULT_DISTANCE_THRESHOLD

    if distance_threshold < 0:
        distance_threshold = DEFAULT_DISTANCE_THRESHOLD

    results = search_documents(
        query=query,
        top_k=top_k,
        user_id=user_id,
    )

    documents = results.get(
        "documents",
        [[]]
    )

    metadatas = results.get(
        "metadatas",
        [[]]
    )

    distances = results.get(
        "distances",
        [[]]
    )

    documents = documents[0] if documents else []
    metadatas = metadatas[0] if metadatas else []
    distances = distances[0] if distances else []

    formatted_results = []

    for text, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):
        metadata = metadata or {}

        try:
            distance_value = float(distance)
        except (TypeError, ValueError):
            continue

        if distance_value > distance_threshold:
            continue

        formatted_results.append(
            {
                "text": text,
                "source": metadata.get(
                    "source",
                    "unknown",
                ),
                "page": metadata.get(
                    "page",
                    None,
                ),
                "distance": distance_value,
                "scope": metadata.get(
                    "scope",
                    "global",
                ),
                "user_id": metadata.get(
                    "user_id",
                    "",
                ),
                "ocr_used": metadata.get(
                    "ocr_used",
                    False,
                ),
                "content_type": metadata.get(
                    "content_type",
                    None,
                ),
            }
        )

    return formatted_results