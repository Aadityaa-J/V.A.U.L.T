"""
V.A.U.L.T. - PAGE 1: LANDING
Run with:  streamlit run 1_landing.py
Requires LANDING.HTML to sit in the SAME folder as this script.
"""
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(
    page_title="V.A.U.L.T. // Landing",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Strip Streamlit's own chrome (menu/header/footer/padding) so the
# embedded design fills the browser edge-to-edge, exactly like the
# original standalone HTML file did.
st.markdown(
    """
    <style>
        #MainMenu, header, footer {visibility: hidden;}
        div.block-container {padding: 0 !important; margin: 0 !important; max-width: 100% !important;}
        /* Stretch the embedded iframe to fill the actual browser window
           (100vw x 100vh) instead of a fixed pixel size, so the h-screen
           layout inside it always fits your screen with no scrollbar. */
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

HTML_FILE = Path(__file__).parent / "LANDING.HTML"
html_code = HTML_FILE.read_text(encoding="utf-8")

# The height passed here is just a starting size before the CSS above
# takes over and stretches the iframe to fill the real viewport.
components.html(html_code, height=1000, scrolling=False)
