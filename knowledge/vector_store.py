from pathlib import Path
import hashlib
import threading

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
# Legacy metadata migration
# ---------------------------------------

_scope_metadata_ready = False
_scope_metadata_lock = threading.Lock()


def migrate_legacy_documents():
    """
    Convert older Chroma records that were created before
    scope-aware retrieval was introduced.

    Older records did not contain:
        scope
        user_id
        ocr_used
        content_type

    Existing records are treated as Global Knowledge Base
    documents because that was the behavior of the original
    V.A.U.L.T. knowledge store.
    """

    result = collection.get(
        include=["metadatas"]
    )

    ids = result.get("ids", [])
    metadatas = result.get("metadatas", [])

    if not ids:
        return 0

    update_ids = []
    update_metadatas = []

    for record_id, metadata in zip(ids, metadatas):

        metadata = dict(metadata or {})

        # Already migrated.
        if "scope" in metadata:
            continue

        metadata["scope"] = "global"
        metadata["user_id"] = ""

        if "ocr_used" not in metadata:
            metadata["ocr_used"] = False

        if "content_type" not in metadata:
            metadata["content_type"] = "legacy"

        update_ids.append(record_id)
        update_metadatas.append(metadata)

    if not update_ids:
        return 0

    collection.update(
        ids=update_ids,
        metadatas=update_metadatas,
    )

    return len(update_ids)


def _ensure_scope_metadata():
    """
    Run the legacy migration once per application process.
    """

    global _scope_metadata_ready

    if _scope_metadata_ready:
        return

    with _scope_metadata_lock:

        if _scope_metadata_ready:
            return

        migrate_legacy_documents()

        _scope_metadata_ready = True


# ---------------------------------------
# Scope helpers
# ---------------------------------------

def _validate_user_id(user_id):
    """
    Validate and normalize an authenticated user ID.
    """

    try:
        user_id = int(user_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "user_id must be an integer."
        ) from exc

    if user_id <= 0:
        raise ValueError(
            "user_id must be a positive integer."
        )

    return user_id


def _build_user_scope_filter(user_id):
    """
    Return a Chroma filter matching documents belonging
    to one private user.
    """

    user_id = _validate_user_id(user_id)

    return {
        "$and": [
            {
                "scope": "user"
            },
            {
                "user_id": str(user_id)
            }
        ]
    }


def _build_authorized_scope_filter(user_id):
    """
    Return the authorization filter for an authenticated user.

    Authorized documents are:

        Global Knowledge Base
        OR
        current user's private Library
    """

    user_id = _validate_user_id(user_id)

    return {
        "$or": [
            {
                "scope": "global"
            },
            {
                "$and": [
                    {
                        "scope": "user"
                    },
                    {
                        "user_id": str(user_id)
                    }
                ]
            }
        ]
    }


# ---------------------------------------
# Helper: generate stable chunk ID
# ---------------------------------------

def generate_chunk_id(
    chunk,
    index,
    scope="global",
    user_id=None,
):
    """
    Generate a deterministic ID for a document chunk.

    Scope and user_id are included so identical documents
    belonging to different authorization scopes cannot collide.
    """

    source = str(
        chunk.metadata.get(
            "source",
            "unknown",
        )
    )

    content = chunk.page_content.strip()

    scope_value = str(
        scope or "global"
    )

    user_value = (
        str(user_id)
        if user_id is not None
        else ""
    )

    raw_id = (
        f"{scope_value}|"
        f"{user_value}|"
        f"{source}|"
        f"{index}|"
        f"{content}"
    )

    hash_id = hashlib.sha256(
        raw_id.encode("utf-8")
    ).hexdigest()

    return f"chunk_{hash_id}"


# ---------------------------------------
# Add documents
# ---------------------------------------

