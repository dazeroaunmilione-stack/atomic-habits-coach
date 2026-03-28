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

/* ─── HIDE SIDEBAR ─────────────────────────────────────────── */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }

/* ─── MAIN CONTAINER ───────────────────────────────────────── */
.main .block-container {
    max-width: 700px !important;
    padding: 2rem 2rem 7rem 2rem !important;
    margin: 0 auto !important;
}

/* ─── NUOVO CASO BUTTON ────────────────────────────────────── */
.stButton > button {
    background: transparent !important;
    border: 1px solid #E0DBD3 !important;
    border-radius: 50px !important;
    padding: 0.4rem 1rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.68rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #B0A898 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    white-space: nowrap !important;
}

.stButton > button:hover {
    border-color: #C4A35A !important;
    color: #C4A35A !important;
}

/* ─── HEADER ───────────────────────────────────────────────── */
.coach-header {
    text-align: center;
    padding: 1.5rem 0 2.5rem 0;
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

.coach-title strong {
    font-weight: 600;
    color: #C4A35A;
}

.coach-subtitle {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.75rem;
    font-weight: 300;
    color: #B0A898;
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
    padding: 2rem 2rem 1.5rem 2rem;
}

.empty-state .icon {
    font-size: 1.6rem;
    margin-bottom: 0.8rem;
    opacity: 0.25;
    color: #C4A35A;
}

.empty-state p {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.82rem;
    font-weight: 300;
    line-height: 1.8;
    color: #C0B8AE;
    max-width: 300px;
    margin: 0 auto;
}

/* ─── CHAT MESSAGES ────────────────────────────────────────── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 0.3rem 0 !important;
    margin-bottom: 0.4rem !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stMarkdown {
    background: #1A1A1A !important;
    color: #F8F7F5 !important;
    border-radius: 20px 20px 4px 20px !important;
    padding: 0.85rem 1.15rem !important;
    max-width: 76% !important;
    font-size: 0.88rem !important;
    line-height: 1.6 !important;
    margin-left: auto !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stMarkdown {
    background: #FFFFFF !important;
    color: #1A1A1A !important;
    border-radius: 20px 20px 20px 4px !important;
    padding: 1rem 1.3rem !important;
    max-width: 84% !important;
    font-size: 0.88rem !important;
    line-height: 1.75 !important;
    border: 1px solid #EDEAE4 !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04) !important;
}

[data-testid="chatAvatarIcon-user"] {
    background: #1A1A1A !important;
    border-radius: 50% !important;
    color: #C4A35A !important;
}

[data-testid="chatAvatarIcon-assistant"] {
    background: linear-gradient(135deg, #C4A35A, #E8C97A) !important;
    border-radius: 50% !important;
    color: #FFF !important;
}

/* ─── CHAT INPUT ───────────────────────────────────────────── */
[data-testid="stChatInput"] {
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    background: rgba(248, 247, 245, 0.94) !important;
    backdrop-filter: blur(14px) !important;
    -webkit-backdrop-filter: blur(14px) !important;
    border-top: 1px solid #EAE7E1 !important;
    padding: 0.9rem 0 1.1rem 0 !important;
    z-index: 999 !important;
    display: flex !important;
    justify-content: center !important;
}

[data-testid="stChatInput"] > div {
    max-width: 560px !important;
    width: 100% !important;
    padding: 0 2rem !important;
}

[data-testid="stChatInput"] textarea {
    background: #FFFFFF !important;
    border: 1px solid #E0DBD3 !important;
    border-radius: 50px !important;
    padding: 0.75rem 1.3rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.86rem !important;
    color: #1A1A1A !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    box-shadow: 0 2px 14px rgba(0,0,0,0.05) !important;
    resize: none !important;
}

[data-testid="stChatInput"] textarea:focus {
    border-color: #C4A35A !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(196, 163, 90, 0.1), 0 2px 14px rgba(0,0,0,0.05) !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #C0B8AE !important;
    font-style: italic !important;
    font-weight: 300 !important;
}

[data-testid="stChatInput"] button {
    background: #C4A35A !important;
    border: none !important;
    border-radius: 50% !important;
    color: white !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(196,163,90,0.3) !important;
}

[data-testid="stChatInput"] button:hover {
    background: #1A1A1A !important;
    transform: scale(1.05) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
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

# ─── TOP BAR con bottone Nuovo caso ─────────────────────────────────────────
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