"""
V.A.U.L.T. - PAGE 5: LIBRARY
Run with:  streamlit run 5_library.py
Requires Library.html to sit in the SAME folder as this script.
"""
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(
    page_title="V.A.U.L.T. // Library",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        #MainMenu, header, footer {visibility: hidden;}
        div.block-container {padding: 0 !important; margin: 0 !important; max-width: 100% !important;}
        /* Stretch the embedded iframe to fill the actual browser window
           (100vw x 100vh). The page's own min-h-screen layout then sizes
           itself to your real screen, just like opening the HTML directly.
           scrolling stays enabled below so if your library ever has more
           items than fit on one screen, it scrolls internally instead of
           stretching the whole layout and leaving a dead gap. */
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

HTML_FILE = Path(__file__).parent / "Library.html"
html_code = HTML_FILE.read_text(encoding="utf-8")

components.html(html_code, height=1000, scrolling=True)
