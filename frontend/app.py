import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path


# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------

st.set_page_config(
    page_title="V.A.U.L.T.",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------
# FRONTEND PATHS
# ---------------------------------------------------------

FRONTEND_DIR = Path(__file__).parent


PAGES = {
    "landing": "LANDING.HTML",
    "login": "LOGIN.HTML",
    "anchor": "ANCHOR_PAGE.HTML",
    "analysis": "Analysis.html",
    "library": "Library.html",
    "security": "security.html",
}


# ---------------------------------------------------------
# CURRENT PAGE
# ---------------------------------------------------------

page = st.query_params.get("page", "landing")

if page not in PAGES:
    page = "landing"


# ---------------------------------------------------------
# REMOVE STREAMLIT CHROME
# ---------------------------------------------------------

st.markdown(
    """
    <style>
        #MainMenu,
        header,
        footer {
            visibility: hidden;
        }

        div.block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
        }

        iframe {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            border: none !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# FIND HTML FILE
# ---------------------------------------------------------

html_file = FRONTEND_DIR / PAGES[page]

if not html_file.exists():
    st.error(f"Frontend page not found: {html_file}")
    st.stop()


# ---------------------------------------------------------
# READ HTML
# ---------------------------------------------------------

html_code = html_file.read_text(encoding="utf-8")


# ---------------------------------------------------------
# NAVIGATION BRIDGE
# ---------------------------------------------------------
#
# The HTML is displayed inside a Streamlit iframe.
# This JavaScript listens for clicks on links/buttons
# and changes the "page" query parameter of the
# Streamlit application.
#
# Existing HTML files are NOT modified.
# ---------------------------------------------------------

navigation_script = """
<script>
(function () {

    function navigate(page) {

        try {

            const parentUrl = new URL(window.top.location.href);

            parentUrl.searchParams.set("page", page);

            window.top.location.assign(parentUrl.toString());

        } catch (error) {

            console.error(
                "V.A.U.L.T. navigation error:",
                error
            );

        }
    }


    document.addEventListener(
        "click",
        function (event) {

            const element =
                event.target.closest("a, button");

            if (!element) {
                return;
            }


            const text =
                (element.innerText || "")
                .trim()
                .toLowerCase();


            // =================================================
            // LANDING → LOGIN
            // =================================================

            if (
                text.includes("launch v.a.u.l.t.") ||
                text === "sign in"
            ) {

                event.preventDefault();
                event.stopPropagation();

                navigate("login");

                return;
            }


            // =================================================
            // LOGIN → ANCHOR
            // =================================================

            if (
                text.includes("enter v.a.u.l.t.")
            ) {

                event.preventDefault();
                event.stopPropagation();

                navigate("anchor");

                return;
            }


            // =================================================
            // ANCHOR → LIBRARY
            // =================================================

            if (
                text.includes("knowledge")
            ) {

                event.preventDefault();
                event.stopPropagation();

                navigate("library");

                return;
            }


            // =================================================
            // ANCHOR → SECURITY
            // =================================================

            if (
                text.includes("security")
            ) {

                event.preventDefault();
                event.stopPropagation();

                navigate("security");

                return;
            }


            // =================================================
            // ANCHOR → ANALYSIS
            // =================================================

            if (
                text.includes("analyze documents") ||
                text.includes("inspection analysis")
            ) {

                event.preventDefault();
                event.stopPropagation();

                navigate("analysis");

                return;
            }

        },
        true
    );

})();
</script>
"""


# ---------------------------------------------------------
# INJECT NAVIGATION SCRIPT
# ---------------------------------------------------------

if "</body>" in html_code:

    html_code = html_code.replace(
        "</body>",
        navigation_script + "</body>"
    )

else:

    html_code += navigation_script


# ---------------------------------------------------------
# DISPLAY CURRENT PAGE
# ---------------------------------------------------------

components.html(
    html_code,
    height=1000,
    scrolling=False,
)