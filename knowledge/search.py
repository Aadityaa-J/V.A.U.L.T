from .vector_store import search_documents


# Maximum Chroma distance considered relevant
DEFAULT_DISTANCE_THRESHOLD = 1.3


def search_knowledge(
    query: str,
    top_k: int = 4,
    distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD
):
    """
    Search the V.A.U.L.T. knowledge base.

    Only results within the relevance threshold
    are returned.

    Args:
        query: Natural-language search query.
        top_k: Number of results to retrieve.
        distance_threshold: Maximum acceptable
            Chroma distance.

    Returns:
        List of dictionaries containing:
        - text
        - source
        - page
        - distance
    """

    if not query or not query.strip():
        return []

    results = search_documents(
        query=query,
        top_k=top_k
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    formatted_results = []

    for text, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):
        # Reject weak/unrelated results
        if distance > distance_threshold:
            continue

        formatted_results.append({
            "text": text,
            "source": metadata.get(
                "source",
                "unknown"
            ),
            "page": metadata.get(
                "page",
                None
            ),
            "distance": distance
        })

    return formatted_results