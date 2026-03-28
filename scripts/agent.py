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
    'retrieval_done': False,
    'retrieved_modules': None
}

# === POST-PROCESSING ===

def strip_process_blocks(text: str) -> str:
    cleaned = re.sub(r'<process[^>]*>.*?</process>', '', text, flags=re.DOTALL)
    cleaned = re.sub(r'<process[^>]*>.*', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

# === ESTRAZIONE DIAGNOSI PER RETRIEVAL ===

def extract_diagnosis_queries() -> dict:
    """
    Chiama Claude con la conversazione corrente e chiede di estrarre
    in JSON le query per il retrieval semantico su Pinecone:
    - dominant: descrizione della causa dominante identificata
    - rival: descrizione della causa rivale considerata
    - dominant_bdm: ID pattern BDM dominante (es. BD09)
    - rival_bdm: ID pattern BDM rivale (es. BD13)
    Restituisce un dict con queste 4 chiavi.
    """
    if not session['conversation']:
        return None

    conversation_text = "\n".join([
        f"{'Utente' if m['role'] == 'user' else 'Coach'}: {m['content']}"
        for m in session['conversation']
    ])

    extraction_prompt = f"""Analizza questa conversazione di coaching sul behavior change.

CONVERSAZIONE:
{conversation_text}

Basandoti su ciò che il Coach ha identificato nella conversazione, estrai le seguenti informazioni in formato JSON puro (nessun testo aggiuntivo, nessun markdown):

{{
  "dominant": "descrizione in italiano della causa dominante del blocco comportamentale (2-3 frasi che catturano il meccanismo specifico)",
  "rival": "descrizione in italiano della causa rivale considerata e perché è stata esclusa o trattata come secondaria (2-3 frasi)",
  "dominant_bdm": "ID del pattern BDM dominante se identificabile (es. BD09), altrimenti null",
  "rival_bdm": "ID del pattern BDM rivale se identificabile (es. BD13), altrimenti null"
}}

Se la diagnosi non è ancora stata completata nella conversazione, restituisci:
{{"dominant": null, "rival": null, "dominant_bdm": null, "rival_bdm": null}}"""

    try:
        response = claude.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=512,
            messages=[{"role": "user", "content": extraction_prompt}]
        )
        raw = response.content[0].text.strip()
        # Rimuove eventuali backtick markdown
        raw = re.sub(r'```json|```', '', raw).strip()
        result = json.loads(raw)
        # Valida che abbia le chiavi attese
        if result.get('dominant'):
            return result
        return None
    except Exception as e:
        print(f"[extract_diagnosis_queries] Errore: {e}")
        return None

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

def get_recommended_modules_from_bdm(bdm_id: str) -> list:
    """
    Dato un BDM ID (es. 'BD09'), restituisce la lista di module_id
    raccomandati dal BDM post-gate per quel pattern.
    """
    for pattern in BDM_POST:
        if pattern.get('diagnosis_id') == bdm_id:
            raw = pattern.get('recommended_modules', '')
            if raw:
                return [m.strip() for m in str(raw).split('|') if m.strip()]
    return []

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

# === ESECUZIONE RETRIEVAL ===

def run_retrieval_if_needed():
    """
    Eseguito quando gate >= 3 e retrieval non ancora fatto.
    1. Estrae diagnosi dalla conversazione via Claude
    2. Se ha BDM ID, usa i moduli raccomandati dal BDM per filtrare
    3. In parallelo fa retrieval semantico su dominant + rival query
    4. Salva i risultati in session['retrieved_modules']
    """
    if session['retrieval_done']:
        return
    if session['gate'] < 3:
        return

    diagnosis = extract_diagnosis_queries()
    if not diagnosis:
        return

    session['diagnosis'] = diagnosis

    dominant_query = diagnosis.get('dominant', '')
    rival_query = diagnosis.get('rival', dominant_query)

    # Retrieval semantico su query estratte
    dominant_modules, rival_modules = retrieve_modules_paired(
        dominant_query, rival_query, top_k=4
    )

    # Se BDM ID disponibili, recupera anche i moduli raccomandati dal BDM
    bdm_recommended = []
    dominant_bdm = diagnosis.get('dominant_bdm')
    if dominant_bdm:
        recommended_ids = get_recommended_modules_from_bdm(dominant_bdm)
        if recommended_ids:
            # Filtra Pinecone per module_id raccomandati
            for mod_id in recommended_ids[:3]:
                try:
                    filtered = retrieve_modules(
                        dominant_query,
                        top_k=1,
                        filter_metadata={"module_id": mod_id}
                    )
                    bdm_recommended.extend(filtered)
                except Exception:
                    pass

    session['retrieval_done'] = True
    session['retrieved_modules'] = {
        'dominant': dominant_modules,
        'rival': rival_modules,
        'bdm_recommended': bdm_recommended
    }

# === COSTRUZIONE PROMPT PER TURNO ===

def build_messages(user_input):
    gate_context = f"\n\n=== STATO CORRENTE SESSIONE ===\nGate attivo: {session['gate']}\n"

    if session['gate'] == 2:
        gate_context += "\nHai accesso al BDM pre-gate. Puoi usarlo per shortlist diagnostica ma NON per prescrivere tecniche.\n"
        gate_context += format_bdm_for_prompt(2)

    if session['gate'] >= 3:
        gate_context += "\nMicro-gate superato. Hai accesso a BDM completo e Knowledge base.\n"
        gate_context += format_bdm_for_prompt(3)

        # Esegui retrieval se non già fatto
        run_retrieval_if_needed()

        if session.get('retrieved_modules'):
            rm = session['retrieved_modules']

            # Moduli BDM-guidati (più precisi)
            if rm.get('bdm_recommended'):
                gate_context += "\n=== MODULI RACCOMANDATI DAL BDM PER IL PATTERN DOMINANTE ===\n"
                gate_context += format_retrieved_modules(rm['bdm_recommended'])

            # Moduli semantici per ipotesi dominante
            gate_context += "\n" + format_retrieved_modules(rm['dominant'])

            # Moduli per testare l'ipotesi rivale
            gate_context += "\n=== MODULI PER TESTARE IPOTESI RIVALE ===\n"
            gate_context += format_retrieved_modules(rm['rival'])

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
                session['diagnosis'] = None
                print("\n[Sessione resettata — nuovo caso]\n")
                continue
            reply = chat(user_input)
            print(f"\nCoach: {reply}")
            print(f"\n[Gate: {session['gate']} | Retrieval: {session['retrieval_done']} | Diagnosis: {bool(session['diagnosis'])}]\n")
        except KeyboardInterrupt:
            print("\nInterrotto.")
            break