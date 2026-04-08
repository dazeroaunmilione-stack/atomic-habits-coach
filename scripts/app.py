import streamlit as st
from agent import chat, reset_session, get_session
import re
from datetime import datetime

st.set_page_config(
    page_title="Atomic Habits Coach",
    page_icon="◈",
    layout="centered"
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;500;600;700&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">

<style>

/* === RESET & BASE === */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background: #F8F7F5 !important;
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

[data-testid="stHeader"] { background: transparent !important; border: none !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
.stDeployButton { display: none; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }

/* === MAIN CONTAINER === */
.main .block-container {
    max-width: 720px !important;
    padding: 0 1.5rem 9rem 1.5rem !important;
    margin: 0 auto !important;
}

/* === BUTTONS === */
.stButton > button {
    background: transparent !important;
    border: 1.5px solid #E0DBD3 !important;
    border-radius: 50px !important;
    padding: 0.4rem 1rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.68rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: #8A847C !important;
    cursor: pointer !important;
    transition: all 0.25s ease !important;
}
.stButton > button:hover {
    border-color: #C4A35A !important;
    color: #C4A35A !important;
    background: rgba(196, 163, 90, 0.06) !important;
}

/* === DOWNLOAD BUTTON === */
.stDownloadButton > button {
    background: transparent !important;
    border: 1.5px solid #E0DBD3 !important;
    border-radius: 50px !important;
    padding: 0.4rem 1rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.68rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: #8A847C !important;
    cursor: pointer !important;
    transition: all 0.25s ease !important;
}
.stDownloadButton > button:hover {
    border-color: #C4A35A !important;
    color: #C4A35A !important;
    background: rgba(196, 163, 90, 0.06) !important;
}

/* === HEADER === */
.coach-header {
    text-align: center;
    padding: 2.5rem 0 1.8rem 0;
    margin-bottom: 0;
}
.coach-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 3.4rem;
    font-weight: 300;
    color: #1A1A1A;
    letter-spacing: 0.03em;
    line-height: 1.1;
    margin-bottom: 0.6rem;
}
.coach-title strong { font-weight: 600; color: #C4A35A; }
.coach-subtitle {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.72rem;
    font-weight: 400;
    color: #A09A92;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}
.header-divider {
    width: 40px;
    height: 1px;
    background: linear-gradient(90deg, transparent, #C4A35A, transparent);
    margin: 1rem auto 0 auto;
}

/* === GATE PROGRESS === */
.gate-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    margin: 1rem auto 1.2rem auto;
    max-width: 320px;
}
.gate-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    position: relative;
}
.gate-step-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #E8E4DC;
    border: 2px solid #E8E4DC;
    transition: all 0.4s ease;
    z-index: 2;
}
.gate-step-dot.active {
    background: #C4A35A;
    border-color: #C4A35A;
    box-shadow: 0 0 10px rgba(196, 163, 90, 0.35);
}
.gate-step-dot.passed {
    background: #C4A35A;
    border-color: #C4A35A;
}
.gate-step-label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.58rem;
    font-weight: 500;
    color: #C5BFB6;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-top: 5px;
    transition: color 0.3s ease;
}
.gate-step-label.active { color: #C4A35A; font-weight: 600; }
.gate-step-label.passed { color: #A09A92; }
.gate-connector {
    height: 2px;
    flex: 1;
    background: #E8E4DC;
    margin: 0 -2px;
    margin-bottom: 18px;
    transition: background 0.4s ease;
}
.gate-connector.active {
    background: linear-gradient(90deg, #C4A35A, #D4B66A);
}

/* === EMPTY STATE === */
.empty-state {
    text-align: center;
    padding: 2.5rem 2rem;
    background: #FFFFFF;
    border-radius: 24px;
    border: 1px solid #EDE9E2;
    box-shadow: 0 4px 30px rgba(0,0,0,0.03);
    margin: 0.5rem 0 1rem 0;
}
.empty-icon {
    width: 52px;
    height: 52px;
    border-radius: 50%;
    background: linear-gradient(135deg, #FBF5E8, #F0E6CC);
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 1rem auto;
    font-size: 1.3rem;
    color: #C4A35A;
}
.empty-state h3 {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.2rem;
    font-weight: 500;
    color: #1A1A1A;
    margin-bottom: 0.5rem;
}
.empty-state p {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.82rem;
    font-weight: 400;
    line-height: 1.75;
    color: #A09A92;
    max-width: 360px;
    margin: 0 auto;
}
.empty-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin-top: 1.2rem;
}
.empty-chip {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.7rem;
    font-weight: 500;
    color: #C4A35A;
    background: #FBF5E8;
    border: 1px solid #F0E6CC;
    border-radius: 50px;
    padding: 0.28rem 0.75rem;
    letter-spacing: 0.02em;
}

/* === CHAT MESSAGES === */
.msg-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 1rem;
    animation: fadeIn 0.35s ease;
}
.msg-row.user { flex-direction: row-reverse; }

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
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
.avatar-coach {
    background: linear-gradient(135deg, #C4A35A, #E0C476);
    color: #FFFFFF;
}

.bubble {
    max-width: 78%;
    padding: 0.9rem 1.2rem;
    font-size: 0.88rem;
    line-height: 1.72;
    font-family: 'DM Sans', sans-serif;
    font-weight: 400;
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
    border: 1px solid #EDE9E2;
    box-shadow: 0 2px 16px rgba(0,0,0,0.035);
}

.bubble-coach strong {
    color: #C4A35A;
    font-weight: 600;
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
    border: 1px solid #EDE9E2;
    border-radius: 20px 20px 20px 4px;
    padding: 0.9rem 1.2rem;
    display: flex;
    align-items: center;
    gap: 6px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.035);
}
.loading-text {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.8rem;
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
    0%, 80%, 100% { opacity: 0.15; transform: scale(0.8); }
    40% { opacity: 1; transform: scale(1); }
}

/* === CHAT INPUT === */
[data-testid="stChatInput"] {
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    background: rgba(248, 247, 245, 0.92) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border-top: 1px solid #EDE9E2 !important;
    padding: 0.8rem 0 1rem 0 !important;
    z-index: 998 !important;
    display: flex !important;
    justify-content: center !important;
    box-shadow: none !important;
    outline: none !important;
}
[data-testid="stChatInput"] > div {
    max-width: 540px !important;
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
    border: 1.5px solid #E0DBD3 !important;
    border-radius: 50px !important;
    padding: 0.75rem 1.3rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.86rem !important;
    color: #2C2C2C !important;
    box-shadow: 0 2px 16px rgba(0,0,0,0.04) !important;
    resize: none !important;
    outline: none !important;
    transition: border-color 0.2s ease !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #C4A35A !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(196, 163, 90, 0.1) !important;
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
    box-shadow: 0 2px 10px rgba(196, 163, 90, 0.3) !important;
    outline: none !important;
    transition: all 0.25s ease !important;
}
[data-testid="stChatInput"] button:hover {
    background: linear-gradient(135deg, #B08F4A, #C4A35A) !important;
    transform: scale(1.05) !important;
    box-shadow: 0 4px 14px rgba(196, 163, 90, 0.4) !important;
}

/* === MOBILE === */
@media (max-width: 768px) {
    .coach-title { font-size: 2.6rem !important; }
    .bubble { max-width: 88% !important; font-size: 0.84rem !important; }
    .main .block-container { padding: 0 1rem 11rem 1rem !important; }
    [data-testid="stChatInput"] { padding-bottom: 3.5rem !important; }
    .empty-chips { gap: 6px; }
    .gate-bar { max-width: 260px; }
}

/* === SCROLLBAR === */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #E0DBD3; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #C4A35A; }

</style>
""", unsafe_allow_html=True)

# --- AVATAR SVG ---
USER_AVATAR_SVG = """<svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="16" fill="#2C2C2C"/>
  <circle cx="16" cy="12" r="4.5" fill="#C4A35A" opacity="0.9"/>
  <path d="M7 26c0-5 4-9 9-9s9 4 9 9" fill="#C4A35A" opacity="0.7"/>
</svg>"""

COACH_AVATAR_SVG = """<svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="cg" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" style="stop-color:#C4A35A"/>
    <stop offset="100%" style="stop-color:#E0C476"/>
  </linearGradient></defs>
  <circle cx="16" cy="16" r="16" fill="url(#cg)"/>
  <text x="16" y="21" text-anchor="middle" font-size="13" fill="white" font-family="'Cormorant Garamond', serif" font-weight="600">&#9672;</text>
</svg>"""

LOADING_INDICATOR = f"""<div class="loading-row">
    <div class="avatar">{COACH_AVATAR_SVG}</div>
    <div class="loading-bubble">
        <span class="loading-text">Analisi in corso</span>
        <div class="dot"></div><div class="dot"></div><div class="dot"></div>
    </div>
</div>"""

# --- GATE INDICATOR ---
def render_gate_bar(gate_level):
    labels = ['Ascolto', 'Raccolta', 'Diagnosi', 'Intervento']
    parts = []
    for i in range(4):
        dot_cls = 'active' if i == gate_level else ('passed' if i < gate_level else '')
        lbl_cls = 'active' if i == gate_level else ('passed' if i < gate_level else '')
        parts.append(f'<div class="gate-step"><div class="gate-step-dot {dot_cls}"></div><div class="gate-step-label {lbl_cls}">{labels[i]}</div></div>')
        if i < 3:
            conn_cls = 'active' if i < gate_level else ''
            parts.append(f'<div class="gate-connector {conn_cls}"></div>')
    return f'<div class="gate-bar">{"".join(parts)}</div>'

# --- RENDER MESSAGGIO ---
def render_message(content, role):
    html = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(
        r'\n---+\n',
        '\n<hr style="border:none;border-top:1px solid #EDE9E2;margin:10px 0;">\n',
        html
    )

    lines = html.split('\n')
    result = []

    for line in lines:
        line = line.rstrip()

        m = re.match(r'^(\d+\.)\s+(.*)', line)
        if m:
            num = m.group(1)
            text = m.group(2)
            result.append(
                '<div style="display:flex;gap:8px;margin:5px 0;">'
                '<span style="color:#C4A35A;font-weight:600;flex-shrink:0;min-width:20px;">' + num + '</span>'
                '<span>' + text + '</span>'
                '</div>'
            )
            continue

        m2 = re.match(r'^[-*]\s+(.*)', line)
        if m2:
            text = m2.group(1)
            result.append(
                '<div style="display:flex;gap:8px;margin:4px 0;">'
                '<span style="color:#C4A35A;flex-shrink:0;font-size:0.6em;margin-top:5px;">&#9679;</span>'
                '<span>' + text + '</span>'
                '</div>'
            )
            continue

        if line.strip() == '':
            result.append('<div style="height:8px;"></div>')
            continue

        result.append('<span>' + line + '</span><br>')

    content_html = ''.join(result)

    if role == "user":
        return (
            '<div class="msg-row user">'
            '<div class="avatar avatar-user">' + USER_AVATAR_SVG + '</div>'
            '<div class="bubble bubble-user">' + content_html + '</div>'
            '</div>'
        )
    else:
        return (
            '<div class="msg-row">'
            '<div class="avatar avatar-coach">' + COACH_AVATAR_SVG + '</div>'
            '<div class="bubble bubble-coach">' + content_html + '</div>'
            '</div>'
        )

# --- DOWNLOAD ---
def generate_chat_text(messages):
    lines = [
        "ATOMIC HABITS COACH",
        "Sessione del " + datetime.now().strftime('%d/%m/%Y %H:%M'),
        "=" * 50, ""
    ]
    for msg in messages:
        role = "TU" if msg['role'] == 'user' else "COACH"
        lines.append(role + ":")
        lines.append(msg['content'])
        lines.append("\n" + "-" * 40 + "\n")
    return "\n".join(lines).encode('utf-8')

def generate_pdf_bytes(messages):
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
            fontSize=9, textColor=colors.HexColor('#A09A92'), spaceAfter=18)
        label_s = ParagraphStyle('AHLabel', parent=styles['Normal'],
            fontSize=7, textColor=colors.HexColor('#C4A35A'),
            spaceAfter=2, fontName='Helvetica-Bold')
        user_s = ParagraphStyle('AHUser', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor('#2C2C2C'),
            backColor=colors.HexColor('#F8F7F5'),
            leftIndent=60, spaceAfter=10,
            borderPadding=(6, 8, 6, 8))
        coach_s = ParagraphStyle('AHCoach', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor('#2C2C2C'),
            backColor=colors.HexColor('#FAFAFA'),
            rightIndent=60, spaceAfter=10,
            borderPadding=(6, 8, 6, 8))

        story = [
            Paragraph("Atomic Habits Coach", title_s),
            Paragraph("Sessione del " + datetime.now().strftime('%d %B %Y, %H:%M'), sub_s),
        ]

        for msg in messages:
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
        return generate_chat_text(messages), "text/plain"
    except Exception:
        return generate_chat_text(messages), "text/plain"

# --- TOP BAR ---
col1, col2, col3 = st.columns([6, 2, 2])

with col2:
    messages = st.session_state.get('messages', [])
    if messages:
        chat_bytes, mime = generate_pdf_bytes(messages)
        ext = "pdf" if mime == "application/pdf" else "txt"
        st.download_button(
            label="Scarica",
            data=chat_bytes,
            file_name="atomic_habits_coach_" + datetime.now().strftime('%Y%m%d_%H%M') + "." + ext,
            mime=mime,
            key="download_chat"
        )

with col3:
    if st.button("Nuovo caso"):
        reset_session()
        st.session_state.messages = []
        st.rerun()

# --- HEADER ---
st.markdown("""
    <div class="coach-header">
        <div class="coach-title">Atomic <strong>Habits</strong> Coach</div>
        <div class="coach-subtitle">Behavior change &middot; Diagnosi &middot; Intervento su misura</div>
        <div class="header-divider"></div>
    </div>
""", unsafe_allow_html=True)

# --- GATE PROGRESS ---
s = get_session()
st.markdown(render_gate_bar(s['gate']), unsafe_allow_html=True)

# --- CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">&#9672;</div>
            <h3>Inizia una sessione</h3>
            <p>Descrivi il comportamento su cui vuoi lavorare. Il Coach analizzer&agrave;
            la situazione e costruir&agrave; un intervento personalizzato.</p>
            <div class="empty-chips">
                <span class="empty-chip">Abitudini</span>
                <span class="empty-chip">Produttivit&agrave;</span>
                <span class="empty-chip">Motivazione</span>
                <span class="empty-chip">Costanza</span>
                <span class="empty-chip">Recovery</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

for message in st.session_state.messages:
    st.markdown(render_message(message["content"], message["role"]), unsafe_allow_html=True)

if prompt := st.chat_input("Descrivi il tuo caso..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(render_message(prompt, "user"), unsafe_allow_html=True)

    loading_placeholder = st.empty()
    loading_placeholder.markdown(LOADING_INDICATOR, unsafe_allow_html=True)

    reply = chat(prompt)

    loading_placeholder.empty()

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
