from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import sys
import re
import json
import html as html_module
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.orchestrator import Orchestrator


# ============================================================
# V.A.U.L.T. FRONTEND WEB SERVER
# ============================================================

FRONTEND_DIR = Path(__file__).resolve().parent
PORT = 8000


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


def start_chat_job(message):
    """Run the existing Orchestrator asynchronously."""

    job_id = uuid.uuid4().hex

    with CHAT_JOBS_LOCK:
        CHAT_JOBS[job_id] = {
            "status": "queued",
            "response": None,
            "error": None,
        }

    def run_job():
        with CHAT_JOBS_LOCK:
            CHAT_JOBS[job_id]["status"] = "processing"

        try:
            result = vault.run(message)

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
    # LOGIN FORM
    # ========================================================

    html = re.sub(
        r'onsubmit\s*=\s*["\']\s*event\.preventDefault\(\)\s*;?\s*["\']',
        'onsubmit="window.location.href=\'/anchor\'; return false;"',
        html,
        flags=re.IGNORECASE,
    )


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
            // LOGIN -> ANCHOR
            // =================================================

            if (
                text.includes("enter v.a.u.l.t")
            ) {

                event.preventDefault();
                event.stopPropagation();

                window.location.href = "/anchor";

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
                text.includes("files") ||
                text.includes("library")
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

        const message = textarea.value.trim();

        if (!message) {
            updateSendState();
            return;
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
        updateSendState();

        sendButton.disabled = true;
        sendButton.style.cursor = "wait";

        const thinking = createThinkingMessage();

        try {

            const response = await fetch(
                "/api/chat",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        message: message
                    })
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

            while (!finished) {

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
# HTTP HANDLER
# ============================================================

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
        # CHAT JOB STATUS
        # ----------------------------------------------------

        if route.startswith("/api/chat/status/"):

            job_id = route.split(
                "/api/chat/status/",
                1
            )[1]

            self.handle_chat_status(
                job_id
            )

            return


        # ----------------------------------------------------
        # HTML PAGE
        # ----------------------------------------------------

        if route in PAGES:

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

        if route == "/api/chat":
            self.handle_chat()
            return

        if route == "/api/clear-session":
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
    # HANDLE CHAT
    # ========================================================

    def handle_chat(self):

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

            body = self.rfile.read(
                content_length
            )

            data = json.loads(
                body.decode("utf-8")
            )

        except Exception as error:

            self.send_json(
                {
                    "success": False,
                    "error":
                        "Invalid JSON request: "
                        + str(error),
                },
                status=400,
            )

            return


        message = data.get(
            "message"
        )


        if not isinstance(
            message,
            str,
        ):

            self.send_json(
                {
                    "success": False,
                    "error":
                        "The request must contain a string "
                        "field named 'message'.",
                },
                status=400,
            )

            return


        message = message.strip()


        if not message:

            self.send_json(
                {
                    "success": False,
                    "error":
                        "Message cannot be empty.",
                },
                status=400,
            )

            return


        job_id = start_chat_job(
            message
        )


        self.send_json(
            {
                "success": True,
                "job_id": job_id,
                "status": "queued",
            },
            status=202,
        )


    # ========================================================
    # CHAT JOB STATUS
    # ========================================================

    def handle_chat_status(self, job_id):

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