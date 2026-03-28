import streamlit as st
from agent import chat, session
import re
from datetime import datetime

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
    padding: 0 2rem 9rem 2rem !important;
    margin: 0 auto !important;
}

/* ─── BUTTONS ──────────────────────────────────────────────── */
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

/* ─── DOWNLOAD BUTTON ──────────────────────────────────────── */
.stDownloadButton > button {
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
.stDownloadButton > button:hover {
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
    flex-shrink: 0;
    margin-top: 2px;
}
.avatar-user { background: #2C2C2C; }
.avatar-coach {
    background: linear-gradient(135deg, #C4A35A, #E8C97A);
    color: #FFFFFF;
    font-size: 0.65rem;
    font-family: 'Cormorant Garamond', serif;
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

/* ─── LOADING INDICATOR ────────────────────────────────────── */
.loading-row {
    display: flex;
    align-items: flex-start;
    gap: 0.7rem;
    margin-bottom: 0.9rem;
}
.loading-bubble {
    background: #FFFFFF;
    border: 1px solid #E8E4DC;
    border-radius: 20px 20px 20px 4px;
    padding: 0.85rem 1.15rem;
    display: flex;
    align-items: center;
    gap: 6px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.loading-text {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.82rem;
    color: #B0A898;
    font-style: italic;
}
.dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #C4A35A;
    animation: pulse 1.4s ease-in-out infinite;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes pulse {
    0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
    40% { opacity: 1; transform: scale(1); }
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
    [data-testid="stChatInput"] { padding-bottom: 3.5rem !important; }
}

/* ─── SCROLLBAR ────────────────────────────────────────────── */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #D8D3CA; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #C4A35A; }

</style>
""", unsafe_allow_html=True)

# ─── AVATAR SVG ─────────────────────────────────────────────────────────────
USER_AVATAR_SVG = """<svg width="30" height="30" viewBox="0 0 30 30" xmlns="http://www.w3.org/2000/svg">
  <circle cx="15" cy="15" r="15" fill="#2C2C2C"/>
  <circle cx="15" cy="11" r="4.5" fill="#C4A35A"/>
  <path d="M6 24c0-4.97 4.03-9 9-9s9 4.03 9 9" fill="#C4A35A" opacity="0.85"/>
</svg>"""

COACH_AVATAR_SVG = """<svg width="30" height="30" viewBox="0 0 30 30" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="cg" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" style="stop-color:#C4A35A"/>
    <stop offset="100%" style="stop-color:#E8C97A"/>
  </linearGradient></defs>
  <circle cx="15" cy="15" r="15" fill="url(#cg)"/>
  <text x="15" y="20" text-anchor="middle" font-size="13" fill="white" font-family="serif">&#9672;</text>
</svg>"""

LOADING_INDICATOR = f"""<div class="loading-row">
    <div class="avatar">{COACH_AVATAR_SVG}</div>
    <div class="loading-bubble">
        <span class="loading-text">Il Coach sta elaborando</span>
        <div class="dot"></div><div class="dot"></div><div class="dot"></div>
    </div>
</div>"""

# ─── RENDER MESSAGGIO ────────────────────────────────────────────────────────

def render_message(content, role):
    content_html = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    content_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content_html)
    content_html = content_html.replace("\n", "<br>")
    if role == "user":
        return f'<div class="msg-row user"><div class="avatar avatar-user">{USER_AVATAR_SVG}</div><div class="bubble bubble-user">{content_html}</div></div>'
    else:
        return f'<div class="msg-row"><div class="avatar avatar-coach">{COACH_AVATAR_SVG}</div><div class="bubble bubble-coach">{content_html}</div></div>'

# ─── GENERAZIONE TESTO CHAT (per download) ──────────────────────────────────

def generate_chat_text(messages: list) -> bytes:
    """
    Genera testo semplice della conversazione.
    Usato come fallback leggero e veloce — sempre disponibile senza librerie esterne.
    """
    lines = [
        f"ATOMIC HABITS COACH",
        f"Sessione del {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "=" * 50,
        ""
    ]
    for msg in messages:
        role = "TU" if msg['role'] == 'user' else "COACH"
        lines.append(f"{role}:")
        lines.append(msg['content'])
        lines.append("\n" + "─" * 40 + "\n")
    return "\n".join(lines).encode('utf-8')


def generate_pdf_bytes(messages: list) -> tuple:
    """
    Genera PDF della conversazione.
    Restituisce (bytes, mime_type).
    Se reportlab non è disponibile, restituisce testo con mime corretto.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        import io

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm)

        styles = getSampleStyleSheet()
        title_s = ParagraphStyle('AHTitle', parent=styles['Heading1'],
            fontSize=18, textColor=colors.HexColor('#1A1A1A'), spaceAfter=4)
        sub_s = ParagraphStyle('AHSub', parent=styles['Normal'],
            fontSize=9, textColor=colors.HexColor('#999999'), spaceAfter=18)
        label_s = ParagraphStyle('AHLabel', parent=styles['Normal'],
            fontSize=7, textColor=colors.HexColor('#C4A35A'),
            spaceAfter=2, fontName='Helvetica-Bold')
        user_s = ParagraphStyle('AHUser', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor('#2C2C2C'),
            backColor=colors.HexColor('#F0EDE8'),
            leftIndent=60, spaceAfter=10,
            borderPadding=(6, 8, 6, 8))
        coach_s = ParagraphStyle('AHCoach', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor('#2C2C2C'),
            backColor=colors.HexColor('#FAFAFA'),
            rightIndent=60, spaceAfter=10,
            borderPadding=(6, 8, 6, 8))

        story = [
            Paragraph("Atomic Habits Coach", title_s),
            Paragraph(f"Sessione del {datetime.now().strftime('%d %B %Y, %H:%M')}", sub_s),
        ]

        for msg in messages:
            # Escape XML per reportlab
            content = (msg['content']
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))
            if msg['role'] == 'user':
                story.append(Paragraph("TU", label_s))
                story.append(Paragraph(content, user_s))
            else:
                story.append(Paragraph("COACH", label_s))
                story.append(Paragraph(content, coach_s))
            story.append(Spacer(1, 4))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue(), "application/pdf"

    except ImportError:
        # reportlab non installato — fallback a testo
        return generate_chat_text(messages), "text/plain"
    except Exception:
        # Qualsiasi altro errore — fallback sicuro a testo
        return generate_chat_text(messages), "text/plain"

# ─── TOP BAR ────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([6, 2, 2])

with col2:
    messages = st.session_state.get('messages', [])
    if messages:
        # Genera solo testo (veloce, nessuna dipendenza esterna)
        # Il PDF viene generato al click grazie a st.download_button
        chat_bytes, mime = generate_pdf_bytes(messages)
        ext = "pdf" if mime == "application/pdf" else "txt"
        st.download_button(
            label="↓ Scarica",
            data=chat_bytes,
            file_name=f"atomic_habits_coach_{datetime.now().strftime('%Y%m%d_%H%M')}.{ext}",
            mime=mime,
            key="download_chat"
        )

with col3:
    if st.button("↺ Nuovo caso"):
        session['conversation'] = []
        session['gate'] = 0
        session['retrieval_done'] = False
        session['areas_status'] = {}
        session['retrieved_modules'] = None
        session['diagnosis'] = None
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
            <div class="icon">&#9672;</div>
            <p>Descrivi il comportamento su cui vuoi lavorare.<br>
            Il Coach analizzerà la situazione e costruirà un intervento su misura.</p>
        </div>
    """, unsafe_allow_html=True)

for message in st.session_state.messages:
    st.markdown(render_message(message["content"], message["role"]), unsafe_allow_html=True)

if prompt := st.chat_input("Descrivi il tuo caso..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(render_message(prompt, "user"), unsafe_allow_html=True)

    # Loading indicator animato
    loading_placeholder = st.empty()
    loading_placeholder.markdown(LOADING_INDICATOR, unsafe_allow_html=True)

    reply = chat(prompt)

    loading_placeholder.empty()

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()