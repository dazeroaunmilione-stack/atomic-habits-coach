import streamlit as st
from agent import chat, reset_session, get_session
from session_store import (
    create_session, list_sessions, update_session, delete_session,
    save_message, load_messages, save_feedback, SUPABASE_AVAILABLE
)
import re
from datetime import datetime

st.set_page_config(
    page_title="Atomic Habits Coach",
    page_icon="◈",
    layout="wide"
)

# ─────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;500;600;700&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&display=swap" rel="stylesheet">

<style>

/* === RESET === */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background: #FAFAF8 !important;
    font-family: 'DM Sans', -apple-system, sans-serif;
}

[data-testid="stHeader"] { background: transparent !important; border: none !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
.stDeployButton { display: none; }

/* === SIDEBAR === */
section[data-testid="stSidebar"] {
    background: #1A1A1A !important;
    border-right: none !important;
    width: 280px !important;
    min-width: 280px !important;
}
section[data-testid="stSidebar"] > div:first-child {
    background: #1A1A1A !important;
    padding: 1.2rem 1rem !important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdown"] p {
    color: #A09A92 !important;
}

/* Sidebar buttons */
.sidebar-new-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 0.65rem 0.9rem;
    background: transparent;
    border: 1.5px solid rgba(196, 163, 90, 0.3);
    border-radius: 12px;
    color: #C4A35A;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.25s ease;
    text-decoration: none;
    letter-spacing: 0.02em;
}
.sidebar-new-btn:hover {
    background: rgba(196, 163, 90, 0.1);
    border-color: #C4A35A;
}

.sidebar-section-title {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.62rem;
    font-weight: 600;
    color: #5A5650;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 1rem 0 0.5rem 0.2rem;
}

