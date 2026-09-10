"""
Document tools for V.A.U.L.T.

This module provides the low-level text-document utilities used by the
unified document ingestion pipeline.

It intentionally handles text-like files only. Binary/structured formats
such as PDF, DOCX, XLSX, PPTX and images are routed by
document_pipeline.py to their appropriate native parser or OCR path.
"""

from pathlib import Path


# Text-like formats that can safely be read as text.
# Keep this list focused on formats where Path.read_text() is appropriate.
SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".rst",
    ".log",
    ".csv",
    ".tsv",
    ".json",
    ".jsonl",
    ".ndjson",
    ".xml",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".cc",
    ".cxx",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".kts",
    ".sh",
    ".bash",
    ".zsh",
    ".bat",
    ".ps1",
    ".sql",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".tex",
    ".svg",
}


def _validate_file(file_path: str) -> Path:
    """Validate a path and return it as a Path object."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    return path


def _read_text_with_fallback(path: Path) -> str:
    """
    Read a text document using UTF-8 first, then common legacy encodings.

    errors='replace' is deliberately avoided as the first choice so that
    malformed/binary data is not silently presented as valid document text.
    """
    encodings = ("utf-8", "utf-8-sig", "cp1252", "latin-1")

    last_error = None

    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc

    raise UnicodeDecodeError(
        "unknown",
        b"",
        0,
        1,
        f"Unable to decode text document: {last_error}",
    )


def read_document(file_path: str) -> str:
    """
    Read a text-based document and return its contents.

    This function is intentionally limited to text-like formats. The unified
    ingestion pipeline handles richer/binary formats separately.
    """
    path = _validate_file(file_path)

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported text document type: {path.suffix or '[no extension]'}"
        )

    return _read_text_with_fallback(path)


def document_info(file_path: str) -> dict:
    """
    Return basic information about a text-based document.
    """
    path = _validate_file(file_path)
    content = read_document(file_path)

    return {
        "name": path.name,
        "path": str(path.absolute()),
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
        "characters": len(content),
        "lines": len(content.splitlines()),
        "words": len(content.split()),
    }


def search_document(file_path: str, query: str) -> list[dict]:
    """
    Search for a word or phrase inside a text document.

    Returns matching lines and their line numbers.
    """
    if not query:
        raise ValueError("Search query cannot be empty.")

    content = read_document(file_path)
    matches = []

    for line_number, line in enumerate(content.splitlines(), start=1):
        if query.lower() in line.lower():
            matches.append(
                {
                    "line": line_number,
                    "content": line,
                }
            )

    return matches


def get_document_summary(file_path: str, max_words: int = 100) -> str:
    """
    Return a simple extractive summary by taking the first N words.
    """
    if max_words < 1:
        raise ValueError("max_words must be at least 1.")

    content = read_document(file_path)
    words = content.split()

    if len(words) <= max_words:
        return content

    return " ".join(words[:max_words]) + "..."
