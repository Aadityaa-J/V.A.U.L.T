from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import re
import json
import html as html_module

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

                window.location.href = "/anchor";

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

    const promptCard = textarea.parentElement;

    if (!promptCard) {
        return;
    }

    const chatArea = document.createElement("div");

    chatArea.id = "vault-chat-history";
    chatArea.style.width = "100%";
    chatArea.style.maxWidth = "760px";
    chatArea.style.margin = "0 auto";
    chatArea.style.padding = "0 24px 18px 24px";
    chatArea.style.boxSizing = "border-box";
    chatArea.style.display = "flex";
    chatArea.style.flexDirection = "column";
    chatArea.style.gap = "18px";
    chatArea.style.maxHeight = "45vh";
    chatArea.style.overflowY = "auto";

    promptCard.parentNode.insertBefore(chatArea, promptCard);

    const params = new URLSearchParams(window.location.search);

    if (params.get("new_task") === "1") {
        chatArea.innerHTML = "";
        window.history.replaceState({}, document.title, "/anchor");
    }

    function createMessage(sender, message, isAgent) {

        const wrapper = document.createElement("div");
        wrapper.style.width = "100%";
        wrapper.style.boxSizing = "border-box";

        if (isAgent) {
            wrapper.style.borderLeft = "2px solid rgba(56, 189, 248, 0.45)";
            wrapper.style.paddingLeft = "14px";
        }

        const header = document.createElement("div");
        header.style.display = "flex";
        header.style.alignItems = "center";
        header.style.gap = "7px";
        header.style.marginBottom = "5px";

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
        timeElement.textContent = new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit"
        });
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

    async function sendMessage() {

        const message = textarea.value.trim();

        if (!message) {
            return;
        }

        createMessage("Operator", message, false);

        textarea.value = "";
        textarea.style.height = "auto";

        sendButton.disabled = true;
        sendButton.style.opacity = "0.5";
        sendButton.style.cursor = "wait";

        const thinking = createThinkingMessage();

        try {

            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ message: message })
            });

            let data;

            try {
                data = await response.json();
            } catch (error) {
                throw new Error("The server returned an invalid response.");
            }

            if (thinking) {
                thinking.remove();
            }

            if (!response.ok || !data.success) {
                throw new Error(
                    data.error ||
                    "V.A.U.L.T. could not process the request."
                );
            }

            createMessage(
                "V.A.U.L.T.",
                data.response,
                true
            );

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

            sendButton.disabled = false;
            sendButton.style.opacity = "";
            sendButton.style.cursor = "";
            textarea.focus();
        }
    }

    sendButton.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        sendMessage();
    }, true);

    textarea.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });

    textarea.addEventListener("input", function () {
        textarea.style.height = "auto";
        textarea.style.height = Math.min(textarea.scrollHeight, 180) + "px";
    });

    console.log("[V.A.U.L.T.] Live chat connected.");

})();
</script>
"""

    if "</body>" in html:
        html = html.replace("</body>", chat_script + "\n</body>")
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

            body = self.rfile.read(content_length)

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

        message = data.get("message")

        if not isinstance(message, str):

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
                    "error": "Message cannot be empty.",
                },
                status=400,
            )

            return

        try:

            result = vault.run(message)

            if result is None:
                result = ""

            result = str(result)

        except Exception as error:

            print(
                "[V.A.U.L.T.] Backend error:",
                repr(error),
            )

            self.send_json(
                {
                    "success": False,
                    "error":
                        "V.A.U.L.T. backend error: "
                        + str(error),
                },
                status=500,
            )

            return

        self.send_json(
            {
                "success": True,
                "response": result,
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