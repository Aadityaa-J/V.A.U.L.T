from sentence_transformers import SentenceTransformer


MODEL_NAME = "all-MiniLM-L6-v2"

_model = None


def get_embedding_model():
    """
    Load the embedding model once and reuse it.
    """

    global _model

    if _model is None:
        print(f"Loading embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def embed_texts(texts):
    """
    Convert multiple text chunks into embeddings.
    """

    if not texts:
        return []

    model = get_embedding_model()

    embeddings = model.encode(
        texts,
        normalize_embeddings=True
    )

    return embeddings.tolist()


def embed_query(query):
    """
    Convert a search query into an embedding.
    """

    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    model = get_embedding_model()

    embedding = model.encode(
        query,
        normalize_embeddings=True
    )

    return embedding.tolist()