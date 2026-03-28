import streamlit as st
from agent import chat, session

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

[data-testid="stAppViewContainer"] {
    background: #F8F7F5 !important;
}

[data-testid="stHeader"] {
    background: transparent !important;
    border: none !important;
}

/* ─── HIDE STREAMLIT DEFAULTS ──────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
.stDeployButton { display: none; }

/* ─── SIDEBAR ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #E8E4DC !important;
    padding: 2rem 1.5rem !important;
    min-width: 220px !important;
    max-width: 220px !important;
}

[data-testid="stSidebar"] > div:first-child {
    padding: 0 !important;
}

.sidebar-logo {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.1rem;
    font-weight: 500;
    color: #1A1A1A;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 2.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid #E8E4DC;
}

.sidebar-logo span {
    color: #C4A35A;
}

.sidebar-label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.65rem;
    font-weight: 500;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #999;
    margin-bottom: 2rem;
}

/* ─── SIDEBAR BUTTON ───────────────────────────────────────── */
[data-testid="stSidebar"] .stButton > button {
    width: 100% !important;
    background: transparent !important;
    border: 1px solid #C4A35A !important;
    color: #C4A35A !important;
    border-radius: 50px !important;
    padding: 0.6rem 1.2rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    cursor: pointer !important;
    transition: all 0.25s ease !important;
    margin-top: 1rem !important;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: #C4A35A !important;
    color: #FFFFFF !important;
}

/* ─── MAIN CONTAINER ───────────────────────────────────────── */
.main .block-container {
    max-width: 760px !important;
    padding: 3rem 2rem 8rem 2rem !important;
    margin: 0 auto !important;
}

/* ─── HEADER ───────────────────────────────────────────────── */
.coach-header {
    text-align: center;
    padding: 3rem 0 2.5rem 0;
    margin-bottom: 1rem;
}

.coach-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 2.6rem;
    font-weight: 300;
    color: #1A1A1A;
    letter-spacing: 0.04em;
    line-height: 1.1;
    margin-bottom: 0.6rem;
}

.coach-title strong {
    font-weight: 600;
    color: #C4A35A;
}

.coach-subtitle {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.8rem;
    font-weight: 300;
    color: #999;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}

.header-divider {
    width: 40px;
    height: 1px;
    background: linear-gradient(90deg, transparent, #C4A35A, transparent);
    margin: 1.2rem auto 0 auto;
}

/* ─── CHAT MESSAGES ────────────────────────────────────────── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 0.4rem 0 !important;
    margin-bottom: 0.5rem !important;
}

/* User messages */
[data-testid="stChatMessage"][data-testid*="user"],
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    display: flex;
    justify-content: flex-end;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stMarkdown {
    background: #1A1A1A !important;
    color: #F8F7F5 !important;
    border-radius: 20px 20px 4px 20px !important;
    padding: 0.9rem 1.2rem !important;
    max-width: 78% !important;
    font-size: 0.9rem !important;
    line-height: 1.6 !important;
    margin-left: auto !important;
}

/* Assistant messages */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stMarkdown {
    background: #FFFFFF !important;
    color: #1A1A1A !important;
    border-radius: 20px 20px 20px 4px !important;
    padding: 1rem 1.3rem !important;
    max-width: 86% !important;
    font-size: 0.9rem !important;
    line-height: 1.7 !important;
    border: 1px solid #EDEAE4 !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04) !important;
}

/* Avatar icons */
[data-testid="chatAvatarIcon-user"] {
    background: #1A1A1A !important;
    border-radius: 50% !important;
    color: #C4A35A !important;
    font-size: 0.7rem !important;
}

[data-testid="chatAvatarIcon-assistant"] {
    background: linear-gradient(135deg, #C4A35A, #E8C97A) !important;
    border-radius: 50% !important;
    color: #FFF !important;
    font-size: 0.7rem !important;
}

/* ─── CHAT INPUT ───────────────────────────────────────────── */
[data-testid="stChatInput"] {
    position: fixed !important;
    bottom: 0 !important;
    left: 220px !important;
    right: 0 !important;
    background: rgba(248, 247, 245, 0.92) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border-top: 1px solid #E8E4DC !important;
    padding: 1rem 2rem 1.2rem 2rem !important;
    z-index: 999 !important;
}

[data-testid="stChatInput"] textarea {
    background: #FFFFFF !important;
    border: 1px solid #E0DBD3 !important;
    border-radius: 50px !important;
    padding: 0.8rem 1.4rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
    color: #1A1A1A !important;
    transition: border-color 0.2s ease !important;
    box-shadow: 0 2px 16px rgba(0,0,0,0.05) !important;
    resize: none !important;
}

[data-testid="stChatInput"] textarea:focus {
    border-color: #C4A35A !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(196, 163, 90, 0.12), 0 2px 16px rgba(0,0,0,0.05) !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #B0A898 !important;
    font-style: italic !important;
}

/* Send button */
[data-testid="stChatInput"] button {
    background: #C4A35A !important;
    border: none !important;
    border-radius: 50% !important;
    color: white !important;
    transition: all 0.2s ease !important;
}

[data-testid="stChatInput"] button:hover {
    background: #1A1A1A !important;
    transform: scale(1.05) !important;
}

/* ─── SPINNER ──────────────────────────────────────────────── */
.stSpinner > div {
    border-color: #C4A35A transparent transparent transparent !important;
}

/* ─── SCROLLBAR ────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #D8D3CA; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #C4A35A; }

/* ─── EMPTY STATE ──────────────────────────────────────────── */
.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: #B0A898;
}

.empty-state .icon {
    font-size: 2rem;
    margin-bottom: 1rem;
    opacity: 0.4;
}

.empty-state p {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.85rem;
    font-weight: 300;
    line-height: 1.7;
    color: #B0A898;
    max-width: 320px;
    margin: 0 auto;
}

/* ─── GATE INDICATOR ───────────────────────────────────────── */
.gate-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: #FFFFFF;
    border: 1px solid #E8E4DC;
    border-radius: 50px;
    padding: 0.3rem 0.8rem;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.65rem;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #999;
    margin-bottom: 2rem;
}

.gate-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #C4A35A;
}

</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div class="sidebar-logo">Atomic<br><span>Habits</span> Coach</div>
        <div class="sidebar-label">Sessione attiva</div>
    """, unsafe_allow_html=True)

    if st.button("↺  Nuovo caso"):
        session['conversation'] = []
        session['gate'] = 0
        session['retrieval_done'] = False
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

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Descrivi il tuo caso..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner(""):
            reply = chat(prompt)
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()