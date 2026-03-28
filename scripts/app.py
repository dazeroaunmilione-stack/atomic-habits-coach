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
    padding: 0 2rem 7rem 2rem !important;
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
    white-space: nowrap !important;
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

.coach-title strong {
    font-weight: 600;
    color: #C4A35A;
}

.coach-subtitle {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.75rem;
    font-weight: 400;
    color: #7A7570 !important; /* più scuro */
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
    opacity: 0.3;
    color: #C4A35A;
}

.empty-state p {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.82rem;
    font-weight: 400;
    line-height: 1.8;
    color: #8A847C !important; /* più scuro */
    max-width: 300px;
    margin: 0 auto;
}

/* ─── HIDE DEFAULT AVATARS ─────────────────────────────────── */
[data-testid="chatAvatarIcon-user"],
[data-testid="chatAvatarIcon-assistant"] {
    display: none !important;
}

/* ─── CHAT MESSAGES ────────────────────────────────────────── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 0.3rem 0 !important;
    margin-bottom: 0.6rem !important;
    gap: 0.6rem !important;
}

/* Avatar custom — utente */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"])::before {
    content: "U";
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #2C2C2C;
    color: #C4A35A;
    font-family: 'Cormorant Garamond', serif;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    flex-shrink: 0;
}

/* Avatar custom — coach */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"])::before {
    content: "◈";
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 28px;
    height: 28px;
    border-radius: 50%;
    background: linear-gradient(135deg, #C4A35A, #E8C97A);
    color: #fff;
    font-size: 0.7rem;
    flex-shrink: 0;
}

/* Bubble utente */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stMarkdown {
    background: #2C2C2C !important;
    color: #F0EDE8 !important;
    border-radius: 20px 20px 4px 20px !important;
    padding: 0.85rem 1.15rem !important;
    max-width: 76% !important;
    font-size: 0.88rem !important;
    line-height: 1.6 !important;
    margin-left: auto !important;
}

/* Bubble coach */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stMarkdown {
    background: #FFFFFF !important;
    color: #2C2C2C !important;
    border-radius: 20px 20px 20px 4px !important;
    padding: 1rem 1.3rem !important;
    max-width: 84% !important;
    font-size: 0.88rem !important;
    line-height: 1.75 !important;
    border: 1px solid #E8E4DC !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04) !important;
}

/* testo dentro le bubble sempre visibile */
[data-testid="stChatMessage"] .stMarkdown p,
[data-testid="stChatMessage"] .stMarkdown li,
[data-testid="stChatMessage"] .stMarkdown strong {
    color: inherit !important;
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
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    box-shadow: 0 2px 14px rgba(0,0,0,0.05) !important;
    resize: none !important;
    outline: none !important;
}

[data-testid="stChatInput"] textarea:focus {
    border-color: #C4A35A !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(196, 163, 90, 0.1), 0 2px 14px rgba(0,0,0,0.05) !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #7A7570 !important; /* più scuro */
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
    outline: none !important;
}

[data-testid="stChatInput"] button:hover {
    background: #2C2C2C !important;
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

# ─── BOTTONE NUOVO CASO — top right ─────────────────────────────────────────
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