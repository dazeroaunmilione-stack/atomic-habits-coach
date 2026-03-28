import os
import re
import json
from dotenv import load_dotenv
import anthropic
from openai import OpenAI
from pinecone import Pinecone

# === PATH ASSOLUTI ===
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

# === SESSIONE PER-UTENTE ===
_CLI_SESSION = None

def _default_session() -> dict:
    return {
        'gate': 0,
        'conversation': [],
        'areas_status': {},
        'diagnosis': None,
        'retrieval_done': False,
        'retrieved_modules': None
    }

def get_session() -> dict:
    try:
        import streamlit as st
        if 'ah_session' not in st.session_state:
            st.session_state['ah_session'] = _default_session()
        return st.session_state['ah_session']
    except Exception:
        global _CLI_SESSION
        if _CLI_SESSION is None:
            _CLI_SESSION = _default_session()
        return _CLI_SESSION

def reset_session():
    try:
        import streamlit as st
        st.session_state['ah_session'] = _default_session()
    except Exception:
        global _CLI_SESSION
        _CLI_SESSION = _default_session()

class _SessionProxy:
    def __getitem__(self, key):
        return get_session()[key]
    def __setitem__(self, key, value):
        get_session()[key] = value
    def __contains__(self, key):
        return key in get_session()
    def get(self, key, default=None):
        return get_session().get(key, default)
    def __repr__(self):
        return repr(get_session())

session = _SessionProxy()

# === POST-PROCESSING ===

def strip_process_blocks(text: str) -> str:
    cleaned = re.sub(r'<process[^>]*>.*?</process>', '', text, flags=re.DOTALL)
    cleaned = re.sub(r'<process[^>]*>.*', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

# === GATE SEMANTICO ===

def assess_area_coverage() -> dict:
    s = get_session()
    if not s['conversation']:
        return {}

    conversation_text = "\n".join([
        f"{'Utente' if m['role'] == 'user' else 'Coach'}: {m['content']}"
        for m in s['conversation']
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
        s['areas_status'] = {k: v for k, v in result.items() if k != 'gate_ready'}
        print(f"[assess_area_coverage] {s['areas_status']} | gate_ready: {result.get('gate_ready')}")
        return result
    except Exception as e:
        print(f"[assess_area_coverage] Errore: {e}")
        return {}

# === ESTRAZIONE DIAGNOSI PER RETRIEVAL ===

def extract_diagnosis_queries() -> dict:
    s = get_session()
    if not s['conversation']:
        return None

    conversation_text = "\n".join([
        f"{'Utente' if m['role'] == 'user' else 'Coach'}: {m['content']}"
        for m in s['conversation']
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

# === LOGICA DI GATE ===

def check_gate_advancement(user_message):
    s = get_session()

    if s['gate'] == 0:
        s['gate'] = 1
        return

    if s['gate'] == 1:
        user_turns = [m for m in s['conversation'] if m['role'] == 'user']
        if len(user_turns) >= 2:
            assessment = assess_area_coverage()
            if assessment.get('gate_ready'):
                s['gate'] = 2
                print("[gate] 1 → 2: tutte le aree coperte semanticamente")

# === ESECUZIONE RETRIEVAL ===

def run_retrieval_if_needed():
    s = get_session()

    if s['retrieval_done']:
        return
    if s['gate'] < 3:
        return

    diagnosis = extract_diagnosis_queries()
    if not diagnosis:
        return

    s['diagnosis'] = diagnosis

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

    s['retrieval_done'] = True
    s['retrieved_modules'] = {
        'dominant': dominant_modules,
        'rival': rival_modules,
        'bdm_recommended': bdm_recommended
    }

# === COSTRUZIONE PROMPT PER TURNO ===

def build_messages(user_input):
    s = get_session()

    gate_context = f"\n\n=== STATO CORRENTE SESSIONE ===\nGate attivo: {s['gate']}\n"

    if s.get('areas_status'):
        gate_context += "\nStato aree di raccolta:\n"
        for area, stato in s['areas_status'].items():
            gate_context += f"  {area}: {stato}\n"

    if s['gate'] == 2:
        gate_context += "\nHai accesso al BDM pre-gate. Puoi usarlo per shortlist diagnostica ma NON per prescrivere tecniche.\n"
        gate_context += format_bdm_for_prompt(2)

    if s['gate'] >= 3:
        gate_context += "\nMicro-gate superato. Hai accesso a BDM completo e Knowledge base.\n"
        gate_context += format_bdm_for_prompt(3)

        run_retrieval_if_needed()

        if s.get('retrieved_modules'):
            rm = s['retrieved_modules']
            if rm.get('bdm_recommended'):
                gate_context += "\n=== MODULI RACCOMANDATI DAL BDM PER IL PATTERN DOMINANTE ===\n"
                gate_context += format_retrieved_modules(rm['bdm_recommended'])
            gate_context += "\n" + format_retrieved_modules(rm['dominant'])
            gate_context += "\n=== MODULI PER TESTARE IPOTESI RIVALE ===\n"
            gate_context += format_retrieved_modules(rm['rival'])

    full_system = SYSTEM_PROMPT + gate_context

    messages = s['conversation'].copy()
    messages.append({'role': 'user', 'content': user_input})

    return full_system, messages

# === MESSAGGI DI ERRORE ===

_ERROR_MESSAGES = {
    'api': "Il Coach non è disponibile in questo momento. Riprova tra qualche secondo.",
    'timeout': "La risposta sta impiegando troppo tempo. Riprova.",
    'overload': "Il servizio è temporaneamente sovraccarico. Attendi un momento e riprova.",
    'generic': "Si è verificato un problema temporaneo. Riprova."
}

# === LOOP PRINCIPALE ===

def chat(user_input):
    s = get_session()

    try:
        check_gate_advancement(user_input)
    except Exception as e:
        print(f"[gate] Errore: {e}")

    try:
        system, messages = build_messages(user_input)
    except Exception as e:
        print(f"[build_messages] Errore: {e}")
        return _ERROR_MESSAGES['generic']

    try:
        response = claude.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=system,
            messages=messages
        )
        assistant_reply = response.content[0].text
    except anthropic.APITimeoutError:
        return _ERROR_MESSAGES['timeout']
    except anthropic.APIConnectionError:
        return _ERROR_MESSAGES['api']
    except anthropic.RateLimitError:
        return _ERROR_MESSAGES['overload']
    except anthropic.APIStatusError as e:
        print(f"[claude API] Errore {e.status_code}: {e.message}")
        return _ERROR_MESSAGES['api']
    except Exception as e:
        print(f"[chat] Errore inatteso: {e}")
        return _ERROR_MESSAGES['generic']

    assistant_reply = strip_process_blocks(assistant_reply)

    s['conversation'].append({'role': 'user', 'content': user_input})
    s['conversation'].append({'role': 'assistant', 'content': assistant_reply})

    if s['gate'] == 2:
        if len(s['conversation']) >= 8:
            s['gate'] = 3
            print("[gate] 2 → 3: conversazione diagnostica sufficiente")

    return assistant_reply

# === INTERFACCIA CLI ===

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
                reset_session()
                print("\n[Sessione resettata — nuovo caso]\n")
                continue
            reply = chat(user_input)
            s = get_session()
            print(f"\nCoach: {reply}")
            print(f"\n[Gate: {s['gate']} | Retrieval: {s['retrieval_done']}]\n")
        except KeyboardInterrupt:
            print("\nInterrotto.")
            break