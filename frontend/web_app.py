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

CHAT_EXECUTOR = ThreadPoolExecutor(max_workers=1)
CHAT_JOBS = {}
CHAT_JOBS_LOCK = threading.Lock()


# These requests do not need a model call. Handling them locally means
# a slow/stuck document job cannot make a simple greeting wait in the
# single-worker queue.
FAST_GREETING_RESPONSES = {
    "hi": "Hello! How can I assist you today?",
    "hello": "Hello! How can I assist you today?",
    "hey": "Hey! How can I assist you today?",
    "hey vault": "Hello! How can I assist you today?",
    "hi vault": "Hello! How can I assist you today?",
    "hello vault": "Hello! How can I assist you today?",
}


def start_chat_job(message, attachment_paths=None, user_id=None):
    """Run the existing Orchestrator asynchronously with local file references."""

    attachment_paths = attachment_paths or []
    job_id = uuid.uuid4().hex

    with CHAT_JOBS_LOCK:
        CHAT_JOBS[job_id] = {
            "status": "queued",
            "response": None,
            "error": None,
            "user_id": user_id,
        }

    # --------------------------------------------------------
    # FAST PATH FOR SIMPLE GREETINGS
    # --------------------------------------------------------
    #
    # Only use this when there are no attachments. A message such
    # as "hi" should not wait for the local LLM, and it should not
    # wait behind a long-running file-analysis request.
    #
    # We intentionally keep this list narrow so normal questions
    # continue through the existing V.A.U.L.T. Orchestrator.

    normalized_message = (
        message.strip().lower()
        if isinstance(message, str)
        else ""
    )

    if (
        not attachment_paths
        and normalized_message in FAST_GREETING_RESPONSES
    ):

        with CHAT_JOBS_LOCK:
            CHAT_JOBS[job_id]["status"] = "completed"
            CHAT_JOBS[job_id]["response"] = (
                FAST_GREETING_RESPONSES[normalized_message]
            )

        return job_id

    def run_job():
        with CHAT_JOBS_LOCK:
            CHAT_JOBS[job_id]["status"] = "processing"

        try:
            backend_task = message

            if attachment_paths:
                attachment_lines = [
                    "\n\nThe user attached the following local file(s). "
                    "Treat them as references for this request. "
                    "Use the available document tools (read_document, "
                    "document_info, search_document, document_summary) "
                    "when you need their contents. Do not invent file contents.",
                ]

                for path in attachment_paths:
                    attachment_lines.append(
                        f"- {Path(path).name}: {path}"
                    )

                backend_task += "\n" + "\n".join(attachment_lines)

            result = vault.run(backend_task)

            if result is None:
                result = ""

            result = str(result)

            with CHAT_JOBS_LOCK:
                CHAT_JOBS[job_id]["status"] = "completed"
                CHAT_JOBS[job_id]["response"] = result

        except Exception as error:
            print(
                "[V.A.U.L.T.] Backend error:",
                repr(error),
            )

            with CHAT_JOBS_LOCK:
                CHAT_JOBS[job_id]["status"] = "error"
                CHAT_JOBS[job_id]["error"] = str(error)

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

        return createMessage(
            "V.A.U.L.T.",
            "Processing request...",
            true
        );
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

            if (!jobId) {
                throw new Error(
                    "V.A.U.L.T. did not return a request ID."
                );
            }

            let finished = false;
            const pollingStartedAt = Date.now();
            const MAX_POLLING_TIME = 5 * 60 * 1000;

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

                if (statusData.status === "completed") {

                    finished = true;

                    if (thinking) {
                        thinking.remove();
                    }

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
                    results.append({"id": existing["id"], "name": original_name, "action": "unchanged"})
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
                results.append({"id": file_id, "name": original_name, "action": action})
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
                },
                status=500,
            )

            return


        self.send_json(
            {
                "success": True,
                "status": status,
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