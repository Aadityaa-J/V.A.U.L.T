"""
Unified document ingestion pipeline for V.A.U.L.T.

Pipeline:

    ANY UPLOAD
        |
        +--> text-like file --------------------+
        |                                       |
        +--> PDF/DOCX/XLSX/PPTX native parser --+
        |                                       |
        +--> image -----------------------------+--> normalized text
        |                                       |
        +--> scanned PDF -----------------------+
        |                                       |
        +--> unknown text-like file ------------+
                                                |
                                                v
                                           chunking
                                                |
                                                v
                                          embeddings
                                                |
                                                v
                                             Chroma

The pipeline reuses the existing V.A.U.L.T. document tool, OCR component and
vector store instead of creating competing implementations.

Important:
"All file types" cannot literally mean that every binary/proprietary format
contains extractable document text. For formats that cannot be meaningfully
parsed, this module fails gracefully with a useful status instead of hanging
forever or pretending that binary bytes are document text.
"""

from __future__ import annotations

import mimetypes
import re
import tempfile
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from tools.documents import SUPPORTED_EXTENSIONS as TOOL_TEXT_EXTENSIONS
from tools.documents import read_document
from knowledge.vector_store import add_documents
from models.vision import analyze_image


PROJECT_ROOT = Path(__file__).resolve().parent

CHUNK_SIZE = 300
CHUNK_OVERLAP = 50
MIN_USEFUL_TEXT_LENGTH = 20

# Formats directly handled by the existing tools/documents.py.
TEXT_EXTENSIONS = set(TOOL_TEXT_EXTENSIONS)

# Common rich-document formats with native parsers.
PDF_EXTENSIONS = {".pdf"}
DOCX_EXTENSIONS = {".docx"}
SPREADSHEET_EXTENSIONS = {".xlsx", ".xlsm"}
PRESENTATION_EXTENSIONS = {".pptx"}
HTML_EXTENSIONS = {".html", ".htm"}

# Image formats sent to the existing Qwen3-VL OCR component.
IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".gif",
}

SUPPORTED_NATIVE_EXTENSIONS = (
    TEXT_EXTENSIONS
    | PDF_EXTENSIONS
    | DOCX_EXTENSIONS
    | SPREADSHEET_EXTENSIONS
    | PRESENTATION_EXTENSIONS
    | HTML_EXTENSIONS
    | IMAGE_EXTENSIONS
)


class DocumentProcessingError(RuntimeError):
    """Raised when a file cannot be converted into useful document text."""


