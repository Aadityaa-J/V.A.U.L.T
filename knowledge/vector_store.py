from pathlib import Path
import hashlib

import chromadb

from .embeddings import embed_texts, embed_query


# ---------------------------------------
# Paths and collection
# ---------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHROMA_PATH = PROJECT_ROOT / "data" / "knowledge" / "chroma"

COLLECTION_NAME = "vault_knowledge"


# ---------------------------------------
# ChromaDB setup
# ---------------------------------------

client = chromadb.PersistentClient(
    path=str(CHROMA_PATH)
)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME
)


# ---------------------------------------
# Helper: generate stable chunk ID
# ---------------------------------------

def generate_chunk_id(chunk, index):
    """
    Generate a deterministic ID for a document chunk.
    """

    source = str(
        chunk.metadata.get(
            "source",
            "unknown"
        )
    )

    content = chunk.page_content.strip()

    raw_id = f"{source}|{index}|{content}"

    hash_id = hashlib.sha256(
        raw_id.encode("utf-8")
    ).hexdigest()

    return f"chunk_{hash_id}"


# ---------------------------------------
# Add documents
# ---------------------------------------

def add_documents(chunks):
    """
    Store document chunks and embeddings
    in ChromaDB.

    Existing chunks from the same source are
    removed before inserting the new version.
    """

    if not chunks:
        return 0

    # Identify document source
    source = str(
        chunks[0].metadata.get(
            "source",
            "unknown"
        )
    )

    # Remove previous version of this document
    collection.delete(
        where={
            "source": source
        }
    )

    texts = [
        chunk.page_content.strip()
        for chunk in chunks
        if chunk.page_content.strip()
    ]

    if not texts:
        return 0

    # Rebuild list after removing empty chunks
    valid_chunks = [
        chunk
        for chunk in chunks
        if chunk.page_content.strip()
    ]

    embeddings = embed_texts(texts)

    ids = []
    metadatas = []

    for index, chunk in enumerate(valid_chunks):

        ids.append(
            generate_chunk_id(
                chunk,
                index
            )
        )

        metadata = chunk.metadata

        chunk_metadata = {
            "source": source
        }

        if "page" in metadata:
            chunk_metadata["page"] = int(
                metadata["page"]
            )

        metadatas.append(chunk_metadata)

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return len(texts)


# ---------------------------------------
# Search documents
# ---------------------------------------

def search_documents(query, top_k=4):
    """
    Search ChromaDB for relevant document chunks.
    """

    if not query or not query.strip():
        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }

    count = collection.count()

    if count == 0:
        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }

    top_k = max(1, min(int(top_k), count))

    query_embedding = embed_query(query)

    return collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )


# ---------------------------------------
# Collection information
# ---------------------------------------

def get_collection_count():
    """
    Return the number of chunks currently
    stored in ChromaDB.
    """

    return collection.count()