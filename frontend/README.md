# V.A.U.L.T. — SIH26117 — Streamlit Wrappers

Each of your 6 HTML mockups now has a matching Streamlit script that embeds
it exactly (same fonts, same colors, same Tailwind styling, same JS
animations) using `streamlit.components.v1.html()`. Nothing is redrawn with
native Streamlit widgets, so the visual result is identical to opening the
HTML file directly in a browser.

| # | Streamlit script     | Embeds              | Page                              |
|---|-----------------------|----------------------|------------------------------------|
| 1 | `1_landing.py`        | `LANDING.HTML`       | Landing                            |
| 2 | `2_login.py`          | `LOGIN.HTML`         | Secure Authentication              |
| 3 | `3_anchor_page.py`    | `ANCHOR_PAGE.HTML`   | Local Workspace                    |
| 4 | `4_analysis.py`       | `Analysis.html`      | Core — Active Agent Workspace      |
| 5 | `5_library.py`        | `Library.html`       | Library                            |
| 6 | `6_security.py`       | `security.html`      | Security / Sovereignty Monitor     |

## 1. One-time setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Keep every `.py` file in the **same folder** as its matching `.HTML`/`.html`
file — the scripts load the HTML by filename from their own folder.

## 2. Run ONE page at a time

Streamlit's default port is 8501, so if you close one app before opening the
next, you don't need anything extra:

```bash
streamlit run 1_landing.py
```
Check it in the browser tab that opens (or http://localhost:8501), then
press `Ctrl+C` in the terminal to stop it before running the next one:

```bash
streamlit run 2_login.py
streamlit run 3_anchor_page.py
streamlit run 4_analysis.py
streamlit run 5_library.py
streamlit run 6_security.py
```

### Want them running side-by-side instead of one-by-one?
Give each a different port:
```bash
streamlit run 1_landing.py --server.port 8501
streamlit run 2_login.py   --server.port 8502
streamlit run 3_anchor_page.py --server.port 8503
streamlit run 4_analysis.py    --server.port 8504
streamlit run 5_library.py     --server.port 8505
streamlit run 6_security.py    --server.port 8506
```

## 3. Why `components.html()` instead of native Streamlit widgets?

Your screens use a heavily customized Tailwind config (custom color tokens,
custom fonts — Geist / Syne / JetBrains Mono / Newsreader — custom spacing)
plus live JS (canvas particle backgrounds, blinking cursor, cycling status
text). Native Streamlit widgets (`st.button`, `st.text_input`, columns, etc.)
cannot reproduce this design pixel-for-pixel — you'd get a *similar-looking*
app, not the *same* one. Embedding the original HTML/CSS/JS in an iframe via
`components.html()` is the only way to guarantee an identical result while
still technically living inside a Streamlit app.

## 4. Turning this into one real multi-page app later

Right now the 6 HTML files are static mockups — none of the buttons/links
actually navigate anywhere (they're all `href="#"`), and the Login form has
no real authentication logic wired up.

When you're ready to make it a *real* app (actual login check, actual
navigation from page to page, actual file analysis, etc.), the common
pattern is:
1. Put all 6 scripts in a `pages/` folder so Streamlit's built-in
   multipage sidebar navigation shows them together.
2. Keep using `components.html()` for the visual shell, but use
   `st.session_state` + Streamlit-native form widgets placed *around* or
   *below* the embedded HTML for the parts that need real Python logic
   (e.g., checking a password, running your actual analysis code).
   Communicating a click *inside* the iframe back to Python requires
   extra plumbing (e.g. `streamlit-javascript`, or swapping the login
   button for a real `st.form`), since an iframe is sandboxed from the
   parent page by default.

Ask me if/when you want that step built out — happy to wire up real
navigation and a real login check next.