def _validate_file(file_path: str | Path) -> Path:
    """Validate and return a file path."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    return path


def _normalize_text(text: str) -> str:
    """
    Normalize extracted text without destroying meaningful line structure.
    """
    if not text:
        return ""

    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove excessive horizontal whitespace but preserve line breaks.
    text = re.sub(r"[ \t]+", " ", text)

    # Prevent huge runs of blank lines from creating noisy chunks.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _has_useful_text(text: str) -> bool:
    """Return True when extracted content contains meaningful text."""
    cleaned = re.sub(r"\s+", "", text or "")
    return len(cleaned) >= MIN_USEFUL_TEXT_LENGTH


def _make_document(
    text: str,
    source: str,
    page: int | None = None,
    ocr_used: bool = False,
    content_type: str | None = None,
) -> Document:
    """Create a normalized LangChain Document with consistent metadata."""
    metadata = {
        "source": source,
        "ocr_used": bool(ocr_used),
    }

    if page is not None:
        metadata["page"] = page

    if content_type:
        metadata["content_type"] = content_type

    return Document(
        page_content=_normalize_text(text),
        metadata=metadata,
    )


def _load_text_file(path: Path) -> list[Document]:
    """
    Use the existing V.A.U.L.T. document tool for text-like formats.
    """
    text = read_document(str(path))

    if not _has_useful_text(text):
        return []

    return [
        _make_document(
            text=text,
            source=path.name,
            content_type="text",
        )
    ]


def _load_pdf_native(path: Path) -> list[Document]:
    """
    Extract text from a PDF using the existing LangChain/PyPDF stack.

    PyPDFLoader is preferred because it preserves page metadata.
    """
    try:
        from langchain_community.document_loaders import PyPDFLoader
    except ImportError as exc:
        raise DocumentProcessingError(
            "PDF support requires langchain-community."
        ) from exc

    try:
        loaded = PyPDFLoader(str(path)).load()
    except Exception as exc:
        raise DocumentProcessingError(
            f"Native PDF parsing failed for {path.name}: {exc}"
        ) from exc

    documents: list[Document] = []

    for index, item in enumerate(loaded, start=1):
        text = _normalize_text(item.page_content)

        if not _has_useful_text(text):
            continue

        page = item.metadata.get("page")
        if page is None:
            page = index

        # PyPDFLoader normally uses zero-based page metadata.
        if isinstance(page, int) and page < index:
            page += 1

        documents.append(
            _make_document(
                text=text,
                source=path.name,
                page=page,
                ocr_used=False,
                content_type="pdf",
            )
        )

    return documents


def _ocr_pdf(path: Path) -> list[Document]:
    """
    Render every PDF page to an image and pass it through Qwen3-VL OCR.

    This is the fallback for scanned/image-only PDFs.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise DocumentProcessingError(
            "Scanned PDF OCR requires PyMuPDF (fitz)."
        ) from exc

    pdf = None

    try:
        pdf = fitz.open(str(path))
        documents: list[Document] = []

        for page_number, page in enumerate(pdf, start=1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)

            temp_path: Path | None = None

            try:
                with tempfile.NamedTemporaryFile(
                    suffix=".png",
                    prefix="vault_pdf_page_",
                    delete=False,
                ) as temp_file:
                    temp_path = Path(temp_file.name)

                pixmap.save(str(temp_path))

                ocr_text = analyze_image(
                    str(temp_path),
                    (
                        "Transcribe all visible document text exactly. "
                        "Preserve headings, labels, tables, numbers, units, "
                        "and reading order. Do not summarize, interpret, "
                        "or invent missing text."
                    ),
                )

                if _has_useful_text(ocr_text):
                    documents.append(
                        _make_document(
                            text=ocr_text,
                            source=path.name,
                            page=page_number,
                            ocr_used=True,
                            content_type="pdf",
                        )
                    )
            finally:
                if temp_path is not None:
                    try:
                        temp_path.unlink(missing_ok=True)
                    except Exception:
                        pass

        return documents

    except Exception as exc:
        raise DocumentProcessingError(
            f"OCR processing failed for PDF {path.name}: {exc}"
        ) from exc
    finally:
        if pdf is not None:
            pdf.close()


def _load_pdf(path: Path) -> list[Document]:
    """
    Native PDF extraction first, OCR fallback for scanned PDFs.
    """
    native_documents = _load_pdf_native(path)

    if any(_has_useful_text(doc.page_content) for doc in native_documents):
        return native_documents

    return _ocr_pdf(path)


def _load_docx(path: Path) -> list[Document]:
    """
    Extract DOCX paragraphs using python-docx, with docx2txt fallback.
    """
    text_parts: list[str] = []

    try:
        from docx import Document as DocxDocument

        document = DocxDocument(str(path))

        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)

        # Also include table contents because inspection/technical
        # documents frequently store important values inside tables.
        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    text_parts.append(" | ".join(cells))

    except ImportError:
        try:
            import docx2txt

            extracted = docx2txt.process(str(path))
            if extracted:
                text_parts.append(extracted)
        except ImportError as exc:
            raise DocumentProcessingError(
                "DOCX support requires python-docx or docx2txt."
            ) from exc

    except Exception as exc:
        raise DocumentProcessingError(
            f"DOCX parsing failed for {path.name}: {exc}"
        ) from exc

    text = _normalize_text("\n".join(text_parts))

    if not _has_useful_text(text):
        raise DocumentProcessingError(
            f"No readable text was found in DOCX: {path.name}"
        )

    return [
        _make_document(
            text=text,
            source=path.name,
            content_type="docx",
        )
    ]



