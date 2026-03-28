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

# === STATI VALIDI PER LE AREE ===
AREA_STATES = {
    'coperta',
    'mancante',
    'troppo_generica',
    'ambigua',
    'contraddittoria',
    'insufficiente'
}

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

# === GATE SEMANTICO ===

def assess_area_coverage() -> dict:
    """
    Chiama Claude con la conversazione corrente e chiede di classificare
    lo stato semantico reale delle 5 aree obbligatorie.
    Restituisce un dict con lo stato di ciascuna area.
    Usato per decidere se il gate può avanzare da 1 a 2.
    """
    if not session['conversation']:
        return {}

    conversation_text = "\n".join([
        f"{'Utente' if m['role'] == 'user' else 'Coach'}: {m['content']}"
        for m in session['conversation']
    ])

    assessment_prompt = f"""Analizza questa conversazione di coaching e classifica lo stato di raccolta delle 5 aree obbligatorie.

CONVERSAZIONE:
{conversation_text}

Le 5 aree sono:
1. stato_attuale: storia recente del comportamento (fragile, intermittente, perso, da ottimizzare, ecc.)
2. punto_rottura: primo punto reale in cui la catena si rompe
3. contesto: ambiente, attriti, trigger, segnali esterni
4. significato: motivazione, identità, reward rivali, resistenze interne
5. tentativi: cosa è già stato provato, fallimenti ricorrenti, vincoli reali, profilo di aderenza

Per ciascuna area, restituisci uno di questi stati:
- "coperta": informazione sufficiente e discriminante per una diagnosi differenziale
- "mancante": area non toccata affatto
- "troppo_generica": informazione presente ma troppo vaga per essere utile
- "ambigua": informazione presente ma contraddittoria o poco chiara
- "insufficiente": qualcosa c'è ma non basta per escludere ipotesi alternative

Restituisci SOLO questo JSON (nessun testo aggiuntivo, nessun markdown):
{{
  "stato_attuale": "stato",
  "punto_rottura": "stato",
  "contesto": "stato",
  "significato": "stato",
  "tentativi": "stato",
  "gate_ready": true/false
}}

"gate_ready" è true SOLO se TUTTE e 5 le aree sono "coperta". Altrimenti false."""

    try:
        response = claude.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=256,
            messages=[{"role": "user", "content": assessment_prompt}]
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r'```json|```', '', raw).strip()
        result = json.loads(raw)
        # Salva lo stato delle aree in sessione
        session['areas_status'] = {
            k: v for k, v in result.items() if k != 'gate_ready'
        }
        print(f"[assess_area_coverage] {session['areas_status']} | gate_ready: {result.get('gate_ready')}")
        return result
    except Exception as e:
        print(f"[assess_area_coverage] Errore: {e}")
        return {}

def all_areas_covered() -> bool:
    """
    Restituisce True se tutte le 5 aree sono classificate come 'coperta'.
    """
    required = {'stato_attuale', 'punto_rottura', 'contesto', 'significato', 'tentativi'}
    status = session.get('areas_status', {})
    return all(status.get(area) == 'coperta' for area in required)

# === ESTRAZIONE DIAGNOSI PER RETRIEVAL ===

def extract_diagnosis_queries() -> dict:
    """
    Chiama Claude con la conversazione corrente e chiede di estrarre
    in JSON le query per il retrieval semantico su Pinecone.
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
        raw = re.sub(r'```json|```', '', raw).strip()
        result = json.loads(raw)
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
            if p.get('follow_up_question_if_ambiguous'):
                lines.append(f"  Disambigua: {p['follow_up_question_if_ambiguous']}")
        return '\n'.join(lines)

    if gate_level >= 3:
        lines = ["=== GUIDA DIAGNOSTICA COMPLETA (post-gate) ==="]
        for p in BDM_POST:
            lines.append(f"\n{p['diagnosis_id']}: {p['problem_pattern']}")
            lines.append(f"  Fase: {p.get('likely_behavior_phase', '')}")
            lines.append(f"  Causa: {p.get('likely_root_cause', '')}")
            lines.append(f"  Tecniche: {p.get('recommended_techniques', '')}")
            lines.append(f"  Moduli: {p.get('recommended_modules', '')}")
            if p.get('disconfirming_signals'):
                lines.append(f"  Esclude: {p['disconfirming_signals']}")
            if p.get('what_this_pattern_does_not_explain'):
                lines.append(f"  Non spiega: {p['what_this_pattern_does_not_explain']}")
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

# === LOGICA DI GATE SEMANTICO ===

def check_gate_advancement(user_message):
    """
    Gate 0 → 1: dopo il primo messaggio dell'utente (nuovo caso ricevuto)
    Gate 1 → 2: solo quando assess_area_coverage() conferma tutte le aree coperte
    Gate 2 → 3: gestito in chat() dopo la risposta del Coach
    """
    if session['gate'] == 0:
        session['gate'] = 1
        return

    if session['gate'] == 1:
        # Valutazione semantica reale delle aree
        # Eseguita solo dopo almeno 2 turni utente per efficienza
        user_turns = [m for m in session['conversation'] if m['role'] == 'user']
        if len(user_turns) >= 2:
            assessment = assess_area_coverage()
            if assessment.get('gate_ready'):
                session['gate'] = 2
                print("[gate] 1 → 2: tutte le aree coperte semanticamente")

# === ESECUZIONE RETRIEVAL ===

def run_retrieval_if_needed():
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

    dominant_modules, rival_modules = retrieve_modules_paired(
        dominant_query, rival_query, top_k=4
    )

    bdm_recommended = []
    dominant_bdm = diagnosis.get('dominant_bdm')
    if dominant_bdm:
        recommended_ids = get_recommended_modules_from_bdm(dominant_bdm)
        if recommended_ids:
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

    # Includi stato aree se disponibile
    if session.get('areas_status'):
        gate_context += "\nStato aree di raccolta:\n"
        for area, stato in session['areas_status'].items():
            gate_context += f"  {area}: {stato}\n"

    if session['gate'] == 2:
        gate_context += "\nHai accesso al BDM pre-gate. Puoi usarlo per shortlist diagnostica ma NON per prescrivere tecniche.\n"
        gate_context += format_bdm_for_prompt(2)

    if session['gate'] >= 3:
        gate_context += "\nMicro-gate superato. Hai accesso a BDM completo e Knowledge base.\n"
        gate_context += format_bdm_for_prompt(3)

        run_retrieval_if_needed()

        if session.get('retrieved_modules'):
            rm = session['retrieved_modules']

            if rm.get('bdm_recommended'):
                gate_context += "\n=== MODULI RACCOMANDATI DAL BDM PER IL PATTERN DOMINANTE ===\n"
                gate_context += format_retrieved_modules(rm['bdm_recommended'])

            gate_context += "\n" + format_retrieved_modules(rm['dominant'])
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

    # Gate 2 → 3: avanza dopo sufficiente scambio diagnostico
    if session['gate'] == 2:
        if len(session['conversation']) >= 8:
            session['gate'] = 3
            print("[gate] 2 → 3: conversazione diagnostica sufficiente")

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
                session['areas_status'] = {}
                print("\n[Sessione resettata — nuovo caso]\n")
                continue
            reply = chat(user_input)
            print(f"\nCoach: {reply}")
            print(f"\n[Gate: {session['gate']} | Aree: {session.get('areas_status',{})} | Retrieval: {session['retrieval_done']}]\n")
        except KeyboardInterrupt:
            print("\nInterrotto.")
            break