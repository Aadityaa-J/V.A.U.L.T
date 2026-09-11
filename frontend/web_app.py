from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import sys
import re
import json
import html as html_module
import hashlib
import mimetypes
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from email.parser import BytesParser
from email.policy import default
from http.cookies import SimpleCookie

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.orchestrator import Orchestrator
from auth import create_session, get_session, destroy_session
from database import (
    authenticate_user,
    add_library_file,
    get_library_files,
    get_library_file,
    get_library_file_by_name,
    update_library_file,
    delete_library_file,
    add_knowledge_file,
    get_knowledge_files,
    get_knowledge_file,
    get_knowledge_file_by_name,
    get_knowledge_file_by_hash,
    update_knowledge_file,
    delete_knowledge_file,
)

try:
    from database import get_connection
except ImportError:
    get_connection = None

from document_pipeline import process_document, extract_document_chunks
from knowledge.search import search_knowledge
from knowledge.vector_store import add_documents

try:
    from knowledge.vector_store import collection as KNOWLEDGE_COLLECTION
    from knowledge.embeddings import embed_query
except ImportError:
    KNOWLEDGE_COLLECTION = None
    embed_query = None


# ============================================================
# V.A.U.L.T. FRONTEND WEB SERVER
# ============================================================

FRONTEND_DIR = Path(__file__).resolve().parent
PORT = 8000

# Uploaded files stay local to the V.A.U.L.T. machine.
UPLOAD_DIR = PROJECT_ROOT / "uploaded_files"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge_files"
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_SIZE = 25 * 1024 * 1024
# Uploads are intentionally not restricted by extension.
# V.A.U.L.T. can store and reference files of any format.


# ============================================================
# V.A.U.L.T. BACKEND
# ============================================================

try:
    vault = Orchestrator()
    VAULT_INIT_ERROR = None
except Exception as error:
    vault = None
    VAULT_INIT_ERROR = error


# ============================================================
# CHAT JOB MANAGER
# ============================================================

CHAT_EXECUTOR = ThreadPoolExecutor(max_workers=3)
DOCUMENT_INDEX_EXECUTOR = ThreadPoolExecutor(max_workers=1)
CHAT_JOBS = {}
CHAT_JOBS_LOCK = threading.Lock()


# These requests do not need a model call. Handling them locally means
# a slow/stuck document job cannot make a simple greeting wait in the
# single-worker queue.
def _is_coding_request(message):
    """Identify clear coding requests so they are not forced through RAG.

    General questioning is intentionally left alone. This only protects
    explicit software-development requests such as "write a Python
    function" from receiving the evidence-only prompt used for internal
    knowledge/document tasks.
    """

    if not isinstance(message, str):
        return False

    text = message.strip().lower()
    if not text:
        return False

    strong_phrases = (
        "write a python", "write python", "python function",
        "python code", "python script", "write code",
        "generate code", "create code", "implement this",
        "implement a ", "debug this code", "fix this code",
        "review this code", "run this code", "execute this code",
        "test this code", "coding task",
    )
    if any(phrase in text for phrase in strong_phrases):
        return True

    languages = (
        "python", "javascript", "typescript", "java", "c++",
        "c#", "golang", "rust", "kotlin", "swift", "sql",
    )
    code_terms = (
        "function", "class", "method", "script", "program",
        "code", "debug", "algorithm", "regex", "stack trace",
        "syntax error",
    )
    return any(x in text for x in languages) and any(x in text for x in code_terms)


FAST_GREETING_RESPONSES = {
    "hi": "Hello! How can I assist you today?",
    "hello": "Hello! How can I assist you today?",
    "hey": "Hey! How can I assist you today?",
    "hey vault": "Hello! How can I assist you today?",
    "hi vault": "Hello! How can I assist you today?",
    "hello vault": "Hello! How can I assist you today?",
}


def _fast_local_database_response(message, user_id=None):
    """Answer deterministic inventory questions directly from SQLite.

    The scope decision is made BEFORE the database lookup:
      - explicit global/shared/company scope -> Global Knowledge Base
      - explicit private/my/personal/local scope -> authenticated User Library
      - otherwise -> not handled here; normal AI routing remains available

    This prevents phrases such as "private db" from accidentally matching the
    generic "database/db" vocabulary used by the Global Knowledge Base.
    """
    text = re.sub(r"\s+", " ", str(message or "")).strip().lower()
    if not text:
        return None

    # ------------------------------------------------------------
    # Inventory / listing language
    # ------------------------------------------------------------
    inventory_words = (
        "what files", "what documents", "what resources", "which files",
        "which documents", "which resources", "list files", "list documents",
        "list resources", "show files", "show documents", "show resources",
        "files are there", "documents are there", "resources are there",
        "files do you have", "documents do you have", "resources do you have",
        "what is in", "what's in", "what is there in", "what's there in",
        "what is there", "what's there", "show me what", "tell me what",
        "list", "show me",
    )

    has_inventory_language = any(phrase in text for phrase in inventory_words)
    if not has_inventory_language:
        return None

    # ------------------------------------------------------------
    # Scope vocabulary
    # ------------------------------------------------------------
    global_qualifiers = (
        "global", "shared", "company", "corporate", "organization",
        "organisational", "organizational", "enterprise",
    )
    global_store_words = (
        "knowledge base", "knowledgebase", "global kb", "global db",
        "global database", "shared kb", "shared db", "shared database",
        "company kb", "company db", "company database",
    )

    private_qualifiers = (
        "private", "personal", "my ", "mine", "i uploaded", "my own",
        "user library", "private library", "local library", "local db",
        "local database", "personal library", "personal db",
        "personal database", "private db", "private database",
    )

    # ------------------------------------------------------------
    # IMPORTANT: resolve PRIVATE first.
    # "private db" contains the generic word "db", so checking generic
    # global-store vocabulary first would incorrectly return Global KB data.
    # ------------------------------------------------------------
    private_inventory = any(term in text for term in private_qualifiers)

    if private_inventory:
        if not user_id:
            return "I need an authenticated user context to list a private Library."

        try:
            rows = get_library_files(int(user_id))
        except Exception as error:
            print("[V.A.U.L.T.] Fast private Library lookup failed:", repr(error))
            return None

        if not rows:
            return "Your private V.A.U.L.T. Library is currently empty."

        lines = [f"Your private V.A.U.L.T. Library contains {len(rows)} file(s):", ""]
        for index, row in enumerate(rows, start=1):
            name = str(row.get("original_name") or row.get("name") or "Unnamed file")
            status = str(row.get("processing_status") or "unknown").lower()
            chunks = int(row.get("chunk_count") or 0)
            state = "indexed" if status == "processed" and chunks > 0 else status
            lines.append(f"{index}. {name} — {state}")
        return "\n".join(lines)

    # ------------------------------------------------------------
    # GLOBAL Knowledge Base inventory
    # ------------------------------------------------------------
    has_global_qualifier = any(term in text for term in global_qualifiers)
    has_explicit_global_store = any(term in text for term in global_store_words)

    # Examples accepted here:
    #   "what files are in your global db?"
    #   "what is there in the global database?"
    #   "show me the shared KB"
    #   "what files do you have in the company knowledge base?"
    global_inventory = has_explicit_global_store or (
        has_global_qualifier and any(
            word in text for word in ("db", "database", "kb", "knowledge base", "files", "documents", "resources")
        )
    )

    if global_inventory:
        try:
            rows = get_knowledge_files()
        except Exception as error:
            print("[V.A.U.L.T.] Fast Global Knowledge lookup failed:", repr(error))
            return None

        if not rows:
            return "The Global Knowledge Base is currently empty."

        lines = [f"The Global Knowledge Base contains {len(rows)} file(s):", ""]
        for index, row in enumerate(rows, start=1):
            name = str(row.get("original_name") or row.get("name") or "Unnamed file")
            status = str(row.get("processing_status") or "unknown").lower()
            chunks = int(row.get("chunk_count") or 0)
            state = "indexed" if status == "processed" and chunks > 0 else status
            lines.append(f"{index}. {name} — {state}")
        return "\n".join(lines)

    # Do not guess a scope for ambiguous phrases such as "what is in the db?".
    # Let the normal orchestrator handle them instead of returning the wrong
    # data domain.
    return None