.session-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0.6rem 0.8rem;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s ease;
    margin-bottom: 2px;
}
.session-item:hover { background: rgba(255,255,255,0.06); }
.session-item.active { background: rgba(196, 163, 90, 0.12); }
.session-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #3A3A3A;
    flex-shrink: 0;
}
.session-item.active .session-dot { background: #C4A35A; }
.session-title {
    font-size: 0.78rem;
    color: #D0CBC3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-weight: 400;
    line-height: 1.3;
}
.session-item.active .session-title { color: #F0EDE8; font-weight: 500; }
.session-date {
    font-size: 0.62rem;
    color: #5A5650;
    margin-left: auto;
    flex-shrink: 0;
}

/* Sidebar collapse button override */
[data-testid="collapsedControl"] {
    color: #C4A35A !important;
}

/* === MAIN CONTAINER === */
.main .block-container {
    max-width: 740px !important;
    padding: 0 1.5rem 10rem 1.5rem !important;
    margin: 0 auto !important;
}

/* === HEADER === */
.coach-header {
    text-align: center;
    padding: 2rem 0 1rem 0;
}
.coach-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 3rem;
    font-weight: 300;
    color: #1A1A1A;
    letter-spacing: 0.03em;
    line-height: 1.1;
    margin-bottom: 0.5rem;
}
.coach-title strong { font-weight: 600; color: #C4A35A; }
.coach-subtitle {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.7rem;
    font-weight: 400;
    color: #B0A898;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}
.header-line {
    width: 36px;
    height: 1px;
    background: linear-gradient(90deg, transparent, #C4A35A, transparent);
    margin: 0.8rem auto 0 auto;
}

/* === GATE PROGRESS === */
.gate-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    margin: 0.8rem auto 1.2rem auto;
    max-width: 340px;
}
.gate-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
}
.gate-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #E8E4DC;
    border: 2px solid #E8E4DC;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 2;
}
.gate-dot.active {
    background: #C4A35A;
    border-color: #C4A35A;
    box-shadow: 0 0 12px rgba(196, 163, 90, 0.4);
    animation: gatePulse 2s ease-in-out infinite;
}
.gate-dot.passed { background: #C4A35A; border-color: #C4A35A; }
@keyframes gatePulse {
    0%, 100% { box-shadow: 0 0 8px rgba(196, 163, 90, 0.3); }
    50% { box-shadow: 0 0 16px rgba(196, 163, 90, 0.5); }
}
.gate-lbl {
    font-size: 0.56rem;
    font-weight: 500;
    color: #C5BFB6;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-top: 5px;
}
.gate-lbl.active { color: #C4A35A; font-weight: 600; }
.gate-lbl.passed { color: #A09A92; }
.gate-conn {
    height: 2px;
    flex: 1;
    background: #E8E4DC;
    margin: 0 -2px;
    margin-bottom: 18px;
    transition: background 0.4s ease;
}
.gate-conn.active { background: linear-gradient(90deg, #C4A35A, #D4B66A); }

/* === EMPTY STATE === */
.empty-state {
    text-align: center;
    padding: 3rem 2rem 2.5rem 2rem;
    background: #FFFFFF;
    border-radius: 24px;
    border: 1px solid #EFEBE5;
    box-shadow: 0 8px 40px rgba(0,0,0,0.03);
    margin: 0.5rem 0 1rem 0;
}
.empty-icon {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: linear-gradient(135deg, #FBF5E8, #F0E6CC);
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 1.2rem auto;
    font-size: 1.4rem;
    color: #C4A35A;
}
.empty-state h3 {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.3rem;
    font-weight: 500;
    color: #1A1A1A;
    margin-bottom: 0.4rem;
}
.empty-state p {
    font-size: 0.82rem;
    font-weight: 400;
    line-height: 1.7;
    color: #A09A92;
    max-width: 380px;
    margin: 0 auto;
}
.prompt-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin-top: 1.4rem;
}
.prompt-chip {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.72rem;
    font-weight: 500;
    color: #8A7A5A;
    background: #FBF5E8;
    border: 1px solid #F0E6CC;
    border-radius: 50px;
    padding: 0.35rem 0.9rem;
    cursor: pointer;
    transition: all 0.25s ease;
    text-decoration: none;
}
.prompt-chip:hover {
    background: #F0E6CC;
    color: #6B5A3A;
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(196, 163, 90, 0.15);
}

/* === MESSAGES === */
.msg-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 0.3rem;
    animation: msgIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.msg-row.user { flex-direction: row-reverse; }
@keyframes msgIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 2px;
}
.avatar-user { background: #2C2C2C; }
.avatar-coach { background: linear-gradient(135deg, #C4A35A, #DFC070); }

.bubble {
    max-width: 78%;
    padding: 0.9rem 1.15rem;
    font-size: 0.87rem;
    line-height: 1.75;
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
    border: 1px solid #EFEBE5;
    box-shadow: 0 2px 16px rgba(0,0,0,0.03);
}
.bubble-coach strong { color: #B08F4A; }

/* === FEEDBACK BUTTONS === */
.feedback-row {
    display: flex;
    gap: 4px;
    margin: 2px 0 0.8rem 42px;
    animation: msgIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.fb-btn {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    border: 1px solid #EFEBE5;
    background: #FAFAF8;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
    font-size: 0.72rem;
    color: #C5BFB6;
}
.fb-btn:hover { background: #F0E6CC; color: #C4A35A; border-color: #E0D6C0; }
.fb-btn.selected-up { background: #F0E6CC; color: #C4A35A; border-color: #C4A35A; }
.fb-btn.selected-down { background: #FDE8E8; color: #D66; border-color: #D66; }

/* === RECAP CARD === */
.recap-card {
    background: linear-gradient(135deg, #FFFDF7, #FBF5E8);
    border: 1px solid #F0E6CC;
    border-radius: 20px;
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: 0 4px 24px rgba(196, 163, 90, 0.08);
}
.recap-badge {
    display: inline-block;
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #C4A35A;
    background: rgba(196, 163, 90, 0.12);
    border-radius: 6px;
    padding: 0.2rem 0.6rem;
    margin-bottom: 0.8rem;
}
.recap-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.15rem;
    font-weight: 600;
    color: #1A1A1A;
    margin-bottom: 0.8rem;
}
.recap-item {
    display: flex;
    gap: 10px;
    margin-bottom: 0.55rem;
    font-size: 0.82rem;
    line-height: 1.5;
    color: #4A4640;
}
.recap-icon {
    width: 22px;
    height: 22px;
    border-radius: 6px;
    background: rgba(196, 163, 90, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    font-size: 0.7rem;
    margin-top: 1px;
}
.recap-label {
    font-weight: 600;
    color: #2C2C2C;
    font-size: 0.72rem;
    letter-spacing: 0.02em;
}

/* === AUDIO BUTTON === */
.audio-section {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-top: 0.5rem;
}
.audio-label {
    font-size: 0.7rem;
    color: #B0A898;
    font-style: italic;
}

/* === LOADING === */
.loading-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 1rem;
}
.loading-bubble {
    background: #FFFFFF;
    border: 1px solid #EFEBE5;
    border-radius: 20px 20px 20px 4px;
    padding: 0.9rem 1.15rem;
    display: flex;
    align-items: center;
    gap: 6px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.03);
}
.loading-text {
    font-size: 0.8rem;
    color: #B0A898;
    font-style: italic;
}
.dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #C4A35A;
    animation: pulse 1.4s ease-in-out infinite;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes pulse {
    0%, 80%, 100% { opacity: 0.12; transform: scale(0.8); }
    40% { opacity: 1; transform: scale(1); }
}

/* === CHAT INPUT === */
[data-testid="stChatInput"] {
    position: fixed !important;
    bottom: 0 !important;
    left: 280px !important;
    right: 0 !important;
    background: rgba(250, 250, 248, 0.9) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-top: 1px solid #EFEBE5 !important;
    padding: 0.7rem 0 0.9rem 0 !important;
    z-index: 998 !important;
    display: flex !important;
    justify-content: center !important;
    box-shadow: none !important;
}
[data-testid="stChatInput"] > div {
    max-width: 560px !important;
    width: 100% !important;
    padding: 0 !important;
    margin: 0 auto !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stChatInput"] div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stChatInput"] textarea {
    background: #FFFFFF !important;
    border: 1.5px solid #E8E4DC !important;
    border-radius: 50px !important;
    padding: 0.72rem 1.2rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
    color: #2C2C2C !important;
    box-shadow: 0 2px 20px rgba(0,0,0,0.04) !important;
    resize: none !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #C4A35A !important;
    box-shadow: 0 0 0 3px rgba(196, 163, 90, 0.08), 0 2px 20px rgba(0,0,0,0.04) !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #B0A898 !important;
    font-style: italic !important;
    font-weight: 300 !important;
}
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #C4A35A, #D4B66A) !important;
    border: none !important;
    border-radius: 50% !important;
    color: white !important;
    box-shadow: 0 2px 10px rgba(196, 163, 90, 0.25) !important;
    transition: all 0.25s ease !important;
}
[data-testid="stChatInput"] button:hover {
    background: linear-gradient(135deg, #B08F4A, #C4A35A) !important;
    transform: scale(1.06) !important;
    box-shadow: 0 4px 16px rgba(196, 163, 90, 0.35) !important;
}

/* === STREAMLIT OVERRIDES === */
.stButton > button {
    background: transparent !important;
    border: 1.5px solid #E0DBD3 !important;
    border-radius: 50px !important;
    padding: 0.35rem 0.9rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.66rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: #8A847C !important;
    transition: all 0.25s ease !important;
}
.stButton > button:hover {
    border-color: #C4A35A !important;
    color: #C4A35A !important;
    background: rgba(196, 163, 90, 0.06) !important;
}

/* Audio input styling */
.stAudioInput > div {
    border-radius: 16px !important;
    border: 1.5px solid #E8E4DC !important;
}
.stAudioInput > div > div {
    background: transparent !important;
}

/* === MOBILE === */
@media (max-width: 768px) {
    .coach-title { font-size: 2.4rem !important; }
    .bubble { max-width: 88% !important; font-size: 0.83rem !important; }
    .main .block-container { max-width: 100% !important; padding: 0 1rem 12rem 1rem !important; }
    [data-testid="stChatInput"] { left: 0 !important; padding-bottom: 3.5rem !important; }
    .gate-bar { max-width: 260px; }
    .recap-card { padding: 1.2rem; }
    .feedback-row { margin-left: 0; }
    /* Fix #16: audio input full width on mobile */
    .stAudioInput { width: 100% !important; }
}

/* === SCROLLBAR === */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #E0DBD3; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #C4A35A; }

</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────
# SVG
# ─────────────────────────────────────────────────────────────────────────
USER_SVG = """<svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="16" fill="#2C2C2C"/>
  <circle cx="16" cy="12" r="4.5" fill="#C4A35A" opacity="0.85"/>
  <path d="M7 26c0-5 4-9 9-9s9 4 9 9" fill="#C4A35A" opacity="0.65"/>
</svg>"""

COACH_SVG = """<svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="cg" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" style="stop-color:#C4A35A"/>
    <stop offset="100%" style="stop-color:#DFC070"/>
  </linearGradient></defs>
  <circle cx="16" cy="16" r="16" fill="url(#cg)"/>
  <text x="16" y="21" text-anchor="middle" font-size="13" fill="white"
        font-family="'Cormorant Garamond',serif" font-weight="600">&#9672;</text>
</svg>"""

# ─────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────

def render_gate_bar(gate):
    labels = ['Ascolto', 'Raccolta', 'Diagnosi', 'Intervento']
    parts = []
    for i in range(4):
        d = 'active' if i == gate else ('passed' if i < gate else '')
        l = 'active' if i == gate else ('passed' if i < gate else '')
        parts.append(f'<div class="gate-step"><div class="gate-dot {d}"></div><div class="gate-lbl {l}">{labels[i]}</div></div>')
        if i < 3:
            c = 'active' if i < gate else ''
            parts.append(f'<div class="gate-conn {c}"></div>')
    return f'<div class="gate-bar">{"".join(parts)}</div>'


def render_message(content, role):
    html = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\n---+\n', '\n<hr style="border:none;border-top:1px solid #EFEBE5;margin:10px 0;">\n', html)

    lines = html.split('\n')
    result = []
    for line in lines:
        line = line.rstrip()
        m = re.match(r'^(\d+\.)\s+(.*)', line)
        if m:
            result.append(
                '<div style="display:flex;gap:8px;margin:5px 0;">'
                '<span style="color:#C4A35A;font-weight:600;flex-shrink:0;min-width:20px;">' + m.group(1) + '</span>'
                '<span>' + m.group(2) + '</span></div>')
            continue
        m2 = re.match(r'^[-*]\s+(.*)', line)
        if m2:
            result.append(
                '<div style="display:flex;gap:8px;margin:4px 0;">'
                '<span style="color:#C4A35A;flex-shrink:0;font-size:0.5em;margin-top:6px;">&#9679;</span>'
                '<span>' + m2.group(1) + '</span></div>')
            continue
        if line.strip() == '':
            result.append('<div style="height:7px;"></div>')
            continue
        result.append('<span>' + line + '</span><br>')

    body = ''.join(result)
    if role == "user":
        return f'<div class="msg-row user"><div class="avatar avatar-user">{USER_SVG}</div><div class="bubble bubble-user">{body}</div></div>'
    return f'<div class="msg-row"><div class="avatar avatar-coach">{COACH_SVG}</div><div class="bubble bubble-coach">{body}</div></div>'


def render_feedback(msg_idx, current_feedback=None):
    up_cls = 'selected-up' if current_feedback == 1 else ''
    dn_cls = 'selected-down' if current_feedback == -1 else ''
    return f"""<div class="feedback-row">
        <div class="fb-btn {up_cls}" title="Utile">&#9650;</div>
        <div class="fb-btn {dn_cls}" title="Non utile">&#9660;</div>
    </div>"""


def render_recap_card(session):
    diagnosis = session.get('diagnosis')
    bdm = session.get('bdm_mapping')
    if not diagnosis and not bdm:
        return ""

    items = []
    if bdm and bdm.get('patterns'):
        top = bdm['patterns'][0]
        items.append(f'<div class="recap-item"><div class="recap-icon">&#9672;</div><div><div class="recap-label">Pattern dominante</div>{top["bdm_id"]} — {top["pattern_name"]} ({top["probability"]}%)</div></div>')

    if diagnosis:
        if diagnosis.get('dominant'):
            items.append(f'<div class="recap-item"><div class="recap-icon">&#9673;</div><div><div class="recap-label">Diagnosi</div>{diagnosis["dominant"][:200]}</div></div>')
        if diagnosis.get('rival'):
            items.append(f'<div class="recap-item"><div class="recap-icon">&#9671;</div><div><div class="recap-label">Ipotesi rivale</div>{diagnosis["rival"][:150]}</div></div>')

    validation = session.get('validation_history')
    if validation:
        last = validation[-1]
        score = last.get('media', '-')
        items.append(f'<div class="recap-item"><div class="recap-icon">&#10003;</div><div><div class="recap-label">Punteggio qualita</div>{score}/10</div></div>')

    if not items:
        return ""

    return f"""<div class="recap-card">
        <div class="recap-badge">Riepilogo sessione</div>
        <div class="recap-title">Analisi completata</div>
        {''.join(items)}
    </div>"""


def transcribe_audio(audio_bytes):
    """Trascrive audio usando OpenAI Whisper."""
    import tempfile, os
    tmp_path = None
    try:
        from openai import OpenAI
        api_key = None
        try:
            api_key = st.secrets['OPENAI_API_KEY']
        except Exception:
            api_key = os.getenv('OPENAI_API_KEY')

        if not api_key:
            st.warning("Chiave OpenAI non configurata per la trascrizione vocale.")
            return None

        client = OpenAI(api_key=api_key)

        # Streamlit audio_input restituisce WebM — Whisper accetta webm, mp3, wav, m4a
        tmp_path = tempfile.mktemp(suffix='.webm')
        with open(tmp_path, 'wb') as f:
            f.write(audio_bytes)

        with open(tmp_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="it"
            )
        return transcript.text if transcript and transcript.text else None

    except Exception as e:
        error_msg = str(e)
        if 'too large' in error_msg.lower() or 'size' in error_msg.lower():
            st.warning("Audio troppo lungo. Prova con un messaggio piu breve (max 30 secondi).")
        else:
            st.warning(f"Errore trascrizione: {error_msg[:100]}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def format_session_date(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return dt.strftime('%d/%m')
    except Exception:
        return ""

# ─────────────────────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = None
if 'feedback_map' not in st.session_state:
    st.session_state.feedback_map = {}
if 'last_audio_id' not in st.session_state:
    st.session_state.last_audio_id = None

# ─────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────
with st.sidebar:
    # New session button
    if st.button("+ Nuova sessione", key="new_session_btn", use_container_width=True):
        reset_session()
        st.session_state.messages = []
        st.session_state.current_session_id = None
        st.session_state.feedback_map = {}
        st.rerun()

    st.markdown('<div class="sidebar-section-title">Sessioni recenti</div>', unsafe_allow_html=True)

    # List sessions
    sessions = list_sessions(limit=15)
    if sessions:
        for sess in sessions:
            is_active = st.session_state.current_session_id == sess['id']
            title = sess.get('title', 'Sessione senza titolo')
            date_str = format_session_date(sess.get('created_at', ''))
            active_cls = 'active' if is_active else ''

            col_s, col_d = st.columns([5, 1])
            with col_s:
                if st.button(
                    f"{'● ' if is_active else ''}{title[:35]}",
                    key=f"sess_{sess['id']}",
                    use_container_width=True
                ):
                    # Load this session
                    reset_session()
                    st.session_state.current_session_id = sess['id']
                    stored_messages = load_messages(sess['id'])
                    st.session_state.messages = [
                        {'role': m['role'], 'content': m['content'], 'id': m.get('id')}
                        for m in stored_messages
                    ]
                    st.session_state.feedback_map = {
                        m.get('id'): m.get('feedback')
                        for m in stored_messages if m.get('feedback')
                    }
                    # Fix #6: rebuild completo dello stato agente
                    agent_session = get_session()
                    for m in st.session_state.messages:
                        agent_session['conversation'].append({
                            'role': m['role'], 'content': m['content']
                        })
                    agent_session['gate'] = sess.get('gate', 0)
                    # Se gate >= 2, riesegui BDM mapping dalla conversazione
                    if agent_session['gate'] >= 2 and len(agent_session['conversation']) >= 4:
                        try:
                            from agent import map_bdm_patterns
                            map_bdm_patterns()
                        except Exception:
                            pass
                    # Se gate >= 3, riesegui micro-gate per ricostruire diagnosis
                    if agent_session['gate'] >= 3 and len(agent_session['conversation']) >= 6:
                        try:
                            from agent import validate_micro_gate
                            validate_micro_gate()
                        except Exception:
                            pass
                    st.rerun()
            with col_d:
                if st.button("x", key=f"del_{sess['id']}", help="Elimina"):
                    delete_session(sess['id'])
                    if st.session_state.current_session_id == sess['id']:
                        st.session_state.messages = []
                        st.session_state.current_session_id = None
                        reset_session()
                    st.rerun()
    else:
        st.markdown(
            '<p style="font-size:0.75rem;color:#5A5650;padding:0.5rem 0.2rem;font-style:italic;">'
            'Nessuna sessione salvata</p>',
            unsafe_allow_html=True
        )

    # Supabase status
    if not SUPABASE_AVAILABLE:
        st.markdown(
            '<p style="font-size:0.65rem;color:#5A5650;padding:1rem 0.2rem 0 0.2rem;">'
            '&#9432; Le sessioni non vengono salvate.<br>Configura Supabase per la persistenza.</p>',
            unsafe_allow_html=True
        )

# ─────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="coach-header">
    <div class="coach-title">Atomic <strong>Habits</strong> Coach</div>
    <div class="coach-subtitle">Behavior change &middot; Diagnosi &middot; Intervento su misura</div>
    <div class="header-line"></div>
</div>
""", unsafe_allow_html=True)

# Gate bar
agent_s = get_session()
st.markdown(render_gate_bar(agent_s['gate']), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────
# EMPTY STATE with clickable prompts
# ─────────────────────────────────────────────────────────────────────────
SUGGESTED_PROMPTS = {
    "Costanza": "Vorrei essere piu costante con una buona abitudine ma dopo qualche giorno mollo sempre",
    "Motivazione": "Perdo la motivazione dopo le prime settimane e non riesco a mantenere il ritmo",
    "Produttivita": "Voglio essere piu produttivo ma mi distraggo continuamente durante la giornata",
    "Recovery": "Avevo una buona abitudine ma l'ho persa e non riesco a ricominciare",
    "Salute": "Vorrei fare esercizio regolarmente ma trovo sempre una scusa per non farlo",
}

if not st.session_state.messages:
    st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">&#9672;</div>
            <h3>Inizia una sessione</h3>
            <p>Descrivi il comportamento su cui vuoi lavorare. Il Coach analizzer&agrave;
            la situazione e costruir&agrave; un intervento personalizzato.</p>
        </div>
    """, unsafe_allow_html=True)

    # Clickable prompt chips
    st.markdown("")
    cols = st.columns(len(SUGGESTED_PROMPTS))
    for i, (label, prompt_text) in enumerate(SUGGESTED_PROMPTS.items()):
        with cols[i]:
            if st.button(label, key=f"chip_{label}", use_container_width=True):
                st.session_state._pending_prompt = prompt_text
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────
# MESSAGES
# ─────────────────────────────────────────────────────────────────────────
for i, message in enumerate(st.session_state.messages):
    st.markdown(render_message(message["content"], message["role"]), unsafe_allow_html=True)

    # Feedback buttons for coach messages
    if message["role"] == "assistant":
        msg_id = message.get('id', f'local_{i}')
        current_fb = st.session_state.feedback_map.get(msg_id)

        fc1, fc2, fc3 = st.columns([0.06, 0.06, 0.88])
        with fc1:
            if st.button("▲", key=f"up_{i}", help="Risposta utile"):
                st.session_state.feedback_map[msg_id] = 1
                if msg_id and not msg_id.startswith('local_'):
                    save_feedback(msg_id, 1)
                st.rerun()
        with fc2:
            if st.button("▼", key=f"dn_{i}", help="Risposta non utile"):
                st.session_state.feedback_map[msg_id] = -1
                if msg_id and not msg_id.startswith('local_'):
                    save_feedback(msg_id, -1)
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────
# RECAP CARD (dopo Gate 3)
# ─────────────────────────────────────────────────────────────────────────
if agent_s['gate'] >= 3 and st.session_state.messages:
    recap_html = render_recap_card(agent_s)
    if recap_html:
        st.markdown(recap_html, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────
# AUDIO INPUT (full width come la chat input)
# ─────────────────────────────────────────────────────────────────────────
try:
    audio_data = st.audio_input("Oppure registra un messaggio vocale",
                                key="audio_input")
    if audio_data:
        import hashlib
        audio_bytes = audio_data.getvalue()
        if audio_bytes and len(audio_bytes) > 100:
            audio_hash = hashlib.md5(audio_bytes).hexdigest()
            if audio_hash != st.session_state.last_audio_id:
                st.session_state.last_audio_id = audio_hash
                with st.spinner("Trascrizione in corso..."):
                    try:
                        transcription = transcribe_audio(audio_bytes)
                    except Exception as e:
                        transcription = None
                        st.warning(f"Errore durante la trascrizione: {str(e)[:80]}")
                if transcription:
                    st.session_state._pending_prompt = transcription
                    st.rerun()
                elif transcription is None and not st.session_state.get('_audio_error_shown'):
                    st.session_state._audio_error_shown = True
except Exception:
    pass

# ─────────────────────────────────────────────────────────────────────────
# CHAT INPUT + PROCESSING
# ─────────────────────────────────────────────────────────────────────────

# Fix #17: safe pop — salva prima di consumare, così se crasha possiamo recuperare
pending = st.session_state.pop('_pending_prompt', None)
st.session_state._audio_error_shown = False  # reset error flag

prompt = pending or st.chat_input("Descrivi il tuo caso...")

if prompt:
    # Create session if needed
    if not st.session_state.current_session_id:
        title = prompt[:60].strip()
        sid = create_session(title)
        st.session_state.current_session_id = sid

    sid = st.session_state.current_session_id

    # Save & display user message
    user_msg_id = save_message(sid, 'user', prompt)
    st.session_state.messages.append({"role": "user", "content": prompt, "id": user_msg_id})
    st.markdown(render_message(prompt, "user"), unsafe_allow_html=True)

    # Loading
    loading = st.empty()
    loading.markdown(f"""<div class="loading-row">
        <div class="avatar">{COACH_SVG}</div>
        <div class="loading-bubble">
            <span class="loading-text">Analisi in corso</span>
            <div class="dot"></div><div class="dot"></div><div class="dot"></div>
        </div>
    </div>""", unsafe_allow_html=True)

    # Get response
    reply = chat(prompt)
    loading.empty()

    # Save & display assistant message
    asst_msg_id = save_message(sid, 'assistant', reply)
    st.session_state.messages.append({"role": "assistant", "content": reply, "id": asst_msg_id})

    # Fix #12: sincronizza gate e titolo IMMEDIATAMENTE dopo la risposta
    agent_s = get_session()
    try:
        update_session(sid, gate=agent_s['gate'])
        if len(st.session_state.messages) == 2:
            update_session(sid, title=prompt[:60].strip())
    except Exception as e:
        pass  # non bloccare il flusso se il DB non risponde

    st.rerun()
