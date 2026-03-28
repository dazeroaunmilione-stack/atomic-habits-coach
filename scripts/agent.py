import os
import re
import json
from dotenv import load_dotenv
import anthropic
from openai import OpenAI
from pinecone import Pinecone

# === PATH ASSOLUTI (funziona sia in locale che su Streamlit Cloud) ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, '..', 'output')
ENV_PATH = os.path.join(BASE_DIR, '..', '.env')

load_dotenv(ENV_PATH)

# === SETUP CLIENTS ===
def get_secret(key):
    try:
        import streamlit as st
        return st.secrets[key]
    except Exception:
        return os.getenv(key)

claude = anthropic.Anthropic(api_key=get_secret('ANTHROPIC_API_KEY'))
openai_client = OpenAI(api_key=get_secret('OPENAI_API_KEY'))
pc = Pinecone(api_key=get_secret('PINECONE_API_KEY'))
pinecone_index = pc.Index('atomic-habits-knowledge')

# === CARICA FILES ===
with open(os.path.join(OUTPUT_DIR, 'bdm_pre_gate.json'), 'r', encoding='utf-8') as f:
    BDM_PRE = json.load(f)

with open(os.path.join(OUTPUT_DIR, 'bdm_post_gate.json'), 'r', encoding='utf-8') as f:
    BDM_POST = json.load(f)

with open(os.path.join(BASE_DIR, 'system_prompt.txt'), 'r', encoding='utf-8') as f:
    SYSTEM_PROMPT = f.read()

# === STATO SESSIONE ===
session = {
    'gate': 0,
    'conversation': [],
    'areas_status': {},
    'diagnosis': None,
    'retrieval_done': False
}

# === POST-PROCESSING ===

def strip_process_blocks(text: str) -> str:
    cleaned = re.sub(r'<process[^>]*>.*?</process>', '', text, flags=re.DOTALL)
    cleaned = re.sub(r'<process[^>]*>.*', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

# === FUNZIONI RETRIEVAL ===

def get_embedding(text):
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000]
    )
    return response.data[0].embedding

def retrieve_modules(query, top_k=5, filter_metadata=None):
    embedding = get_embedding(query)
    results = pinecone_index.query(
        vector=embedding,
        top_k=top_k,
        include_metadata=True,
        filter=filter_metadata
    )
    return results.matches

def retrieve_modules_paired(dominant_query, rival_query, top_k=3):
    dominant = retrieve_modules(dominant_query, top_k)
    rival = retrieve_modules(rival_query, top_k)
    return dominant, rival

def format_bdm_for_prompt(gate_level):
    if gate_level < 2:
        return ""

    if gate_level == 2:
        lines = ["=== PATTERN DIAGNOSTICI DISPONIBILI (pre-gate) ==="]
        for p in BDM_PRE:
            lines.append(f"\n{p['diagnosis_id']}: {p['problem_pattern']}")
            lines.append(f"  Sintomo: {p['symptom_description']}")
            if p.get('disconfirming_signals'):
                lines.append(f"  Esclude: {p['disconfirming_signals']}")
        return '\n'.join(lines)

    if gate_level >= 3:
        lines = ["=== GUIDA DIAGNOSTICA COMPLETA (post-gate) ==="]
        for p in BDM_POST:
            lines.append(f"\n{p['diagnosis_id']}: {p['problem_pattern']}")
            lines.append(f"  Fase: {p.get('likely_behavior_phase', '')}")
            lines.append(f"  Causa: {p.get('likely_root_cause', '')}")
            lines.append(f"  Tecniche: {p.get('recommended_techniques', '')}")
            lines.append(f"  Moduli: {p.get('recommended_modules', '')}")
        return '\n'.join(lines)

def format_retrieved_modules(matches):
    if not matches:
        return ""
    lines = ["=== MODULI KNOWLEDGE BASE RECUPERATI ==="]
    for m in matches:
        meta = m.metadata
        lines.append(f"\nModulo {meta.get('module_id')}: {meta.get('module_title')}")
        lines.append(f"  Dominio: {meta.get('primary_domain')} | Fase: {meta.get('behavior_change_stage')}")
        lines.append(f"  Contenuto: {meta.get('text_preview', '')[:400]}")
    return '\n'.join(lines)

# === LOGICA DI GATE ===

def check_gate_advancement(user_message):
    if session['gate'] == 0:
        session['gate'] = 1
        return

    if session['gate'] == 1:
        user_turns = [m for m in session['conversation'] if m['role'] == 'user']
        if len(user_turns) >= 2:
            session['gate'] = 2

# === COSTRUZIONE PROMPT PER TURNO ===

def build_messages(user_input):
    gate_context = f"\n\n=== STATO CORRENTE SESSIONE ===\nGate attivo: {session['gate']}\n"

    if session['gate'] == 2:
        gate_context += "\nHai accesso al BDM pre-gate. Puoi usarlo per shortlist diagnostica ma NON per prescrivere tecniche.\n"
        gate_context += format_bdm_for_prompt(2)

    if session['gate'] >= 3:
        gate_context += "\nMicro-gate superato. Hai accesso a BDM completo e Knowledge base.\n"
        gate_context += format_bdm_for_prompt(3)

        if not session['retrieval_done'] and session.get('diagnosis'):
            dominant_query = session['diagnosis'].get('dominant', user_input)
            rival_query = session['diagnosis'].get('rival', user_input)
            dominant_modules, rival_modules = retrieve_modules_paired(dominant_query, rival_query)
            session['retrieval_done'] = True
            session['retrieved_modules'] = {
                'dominant': dominant_modules,
                'rival': rival_modules
            }

        if session.get('retrieved_modules'):
            gate_context += "\n" + format_retrieved_modules(session['retrieved_modules']['dominant'])
            gate_context += "\n=== MODULI PER TESTARE IPOTESI RIVALE ===\n"
            gate_context += format_retrieved_modules(session['retrieved_modules']['rival'])

    full_system = SYSTEM_PROMPT + gate_context

    messages = session['conversation'].copy()
    messages.append({'role': 'user', 'content': user_input})

    return full_system, messages

# === LOOP PRINCIPALE ===

def chat(user_input):
    check_gate_advancement(user_input)

    system, messages = build_messages(user_input)

    response = claude.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        system=system,
        messages=messages
    )

    assistant_reply = response.content[0].text
    assistant_reply = strip_process_blocks(assistant_reply)

    session['conversation'].append({'role': 'user', 'content': user_input})
    session['conversation'].append({'role': 'assistant', 'content': assistant_reply})

    if 'MICRO-GATE-SUPERATO' in assistant_reply or session['gate'] == 2:
        if len(session['conversation']) >= 6:
            session['gate'] = 3

    return assistant_reply

# === INTERFACCIA CHAT (solo uso locale diretto) ===

if __name__ == '__main__':
    print("=" * 60)
    print("ATOMIC HABITS AI COACH")
    print("Digita 'quit' per uscire | 'reset' per nuovo caso")
    print("=" * 60)
    print()

    while True:
        try:
            user_input = input("Tu: ").strip()
            if not user_input:
                continue
            if user_input.lower() == 'quit':
                print("Sessione terminata.")
                break
            if user_input.lower() == 'reset':
                session['conversation'] = []
                session['gate'] = 0
                session['retrieval_done'] = False
                session['retrieved_modules'] = None
                print("\n[Sessione resettata — nuovo caso]\n")
                continue
            reply = chat(user_input)
            print(f"\nCoach: {reply}")
            print(f"\n[Gate corrente: {session['gate']}]\n")
        except KeyboardInterrupt:
            print("\nInterrotto.")
            break