def _activity_event(stage, detail, status="active"):
    from datetime import datetime
    return {
        "stage": stage,
        "detail": detail,
        "status": status,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


def _set_job_activity(job_id, stage, detail, status="active"):
    with CHAT_JOBS_LOCK:
        job = CHAT_JOBS.get(job_id)
        if job is None:
            return

        events = job.setdefault("activity", [])
        if events and events[-1].get("status") == "active":
            events[-1]["status"] = "complete"
        events.append(_activity_event(stage, detail, status))


def _attachment_context_from_chunks(user_id, storage_path, chunks, original_name=None, max_chars=30000):
    """Convert freshly extracted chunks into request-local evidence.

    This path deliberately avoids embeddings. The user's attached file can be
    answered immediately while the same extracted chunks are indexed in the
    background for later RAG queries.
    """
    original_name = original_name or Path(storage_path).name
    results = []
    used_chars = 0

    # Generic summary/explanation requests benefit from broad file coverage.
    # For very large files, keep a bounded context so the local model is not
    # overwhelmed.
    for chunk in chunks:
        text = str(chunk.page_content or "").strip()
        if not text:
            continue

        page = chunk.metadata.get("page")
        remaining = max_chars - used_chars
        if remaining <= 0:
            break
        if len(text) > remaining:
            text = text[:remaining].rstrip() + "\n[Context truncated for local inference.]"

        results.append({
            "text": text,
            "source": original_name,
            "page": page,
            "distance": 0.0,
            "scope": "user",
            "user_id": str(user_id),
            "ocr_used": bool(chunk.metadata.get("ocr_used", False)),
            "content_type": chunk.metadata.get("content_type", ""),
        })
        used_chars += len(text)

    return results


def _index_extracted_attachment(user_id, storage_path, chunks, original_name=None):
    """Index already-extracted chunks without parsing/OCR a second time."""
    if not chunks:
        return

    original_name = original_name or Path(storage_path).name
    prepared = []
    for chunk in chunks:
        metadata = dict(chunk.metadata)
        metadata["source"] = original_name
        metadata["scope"] = "user"
        metadata["user_id"] = str(int(user_id))
        prepared.append(
            type(chunk)(
                page_content=chunk.page_content,
                metadata=metadata,
            )
        )

    stored = add_documents(
        prepared,
        scope="user",
        user_id=int(user_id),
    )

    _set_library_processing_state(
        user_id,
        storage_path,
        "processed",
        ocr_used=any(bool(c.metadata.get("ocr_used", False)) for c in prepared),
        chunk_count=stored,
    )
    return stored


def _queue_attachment_index(user_id, storage_path, chunks, original_name=None):
    """Schedule vector indexing without delaying the chat response."""
    _set_library_processing_state(
        user_id,
        storage_path,
        "processing",
        ocr_used=any(bool(c.metadata.get("ocr_used", False)) for c in chunks),
        chunk_count=0,
    )

    return DOCUMENT_INDEX_EXECUTOR.submit(
        _index_extracted_attachment,
        user_id,
        storage_path,
        chunks,
        original_name,
    )


def _get_original_library_name(user_id, storage_path):
    if get_connection is None or not user_id or not storage_path:
        return Path(storage_path).name
    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT original_name
                FROM library_files
                WHERE user_id = ? AND storage_path = ?
                LIMIT 1
                """,
                (int(user_id), str(storage_path)),
            ).fetchone()
            if row:
                return str(row[0] if not hasattr(row, "keys") else row["original_name"])
    except Exception as error:
        print("[V.A.U.L.T.] Could not resolve original attachment name:", repr(error))
    return Path(storage_path).name


def start_chat_job(message, attachment_paths=None, user_id=None):
    """Run an orchestration request without blocking on vector indexing."""

    attachment_paths = attachment_paths or []
    job_id = uuid.uuid4().hex

    with CHAT_JOBS_LOCK:
        CHAT_JOBS[job_id] = {
            "status": "queued",
            "response": None,
            "error": None,
            "user_id": user_id,
            "activity": [
                _activity_event(
                    "REQUEST RECEIVED",
                    "V.A.U.L.T. accepted the operator request.",
                    "complete",
                )
            ],
        }

    normalized_message = message.strip().lower() if isinstance(message, str) else ""
    coding_request = _is_coding_request(message)

    if not attachment_paths:
        fast_database_response = _fast_local_database_response(message, user_id=user_id)
        if fast_database_response is not None:
            _set_job_activity(
                job_id,
                "TASK ROUTED",
                "Deterministic local database query; model inference and semantic RAG skipped.",
                "active",
            )
            with CHAT_JOBS_LOCK:
                CHAT_JOBS[job_id]["status"] = "completed"
                CHAT_JOBS[job_id]["response"] = fast_database_response
            _set_job_activity(
                job_id,
                "RESPONSE READY",
                "Local database response returned to the operator without model inference.",
                "complete",
            )
            return job_id

    if not attachment_paths and normalized_message in FAST_GREETING_RESPONSES:
        _set_job_activity(
            job_id,
            "TASK ROUTED",
            "Simple greeting handled locally without model inference.",
            "active",
        )
        with CHAT_JOBS_LOCK:
            CHAT_JOBS[job_id]["status"] = "completed"
            CHAT_JOBS[job_id]["response"] = FAST_GREETING_RESPONSES[normalized_message]
        _set_job_activity(
            job_id,
            "RESPONSE READY",
            "Local fast-path response returned to the operator.",
            "complete",
        )
        return job_id

    def run_job():
        with CHAT_JOBS_LOCK:
            CHAT_JOBS[job_id]["status"] = "processing"

        _set_job_activity(
            job_id,
            "TASK ROUTED",
            "Request sent to the V.A.U.L.T. Orchestrator.",
            "active",
        )

        try:
            backend_task = message
            evidence = []
            requested_scope = _infer_knowledge_scope(message)

            # Explicit coding requests should go straight to the CodingAgent.
            # They do not need internal evidence unless the operator also
            # attached a file, in which case that attachment remains valid
            # request context.
            if coding_request and not attachment_paths:
                _set_job_activity(
                    job_id,
                    "TASK ROUTED",
                    "Coding request detected; CodingAgent and coding tools enabled. Knowledge retrieval skipped.",
                    "complete",
                )

            if attachment_paths:
                _set_job_activity(
                    job_id,
                    "CONTEXT ATTACHED",
                    f"{len(attachment_paths)} local file(s) supplied as request context.",
                    "active",
                )

                for path in attachment_paths:
                    filename = _get_original_library_name(user_id, path)
                    existing = _get_library_record_by_storage_path(user_id, path)
                    existing_status = str((existing or {}).get("processing_status", "")).lower()
                    existing_chunks = int((existing or {}).get("chunk_count") or 0)

                    # If the vector index is already ready, use it. Otherwise,
                    # extract directly and answer immediately from the file.
                    if existing_status == "processed" and existing_chunks > 0:
                        _set_job_activity(
                            job_id,
                            "DOCUMENT INGESTION",
                            f"'{filename}' is already indexed; reusing the existing extraction.",
                            "complete",
                        )
                        file_evidence = _retrieve_attached_file_evidence(
                            user_id=user_id,
                            query=message,
                            attachment_paths=[path],
                            top_k=16,
                        )
                        evidence.extend(file_evidence)
                    else:
                        _set_job_activity(
                            job_id,
                            "DOCUMENT INGESTION",
                            f"Extracting '{filename}' directly for this request; vector indexing will continue in the background.",
                            "active",
                        )

                        chunks = extract_document_chunks(Path(path), source_name=filename)
                        file_evidence = _attachment_context_from_chunks(
                            user_id=user_id,
                            storage_path=path,
                            chunks=chunks,
                            original_name=filename,
                        )
                        evidence.extend(file_evidence)

                        if any(bool(c.metadata.get("ocr_used", False)) for c in chunks):
                            _set_job_activity(
                                job_id,
                                "OCR / VISION EXTRACTION",
                                f"OCR was used to recover readable content from '{filename}'.",
                                "complete",
                            )

                        _queue_attachment_index(
                            user_id=user_id,
                            storage_path=path,
                            chunks=chunks,
                            original_name=filename,
                        )

                        _set_job_activity(
                            job_id,
                            "VECTOR INDEX",
                            f"Background indexing queued for {len(chunks)} extracted chunk(s) from '{filename}'.",
                            "complete",
                        )

                html_attachment = any(
                    str(item.get("content_type", "")).lower() == "html"
                    for item in evidence
                )
                backend_task += (
                    "\n\nDOCUMENT-GROUNDED REQUEST RULES:\n"
                    "The operator attached private V.A.U.L.T. Library file(s). "
                    "For this request, ONLY the attached file content is authoritative. "
                    "Do not use any other Global KB or Library document.\n"
                    "Answer the operator's actual request directly. For summarize/explain requests, "
                    "synthesize the supplied document content in clear language; do not describe the "
                    "retrieval process unless asked. If the attached file does not support a claim, say so.\n"
                    + (
                        "The attached file is HTML. Treat it as a webpage/document, not as a PDF or raw program. "
                        "Explain the human-readable content represented by the page. Ignore HTML markup, JavaScript, "
                        "CSS, hidden implementation details, telemetry, and navigation boilerplate unless the operator "
                        "explicitly asks about the HTML source/code.\n"
                        if html_attachment else ""
                    )
                )

            if attachment_paths:
                _set_job_activity(
                    job_id,
                    "RETRIEVAL",
                    "Using evidence exclusively from the attached file(s).",
                    "active",
                )

                backend_task += "\n\n" + _format_rag_evidence(
                    evidence,
                    attachment_only=True,
                )

                _set_job_activity(
                    job_id,
                    "RETRIEVAL",
                    f"Prepared {len(evidence)} attachment evidence item(s) for the model.",
                    "complete",
                )
            elif coding_request:
                _set_job_activity(
                    job_id,
                    "RETRIEVAL",
                    "Knowledge retrieval skipped because this is a normal coding request.",
                    "complete",
                )
            else:
                _set_job_activity(
                    job_id,
                    "RETRIEVAL",
                    (
                        "Searching only the Global Knowledge Base."
                        if requested_scope == "global"
                        else "Searching only the authenticated user's private Library."
                        if requested_scope == "user"
                        else "Searching authorized Global KB + the authenticated user's private Library."
                    ),
                    "active",
                )

                evidence = _retrieve_authorized_evidence(
                    user_id=user_id,
                    query=message,
                    top_k=6,
                    scope=requested_scope,
                )

                backend_task += "\n\n" + _format_rag_evidence(
                    evidence,
                    attachment_only=False,
                )

                _set_job_activity(
                    job_id,
                    "RETRIEVAL",
                    f"Prepared {len(evidence)} authorized evidence item(s) for the model.",
                    "complete",
                )

            _set_job_activity(
                job_id,
                "LOCAL INFERENCE",
                "Executing the configured V.A.U.L.T. backend locally using authorized evidence.",
                "active",
            )

            result = vault.run(
                backend_task,
                human_input={"user_id": user_id},
            )
            if result is None:
                result = ""
            result = str(result)

            with CHAT_JOBS_LOCK:
                CHAT_JOBS[job_id]["status"] = "completed"
                CHAT_JOBS[job_id]["response"] = result

            _set_job_activity(
                job_id,
                "RESPONSE READY",
                "Orchestrator completed the request and returned a response.",
                "complete",
            )

        except Exception as error:
            print("[V.A.U.L.T.] Backend error:", repr(error))
            with CHAT_JOBS_LOCK:
                CHAT_JOBS[job_id]["status"] = "error"
                CHAT_JOBS[job_id]["error"] = str(error)
            _set_job_activity(job_id, "REQUEST FAILED", str(error), "error")

    CHAT_EXECUTOR.submit(run_job)
    return job_id


# ============================================================
# PAGE ROUTES
# ============================================================

PAGES = {
    "/": "LANDING.HTML",
    "/landing": "LANDING.HTML",
    "/login": "LOGIN.HTML",
    "/anchor": "ANCHOR_PAGE.HTML",
    "/analysis": "Analysis.html",
    "/library": "Library.html",
    "/knowledge": "knowledge_base.html",
    "/security": "Security.html",
}


# ============================================================
# TEXT -> ROUTE
# ============================================================

TEXT_ROUTES = {
    "analysis": "/analysis",
    "analysis workspace": "/analysis",

    "library": "/library",
    "files": "/library",

    "knowledge": "/knowledge",
    "knowledge base": "/knowledge",
    "global knowledge": "/knowledge",

    "chats": "/anchor",
    "chat": "/anchor",
    "new task": "/anchor",

    "security": "/security",
    "security monitor": "/security",
    "security enclave": "/security",
    "sovereignty": "/security",
    "sovereignty audit": "/security",

    "anchor": "/anchor",
    "anchor workspace": "/anchor",
    "workspace": "/anchor",

    "home": "/",
    "landing": "/",

    "login": "/login",
}


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    # Remove excessive whitespace
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip().lower()


# ============================================================
# FIND ROUTE FROM TEXT
# ============================================================

def route_from_text(text):

    text = normalize_text(text)

    if not text:
        return None

    # Exact matches first
    if text in TEXT_ROUTES:
        return TEXT_ROUTES[text]

    # Then look for known navigation words
    if "analysis" in text:
        return "/analysis"

    if "files" in text:
        return "/library"

    if "library" in text:
        return "/library"

    if "knowledge" in text:
        return "/knowledge"

    if "new task" in text:
        return "/anchor"

    if "chats" in text:
        return "/anchor"

    if "chat" in text:
        return "/anchor"

    if "security" in text:
        return "/security"

    if "sovereignty" in text:
        return "/security"

    if "anchor" in text:
        return "/anchor"

    return None


# ============================================================
# PATCH HTML
#
# Original HTML files are NEVER modified.
# Everything happens in memory.
# ============================================================

def patch_navigation(html, current_page):

    # ========================================================
    # DIRECT href="#" LINK PATCHING
    # ========================================================

    def patch_link(match):

        opening_tag = match.group(1)
        inner_html = match.group(2)
        closing_tag = match.group(3)

        visible_text = re.sub(
            r"<[^>]*>",
            "",
            inner_html,
        )

        route = route_from_text(
            visible_text
        )

        if route:

            opening_tag = re.sub(
                r'href\s*=\s*["\']#["\']',
                f'href="{route}"',
                opening_tag,
                flags=re.IGNORECASE,
            )

        return (
            opening_tag
            + inner_html
            + closing_tag
        )


    html = re.sub(
        r'(<a\b[^>]*href\s*=\s*["\']#["\'][^>]*>)'
        r'(.*?)'
        r'(</a>)',
        patch_link,
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )


    # ========================================================
    # NAVIGATION JAVASCRIPT
    # ========================================================

    navigation_script = r"""
<script>
(function () {

    /*
     * V.A.U.L.T. navigation bridge
     *
     * This runs in the actual browser page, not inside
     * Streamlit's components.html iframe.
     */

    document.addEventListener(
        "click",
        function (event) {

            /*
             * Find the closest clickable element.
             *
             * This allows clicks on icons, spans, SVGs,
             * etc. inside buttons and links.
             */

            const element =
                event.target.closest("button, a");


            if (!element) {
                return;
            }


            /*
             * Collect every piece of visible text inside
             * the clicked element.
             */

            let text =
                element.textContent || "";

            text = text
                .replace(/\s+/g, " ")
                .trim()
                .toLowerCase();


            // =================================================
            // LANDING -> LOGIN
            // =================================================

            if (
                text.includes("launch v.a.u.l.t")
            ) {

                event.preventDefault();
                event.stopPropagation();

                window.location.href = "/login";

                return;
            }


            // =================================================
            // ANALYSIS
            // =================================================

            if (
                text.includes("analysis")
            ) {

                event.preventDefault();
                event.stopPropagation();

                window.location.href = "/analysis";

                return;
            }


            // =================================================
            // FILES / LIBRARY
            // =================================================

            if (
                (text.includes("files") ||
                 text.includes("library")) &&
                !text.includes("add to library")
            ) {

                event.preventDefault();
                event.stopPropagation();

                window.location.href = "/library";

                return;
            }


            // =================================================
            // CHATS / NEW TASK
            // =================================================

            if (
                text.includes("new task") ||
                text.includes("chats") ||
                text.includes("chat")
            ) {

                event.preventDefault();
                event.stopPropagation();

                if (text.includes("new task")) {

                    /* Start a genuinely fresh backend session. */
                    fetch("/api/clear-session", {
                        method: "POST",
                        cache: "no-store"
                    })
                    .catch(function () {})
                    .finally(function () {
                        window.location.href = "/anchor?new_task=1";
                    });

                } else {

                    window.location.href = "/anchor";
                }

                return;
            }


            // =================================================
            // SECURITY / SOVEREIGNTY
            // =================================================

            if (
                text.includes("security") ||
                text.includes("sovereignty")
            ) {

                event.preventDefault();
                event.stopPropagation();

                window.location.href = "/security";

                return;
            }


            // =================================================
            // ANCHOR
            // =================================================

            if (
                text.includes("anchor") ||
                text.includes("workspace")
            ) {

                event.preventDefault();
                event.stopPropagation();

                window.location.href = "/anchor";

                return;
            }


            // =================================================
            // NORMAL INTERNAL LINKS
            // =================================================

            if (
                element.tagName.toLowerCase() === "a"
            ) {

                const href =
                    element.getAttribute("href");


                if (
                    href &&
                    href.startsWith("/") &&
                    !href.startsWith("//")
                ) {

                    event.preventDefault();
                    event.stopPropagation();

                    window.location.href = href;

                    return;
                }
            }

        },
        true
    );

})();
</script>
"""


    # ========================================================
    # INSERT SCRIPT BEFORE BODY
    # ========================================================

    if "</body>" in html:

        html = html.replace(
            "</body>",
            navigation_script + "\n</body>",
        )

    else:

        html += navigation_script


    return html


# ============================================================
# PATCH LIBRARY PAGE
#
# The original Library.html is kept as the visual shell. The dummy
# resource cards are replaced at runtime with the authenticated
# user's actual Library records.
# ============================================================

def patch_library_page(html):
    """Turn the static Library design into the authenticated user's Library."""

    grid_start = '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4" id="resourceGrid">'
    grid_pos = html.find(grid_start)

    if grid_pos >= 0:
        grid_end = html.find('</div>\n</div>\n</main>', grid_pos)
        if grid_end >= 0:
            grid_end += len('</div>')
            html = (
                html[:grid_pos]
                + grid_start + '</div>'
                + html[grid_end:]
            )

    library_script = r"""
<style>
    .library-empty-state {
        grid-column: 1 / -1;
        min-height: 220px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        border: 1px dashed rgba(135, 146, 154, 0.35);
        background: rgba(25, 28, 33, 0.45);
    }
    .library-error-state {
        grid-column: 1 / -1;
        padding: 18px;
        border: 1px solid rgba(255, 80, 80, 0.3);
        color: #ff6b6b;
        background: rgba(90, 0, 0, 0.12);
        font-family: "JetBrains Mono", monospace;
        font-size: 12px;
    }
    .library-upload-status {
        min-height: 16px;
        margin-top: 8px;
        font-family: "JetBrains Mono", monospace;
        font-size: 10px;
        letter-spacing: 0.06em;
        color: #8ed5ff;
        text-transform: uppercase;
    }
    .library-inspector {
        position: fixed;
        top: 0;
        right: 0;
        bottom: 0;
        width: min(440px, 92vw);
        z-index: 60;
        transform: translateX(100%);
        transition: transform 240ms ease;
        background: #111319;
        border-left: 1px solid rgba(135, 146, 154, 0.3);
        box-shadow: -20px 0 50px rgba(0,0,0,0.35);
        overflow-y: auto;
    }
    .library-inspector.open { transform: translateX(0); }
    .library-inspector-inner { padding: 28px; padding-top: 64px; }
    .library-inspector-label {
        font-family: "JetBrains Mono", monospace;
        font-size: 10px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #87929a;
    }
    .library-inspector-value {
        font-family: "Geist", sans-serif;
        color: #e2e2ea;
        word-break: break-word;
    }
</style>

<div id="libraryInspectorBackdrop" class="fixed inset-0 bg-black/40 backdrop-blur-[2px] z-50 opacity-0 pointer-events-none transition-opacity duration-200"></div>

<aside id="libraryInspector" class="library-inspector">
    <div class="library-inspector-inner">
        <div class="flex items-center justify-between mb-7">
            <div>
                <div class="library-inspector-label mb-1">USER LIBRARY / RESOURCE</div>
                <h2 id="libraryInspectorTitle" class="text-xl font-medium text-on-surface">Resource</h2>
            </div>
            <button id="libraryInspectorClose" class="w-8 h-8 border border-outline-variant/30 text-outline hover:text-on-surface hover:bg-surface-container-high/50 rounded flex items-center justify-center">
                <span class="material-symbols-outlined text-[18px]">close</span>
            </button>
        </div>
        <div class="space-y-5">
            <div><div class="library-inspector-label">TYPE</div><div id="libraryInspectorType" class="library-inspector-value mt-1">—</div></div>
            <div><div class="library-inspector-label">SIZE</div><div id="libraryInspectorSize" class="library-inspector-value mt-1">—</div></div>
            <div><div class="library-inspector-label">UPLOADED</div><div id="libraryInspectorDate" class="library-inspector-value mt-1">—</div></div>
            <div><div class="library-inspector-label">PROCESSING</div><div id="libraryInspectorStatus" class="library-inspector-value mt-1 text-primary">STORED LOCALLY</div></div>
            <div><div class="library-inspector-label">CONTENT HASH</div><div id="libraryInspectorHash" class="library-inspector-value mt-1 text-xs font-mono break-all">—</div></div>
            <div class="pt-4 border-t border-outline-variant/20">
                <div class="library-inspector-label">RAG STATUS</div>
                <div id="libraryInspectorRag" class="library-inspector-value mt-1">Awaiting document processing</div>
            </div>
        </div>
    </div>
</aside>

<script>
(function () {
    const grid = document.getElementById("resourceGrid");
    const addButton = Array.from(document.querySelectorAll("button")).find(
        button => (button.textContent || "").toLowerCase().includes("add to library")
    );
    if (addButton) {
        addButton.style.display = "none";
        addButton.setAttribute("aria-hidden", "true");
    }
    const searchInput = document.querySelector('input[placeholder="Search your library..."]');
    const inspector = document.getElementById("libraryInspector");
    const inspectorBackdrop = document.getElementById("libraryInspectorBackdrop");
    const inspectorClose = document.getElementById("libraryInspectorClose");
    let libraryFiles = [];

    function formatBytes(bytes) {
        if (!Number.isFinite(bytes) || bytes < 0) return "—";
        if (bytes < 1024) return bytes + " B";
        const units = ["KB", "MB", "GB"];
        let value = bytes / 1024;
        let unit = 0;
        while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1; }
        return value.toFixed(value >= 10 ? 1 : 2) + " " + units[unit];
    }

    function formatDate(value) {
        if (!value) return "—";
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleString();
    }

    function extensionOf(file) {
        const ext = (file.file_extension || "").replace(/^\./, "").toUpperCase();
        return ext || "FILE";
    }

    function iconFor(file) {
        const ext = extensionOf(file);
        if (["PNG", "JPG", "JPEG", "WEBP", "BMP", "TIFF", "GIF"].includes(ext)) return "image";
        if (ext === "PDF") return "description";
        if (["CSV", "XLS", "XLSX"].includes(ext)) return "table_chart";
        if (["PY", "JS", "TS", "JAVA", "CPP", "C", "HTML", "CSS"].includes(ext)) return "terminal";
        if (["DOC", "DOCX", "TXT", "MD"].includes(ext)) return "draft";
        return "insert_drive_file";
    }

    function filteredFiles() {
        const query = (searchInput ? searchInput.value : "").trim().toLowerCase();
        if (!query) return libraryFiles;
        return libraryFiles.filter(file =>
            (file.original_name || "").toLowerCase().includes(query) ||
            (file.file_extension || "").toLowerCase().includes(query) ||
            (file.mime_type || "").toLowerCase().includes(query)
        );
    }

    function render() {
        if (!grid) return;
        grid.innerHTML = "";
        const files = filteredFiles();

        if (!files.length) {
            const empty = document.createElement("div");
            empty.className = "library-empty-state p-8 rounded";
            empty.innerHTML = '<span class="material-symbols-outlined text-[32px] text-outline mb-3">folder_open</span>' +
                '<div class="font-label-telemetry text-label-telemetry text-outline uppercase tracking-widest">No user files yet</div>' +
                '<div class="text-on-surface-variant text-body-sm mt-2">Files you attach to V.A.U.L.T. requests appear here automatically.</div>';
            grid.appendChild(empty);
            return;
        }

        files.forEach(file => {
            const card = document.createElement("div");
            const ext = extensionOf(file);
            const status = (file.processing_status || "stored").toUpperCase();
            card.className = "resource-card bg-surface-container-low/75 border border-outline-variant/30 hover:border-primary/50 hover:bg-surface-container/60 p-4 rounded transition-all duration-200 cursor-pointer flex flex-col justify-between relative group";
            card.innerHTML = `
                <div>
                    <div class="flex items-center justify-between mb-3">
                        <span class="p-1.5 rounded bg-surface-container border border-outline-variant/40 text-primary flex items-center justify-center"><span class="material-symbols-outlined text-[18px]">${iconFor(file)}</span></span>
                        <span class="font-label-telemetry text-label-micro text-outline px-1.5 py-0.5 rounded bg-surface-container-lowest border border-outline-variant/20 uppercase">${ext}</span>
                    </div>
                    <h3 class="card-title font-headline-sm text-[15px] leading-tight font-medium text-on-surface group-hover:text-primary transition-colors break-words"></h3>
                    <p class="text-on-surface-variant text-body-sm mt-1">${formatBytes(file.file_size)} • ${status}</p>
                </div>
                <div class="mt-4 pt-3 border-t border-outline-variant/20 flex items-center justify-between font-label-telemetry text-label-micro gap-2">
                    <span class="text-outline truncate">${formatDate(file.uploaded_at)}</span>
                    <span class="text-emerald-400 flex items-center gap-1 whitespace-nowrap">● Local</span>
                </div>`;
            card.querySelector(".card-title").textContent = file.original_name || "Unnamed file";
            card.addEventListener("click", () => openInspector(file));
            grid.appendChild(card);
        });
    }

    function openInspector(file) {
        document.getElementById("libraryInspectorTitle").textContent = file.original_name || "Resource";
        document.getElementById("libraryInspectorType").textContent = file.mime_type || extensionOf(file);
        document.getElementById("libraryInspectorSize").textContent = formatBytes(file.file_size);
        document.getElementById("libraryInspectorDate").textContent = formatDate(file.uploaded_at);
        document.getElementById("libraryInspectorStatus").textContent = (file.processing_status || "stored").toUpperCase();
        document.getElementById("libraryInspectorHash").textContent = file.content_hash || "—";
        document.getElementById("libraryInspectorRag").textContent = file.chunk_count > 0
            ? `Indexed with ${file.chunk_count} chunks`
            : "Awaiting document processing";
        inspector.classList.add("open");
        inspectorBackdrop.classList.remove("opacity-0", "pointer-events-none");
        inspectorBackdrop.classList.add("opacity-100", "pointer-events-auto");
    }

    function closeInspector() {
        inspector.classList.remove("open");
        inspectorBackdrop.classList.remove("opacity-100", "pointer-events-auto");
        inspectorBackdrop.classList.add("opacity-0", "pointer-events-none");
    }

    async function loadLibrary() {
        if (!grid) return;
        try {
            const response = await fetch("/api/library", { cache: "no-store" });
            const data = await response.json();
            if (!response.ok || !data.success) throw new Error(data.error || "Unable to load Library.");
            libraryFiles = Array.isArray(data.files) ? data.files : [];
            render();
        } catch (error) {
            grid.innerHTML = "";
            const errorBox = document.createElement("div");
            errorBox.className = "library-error-state rounded";
            errorBox.textContent = "LIBRARY ERROR // " + (error.message || "Unable to load files.");
            grid.appendChild(errorBox);
        }
    }


    if (searchInput) searchInput.addEventListener("input", render);
    if (inspectorClose) inspectorClose.addEventListener("click", closeInspector);
    if (inspectorBackdrop) inspectorBackdrop.addEventListener("click", closeInspector);
    window.addEventListener("keydown", event => { if (event.key === "Escape") closeInspector(); });

    loadLibrary();
})();
</script>
"""

    if "libraryInspector" not in html:
        if "</body>" in html:
            html = html.replace("</body>", library_script + "\n</body>")
        else:
            html += library_script

    return html


# ============================================================
# PATCH ANCHOR CHAT
#
# The original ANCHOR_PAGE.HTML is never modified on disk.
# This injects the browser-to-Orchestrator chat bridge at runtime.
# ============================================================

def patch_anchor_chat(html):

    chat_script = r"""
<style>
/* ==========================================================
   V.A.U.L.T. CHAT MODE
   ========================================================== */

body.vault-chat-active {
    overflow: hidden !important;
}

/* The live chat layer occupies only the existing center
   workspace. Header, sidebar and footer remain untouched. */
body.vault-chat-active main.vault-conversation-main {
    position: relative !important;
    min-height: 0 !important;
    overflow: hidden !important;
}

#vault-live-chat {
    position: absolute !important;
    inset: 0 !important;
    z-index: 30 !important;
    width: 100% !important;
    height: 100% !important;
    min-height: 0 !important;
    display: none !important;
    flex-direction: column !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
}

body.vault-chat-active #vault-live-chat {
    display: flex !important;
}

/* Full-width/full-height scroll container. The scrollbar is
   therefore at the far right of the center workspace. */
#vault-chat-history {
    flex: 1 1 auto !important;
    min-height: 0 !important;
    width: 100% !important;
    height: auto !important;
    box-sizing: border-box !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    padding: 42px 28px 28px 28px !important;
    scrollbar-gutter: stable;
    overscroll-behavior: contain;
}

/* The conversation itself stays centered and readable. */
#vault-chat-history .vault-chat-message {
    width: 100% !important;
    max-width: 820px !important;
    margin: 0 auto 24px auto !important;
    box-sizing: border-box !important;
}

/* Composer stays centered at the bottom of the workspace. */
#vault-composer-host {
    flex: 0 0 auto !important;
    width: 100% !important;
    box-sizing: border-box !important;
    display: flex !important;
    justify-content: center !important;
    padding: 0 24px 18px 24px !important;
}

#vault-composer-host > #vault-composer-wrapper {
    width: 100% !important;
    max-width: 820px !important;
    margin: 0 !important;
    box-sizing: border-box !important;
}

#vault-chat-history,
#vault-chat-history * {
    user-select: text !important;
    -webkit-user-select: text !important;
}

#vault-chat-input {
    user-select: text !important;
    -webkit-user-select: text !important;
}

#vault-send-button.vault-send-ready {
    background: rgba(56, 189, 248, 0.28) !important;
    border-color: rgba(56, 189, 248, 0.9) !important;
    color: #8ed5ff !important;
    box-shadow:
        0 0 8px rgba(56, 189, 248, 0.45),
        0 0 18px rgba(56, 189, 248, 0.22) !important;
}

#vault-send-button.vault-send-ready .material-symbols-outlined {
    filter: drop-shadow(0 0 5px rgba(56, 189, 248, 0.9));
}

/* ==========================================================
   INLINE ORCHESTRATION ACTIVITY
   ========================================================== */

.vault-inline-activity {
    margin-top: 12px !important;
    padding: 11px 0 2px 0 !important;
    border-top: 1px solid rgba(135, 146, 154, 0.14) !important;
    max-width: 620px !important;
}

.vault-inline-activity-label {
    margin-bottom: 9px !important;
    color: rgba(135, 146, 154, 0.8) !important;
    font-family: "JetBrains Mono", monospace !important;
    font-size: 8px !important;
    font-weight: 600 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
}

.vault-inline-activity-list {
    display: flex !important;
    flex-direction: column !important;
    gap: 7px !important;
}

.vault-inline-activity-item {
    display: grid !important;
    grid-template-columns: 9px minmax(0, 1fr) !important;
    gap: 8px !important;
    align-items: start !important;
}

.vault-inline-activity-dot {
    width: 7px !important;
    height: 7px !important;
    margin-top: 4px !important;
    border: 1px solid rgba(135, 146, 154, 0.45) !important;
    background: transparent !important;
    box-sizing: border-box !important;
    border-radius: 50% !important;
}

.vault-inline-activity-item.active .vault-inline-activity-dot {
    border-color: #38bdf8 !important;
    background: #38bdf8 !important;
    box-shadow: 0 0 7px rgba(56, 189, 248, 0.65) !important;
    animation: vaultActivityPulse 1.25s ease-in-out infinite !important;
}

.vault-inline-activity-item.complete .vault-inline-activity-dot {
    border-color: #34d399 !important;
    background: #34d399 !important;
}

.vault-inline-activity-item.error .vault-inline-activity-dot {
    border-color: #ff6b6b !important;
    background: #ff6b6b !important;
}

.vault-inline-activity-stage {
    color: rgba(226, 226, 234, 0.76) !important;
    font-family: "JetBrains Mono", monospace !important;
    font-size: 8px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    line-height: 1.35 !important;
    text-transform: uppercase !important;
}

.vault-inline-activity-detail {
    margin-top: 1px !important;
    color: rgba(226, 226, 234, 0.48) !important;
    font-family: "Geist", sans-serif !important;
    font-size: 10px !important;
    line-height: 1.4 !important;
}

.vault-inline-activity-time {
    margin-top: 1px !important;
    color: rgba(135, 146, 154, 0.42) !important;
    font-family: "JetBrains Mono", monospace !important;
    font-size: 7px !important;
    line-height: 1.3 !important;
}

@keyframes vaultActivityPulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.45; transform: scale(0.82); }
}

/* ==========================================================
   ATTACHMENT CHIPS
   ========================================================== */

#vault-attachment-list {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 8px !important;
    margin: 0 0 10px 0 !important;
    max-width: 100% !important;
}

.vault-attachment-chip {
    display: inline-flex !important;
    align-items: center !important;
    gap: 7px !important;
    max-width: 100% !important;
    padding: 6px 9px !important;
    border: 1px solid rgba(56, 189, 248, 0.28) !important;
    border-radius: 8px !important;
    background: rgba(10, 20, 28, 0.88) !important;
    color: rgba(255,255,255,0.82) !important;
    font-size: 11px !important;
    box-sizing: border-box !important;
}

.vault-attachment-name {
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
    max-width: 320px !important;
}

.vault-attachment-remove {
    border: 0 !important;
    background: transparent !important;
    color: rgba(255,255,255,0.45) !important;
    cursor: pointer !important;
    padding: 0 2px !important;
    font-size: 15px !important;
    line-height: 1 !important;
}

.vault-attachment-remove:hover {
    color: rgba(255,255,255,0.9) !important;
}

#vault-file-input {
    display: none !important;
}
</style>

<script>
(function () {

    const textarea = document.querySelector("textarea");

    if (!textarea) {
        console.warn("[V.A.U.L.T.] Chat textarea not found.");
        return;
    }

    textarea.id = "vault-chat-input";


    const sendButton = Array.from(
        document.querySelectorAll("button")
    ).find(function (button) {
        return (button.textContent || "").includes("arrow_upward");
    });

    if (!sendButton) {
        console.warn("[V.A.U.L.T.] Send button not found.");
        return;
    }

    sendButton.id = "vault-send-button";


    // ======================================================
    // FILE ATTACHMENTS
    // ======================================================

    const attachButton = Array.from(
        document.querySelectorAll("button")
    ).find(function (button) {
        return (button.textContent || "").toLowerCase().includes("attach");
    });

    let fileInput = null;
    let attachmentList = null;
    let selectedFiles = [];

    if (attachButton) {
        fileInput = document.createElement("input");
        fileInput.type = "file";
        fileInput.id = "vault-file-input";
        fileInput.multiple = true;
        fileInput.removeAttribute("accept");
        document.body.appendChild(fileInput);
    }


    const main = textarea.closest("main");
    const promptCard = textarea.parentElement;
    const composerWrapper = promptCard
        ? promptCard.parentElement
        : null;

    if (!main || !promptCard || !composerWrapper) {
        console.warn("[V.A.U.L.T.] Chat layout could not be initialized.");
        return;
    }

    main.classList.add("vault-conversation-main");


    // Put attachment chips directly above the prompt card.
    if (fileInput && composerWrapper) {
        attachmentList = document.createElement("div");
        attachmentList.id = "vault-attachment-list";
        attachmentList.style.display = "none";
        composerWrapper.insertBefore(
            attachmentList,
            promptCard
        );
    }


    function renderAttachments() {

        if (!attachmentList) {
            return;
        }

        attachmentList.innerHTML = "";
        attachmentList.style.display =
            selectedFiles.length ? "flex" : "none";

        selectedFiles.forEach(function (file, index) {

            const chip = document.createElement("div");
            chip.className = "vault-attachment-chip";

            const icon = document.createElement("span");
            icon.textContent = "📎";

            const name = document.createElement("span");
            name.className = "vault-attachment-name";
            name.textContent = file.name;
            name.title = file.name;

            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "vault-attachment-remove";
            remove.textContent = "×";
            remove.title = "Remove attachment";

            remove.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                selectedFiles.splice(index, 1);
                renderAttachments();
            });

            chip.appendChild(icon);
            chip.appendChild(name);
            chip.appendChild(remove);
            attachmentList.appendChild(chip);
        });
    }


    if (attachButton && fileInput) {

        attachButton.addEventListener(
            "click",
            function (event) {
                event.preventDefault();
                event.stopPropagation();
                fileInput.click();
            },
            true
        );

        fileInput.addEventListener("change", function () {
            const incoming = Array.from(fileInput.files || []);

            incoming.forEach(function (file) {
                const duplicate = selectedFiles.some(function (existing) {
                    return (
                        existing.name === file.name &&
                        existing.size === file.size &&
                        existing.lastModified === file.lastModified
                    );
                });

                if (!duplicate) {
                    selectedFiles.push(file);
                }
            });

            fileInput.value = "";
            renderAttachments();
        });
    }


    // ======================================================
    // CREATE DEDICATED CHAT LAYER
    // ======================================================

    const liveShell = document.createElement("div");
    liveShell.id = "vault-live-chat";

    const chatArea = document.createElement("div");
    chatArea.id = "vault-chat-history";

    const composerHost = document.createElement("div");
    composerHost.id = "vault-composer-host";

    liveShell.appendChild(chatArea);
    liveShell.appendChild(composerHost);
    main.appendChild(liveShell);


    // ======================================================
    // INLINE ORCHESTRATION ACTIVITY
    // ======================================================

    let inlineActivityList = null;

    function renderActivity(events, targetList) {
        const list = targetList || inlineActivityList;
        if (!list) return;

        if (!events || !events.length) {
            list.innerHTML = "";
            return;
        }

        list.innerHTML = "";

        events.forEach(function(event) {
            const item = document.createElement("div");
            item.className = "vault-inline-activity-item " + (event.status || "active");

            const dot = document.createElement("div");
            dot.className = "vault-inline-activity-dot";

            const content = document.createElement("div");

            const stage = document.createElement("div");
            stage.className = "vault-inline-activity-stage";
            stage.textContent = event.stage || "WORKFLOW";

            const detail = document.createElement("div");
            detail.className = "vault-inline-activity-detail";
            detail.textContent = event.detail || "";

            const time = document.createElement("div");
            time.className = "vault-inline-activity-time";
            time.textContent = event.timestamp || "";

            content.appendChild(stage);
            if (event.detail) content.appendChild(detail);
            if (event.timestamp) content.appendChild(time);

            item.appendChild(dot);
            item.appendChild(content);
            list.appendChild(item);
        });
    }

    // ======================================================
    // HELPERS
    // ======================================================

    function cleanText(element) {

        return (element.textContent || "")
            .replace(/\s+/g, " ")
            .trim();
    }


    function hideElement(element) {

        if (!element) {
            return;
        }

        element.style.display = "none";
        element.setAttribute("data-vault-hidden", "true");
    }


    function leafElementsMatching(predicate) {

        return Array.from(
            document.querySelectorAll("body *")
        ).filter(function (element) {

            if (element.children.length !== 0) {
                return false;
            }

            return predicate(
                cleanText(element),
                element
            );
        });
    }


    function lowestCommonAncestor(elements) {

        if (!elements.length) {
            return null;
        }

        let candidate = elements[0];

        while (candidate && candidate !== document.body) {

            const containsEverything = elements.every(function (element) {
                return candidate.contains(element);
            });

            if (containsEverything) {
                return candidate;
            }

            candidate = candidate.parentElement;
        }

        return null;
    }


    function hideRecentWork() {

        const recentNames = [
            "Inspection report analysis",
            "Transformer calculation",
            "Engineering document review"
        ];

        const recentHeading = leafElementsMatching(function (text) {
            return text === "RECENT WORK";
        })[0];

        const recentViewAll = leafElementsMatching(function (text) {
            return /^VIEW ALL/i.test(text);
        })[0];

        const recentRows = recentNames
            .map(function (name) {
                return leafElementsMatching(function (text) {
                    return text === name;
                })[0];
            })
            .filter(Boolean);

        const anchors = [];

        if (recentHeading) anchors.push(recentHeading);
        if (recentViewAll) anchors.push(recentViewAll);
        recentRows.forEach(function (row) {
            anchors.push(row);
        });

        if (!anchors.length) {
            return;
        }

        let section = lowestCommonAncestor(anchors);

        /* Never hide the center workspace or anything containing
           the textarea/composer. Walk upward only while safe. */
        while (
            section &&
            section !== main &&
            (
                section.contains(textarea) ||
                section.contains(liveShell)
            )
        ) {
            section = section.parentElement;
        }

        if (
            section &&
            section !== main &&
            !section.contains(textarea) &&
            !section.contains(liveShell)
        ) {
            hideElement(section);
            return;
        }

        /*
         * If the exact section wrapper cannot be identified, hide
         * the Recent Work header row and every Recent Work row
         * independently. This deliberately targets only those
         * elements, so the composer and conversation are untouched.
         */
        [recentHeading, recentViewAll].forEach(function (element) {

            if (!element) {
                return;
            }

            const parent = element.parentElement;

            if (
                parent &&
                parent !== main &&
                !parent.contains(textarea) &&
                !parent.contains(liveShell)
            ) {
                hideElement(parent);
            } else {
                hideElement(element);
            }
        });

        recentRows.forEach(function (element) {

            const parent = element.parentElement;

            if (
                parent &&
                parent !== main &&
                !parent.contains(textarea) &&
                !parent.contains(liveShell)
            ) {
                hideElement(parent);
            } else {
                hideElement(element);
            }
        });
    }


    function hideQuickActions() {

        const names = [
            "Analyze documents",
            "Analyze visual data",
            "Run calculation",
            "Search knowledge",
            "Build code",
            "Create deliverable"
        ];

        const buttons = Array.from(
            document.querySelectorAll("button")
        ).filter(function (button) {

            const text = cleanText(button);

            return names.some(function (name) {
                return text.includes(name);
            });
        });

        if (!buttons.length) {
            return;
        }

        const section = lowestCommonAncestor(buttons);

        if (
            section &&
            section !== main &&
            !section.contains(textarea) &&
            !section.contains(liveShell)
        ) {
            hideElement(section);
            return;
        }

        buttons.forEach(hideElement);
    }


    function hideIntro() {

        const heading = leafElementsMatching(function (text) {
            return text === "What are you working on?";
        })[0];

        const subtitle = leafElementsMatching(function (text) {
            return text.includes("Tell V.A.U.L.T. what you need.");
        })[0];

        if (heading) {

            let candidate = heading.parentElement;

            while (
                candidate &&
                candidate !== main &&
                !candidate.contains(textarea) &&
                !candidate.contains(liveShell)
            ) {

                const text = cleanText(candidate);

                if (
                    text.includes("What are you working on?") &&
                    text.length < 500
                ) {
                    hideElement(candidate);
                    break;
                }

                candidate = candidate.parentElement;
            }

            if (
                !heading.closest('[data-vault-hidden="true"]')
            ) {
                hideElement(heading);
            }
        }

        if (
            subtitle &&
            !subtitle.contains(textarea) &&
            !subtitle.contains(liveShell)
        ) {
            hideElement(subtitle);
        }
    }


    // ======================================================
    // ENTER CHAT MODE
    // ======================================================

    function enterChatMode() {

        if (
            document.body.classList.contains("vault-chat-active")
        ) {
            return;
        }

        /* Remove the composer from its original layout wrapper.
           Nothing else in the original workspace is moved. */
        composerHost.appendChild(composerWrapper);

        promptCard.id = "vault-chat-composer";

        hideIntro();
        hideQuickActions();
        hideRecentWork();

        document.body.classList.add("vault-chat-active");

        requestAnimationFrame(function () {
            chatArea.scrollTop = chatArea.scrollHeight;
        });
    }


    // ======================================================
    // SEND BUTTON STATE
    // ======================================================

    function updateSendState() {

        const hasText =
            textarea.value.trim().length > 0;

        sendButton.classList.toggle(
            "vault-send-ready",
            hasText
        );
    }


    textarea.addEventListener("input", function () {

        textarea.style.height = "auto";

        textarea.style.height =
            Math.min(textarea.scrollHeight, 180) + "px";

        updateSendState();
    });

    updateSendState();


    // ======================================================
    // MESSAGE CREATION
    // ======================================================

    function createMessage(sender, message, isAgent) {

        const wrapper = document.createElement("div");

        wrapper.className = "vault-chat-message";
        wrapper.style.userSelect = "text";
        wrapper.style.webkitUserSelect = "text";

        if (isAgent) {
            wrapper.style.borderLeft =
                "2px solid rgba(56, 189, 248, 0.45)";
            wrapper.style.paddingLeft = "14px";
        }

        const header = document.createElement("div");

        header.style.display = "flex";
        header.style.alignItems = "center";
        header.style.gap = "7px";
        header.style.marginBottom = "6px";
        header.style.userSelect = "text";

        const senderElement = document.createElement("span");

        senderElement.textContent = sender;
        senderElement.style.fontSize = "11px";
        senderElement.style.fontWeight = "600";
        senderElement.style.letterSpacing = "0.08em";
        senderElement.style.textTransform = "uppercase";
        senderElement.style.color = isAgent
            ? "rgb(56, 189, 248)"
            : "rgba(255,255,255,0.65)";

        const timeElement = document.createElement("span");

        timeElement.textContent = new Date().toLocaleTimeString(
            [],
            {
                hour: "2-digit",
                minute: "2-digit"
            }
        );

        timeElement.style.fontSize = "10px";
        timeElement.style.color = "rgba(255,255,255,0.35)";

        header.appendChild(senderElement);
        header.appendChild(document.createTextNode("·"));
        header.appendChild(timeElement);

        const body = document.createElement("div");

        body.textContent = message;
        body.style.fontSize = "14px";
        body.style.lineHeight = "1.65";
        body.style.whiteSpace = "pre-wrap";
        body.style.wordBreak = "break-word";
        body.style.color = "rgba(255,255,255,0.9)";
        body.style.userSelect = "text";
        body.style.webkitUserSelect = "text";

        wrapper.appendChild(header);
        wrapper.appendChild(body);
        chatArea.appendChild(wrapper);

        chatArea.scrollTop = chatArea.scrollHeight;

        return wrapper;
    }


    function createThinkingMessage() {

        const wrapper = createMessage(
            "V.A.U.L.T.",
            "Processing request...",
            true
        );

        if (!wrapper) return wrapper;

        const activity = document.createElement("div");
        activity.className = "vault-inline-activity";

        const label = document.createElement("div");
        label.className = "vault-inline-activity-label";
        label.textContent = "System activity";

        const list = document.createElement("div");
        list.className = "vault-inline-activity-list";

        activity.appendChild(label);
        activity.appendChild(list);
        wrapper.appendChild(activity);

        inlineActivityList = list;
        renderActivity([
            {
                stage: "REQUEST RECEIVED",
                detail: "V.A.U.L.T. accepted the operator request.",
                status: "complete",
                timestamp: new Date().toLocaleTimeString()
            }
        ], list);

        return wrapper;
    }


    // ======================================================
    // SEND MESSAGE
    // ======================================================

    let sending = false;

    async function sendMessage() {

        if (sending) {
            return;
        }

        let message = textarea.value.trim();

        if (!message && !selectedFiles.length) {
            updateSendState();
            return;
        }

        if (!message && selectedFiles.length) {
            message = "Analyze the attached file(s) and provide the most relevant findings.";
        }

        sending = true;

        enterChatMode();

        createMessage(
            "Operator",
            message,
            false
        );

        textarea.value = "";
        textarea.style.height = "auto";

        /* Keep the selected File objects until FormData has been built.
           Clearing selectedFiles here would make the upload contain
           zero files even though the UI showed the attachments. */
        const filesToUpload = selectedFiles.slice();

        selectedFiles = [];
        renderAttachments();
        updateSendState();

        sendButton.disabled = true;
        sendButton.style.cursor = "wait";

        const thinking = createThinkingMessage();

        try {

            const formData = new FormData();
            formData.append("message", message);

            filesToUpload.forEach(function (file) {
                formData.append("files", file, file.name);
            });

            const response = await fetch(
                "/api/chat",
                {
                    method: "POST",
                    body: formData
                }
            );

            let data;

            try {
                data = await response.json();
            } catch (error) {
                throw new Error(
                    "The server returned an invalid response."
                );
            }

            if (!response.ok || !data.success) {
                throw new Error(
                    data.error ||
                    "V.A.U.L.T. could not start the request."
                );
            }

            const jobId = data.job_id;

            renderActivity([
                {
                    stage: "REQUEST RECEIVED",
                    detail: "V.A.U.L.T. accepted the operator request.",
                    status: "complete",
                    timestamp: new Date().toLocaleTimeString()
                },
                {
                    stage: "REQUEST QUEUED",
                    detail: "Request ID assigned and orchestration job queued.",
                    status: "active",
                    timestamp: new Date().toLocaleTimeString()
                }
            ], inlineActivityList);

            if (!jobId) {
                throw new Error(
                    "V.A.U.L.T. did not return a request ID."
                );
            }

            let finished = false;
            const pollingStartedAt = Date.now();
            const MAX_POLLING_TIME = 20 * 60 * 1000;

            while (!finished) {

                if (Date.now() - pollingStartedAt > MAX_POLLING_TIME) {
                    throw new Error(
                        "V.A.U.L.T. is taking too long to process this request. " +
                        "The upload was saved, but backend processing did not finish."
                    );
                }

                await new Promise(function (resolve) {
                    setTimeout(resolve, 500);
                });

                const statusResponse = await fetch(
                    "/api/chat/status/" +
                    encodeURIComponent(jobId),
                    {
                        method: "GET",
                        cache: "no-store"
                    }
                );

                let statusData;

                try {
                    statusData = await statusResponse.json();
                } catch (error) {
                    throw new Error(
                        "Invalid status response from V.A.U.L.T."
                    );
                }

                if (!statusResponse.ok || !statusData.success) {
                    throw new Error(
                        statusData.error ||
                        "V.A.U.L.T. request failed."
                    );
                }

                renderActivity(statusData.activity || []);

                if (statusData.status === "completed") {

                    finished = true;

                    if (thinking) {
                        thinking.remove();
                    }
                    inlineActivityList = null;

                    createMessage(
                        "V.A.U.L.T.",
                        statusData.response || "",
                        true
                    );

                } else if (statusData.status === "error") {

                    finished = true;

                    if (thinking) {
                        thinking.remove();
                    }
                    inlineActivityList = null;

                    throw new Error(
                        statusData.error ||
                        "V.A.U.L.T. backend error."
                    );
                }
            }

        } catch (error) {

            if (thinking) {
                thinking.remove();
            }

            createMessage(
                "V.A.U.L.T. ERROR",
                error.message ||
                    "Unable to communicate with the V.A.U.L.T. backend.",
                true
            );

        } finally {

            sending = false;
            sendButton.disabled = false;
            sendButton.style.cursor = "";
            updateSendState();
            textarea.focus();
        }
    }


    // ======================================================
    // SEND BUTTON
    // ======================================================

    sendButton.addEventListener(
        "click",
        function (event) {

            event.preventDefault();
            event.stopPropagation();

            sendMessage();
        },
        true
    );


    // ======================================================
    // ENTER TO SEND
    // ======================================================

    window.addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Escape") {
                closeActivity();
                return;
            }
        }
    );

    textarea.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();
                sendMessage();
            }
        }
    );


    textarea.focus();

    console.log(
        "[V.A.U.L.T.] Live chat connected."
    );

})();
</script>
"""

    if "</body>" in html:
        html = html.replace(
            "</body>",
            chat_script + "\n</body>"
        )
    else:
        html += chat_script

    return html


# ============================================================
# UPLOAD PARSING
# ============================================================

def _store_chat_attachment_in_library(user_id, safe_name, payload, mime_type):
    """Store a chat attachment in the authenticated user's Library.

    De-duplication is based on filename only. Identical content with different
    filenames remains as separate Library records; changed content under an
    existing filename replaces that filename's current record.
    """
    if not user_id:
        raise ValueError("Authenticated user is required for file uploads.")

    content_hash = hashlib.sha256(payload).hexdigest()
    file_extension = Path(safe_name).suffix.lower()
    existing = get_library_file_by_name(user_id, safe_name)

    if existing and existing.get("content_hash") == content_hash:
        existing_path = existing.get("storage_path")
        if existing_path and Path(existing_path).exists():
            return existing_path

    user_library_dir = UPLOAD_DIR / "library" / f"user_{int(user_id)}"
    user_library_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    destination = user_library_dir / stored_name
    destination.write_bytes(payload)
    destination_path = str(destination.resolve())

    if existing:
        old_path = existing.get("storage_path")
        update_library_file(
            existing["id"], user_id,
            original_name=safe_name,
            stored_name=stored_name,
            storage_path=destination_path,
            mime_type=mime_type or "",
            file_extension=file_extension,
            file_size=len(payload),
            content_hash=content_hash,
        )
        if old_path and old_path != destination_path:
            try:
                Path(old_path).unlink(missing_ok=True)
            except OSError:
                pass
        return destination_path

    record_id = add_library_file(
        user_id=user_id, original_name=safe_name, stored_name=stored_name,
        storage_path=destination_path, mime_type=mime_type or "",
        file_extension=file_extension, file_size=len(payload),
        content_hash=content_hash,
    )
    if record_id is None:
        concurrent = get_library_file_by_name(user_id, safe_name)
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        if concurrent and concurrent.get("content_hash") == content_hash:
            return concurrent.get("storage_path")
        raise ValueError(f"Unable to save '{safe_name}' to the private Library.")
    return destination_path


def _set_library_processing_state(user_id, storage_path, status, ocr_used=0, chunk_count=0):
    """Update processing metadata for one private Library file."""
    if get_connection is None or not user_id or not storage_path:
        return False

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE library_files
                SET processing_status = ?,
                    ocr_used = ?,
                    chunk_count = ?
                WHERE user_id = ? AND storage_path = ?
                """,
                (
                    str(status),
                    1 if ocr_used else 0,
                    int(chunk_count or 0),
                    int(user_id),
                    str(storage_path),
                ),
            )
            connection.commit()
            return cursor.rowcount > 0
    except Exception as error:
        print("[V.A.U.L.T.] Library processing metadata update failed:", repr(error))
        return False


def _get_library_record_by_storage_path(user_id, storage_path):
    """Return the authenticated user's Library record for a stored path."""
    if get_connection is None or not user_id or not storage_path:
        return None

    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM library_files
                WHERE user_id = ? AND storage_path = ?
                LIMIT 1
                """,
                (int(user_id), str(storage_path)),
            ).fetchone()

            if row is None:
                return None

            if hasattr(row, "keys"):
                return dict(row)

            columns = [column[0] for column in connection.execute(
                "PRAGMA table_info(library_files)"
            ).fetchall()]
            return dict(zip(columns, row))
    except Exception as error:
        print("[V.A.U.L.T.] Could not read Library processing state:", repr(error))
        return None


def _process_private_attachment(user_id, storage_path):
    """Extract/OCR, chunk, embed, and scope-index one private attachment.

    A previously completed upload is reused instead of being parsed and
    embedded again. This is important for large PPTX/PDF/image files: a
    browser timeout must not cause the same already-indexed file to be
    reprocessed on the next message.
    """
    existing = _get_library_record_by_storage_path(user_id, storage_path)

    if existing:
        existing_status = str(existing.get("processing_status", "")).lower()
        existing_chunks = int(existing.get("chunk_count") or 0)

        if (
            existing_status == "processed"
            and existing_chunks > 0
            and Path(storage_path).exists()
        ):
            return {
                "file": existing.get("original_name") or Path(storage_path).name,
                "path": str(storage_path),
                "extension": existing.get("file_extension") or Path(storage_path).suffix.lower(),
                "mime_type": existing.get("mime_type"),
                "documents": 0,
                "pages": [],
                "chunks": existing_chunks,
                "stored_chunks": existing_chunks,
                "ocr_used": bool(existing.get("ocr_used")),
                "status": "processed",
                "cached": True,
            }

    _set_library_processing_state(
        user_id,
        storage_path,
        "processing",
        ocr_used=0,
        chunk_count=0,
    )

    try:
        result = process_document(
            Path(storage_path),
            store=True,
            scope="user",
            user_id=int(user_id),
        )
    except Exception:
        _set_library_processing_state(
            user_id,
            storage_path,
            "failed",
            ocr_used=0,
            chunk_count=0,
        )
        raise

    _set_library_processing_state(
        user_id,
        storage_path,
        "processed",
        ocr_used=result.get("ocr_used", False),
        chunk_count=result.get("stored_chunks", result.get("chunks", 0)),
    )

    return result


def _get_private_source_names(user_id, storage_path):
    """Return both the stored filename and original Library filename for one attachment."""
    names = []

    stored_name = Path(storage_path).name if storage_path else ""
    if stored_name:
        names.append(stored_name)

    if get_connection is not None and user_id and storage_path:
        try:
            with get_connection() as connection:
                row = connection.execute(
                    """
                    SELECT original_name
                    FROM library_files
                    WHERE user_id = ? AND storage_path = ?
                    LIMIT 1
                    """,
                    (int(user_id), str(storage_path)),
                ).fetchone()
                if row:
                    original_name = row[0] if not hasattr(row, "keys") else row["original_name"]
                    if original_name and str(original_name) not in names:
                        names.append(str(original_name))
        except Exception as error:
            print("[V.A.U.L.T.] Could not resolve original attachment name:", repr(error))

    return names


def _retrieve_attached_file_evidence(user_id, query, attachment_paths, top_k=12):
    """Retrieve evidence ONLY from the files attached to the current request."""
    if not attachment_paths:
        return []

    # Prefer the vector store's native metadata filter. This is the important
    # distinction between ordinary RAG and file-grounded analysis.
    if KNOWLEDGE_COLLECTION is not None and embed_query is not None:
        source_names = []
        for path in attachment_paths:
            for name in _get_private_source_names(user_id, path):
                if name not in source_names:
                    source_names.append(name)

        if source_names:
            try:
                query_embedding = embed_query(query or "Explain the attached file")
                count = KNOWLEDGE_COLLECTION.count()
                if count:
                    n_results = max(1, min(int(top_k), count))
                    source_filters = [
                        {
                            "$and": [
                                {"scope": "user"},
                                {"user_id": str(int(user_id))},
                                {"source": name},
                            ]
                        }
                        for name in source_names
                    ]

                    where_filter = (
                        source_filters[0]
                        if len(source_filters) == 1
                        else {"$or": source_filters}
                    )

                    raw = KNOWLEDGE_COLLECTION.query(
                        query_embeddings=[query_embedding],
                        n_results=n_results,
                        where=where_filter,
                        include=["documents", "metadatas", "distances"],
                    )

                    documents = raw.get("documents", [[]])[0] or []
                    metadatas = raw.get("metadatas", [[]])[0] or []
                    distances = raw.get("distances", [[]])[0] or []

                    results = []
                    for index, text in enumerate(documents):
                        metadata = metadatas[index] if index < len(metadatas) else {}
                        distance = distances[index] if index < len(distances) else None
                        results.append(
                            {
                                "text": text,
                                "source": metadata.get("source", "unknown"),
                                "page": metadata.get("page"),
                                "distance": distance,
                                "scope": metadata.get("scope", "user"),
                                "user_id": metadata.get("user_id", str(user_id)),
                                "ocr_used": metadata.get("ocr_used", False),
                                "content_type": metadata.get("content_type", ""),
                            }
                        )

                    if results:
                        return results
            except Exception as error:
                print("[V.A.U.L.T.] Attachment-scoped vector retrieval failed:", repr(error))

    # Compatibility fallback: use normal authorized search, but only retain
    # chunks whose source exactly matches an attached file. This still prevents
    # unrelated documents from reaching the model.
    allowed_sources = set()
    for path in attachment_paths:
        allowed_sources.update(_get_private_source_names(user_id, path))

    try:
        broad_results = search_knowledge(
            query=query or "Explain the attached file",
            top_k=max(20, int(top_k)),
            user_id=int(user_id),
        )
    except TypeError:
        broad_results = search_knowledge(
            query=query or "Explain the attached file",
            top_k=max(20, int(top_k)),
        )

    return [
        item
        for item in broad_results
        if str(item.get("source", "")) in allowed_sources
        and str(item.get("scope", "user")) == "user"
        and str(item.get("user_id", user_id)) == str(user_id)
    ][:top_k]


def _infer_knowledge_scope(query):
    """Infer an explicit knowledge scope from the operator's wording.

    Returns ``"global"`` for shared/company KB requests, ``"user"`` for
    private/local Library requests, and ``None`` when the operator did not
    specify a scope.  Unqualified requests remain authorized across both
    scopes.
    """
    text = re.sub(r"\s+", " ", str(query or "")).strip().lower()

    private_markers = (
        "my library", "my files", "my documents", "private library",
        "private files", "private documents", "local library", "local files",
        "personal library", "personal files", "uploaded by me", "my uploaded",
    )
    global_markers = (
        "global knowledge", "global kb", "knowledge base", "company knowledge",
        "company kb", "shared knowledge", "shared kb", "organization knowledge",
        "organization kb", "corporate knowledge", "corporate kb", "all users",
    )

    if any(marker in text for marker in private_markers):
        return "user"
    if any(marker in text for marker in global_markers):
        return "global"
    return None


def _retrieve_authorized_evidence(user_id, query, top_k=4, scope=None):
    """Retrieve evidence from the correct authorized scope(s).

    Explicit scope requests are filtered after a broader authorized search so
    private and global sources can never be mixed into a scope-specific answer.
    Unqualified questions may use both Global KB and the authenticated user's
    private Library.
    """
    requested_scope = scope or _infer_knowledge_scope(query)
    search_top_k = max(int(top_k), 20) if requested_scope else int(top_k)

    try:
        results = search_knowledge(
            query=query,
            top_k=search_top_k,
            user_id=int(user_id),
        )
    except TypeError:
        results = search_knowledge(query=query, top_k=search_top_k)

    if not requested_scope:
        return results[:int(top_k)]

    filtered = []
    for item in results:
        item_scope = str(item.get("scope", "")).lower()
        if item_scope != requested_scope:
            continue
        if requested_scope == "user" and str(item.get("user_id", "")) != str(user_id):
            continue
        if requested_scope == "global" and item_scope != "global":
            continue
        filtered.append(item)

    return filtered[:int(top_k)]


def _format_rag_evidence(results, attachment_only=False):
    """Format scoped retrieval results as explicit evidence for the orchestrator."""
    if not results:
        if attachment_only:
            return (
                "ATTACHED-FILE EVIDENCE: No readable/indexed evidence was "
                "retrieved from the attached file(s). Do not use unrelated "
                "Global KB or private Library documents to answer this request. "
                "If the file content cannot be established, say so explicitly."
            )
        return (
            "AUTHORIZED V.A.U.L.T. KNOWLEDGE SEARCH RESULT: "
            "No sufficiently relevant evidence was retrieved from the "
            "authorized Global Knowledge Base or this user's private Library."
        )

    lines = [
        (
            "ATTACHED-FILE V.A.U.L.T. EVIDENCE:"
            if attachment_only
            else
            "AUTHORIZED V.A.U.L.T. KNOWLEDGE EVIDENCE:"
        ),
        (
            "These excerpts come ONLY from the file(s) attached to the current "
            "request. Ignore every other Global KB or Library source, even if "
            "it appears semantically related. Answer the user's request using "
            "the attached file content only; if the file does not contain the "
            "requested information, say that it is not present."
            if attachment_only
            else
            "The following excerpts were retrieved from the selected authorized scope. "
            "Never merge Global KB and private Library facts when the request names a specific scope. "
            "The following excerpts were retrieved from sources the authenticated "
            "operator is authorized to access. Use them as evidence; do not invent "
            "internal facts that are not supported here."
        ),
    ]

    for index, item in enumerate(results, start=1):
        source = item.get("source", "unknown")
        page = item.get("page")
        scope = item.get("scope", "unknown")
        owner = item.get("user_id", "")
        location = source if page is None else f"{source}, page {page}"
        access_label = "GLOBAL" if scope == "global" else "PRIVATE USER LIBRARY"

        lines.append(
            f"[Evidence {index}] {access_label} | {location} | "
            f"distance={item.get('distance', 'n/a')}"
        )
        if scope == "user":
            lines.append(f"Authorized owner: user {owner}")
        lines.append(str(item.get("text", "")).strip())

    lines.append(
        (
            "Evidence rule: the attached file is the sole source of truth for "
            "this request. Do not import facts, values, names, policies, or "
            "examples from any other V.A.U.L.T. document. If the attached file "
            "does not support a claim, state that clearly."
            if attachment_only
            else
            "Evidence rule: distinguish retrieved internal facts from general "
            "knowledge. If an internal claim is not supported by the retrieved "
            "evidence, do not present it as a V.A.U.L.T. fact."
        )
    )
    return "\n".join(lines)


def save_uploaded_files(handler, content_length, user_id):
    """Parse multipart chat uploads and automatically add them to User Library."""
    if content_length <= 0:
        raise ValueError("Upload request was empty.")
    if content_length > MAX_UPLOAD_SIZE:
        raise ValueError(f"Upload exceeds the {MAX_UPLOAD_SIZE // (1024 * 1024)} MB limit.")
    content_type = handler.headers.get("Content-Type", "")
    if not content_type.lower().startswith("multipart/form-data"):
        raise ValueError("Expected a multipart/form-data upload request.")
    body = handler.rfile.read(content_length)
    message = BytesParser(policy=default).parsebytes(
        (f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n").encode("utf-8") + body
    )
    text_message = ""
    saved_paths = []
    seen_names = set()
    for part in message.iter_parts():
        field_name = part.get_param("name", header="Content-Disposition")
        filename = part.get_filename()
        if field_name == "message" and not filename:
            payload = part.get_payload(decode=True) or b""
            text_message = payload.decode("utf-8", errors="replace")
            continue
        if field_name != "files" or not filename:
            continue
        safe_name = Path(filename).name.strip()
        if not safe_name:
            raise ValueError("One of the attached files has an invalid filename.")
        payload = part.get_payload(decode=True) or b""
        if len(payload) > MAX_UPLOAD_SIZE:
            raise ValueError(f"File '{safe_name}' exceeds {MAX_UPLOAD_SIZE // (1024 * 1024)} MB limit.")
        key = safe_name.casefold()
        if key in seen_names:
            raise ValueError(f"The filename '{safe_name}' is attached more than once. Please attach only one version per request.")
        seen_names.add(key)
        mime_type = part.get_content_type() or mimetypes.guess_type(safe_name)[0] or ""
        saved_paths.append(_store_chat_attachment_in_library(user_id, safe_name, payload, mime_type))
    return text_message.strip(), saved_paths


def save_library_files(handler, content_length, user_id):
    """Legacy compatibility endpoint using the same filename-based Library rules."""
    if content_length <= 0:
        raise ValueError("Upload request was empty.")
    if content_length > MAX_UPLOAD_SIZE:
        raise ValueError(f"Upload exceeds the {MAX_UPLOAD_SIZE // (1024 * 1024)} MB limit.")
    content_type = handler.headers.get("Content-Type", "")
    if not content_type.lower().startswith("multipart/form-data"):
        raise ValueError("Expected a multipart/form-data upload request.")
    body = handler.rfile.read(content_length)
    message = BytesParser(policy=default).parsebytes(
        (f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n").encode("utf-8") + body
    )
    added = []
    for part in message.iter_parts():
        filename = part.get_filename()
        if not filename:
            continue
        safe_name = Path(filename).name.strip()
        if not safe_name:
            continue
        payload = part.get_payload(decode=True) or b""
        if len(payload) > MAX_UPLOAD_SIZE:
            raise ValueError(f"File '{safe_name}' exceeds {MAX_UPLOAD_SIZE // (1024 * 1024)} MB limit.")
        mime_type = part.get_content_type() or mimetypes.guess_type(safe_name)[0] or ""
        path = _store_chat_attachment_in_library(user_id, safe_name, payload, mime_type)
        record = get_library_file_by_name(user_id, safe_name)
        added.append({"id": record["id"], "original_name": safe_name, "path": path})
    return added


# ============================================================
# AUTHENTICATION HELPERS
# ============================================================

SESSION_COOKIE_NAME = "vault_session"


def get_session_token(handler):
    cookie_header = handler.headers.get("Cookie", "")
    if not cookie_header:
        return None

    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
    except Exception:
        return None

    morsel = cookie.get(SESSION_COOKIE_NAME)
    return morsel.value if morsel else None


def get_authenticated_user(handler):
    token = get_session_token(handler)
    if not token:
        return None
    return get_session(token)


# ============================================================
# HTTP HANDLER
# ============================================================


def patch_knowledge_page(html):
    script = '<script>\n(function () {\n  const grid = document.getElementById(\'resourceGrid\');\n  const addButton = Array.from(document.querySelectorAll(\'button\')).find(b => (b.textContent || \'\').includes(\'Add to Knowledge Base\'));\n  if (!grid) return;\n\n  const input = document.createElement(\'input\');\n  input.type = \'file\'; input.multiple = true; input.style.display = \'none\';\n  document.body.appendChild(input);\n\n  const drawer = document.createElement(\'aside\');\n  drawer.id = \'inspectorDrawer\';\n  drawer.className = \'fixed top-12 right-0 bottom-7 z-50 w-full max-w-md bg-surface-container-lowest border-l border-outline-variant/40 shadow-2xl translate-x-full transition-transform duration-300 overflow-y-auto\';\n  drawer.innerHTML = `\n    <div class="p-5 border-b border-outline-variant/30 flex items-center justify-between">\n      <div><div class="font-label-micro text-outline tracking-widest">RESOURCE INSPECTOR</div><h2 id="vaultDrawerTitle" class="text-xl font-semibold text-on-surface mt-1"></h2></div>\n      <button id="vaultCloseDrawer" class="text-outline hover:text-on-surface text-xl">×</button>\n    </div>\n    <div class="p-5 space-y-5">\n      <div><span id="vaultDrawerBadge" class="font-label-micro px-2 py-1 bg-surface-container border border-outline-variant/40 text-primary rounded"></span></div>\n      <p id="vaultDrawerSummary" class="text-sm text-on-surface-variant"></p>\n      <div class="grid grid-cols-2 gap-3 text-xs">\n        <div class="p-3 bg-surface-container-low border border-outline-variant/20"><div class="text-outline">CHUNKS</div><div id="vaultDrawerChunks" class="text-on-surface mt-1">0</div></div>\n        <div class="p-3 bg-surface-container-low border border-outline-variant/20"><div class="text-outline">SIZE</div><div id="vaultDrawerSize" class="text-on-surface mt-1"></div></div>\n        <div class="p-3 bg-surface-container-low border border-outline-variant/20"><div class="text-outline">UPDATED</div><div id="vaultDrawerUpdated" class="text-on-surface mt-1"></div></div>\n        <div class="p-3 bg-surface-container-low border border-outline-variant/20"><div class="text-outline">STATUS</div><div id="vaultDrawerStatus" class="text-primary mt-1 uppercase"></div></div>\n      </div>\n      <div><div class="text-[9px] text-outline tracking-widest mb-2">SHA-256</div><div id="vaultDrawerHash" class="font-mono text-[10px] break-all text-on-surface-variant"></div></div>\n      <div><div class="text-[9px] text-outline tracking-widest mb-2">PREVIEW</div><pre id="vaultDrawerPreview" class="whitespace-pre-wrap max-h-56 overflow-auto text-xs text-on-surface-variant bg-surface-container-low p-3 border border-outline-variant/20"></pre></div>\n      <div class="flex gap-2">\n        <a id="vaultDownload" class="flex-1 text-center px-3 py-2 bg-primary-container text-on-primary-container font-semibold rounded" href="#">Download</a>\n        <button id="vaultDelete" class="px-3 py-2 border border-error/40 text-error rounded">Delete</button>\n      </div>\n    </div>`;\n  document.body.appendChild(drawer);\n  const backdrop = document.getElementById(\'inspectorBackdrop\');\n\n  let resources = [];\n  let activeFilter = \'All\';\n  let activeSort = \'Recently added\';\n  let query = \'\';\n  let selected = null;\n\n  const esc = value => String(value ?? \'\').replace(/[&<>\'"]/g, c => ({\'&\':\'&amp;\',\'<\':\'&lt;\',\'>\':\'&gt;\',"\'":\'&#39;\',\'"\':\'&quot;\'}[c]));\n  const typeFor = r => {\n    const ext = (r.file_extension || \'\').toLowerCase();\n    if ([\'.jpg\',\'.jpeg\',\'.png\',\'.gif\',\'.bmp\',\'.webp\',\'.svg\',\'.tif\',\'.tiff\'].includes(ext)) return \'IMAGES\';\n    if ([\'.csv\',\'.xlsx\',\'.xls\',\'.parquet\'].includes(ext)) return \'DATA\';\n    if ([\'.py\',\'.js\',\'.ts\',\'.java\',\'.cpp\',\'.c\',\'.h\',\'.css\',\'.html\',\'.sql\',\'.json\'].includes(ext)) return \'CODE\';\n    if ([\'.pdf\',\'.doc\',\'.docx\',\'.txt\',\'.md\',\'.rtf\'].includes(ext)) return \'DOCUMENTS\';\n    return \'KNOWLEDGE\';\n  };\n  const sizeFor = n => { n=Number(n||0); if(n<1024) return n+\' B\'; if(n<1024*1024) return (n/1024).toFixed(1)+\' KB\'; if(n<1024*1024*1024) return (n/1024/1024).toFixed(1)+\' MB\'; return (n/1024/1024/1024).toFixed(2)+\' GB\'; };\n  const dateFor = s => { try { return new Date(s).toLocaleString(); } catch (_) { return s || \'\'; } };\n\n  function filtered() {\n    let list = resources.filter(r => {\n      const t = (r.original_name+\' \'+(r.summary||\'\')+\' \'+(r.preview||\'\')).toLowerCase();\n      return (!query || t.includes(query.toLowerCase())) && (activeFilter === \'All\' || typeFor(r) === activeFilter.toUpperCase());\n    });\n    if (activeSort === \'Alphabetical\') list.sort((a,b)=>a.original_name.localeCompare(b.original_name));\n    else if (activeSort === \'Recently used\') list.sort((a,b)=>String(b.updated_at).localeCompare(String(a.updated_at)));\n    else list.sort((a,b)=>String(b.added_at).localeCompare(String(a.added_at)));\n    return list;\n  }\n\n  function render() {\n    const list = filtered();\n    grid.innerHTML = list.length ? list.map(r => `\n      <article class="resource-card cursor-pointer border border-outline-variant/30 bg-surface-container-low/75 hover:border-primary/60 hover:bg-surface-container/80 transition-all p-4" data-id="${r.id}">\n        <div class="flex items-start justify-between gap-3"><div class="w-10 h-10 bg-surface-container-high border border-outline-variant/30 flex items-center justify-center text-primary font-mono">${esc((r.file_extension||\'FILE\').replace(\'.\',\'\').slice(0,4).toUpperCase())}</div><span class="inspecting-badge hidden font-label-micro text-primary">INSPECTING</span></div>\n        <div class="mt-4"><div class="card-title text-on-surface font-semibold truncate" title="${esc(r.original_name)}">${esc(r.original_name)}</div><div class="mt-1 text-[10px] text-outline uppercase tracking-wider">${esc(typeFor(r))} // ${esc(r.processing_status || \'pending\')}</div></div>\n        <p class="mt-3 text-xs leading-5 text-on-surface-variant line-clamp-3">${esc(r.summary || \'Global Knowledge Base resource.\')}</p>\n        <div class="mt-4 pt-3 border-t border-outline-variant/20 flex justify-between text-[9px] text-outline font-mono"><span>${sizeFor(r.file_size)}</span><span>${Number(r.chunk_count||0)} CHUNKS</span></div>\n      </article>`).join(\'\') : \'<div class="col-span-full border border-dashed border-outline-variant/30 p-10 text-center text-sm text-outline">NO GLOBAL KNOWLEDGE RESOURCES</div>\';\n    grid.querySelectorAll(\'.resource-card\').forEach(card => card.addEventListener(\'click\', () => openDrawer(Number(card.dataset.id))));\n  }\n\n  async function load() {\n    try { const res = await fetch(\'/api/knowledge\', {credentials:\'same-origin\'}); const data = await res.json(); if (!res.ok || !data.success) throw new Error(data.error || \'Unable to load Knowledge Base.\'); resources = data.resources || []; render(); }\n    catch (e) { grid.innerHTML = `<div class="col-span-full border border-error/30 p-8 text-center text-error">${esc(e.message)}</div>`; }\n  }\n\n  function openDrawer(id) {\n    selected = resources.find(r=>Number(r.id)===id); if (!selected) return;\n    document.getElementById(\'vaultDrawerTitle\').textContent = selected.original_name;\n    document.getElementById(\'vaultDrawerBadge\').textContent = typeFor(selected) + \' // \' + (selected.file_extension || \'FILE\').toUpperCase();\n    document.getElementById(\'vaultDrawerSummary\').textContent = selected.summary || \'\';\n    document.getElementById(\'vaultDrawerChunks\').textContent = selected.chunk_count || 0;\n    document.getElementById(\'vaultDrawerSize\').textContent = sizeFor(selected.file_size);\n    document.getElementById(\'vaultDrawerUpdated\').textContent = dateFor(selected.updated_at);\n    document.getElementById(\'vaultDrawerStatus\').textContent = selected.processing_status || \'pending\';\n    document.getElementById(\'vaultDrawerHash\').textContent = selected.content_hash || \'\';\n    document.getElementById(\'vaultDrawerPreview\').textContent = selected.preview || \'Preview will be populated by the ingestion pipeline.\';\n    document.getElementById(\'vaultDownload\').href = selected.download_url;\n    drawer.classList.remove(\'translate-x-full\'); drawer.classList.add(\'translate-x-0\');\n    backdrop.classList.remove(\'opacity-0\',\'pointer-events-none\'); backdrop.classList.add(\'opacity-100\',\'pointer-events-auto\');\n  }\n  function closeDrawer() { drawer.classList.remove(\'translate-x-0\'); drawer.classList.add(\'translate-x-full\'); backdrop.classList.remove(\'opacity-100\',\'pointer-events-auto\'); backdrop.classList.add(\'opacity-0\',\'pointer-events-none\'); selected=null; }\n\n  if (addButton) addButton.addEventListener(\'click\', () => input.click());\n  input.addEventListener(\'change\', async () => {\n    if (!input.files.length) return;\n    const form = new FormData(); Array.from(input.files).forEach(f=>form.append(\'files\', f));\n    if (addButton) { addButton.disabled=true; addButton.style.opacity=\'.6\'; }\n    try { const res=await fetch(\'/api/knowledge/upload\',{method:\'POST\',body:form,credentials:\'same-origin\'}); const data=await res.json(); if(!res.ok || !data.success) throw new Error(data.error||\'Upload failed.\'); resources=data.resources||[]; render(); }\n    catch(e) { alert(e.message); }\n    finally { input.value=\'\'; if(addButton){addButton.disabled=false;addButton.style.opacity=\'\';} }\n  });\n  document.getElementById(\'vaultCloseDrawer\').addEventListener(\'click\',closeDrawer);\n  backdrop.addEventListener(\'click\',closeDrawer);\n  document.getElementById(\'vaultDelete\').addEventListener(\'click\', async () => {\n    if (!selected || !confirm(\'Remove this resource from the global Knowledge Base?\')) return;\n    const res=await fetch(\'/api/knowledge/delete\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({id:selected.id}),credentials:\'same-origin\'}); const data=await res.json(); if(!res.ok||!data.success){alert(data.error||\'Delete failed.\');return;} closeDrawer(); await load();\n  });\n  window.addEventListener(\'keydown\',e=>{if(e.key===\'Escape\')closeDrawer();});\n\n  const search = document.querySelector(\'input[placeholder="Search your knowledge base..."]\');\n  if(search) search.addEventListener(\'input\',()=>{query=search.value;render();});\n  const filterButtons = Array.from(document.querySelectorAll(\'button\')).filter(b=>[\'All\',\'Documents\',\'Knowledge\',\'Images\',\'Data\',\'Code\'].includes((b.textContent||\'\').trim()));\n  filterButtons.forEach(b=>b.addEventListener(\'click\',()=>{activeFilter=b.textContent.trim();filterButtons.forEach(x=>x.classList.remove(\'bg-primary\',\'text-on-primary\'));b.classList.add(\'bg-primary\',\'text-on-primary\');render();}));\n  const sortButtons = Array.from(document.querySelectorAll(\'button\')).filter(b=>[\'Recently added\',\'Recently used\',\'Alphabetical\'].includes((b.textContent||\'\').trim()));\n  sortButtons.forEach(b=>b.addEventListener(\'click\',()=>{activeSort=b.textContent.trim();sortButtons.forEach(x=>x.classList.remove(\'text-primary\'));b.classList.add(\'text-primary\');render();}));\n  load();\n})();\n</script>'
    # The original page already contains a placeholder inspector script; remove it so
    # it cannot dereference the dynamically-created drawer before our live script runs.
    html = re.sub(r"<script>\s*\(function\s*\(\)\s*\{\s*const drawer = document\.getElementById\('inspectorDrawer'\).*?</script>", "", html, count=1, flags=re.S)
    return html.replace("</body>", script + "\n</body>")


class VaultHandler(BaseHTTPRequestHandler):


    # --------------------------------------------------------
    # Terminal logging
    # --------------------------------------------------------

    def log_message(self, format, *args):

        print(
            "[V.A.U.L.T.]",
            format % args,
        )


    # --------------------------------------------------------
    # Send HTML
    # --------------------------------------------------------

    def send_html(
        self,
        html,
        status=200,
    ):

        encoded = html.encode(
            "utf-8"
        )

        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(encoded)),
        )

        self.send_header(
            "Cache-Control",
            "no-cache, no-store, must-revalidate",
        )

        self.send_header(
            "Pragma",
            "no-cache",
        )

        self.send_header(
            "Expires",
            "0",
        )

        self.end_headers()

        self.wfile.write(
            encoded
        )


    # --------------------------------------------------------
    # Send JSON
    # --------------------------------------------------------

    def send_json(
        self,
        payload,
        status=200,
        extra_headers=None,
    ):

        encoded = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(encoded)),
        )

        self.send_header(
            "Cache-Control",
            "no-cache, no-store, must-revalidate",
        )

        for header_name, header_value in (extra_headers or {}).items():
            self.send_header(header_name, header_value)

        self.end_headers()

        self.wfile.write(encoded)


    # --------------------------------------------------------
    # 404
    # --------------------------------------------------------

    def send_not_found(self):

        self.send_html(
            """
<!DOCTYPE html>

<html>

<head>

    <meta charset="UTF-8">

    <title>
        V.A.U.L.T. - 404
    </title>

    <style>

        body {
            margin: 0;
            height: 100vh;

            display: flex;
            align-items: center;
            justify-content: center;

            background: #050505;
            color: white;

            font-family: Arial, sans-serif;
        }

        .container {
            text-align: center;
        }

        a {
            color: white;
        }

    </style>

</head>

<body>

    <div class="container">

        <h1>404</h1>

        <p>
            V.A.U.L.T. route not found.
        </p>

        <a href="/">
            Return to V.A.U.L.T.
        </a>

    </div>

</body>

</html>
            """,
            status=404,
        )


    # ========================================================
    # AUTH GUARD
    # ========================================================

    def require_auth_page(self):
        user = get_authenticated_user(self)
        if user is not None:
            return user

        self.send_response(302)
        self.send_header("Location", "/login")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        return None


    def require_auth_api(self):
        user = get_authenticated_user(self)
        if user is not None:
            return user

        self.send_json(
            {
                "success": False,
                "error": "Authentication required.",
            },
            status=401,
        )
        return None


    # ========================================================
    # GET
    # ========================================================


    def do_GET(self):

        parsed_url = urlparse(
            self.path
        )

        route = (
            parsed_url.path.rstrip("/")
            or "/"
        )


        # ----------------------------------------------------
        # BACKEND STATUS
        # ----------------------------------------------------

        if route == "/api/status":

            if vault is None:

                self.send_json(
                    {
                        "success": False,
                        "backend": "offline",
                        "error": str(VAULT_INIT_ERROR),
                    },
                    status=500,
                )

                return

            self.send_json(
                {
                    "success": True,
                    "backend": "online",
                }
            )

            return


        # ----------------------------------------------------
        # USER LIBRARY
        # ----------------------------------------------------

        if route == "/api/library":
            user = self.require_auth_api()
            if user is None:
                return
            self.handle_library_list(user)
            return


        # ----------------------------------------------------
        # GLOBAL KNOWLEDGE BASE
        # ----------------------------------------------------

        if route == "/api/knowledge":
            user = self.require_auth_api()
            if user is None:
                return
            self.handle_knowledge_list()
            return

        if route.startswith("/api/knowledge/") and route.endswith("/download"):
            user = self.require_auth_api()
            if user is None:
                return
            try:
                file_id = int(route.split("/api/knowledge/", 1)[1].rsplit("/download", 1)[0])
            except (ValueError, TypeError):
                self.send_json({"success": False, "error": "Invalid Knowledge Base file ID."}, status=400)
                return
            self.handle_knowledge_download(file_id)
            return

        # ----------------------------------------------------
        # CHAT JOB STATUS
        # ----------------------------------------------------

        if route.startswith("/api/chat/status/"):
            user = self.require_auth_api()
            if user is None:
                return


            job_id = route.split(
                "/api/chat/status/",
                1
            )[1]

            self.handle_chat_status(
                job_id,
                user,
            )

            return


        # ----------------------------------------------------
        # HTML PAGE
        # ----------------------------------------------------

        if route in PAGES:

            if route not in {"/", "/landing", "/login"}:
                if self.require_auth_page() is None:
                    return

            filename = PAGES[
                route
            ]

            file_path = (
                FRONTEND_DIR / filename
            )


            # ------------------------------------------------
            # Missing file
            # ------------------------------------------------

            if not file_path.exists():

                self.send_html(
                    f"""
<!DOCTYPE html>

<html>

<head>

    <meta charset="UTF-8">

    <title>
        V.A.U.L.T. Error
    </title>

</head>

<body>

    <h1>
        V.A.U.L.T. Frontend Error
    </h1>

    <p>
        Missing file:
        <strong>{filename}</strong>
    </p>

</body>

</html>
                    """,
                    status=500,
                )

                return


            # ------------------------------------------------
            # Read HTML
            # ------------------------------------------------

            try:

                html = file_path.read_text(
                    encoding="utf-8"
                )


                # --------------------------------------------
                # Patch navigation in memory
                # --------------------------------------------

                html = patch_navigation(
                    html,
                    route,
                )


                # --------------------------------------------
                # Add live chat to Anchor only
                # --------------------------------------------

                if route == "/anchor":

                    html = patch_anchor_chat(
                        html
                    )

                if route == "/library":

                    html = patch_library_page(
                        html
                    )

                if route == "/knowledge":

                    html = patch_knowledge_page(
                        html
                    )


                # --------------------------------------------
                # Send page
                # --------------------------------------------

                self.send_html(
                    html
                )


            except Exception as error:

                self.send_html(
                    f"""
<!DOCTYPE html>

<html>

<head>

    <meta charset="UTF-8">

    <title>
        V.A.U.L.T. Error
    </title>

</head>

<body>

    <h1>
        V.A.U.L.T. Frontend Error
    </h1>

    <pre>{error}</pre>

</body>

</html>
                    """,
                    status=500,
                )

            return


        # ----------------------------------------------------
        # Favicon
        # ----------------------------------------------------

        if route == "/favicon.ico":

            self.send_response(
                204
            )

            self.end_headers()

            return


        # ----------------------------------------------------
        # Unknown route
        # ----------------------------------------------------

        self.send_not_found()


    # ========================================================
    # POST
    # ========================================================

    def do_POST(self):

        parsed_url = urlparse(self.path)

        route = (
            parsed_url.path.rstrip("/")
            or "/"
        )

        if route == "/api/login":
            self.handle_login()
            return

        if route == "/api/logout":
            self.handle_logout()
            return

        if route == "/api/library/upload":
            user = self.require_auth_api()
            if user is None:
                return
            self.handle_library_upload(user)
            return

        if route == "/api/knowledge/upload":
            user = self.require_auth_api()
            if user is None:
                return
            self.handle_knowledge_upload()
            return

        if route == "/api/knowledge/delete":
            user = self.require_auth_api()
            if user is None:
                return
            self.handle_knowledge_delete()
            return

        if route == "/api/chat":
            user = self.require_auth_api()
            if user is None:
                return
            self.handle_chat(user)
            return

        if route == "/api/clear-session":
            user = self.require_auth_api()
            if user is None:
                return
            self.handle_clear_session()
            return

        self.send_json(
            {
                "success": False,
                "error": "API route not found.",
            },
            status=404,
        )


    # ========================================================
    # GLOBAL KNOWLEDGE BASE HANDLERS
    # ========================================================

    def handle_knowledge_list(self):
        rows = get_knowledge_files()
        payload = []
        for row in rows:
            item = dict(row)
            item.pop("storage_path", None)
            item.pop("stored_name", None)
            item["download_url"] = f"/api/knowledge/{row['id']}/download"
            payload.append(item)
        self.send_json({"success": True, "resources": payload, "count": len(payload)})

    def handle_knowledge_upload(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        if content_length <= 0 or content_length > MAX_UPLOAD_SIZE + 1024 * 1024:
            self.send_json({"success": False, "error": "Invalid or oversized Knowledge Base upload."}, status=400)
            return
        content_type = self.headers.get("Content-Type", "")
        if not content_type.lower().startswith("multipart/form-data"):
            self.send_json({"success": False, "error": "Expected a multipart/form-data upload request."}, status=400)
            return
        try:
            body = self.rfile.read(content_length)
            message = BytesParser(policy=default).parsebytes(
                (f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n").encode("utf-8") + body
            )
            parts = []
            for part in message.iter_parts():
                filename = part.get_filename()
                if not filename:
                    continue
                safe_name = Path(filename).name.strip()
                if not safe_name:
                    raise ValueError("One of the files has an invalid filename.")
                payload = part.get_payload(decode=True) or b""
                if len(payload) > MAX_UPLOAD_SIZE:
                    raise ValueError(f"File '{safe_name}' exceeds {MAX_UPLOAD_SIZE // (1024 * 1024)} MB limit.")
                parts.append((safe_name, payload, part.get_content_type() or "application/octet-stream"))
            if not parts:
                raise ValueError("No file was supplied.")
            if len(parts) > 10:
                raise ValueError("A maximum of 10 files can be added at once.")
            results = []
            seen = set()
            for original_name, payload, mime_type in parts:
                key = original_name.casefold()
                if key in seen:
                    raise ValueError(f"The filename '{original_name}' is attached more than once.")
                seen.add(key)
                content_hash = hashlib.sha256(payload).hexdigest()
                existing = get_knowledge_file_by_name(original_name)
                old_path = existing.get("storage_path") if existing else None
                if existing and existing.get("content_hash") == content_hash and Path(existing.get("storage_path", "")).exists():
                    if (
                        str(existing.get("processing_status", "")).lower() == "processed"
                        and int(existing.get("chunk_count") or 0) > 0
                    ):
                        results.append({
                            "id": existing["id"],
                            "name": original_name,
                            "action": "unchanged",
                            "processing_status": "processed",
                            "ocr_used": bool(existing.get("ocr_used")),
                            "chunk_count": int(existing.get("chunk_count") or 0),
                        })
                        continue

                    # Existing bytes are present, but ingestion was incomplete.
                    file_id = existing["id"]
                    target = Path(existing["storage_path"])
                    try:
                        processing_result = process_document(
                            target,
                            store=True,
                            scope="global",
                            user_id=None,
                            source_name=original_name,
                        )
                        update_knowledge_file(
                            file_id,
                            processing_status="processed",
                            ocr_used=1 if processing_result.get("ocr_used") else 0,
                            chunk_count=int(
                                processing_result.get(
                                    "stored_chunks",
                                    processing_result.get("chunks", 0),
                                )
                            ),
                        )
                        results.append({
                            "id": file_id,
                            "name": original_name,
                            "action": "processed",
                            "processing_status": "processed",
                            "ocr_used": bool(processing_result.get("ocr_used")),
                            "chunk_count": int(
                                processing_result.get(
                                    "stored_chunks",
                                    processing_result.get("chunks", 0),
                                )
                            ),
                        })
                    except Exception as processing_error:
                        update_knowledge_file(
                            file_id,
                            processing_status="failed",
                            ocr_used=0,
                            chunk_count=0,
                        )
                        results.append({
                            "id": file_id,
                            "name": original_name,
                            "action": "processed",
                            "processing_status": "failed",
                            "error": str(processing_error),
                        })
                    continue
                stored_name = f"{uuid.uuid4().hex}{Path(original_name).suffix}"
                target = KNOWLEDGE_DIR / stored_name
                target.write_bytes(payload)
                suffix = Path(original_name).suffix.lower()
                summary = "Global Knowledge Base resource. Ready for ingestion."
                preview = ""
                if mime_type.startswith("text/") or suffix in {".txt", ".md", ".csv", ".json", ".xml", ".log", ".py", ".js", ".html", ".css"}:
                    preview = payload[:1200].decode("utf-8", errors="replace").strip()
                    if preview:
                        summary = "Text resource stored locally; ingestion metadata is ready for the RAG pipeline."
                if existing:
                    update_knowledge_file(existing["id"], stored_name=stored_name, storage_path=str(target), mime_type=mime_type, file_extension=suffix, file_size=len(payload), content_hash=content_hash, processing_status="pending", ocr_used=0, chunk_count=0, summary=summary, preview=preview)
                    file_id = existing["id"]
                    action = "replaced"
                else:
                    file_id = add_knowledge_file(original_name, stored_name, str(target), mime_type, suffix, len(payload), content_hash, summary, preview)
                    action = "added"
                if old_path and old_path != str(target):
                    try:
                        Path(old_path).unlink(missing_ok=True)
                    except OSError:
                        pass

                # Immediately ingest the shared Global Knowledge Base resource.
                try:
                    processing_result = process_document(
                        target,
                        store=True,
                        scope="global",
                        user_id=None,
                        source_name=original_name,
                    )

                    update_knowledge_file(
                        file_id,
                        processing_status="processed",
                        ocr_used=1 if processing_result.get("ocr_used") else 0,
                        chunk_count=int(
                            processing_result.get(
                                "stored_chunks",
                                processing_result.get("chunks", 0),
                            )
                        ),
                    )

                    results.append({
                        "id": file_id,
                        "name": original_name,
                        "action": action,
                        "processing_status": "processed",
                        "ocr_used": bool(processing_result.get("ocr_used")),
                        "chunk_count": int(
                            processing_result.get(
                                "stored_chunks",
                                processing_result.get("chunks", 0),
                            )
                        ),
                    })
                except Exception as processing_error:
                    update_knowledge_file(
                        file_id,
                        processing_status="failed",
                        ocr_used=0,
                        chunk_count=0,
                    )
                    results.append({
                        "id": file_id,
                        "name": original_name,
                        "action": action,
                        "processing_status": "failed",
                        "error": str(processing_error),
                    })

            rows = get_knowledge_files()
            resources = []
            for row in rows:
                item = dict(row)
                item.pop("storage_path", None)
                item.pop("stored_name", None)
                item["download_url"] = f"/api/knowledge/{row['id']}/download"
                resources.append(item)
            self.send_json({"success": True, "results": results, "resources": resources})
        except Exception as error:
            self.send_json({"success": False, "error": str(error)}, status=400)

    def handle_knowledge_download(self, file_id):
        row = get_knowledge_file(file_id)
        if row is None:
            self.send_json({"success": False, "error": "Knowledge Base resource not found."}, status=404)
            return
        path = Path(row["storage_path"])
        if not path.exists() or not path.is_file():
            self.send_json({"success": False, "error": "Stored Knowledge Base file is missing."}, status=404)
            return
        try:
            data = path.read_bytes()
            from urllib.parse import quote
            self.send_response(200)
            self.send_header("Content-Type", row.get("mime_type") or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(row['original_name'])}")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(data)
        except Exception as error:
            self.send_json({"success": False, "error": str(error)}, status=500)

    def handle_knowledge_delete(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(content_length).decode("utf-8"))
            file_id = int(data.get("id"))
        except Exception:
            self.send_json({"success": False, "error": "Invalid Knowledge Base delete request."}, status=400)
            return
        storage_path = delete_knowledge_file(file_id)
        if storage_path is None:
            self.send_json({"success": False, "error": "Knowledge Base resource not found."}, status=404)
            return
        try:
            Path(storage_path).unlink(missing_ok=True)
        except OSError:
            pass
        self.send_json({"success": True, "deleted": file_id})

    # ========================================================
    # HANDLE LOGIN
    # ========================================================

    def handle_login(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0

        if content_length <= 0 or content_length > 1024 * 1024:
            self.send_json(
                {"success": False, "error": "Invalid login request."},
                status=400,
            )
            return

        try:
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_json(
                {"success": False, "error": "Invalid JSON login request."},
                status=400,
            )
            return

        operator_id = str(data.get("operator_id", "")).strip()
        password = str(data.get("password", ""))

        if not operator_id or not password:
            self.send_json(
                {"success": False, "error": "Operator ID and security key are required."},
                status=400,
            )
            return

        user = authenticate_user(operator_id, password)
        if user is None:
            self.send_json(
                {"success": False, "error": "Invalid operator ID or security key."},
                status=401,
            )
            return

        old_token = get_session_token(self)
        if old_token:
            destroy_session(old_token)

        token = create_session(user)
        cookie = (
            f"{SESSION_COOKIE_NAME}={token}; "
            "Path=/; HttpOnly; SameSite=Lax"
        )

        self.send_json(
            {
                "success": True,
                "message": "Authentication successful.",
                "user": {
                    "operator_id": user["operator_id"],
                    "name": user["name"],
                    "role": user["role"],
                    "organization": user["organization"],
                },
            },
            status=200,
            extra_headers={"Set-Cookie": cookie},
        )


    # ========================================================
    # HANDLE LOGOUT
    # ========================================================

    def handle_logout(self):
        token = get_session_token(self)
        if token:
            destroy_session(token)

        expired_cookie = (
            f"{SESSION_COOKIE_NAME}=; Path=/; HttpOnly; "
            "SameSite=Lax; Max-Age=0"
        )

        self.send_json(
            {"success": True},
            extra_headers={"Set-Cookie": expired_cookie},
        )


    # ========================================================
    # HANDLE USER LIBRARY
    # ========================================================

    def handle_library_list(self, user):
        try:
            files = get_library_files(int(user["user_id"]))
            self.send_json(
                {
                    "success": True,
                    "files": files,
                }
            )
        except Exception as error:
            self.send_json(
                {
                    "success": False,
                    "error": str(error),
                },
                status=500,
            )


    def handle_library_upload(self, user):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0

        try:
            added, skipped = save_library_files(
                self,
                content_length,
                user["user_id"],
            )

            self.send_json(
                {
                    "success": True,
                    "added": added,
                    "skipped": skipped,
                },
                status=201 if added else 200,
            )
        except Exception as error:
            self.send_json(
                {
                    "success": False,
                    "error": str(error),
                },
                status=400,
            )


    # ========================================================
    # HANDLE CHAT
    # ========================================================

    def handle_chat(self, user):

        if vault is None:

            self.send_json(
                {
                    "success": False,
                    "error":
                        "V.A.U.L.T. backend failed to initialize: "
                        + str(VAULT_INIT_ERROR),
                },
                status=500,
            )

            return

        try:
            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )

            message, attachment_paths = save_uploaded_files(
                self,
                content_length,
                user["user_id"],
            )

        except Exception as error:
            self.send_json(
                {
                    "success": False,
                    "error": "Invalid upload request: " + str(error),
                },
                status=400,
            )

            return

        if not message and attachment_paths:
            message = "Analyze the attached file(s) and provide the most relevant findings."

        if not message:
            self.send_json(
                {
                    "success": False,
                    "error": "Message cannot be empty.",
                },
                status=400,
            )

            return

        try:
            job_id = start_chat_job(
                message,
                attachment_paths=attachment_paths,
                user_id=user["user_id"],
            )

        except Exception as error:
            self.send_json(
                {
                    "success": False,
                    "error": str(error),
                },
                status=500,
            )

            return

        self.send_json(
            {
                "success": True,
                "job_id": job_id,
                "status": "queued",
                "attachments": [
                    Path(path).name
                    for path in attachment_paths
                ],
            },
            status=202,
        )


    # ========================================================
    # CHAT JOB STATUS
    # ========================================================

    def handle_chat_status(self, job_id, user):

        with CHAT_JOBS_LOCK:
            job = CHAT_JOBS.get(job_id)

            if job is None:
                job = None
            else:
                job = dict(job)


        if job is None:

            self.send_json(
                {
                    "success": False,
                    "error":
                        "V.A.U.L.T. request ID not found.",
                },
                status=404,
            )

            return


        if job.get("user_id") != user.get("user_id"):
            self.send_json(
                {
                    "success": False,
                    "error": "V.A.U.L.T. request ID not found.",
                },
                status=404,
            )
            return


        status = job["status"]


        if status == "completed":

            self.send_json(
                {
                    "success": True,
                    "status": "completed",
                    "response": job["response"] or "",
                    "activity": job.get("activity", []),
                }
            )

            return


        if status == "error":

            self.send_json(
                {
                    "success": False,
                    "status": "error",
                    "error":
                        job["error"] or
                        "Unknown V.A.U.L.T. backend error.",
                    "activity": job.get("activity", []),
                },
                status=500,
            )

            return


        self.send_json(
            {
                "success": True,
                "status": status,
                "activity": job.get("activity", []),
            }
        )


    # ========================================================
    # HANDLE CLEAR SESSION
    # ========================================================

    def handle_clear_session(self):

        if vault is None:

            self.send_json(
                {
                    "success": False,
                    "error":
                        "V.A.U.L.T. backend is unavailable.",
                },
                status=500,
            )

            return

        try:

            vault.clear_session()

            self.send_json(
                {
                    "success": True,
                }
            )

        except Exception as error:

            self.send_json(
                {
                    "success": False,
                    "error": str(error),
                },
                status=500,
            )


# ============================================================
# START SERVER
# ============================================================

def main():

    server = ThreadingHTTPServer(
        (
            "127.0.0.1",
            PORT,
        ),
        VaultHandler,
    )


    print()
    print("=" * 60)
    print("              V.A.U.L.T. FRONTEND")
    print("=" * 60)
    print()

    print(
        "Server running at:"
    )

    print(
        f"  http://127.0.0.1:{PORT}"
    )

    print()

    print(
        "Available routes:"
    )

    print(
        "  /          -> Landing"
    )

    print(
        "  /login     -> Login"
    )

    print(
        "  /anchor    -> Anchor Workspace"
    )

    print(
        "  /analysis  -> Analysis"
    )

    print(
        "  /library   -> Library"
    )

    print(
        "  /security  -> Security"
    )

    print(
        "  /knowledge -> Global Knowledge Base"
    )

    print()

    print(
        "API:"
    )

    print(
        "  GET  /api/status"
    )

    print(
        "  POST /api/chat"
    )

    print(
        "  POST /api/clear-session"
    )

    print()

    if vault is None:

        print(
            "[WARNING] V.A.U.L.T. backend failed to initialize."
        )

        print(
            f"[WARNING] {VAULT_INIT_ERROR}"
        )

    else:

        print(
            "[V.A.U.L.T.] Backend initialized successfully."
        )

    print()

    print(
        "Press CTRL+C to stop."
    )

    print("=" * 60)
    print()


    try:

        server.serve_forever()

    except KeyboardInterrupt:

        print()
        print(
            "Stopping V.A.U.L.T. frontend..."
        )

    finally:

        server.server_close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()