def _load_html_file(path: Path) -> list[Document]:
    """Parse HTML as a document, removing code/UI noise before RAG.

    HTML is not treated as a PDF or as arbitrary raw source code. The parser
    keeps the human-readable page content (title, headings, paragraphs,
    lists, table text and meaningful links) while removing script/style/meta
    noise that can otherwise dominate a summary.
    """
    raw = path.read_text(encoding="utf-8", errors="replace")

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        # Conservative fallback when BeautifulSoup is unavailable.
        cleaned = re.sub(r"(?is)<(script|style|noscript|template).*?>.*?</\1>", " ", raw)
        cleaned = re.sub(r"(?is)<[^>]+>", "\n", cleaned)
        text = _normalize_text(cleaned)
    else:
        soup = BeautifulSoup(raw, "html.parser")
        for element in soup(["script", "style", "noscript", "template", "svg"]):
            element.decompose()

        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        body = soup.body or soup
        text = body.get_text("\n", strip=True)
        text = _normalize_text((f"Title: {title}\n\n" if title else "") + text)

    if not _has_useful_text(text):
        raise DocumentProcessingError(
            f"HTML file contains no useful readable content: {path.name}"
        )

    return [
        _make_document(
            text=text,
            source=path.name,
            content_type="html",
        )
    ]

def _load_spreadsheet(path: Path) -> list[Document]:
    """
    Extract XLSX/XLSM worksheets into searchable text.

    Each worksheet becomes one document, with row values separated by '|'.
    """
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise DocumentProcessingError(
            "Spreadsheet support requires openpyxl."
        ) from exc

    try:
        workbook = load_workbook(
            filename=str(path),
            read_only=True,
            data_only=True,
        )
    except Exception as exc:
        raise DocumentProcessingError(
            f"Spreadsheet parsing failed for {path.name}: {exc}"
        ) from exc

    documents: list[Document] = []

    try:
        for sheet in workbook.worksheets:
            rows: list[str] = []

            for row in sheet.iter_rows(values_only=True):
                values = [
                    str(value).strip()
                    for value in row
                    if value is not None and str(value).strip()
                ]

                if values:
                    rows.append(" | ".join(values))

            if rows:
                text = f"Worksheet: {sheet.title}\n" + "\n".join(rows)

                documents.append(
                    _make_document(
                        text=text,
                        source=path.name,
                        content_type="spreadsheet",
                    )
                )
    finally:
        workbook.close()

    if not documents:
        raise DocumentProcessingError(
            f"No readable cells were found in spreadsheet: {path.name}"
        )

    return documents


def _load_presentation(path: Path) -> list[Document]:
    """
    Extract text from PPTX slides.

    Each slide becomes one document with slide metadata.
    """
    try:
        from pptx import Presentation
    except ImportError as exc:
        raise DocumentProcessingError(
            "PPTX support requires python-pptx."
        ) from exc

    try:
        presentation = Presentation(str(path))
    except Exception as exc:
        raise DocumentProcessingError(
            f"PPTX parsing failed for {path.name}: {exc}"
        ) from exc

    documents: list[Document] = []

    for slide_number, slide in enumerate(presentation.slides, start=1):
        parts: list[str] = []

        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                text = shape.text.strip()
                if text:
                    parts.append(text)

        if parts:
            documents.append(
                _make_document(
                    text="\n".join(parts),
                    source=path.name,
                    page=slide_number,
                    content_type="presentation",
                )
            )

    if not documents:
        raise DocumentProcessingError(
            f"No readable text was found in presentation: {path.name}"
        )

    return documents


