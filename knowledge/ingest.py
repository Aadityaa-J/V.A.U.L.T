from pathlib import Path

from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader
)

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)

from .vector_store import add_documents


# ---------------------------------------
# Document loading
# ---------------------------------------

def load_document(file_path: str):
    """
    Load a PDF or DOCX document.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    extension = path.suffix.lower()

    if extension == ".pdf":

        loader = PyPDFLoader(
            str(path)
        )

    elif extension == ".docx":

        loader = Docx2txtLoader(
            str(path)
        )

    else:

        raise ValueError(
            "Unsupported file format. "
            "Supported formats: PDF and DOCX."
        )

    documents = loader.load()

    if not documents:
        raise ValueError(
            f"No content could be extracted from: {file_path}"
        )

    return documents


# ---------------------------------------
# Chunking
# ---------------------------------------

def split_documents(documents):
    """
    Split documents into overlapping chunks.
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50
    )

    return splitter.split_documents(documents)


# ---------------------------------------
# Complete ingestion pipeline
# ---------------------------------------

def ingest_document(file_path: str):
    """
    Load, chunk, embed and store a document
    in the V.A.U.L.T. knowledge base.
    """

    path = Path(file_path)

    documents = load_document(
        str(path)
    )

    chunks = split_documents(
        documents
    )

    stored_chunks = add_documents(
        chunks
    )

    return {
        "file": path.name,
        "documents": len(documents),
        "chunks": len(chunks),
        "stored_chunks": stored_chunks
    }