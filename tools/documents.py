"""
Document tools for V.A.U.L.T.
"""

from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".json",
    ".csv",
    ".html",
    ".xml",
}


def read_document(file_path: str) -> str:
    """
    Read a text-based document and return its contents.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported document type: {path.suffix}"
        )

    return path.read_text(encoding="utf-8")


def document_info(file_path: str) -> dict:
    """
    Return basic information about a document.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    content = read_document(file_path)

    return {
        "name": path.name,
        "path": str(path.absolute()),
        "extension": path.suffix,
        "size_bytes": path.stat().st_size,
        "characters": len(content),
        "lines": len(content.splitlines()),
        "words": len(content.split()),
    }


def search_document(file_path: str, query: str) -> list[dict]:
    """
    Search for a word or phrase inside a document.

    Returns matching lines and their line numbers.
    """

    if not query:
        raise ValueError("Search query cannot be empty.")

    content = read_document(file_path)

    matches = []

    for line_number, line in enumerate(content.splitlines(), start=1):
        if query.lower() in line.lower():
            matches.append({
                "line": line_number,
                "content": line,
            })

    return matches


def get_document_summary(file_path: str, max_words: int = 100) -> str:
    """
    Return a simple extractive summary by taking the first N words.
    """

    content = read_document(file_path)
    words = content.split()

    if len(words) <= max_words:
        return content

    return " ".join(words[:max_words]) + "..."