def add_documents(
    chunks,
    scope="global",
    user_id=None,
):
    """
    Store document chunks and embeddings in ChromaDB.

    Existing chunks from the same source and authorization
    scope are removed before inserting the new version.

    Parameters
    ----------
    chunks:
        Iterable of LangChain Document objects.

    scope:
        Supported values:

            "global"
                Shared Global Knowledge Base.

            "user"
                Private User Library.

    user_id:
        Owner of a private user-scoped document.

    Returns
    -------
    int
        Number of chunks stored.
    """

    _ensure_scope_metadata()

    if not chunks:
        return 0

    scope = str(
        scope or "global"
    ).strip().lower()

    if scope not in {
        "global",
        "user",
    }:
        raise ValueError(
            "Invalid document scope. "
            "Expected 'global' or 'user'."
        )

    if scope == "user":

        user_id = _validate_user_id(
            user_id
        )

    else:
        user_id = None

    chunks = list(chunks)

    if not chunks:
        return 0

    source = str(
        chunks[0].metadata.get(
            "source",
            "unknown",
        )
    )

    # -----------------------------------
    # Delete previous version
    # -----------------------------------

    delete_filters = [
        {
            "source": source
        },
        {
            "scope": scope
        },
    ]

    if scope == "user":

        delete_filters.append(
            {
                "user_id": str(user_id)
            }
        )

    collection.delete(
        where={
            "$and": delete_filters
        }
    )

    # -----------------------------------
    # Prepare non-empty chunks
    # -----------------------------------

    valid_chunks = [
        chunk
        for chunk in chunks
        if chunk.page_content
        and chunk.page_content.strip()
    ]

    if not valid_chunks:
        return 0

    texts = [
        chunk.page_content.strip()
        for chunk in valid_chunks
    ]

    # -----------------------------------
    # Generate embeddings
    # -----------------------------------

    embeddings = embed_texts(
        texts
    )

    # -----------------------------------
    # Build IDs and metadata
    # -----------------------------------

    ids = []
    metadatas = []

    for index, chunk in enumerate(
        valid_chunks
    ):

        metadata = dict(
            chunk.metadata or {}
        )

        ids.append(
            generate_chunk_id(
                chunk,
                index,
                scope=scope,
                user_id=user_id,
            )
        )

        chunk_metadata = {
            "source": source,
            "scope": scope,
            "user_id": (
                str(user_id)
                if scope == "user"
                else ""
            ),
            "ocr_used": bool(
                metadata.get(
                    "ocr_used",
                    False,
                )
            ),
        }

        # Page number
        if "page" in metadata:

            try:
                chunk_metadata["page"] = int(
                    metadata["page"]
                )

            except (
                TypeError,
                ValueError,
            ):
                pass

        # Content type
        if "content_type" in metadata:

            chunk_metadata[
                "content_type"
            ] = str(
                metadata["content_type"]
            )

        metadatas.append(
            chunk_metadata
        )

    # -----------------------------------
    # Store
    # -----------------------------------

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(texts)


# ---------------------------------------
# Search documents
# ---------------------------------------

def search_documents(
    query,
    top_k=4,
    user_id=None,
):
    """
    Search ChromaDB for relevant document chunks.

    If user_id is None:
        Global Knowledge Base only.

    If user_id is supplied:
        Global Knowledge Base
        +
        current user's private Library.

    Another user's private documents are excluded.
    """

    _ensure_scope_metadata()

    if not query or not query.strip():

        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    total_count = collection.count()

    if total_count == 0:

        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    try:

        top_k = int(top_k)

    except (
        TypeError,
        ValueError,
    ):

        top_k = 4

    top_k = max(
        1,
        min(
            top_k,
            total_count,
        ),
    )

    query_embedding = embed_query(
        query
    )

    # -----------------------------------
    # Build authorization filter
    # -----------------------------------

    if user_id is None:

        where_filter = {
            "scope": "global"
        }

    else:

        where_filter = (
            _build_authorized_scope_filter(
                user_id
            )
        )

    # -----------------------------------
    # Query Chroma
    # -----------------------------------

    return collection.query(
        query_embeddings=[
            query_embedding
        ],
        n_results=top_k,
        where=where_filter,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )


# ---------------------------------------
# Collection information
# ---------------------------------------

def get_collection_count():
    """
    Return the total number of chunks
    stored in ChromaDB.
    """

    _ensure_scope_metadata()

    return collection.count()