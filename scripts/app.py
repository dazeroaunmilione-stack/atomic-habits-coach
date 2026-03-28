import streamlit as st
from agent import chat, session
import re

st.set_page_config(
    page_title="Atomic Habits Coach",
    page_icon="◈",
    layout="centered"
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;500;600&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">

<style>

/* ─── RESET & BASE ─────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background: #F8F7F5 !important;
    font-family: 'DM Sans', sans-serif;
}

[data-testid="stHeader"] { background: transparent !important; border: none !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
.stDeployButton { display: none; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }

/* ─── MAIN CONTAINER ───────────────────────────────────────── */
.main .block-container {
    max-width: 700px !important;
    padding: 0 2rem 9rem 2rem !important; /* aumentato per mobile */
    margin: 0 auto !important;
}

/* ─── NUOVO CASO BUTTON ────────────────────────────────────── */
.stButton > button {
    background: transparent !important;
    border: 1px solid #D8D3CA !important;
    border-radius: 50px !important;
    padding: 0.35rem 0.9rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.65rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #888 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    border-color: #C4A35A !important;
    color: #C4A35A !important;
}

/* ─── HEADER ───────────────────────────────────────────────── */
.coach-header {
    text-align: center;
    padding: 3rem 0 2.5rem 0;
    margin-bottom: 0.5rem;
}
.coach-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 3.8rem;
    font-weight: 300;
    color: #1A1A1A;
    letter-spacing: 0.04em;
    line-height: 1.1;
    margin-bottom: 0.7rem;
}
.coach-title strong { font-weight: 600; color: #C4A35A; }
.coach-subtitle {
    font-size: 0.75rem;
    font-weight: 400;
    color: #7A7570;
    letter-spacing: 0.18em;
    text-transform: uppercase;
}
.header-divider {
    width: 40px;
    height: 1px;
    background: linear-gradient(90deg, transparent, #C4A35A, transparent);
    margin: 1.2rem auto 0 auto;
}

/* ─── EMPTY STATE ──────────────────────────────────────────── */
.empty-state {
    text-align: center;
    padding: 2.5rem 2rem;
}
.empty-state .icon {
    font-size: 1.6rem;
    margin-bottom: 0.8rem;
    opacity: 0.3;
    color: #C4A35A;
}
.empty-state p {
    font-size: 0.82rem;
    font-weight: 400;
    line-height: 1.8;
    color: #8A847C;
    max-width: 300px;
    margin: 0 auto;
}

/* ─── CUSTOM CHAT MESSAGES ─────────────────────────────────── */
.msg-row {
    display: flex;
    align-items: flex-start;
    gap: 0.7rem;
    margin-bottom: 0.9rem;
}
.msg-row.user { flex-direction: row-reverse; }

.avatar {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Cormorant Garamond', serif;
    font-size: 0.8rem;
    font-weight: 600;
    flex-shrink: 0;
    margin-top: 2px;
}
.avatar-user {
    background: #2C2C2C;
    color: #C4A35A;
    font-size: 0.7rem;
    letter-spacing: 0.05em;
}
.avatar-coach {
    background: linear-gradient(135deg, #C4A35A, #E8C97A);
    color: #FFFFFF;
    font-size: 0.65rem;
}

.bubble {
    max-width: 78%;
    padding: 0.85rem 1.15rem;
    font-size: 0.88rem;
    line-height: 1.72;
    font-family: 'DM Sans', sans-serif;
}
.bubble-user {
    background: #2C2C2C;
    color: #F0EDE8;
    border-radius: 20px 20px 4px 20px;
}
.bubble-coach {
    background: #FFFFFF;
    color: #2C2C2C;
    border-radius: 20px 20px 20px 4px;
    border: 1px solid #E8E4DC;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

/* ─── CHAT INPUT ───────────────────────────────────────────── */
[data-testid="stChatInput"] {
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    background: rgba(248, 247, 245, 0.95) !important;
    backdrop-filter: blur(14px) !important;
    -webkit-backdrop-filter: blur(14px) !important;
    border-top: 1px solid #EAE7E1 !important;
    padding: 0.9rem 0 1.1rem 0 !important;
    z-index: 998 !important;
    display: flex !important;
    justify-content: center !important;
    box-shadow: none !important;
    outline: none !important;
}
[data-testid="stChatInput"] > div {
    max-width: 520px !important;
    width: 100% !important;
    padding: 0 !important;
    margin: 0 auto !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}
[data-testid="stChatInput"] div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}
[data-testid="stChatInput"] textarea {
    background: #FFFFFF !important;
    border: 1px solid #E0DBD3 !important;
    border-radius: 50px !important;
    padding: 0.75rem 1.3rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.86rem !important;
    color: #2C2C2C !important;
    box-shadow: 0 2px 14px rgba(0,0,0,0.05) !important;
    resize: none !important;
    outline: none !important;
    transition: border-color 0.2s ease !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #C4A35A !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(196,163,90,0.1) !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #7A7570 !important;
    font-style: italic !important;
    font-weight: 300 !important;
}
[data-testid="stChatInput"] button {
    background: #C4A35A !important;
    border: none !important;
    border-radius: 50% !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(196,163,90,0.3) !important;
    outline: none !important;
    transition: all 0.2s ease !important;
}
[data-testid="stChatInput"] button:hover {
    background: #2C2C2C !important;
    transform: scale(1.05) !important;
}

/* ─── MOBILE ───────────────────────────────────────────────── */
@media (max-width: 768px) {
    .coach-title { font-size: 2.6rem !important; }
    .bubble { max-width: 88% !important; font-size: 0.85rem !important; }
    .main .block-container { padding-bottom: 11rem !important; }
    [data-testid="stChatInput"] { padding-bottom: 1.8rem !important; }
}

/* ─── SPINNER ──────────────────────────────────────────────── */
.stSpinner > div {
    border-color: #C4A35A transparent transparent transparent !important;
}

/* ─── SCROLLBAR ────────────────────────────────────────────── */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #D8D3CA; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #C4A35A; }

</style>
""", unsafe_allow_html=True)

# ─── TOP BAR ────────────────────────────────────────────────────────────────
col1, col2 = st.columns([8, 2])
with col2:
    if st.button("↺ Nuovo caso"):
        session['conversation'] = []
        session['gate'] = 0
        session['retrieval_done'] = False
        if 'retrieved_modules' in session:
            session['retrieved_modules'] = None
        st.session_state.messages = []
        st.rerun()

# ─── HEADER ─────────────────────────────────────────────────────────────────
st.markdown("""
    <div class="coach-header">
        <div class="coach-title">Atomic <strong>Habits</strong> Coach</div>
        <div class="coach-subtitle">Behavior change · Analisi · Intervento</div>
        <div class="header-divider"></div>
    </div>
""", unsafe_allow_html=True)

# ─── CHAT ────────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    st.markdown("""
        <div class="empty-state">
            <div class="icon">◈</div>
            <p>Descrivi il comportamento su cui vuoi lavorare.<br>
            Il Coach analizzerà la situazione e costruirà un intervento su misura.</p>
        </div>
    """, unsafe_allow_html=True)

def render_message(content, role):
    content_html = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    content_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content_html)
    content_html = content_html.replace("\n", "<br>")
    if role == "user":
        return f"""
        <div class="msg-row user">
            <div class="avatar avatar-user">F</div>
            <div class="bubble bubble-user">{content_html}</div>
        </div>"""
    else:
        return f"""
        <div class="msg-row">
            <div class="avatar avatar-coach">◈</div>
            <div class="bubble bubble-coach">{content_html}</div>
        </div>"""

for message in st.session_state.messages:
    st.markdown(render_message(message["content"], message["role"]), unsafe_allow_html=True)

if prompt := st.chat_input("Descrivi il tuo caso..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(render_message(prompt, "user"), unsafe_allow_html=True)
    with st.spinner(""):
        reply = chat(prompt)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()