def _ocr_image(path: Path) -> list[Document]:
    """
    OCR an image using the existing V.A.U.L.T. vision component.
    """
    try:
        text = analyze_image(
            str(path),
            (
                "Transcribe all visible document text exactly. "
                "Preserve headings, labels, tables, numbers, units, "
                "and reading order. Do not summarize, interpret, "
                "or invent missing text."
            ),
        )
    except Exception as exc:
        raise DocumentProcessingError(
            f"Image OCR failed for {path.name}: {exc}"
        ) from exc

    if not _has_useful_text(text):
        raise DocumentProcessingError(
            f"OCR found no useful text in image: {path.name}"
        )

    return [
        _make_document(
            text=text,
            source=path.name,
            ocr_used=True,
            content_type="image",
        )
    ]


def _looks_like_text(path: Path) -> bool:
    """
    Conservative content sniffing for files whose extension is unknown.

    We inspect only a small prefix and reject obvious binary data. This does
    not attempt to parse arbitrary binary/proprietary formats.
    """
    try:
        sample = path.read_bytes()[:8192]
    except OSError:
        return False

    if not sample:
        return True

    if b"\x00" in sample:
        return False

    try:
        decoded = sample.decode("utf-8")
    except UnicodeDecodeError:
        try:
            decoded = sample.decode("cp1252")
        except UnicodeDecodeError:
            return False

    if not decoded.strip():
        return True

    printable = sum(
        1
        for char in decoded
        if char.isprintable() or char in "\n\r\t"
    )

    return printable / max(len(decoded), 1) >= 0.85


def _load_unknown_text(path: Path) -> list[Document]:
    """
    Last-resort parser for unknown extensions that are clearly text.
    """
    if not _looks_like_text(path):
        raise DocumentProcessingError(
            f"No parser is registered for binary file type: "
            f"{path.suffix or '[no extension]'}"
        )

    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw = path.read_text(encoding="cp1252")

    text = _normalize_text(raw)

    if not _has_useful_text(text):
        raise DocumentProcessingError(
            f"File contains no useful text: {path.name}"
        )

    return [
        _make_document(
            text=text,
            source=path.name,
            content_type="unknown-text",
        )
    ]


def _load_documents(path: Path) -> list[Document]:
    """
    Route one file to the appropriate extraction strategy.
    """
    extension = path.suffix.lower()

    if extension in TEXT_EXTENSIONS:
        return _load_text_file(path)

    if extension in PDF_EXTENSIONS:
        return _load_pdf(path)

    if extension in DOCX_EXTENSIONS:
        return _load_docx(path)

    if extension in SPREADSHEET_EXTENSIONS:
        return _load_spreadsheet(path)

    if extension in PRESENTATION_EXTENSIONS:
        return _load_presentation(path)

    if extension in HTML_EXTENSIONS:
        return _load_html_file(path)

    if extension in IMAGE_EXTENSIONS:
        return _ocr_image(path)

    # MIME type is useful for extensionless uploads.
    mime_type, _ = mimetypes.guess_type(str(path))

    if mime_type and mime_type.startswith("text/"):
        return _load_unknown_text(path)

    return _load_unknown_text(path)


def split_documents(documents: Iterable[Document]) -> list[Document]:
    """
    Split extracted documents into RAG-sized chunks.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(list(documents))

    # Ensure every chunk retains the original source metadata.
    for chunk in chunks:
        chunk.page_content = _normalize_text(chunk.page_content)

    return [
        chunk
        for chunk in chunks
        if _has_useful_text(chunk.page_content)
    ]


def _prepare_metadata(
    chunks: list[Document],
    source: str,
) -> list[Document]:
    """
    Normalize metadata before sending chunks to the existing vector store.
    """
    prepared: list[Document] = []

    for chunk in chunks:
        metadata = dict(chunk.metadata)
        metadata["source"] = source
        metadata["ocr_used"] = bool(metadata.get("ocr_used", False))

        prepared.append(
            Document(
                page_content=chunk.page_content,
                metadata=metadata,
            )
        )

    return prepared



def extract_document_chunks(
    file_path: str | Path,
    source_name: str | None = None,
) -> list[Document]:
    """Extract and chunk a document without embedding or storing it.

    This is the fast path used when a user attaches a file to a chat request.
    The chat can answer from the freshly extracted content immediately, while
    vector indexing can happen independently in the background.
    """
    path = _validate_file(file_path)

    documents = _load_documents(path)
    if not documents:
        raise DocumentProcessingError(
            f"No readable content could be extracted from {path.name}"
        )

    chunks = split_documents(documents)
    chunks = _prepare_metadata(chunks, source_name or path.name)

    if not chunks:
        raise DocumentProcessingError(
            f"No useful chunks were produced from {path.name}"
        )

    return chunks

def process_document(
    file_path: str | Path,
    store: bool = True,
    scope: str = "global",
    user_id: int | None = None,
    source_name: str | None = None,
) -> dict:
    """
    Process one uploaded document.

    Returns processing metadata and the number of chunks stored.

    Parameters
    ----------
    file_path:
        Path to the uploaded file.
    store:
        If True, chunks are embedded and upserted into the scoped Chroma
        vector store. Set False when only extraction/chunking is needed.

    scope:
        Chroma authorization scope. Supported values:
            - "global": shared Global Knowledge Base
            - "user": private User Library

    user_id:
        Authenticated user's ID. Required when scope="user".

    source_name:
        Logical source filename stored in vector metadata. This lets the
        application preserve the original filename even when the physical
        stored file has a UUID-based name.
    """
    path = _validate_file(file_path)

    documents = _load_documents(path)

    if not documents:
        raise DocumentProcessingError(
            f"No readable content could be extracted from {path.name}"
        )

    chunks = split_documents(documents)
    chunks = _prepare_metadata(chunks, source_name or path.name)

    if not chunks:
        raise DocumentProcessingError(
            f"No useful chunks were produced from {path.name}"
        )

    ocr_used = any(
        bool(doc.metadata.get("ocr_used", False))
        for doc in documents
    )

    stored_chunks = 0

    if store:
        stored_chunks = add_documents(
            chunks,
            scope=scope,
            user_id=user_id,
        )

    pages = sorted(
        {
            doc.metadata["page"]
            for doc in documents
            if isinstance(doc.metadata.get("page"), int)
        }
    )

    return {
        "file": path.name,
        "path": str(path.absolute()),
        "extension": path.suffix.lower(),
        "mime_type": mimetypes.guess_type(str(path))[0],
        "documents": len(documents),
        "pages": pages,
        "chunks": len(chunks),
        "stored_chunks": stored_chunks,
        "ocr_used": ocr_used,
        "status": "processed",
    }


def process_documents(
    file_paths: Iterable[str | Path],
    store: bool = True,
    scope: str = "global",
    user_id: int | None = None,
) -> list[dict]:
    """
    Process multiple documents independently.

    One bad file does not hide the result of the other files. Each result
    contains either status='processed' or status='failed'.
    """
    results: list[dict] = []

    for file_path in file_paths:
        try:
            results.append(
                process_document(
                    file_path=file_path,
                    store=store,
                    scope=scope,
                    user_id=user_id,
                )
            )
        except Exception as exc:
            path = Path(file_path)

            results.append(
                {
                    "file": path.name,
                    "path": str(path),
                    "extension": path.suffix.lower(),
                    "mime_type": mimetypes.guess_type(str(path))[0],
                    "documents": 0,
                    "pages": [],
                    "chunks": 0,
                    "stored_chunks": 0,
                    "ocr_used": False,
                    "status": "failed",
                    "error": str(exc),
                }
            )

    return results


def supported_extensions() -> set[str]:
    """
    Return extensions explicitly handled by the unified pipeline.
    """
    return set(SUPPORTED_NATIVE_EXTENSIONS)


def is_supported_extension(file_path: str | Path) -> bool:
    """
    Check whether the extension has an explicit native/OCR route.

    Unknown text files may still be accepted through content sniffing.
    """
    return Path(file_path).suffix.lower() in SUPPORTED_NATIVE_EXTENSIONS
