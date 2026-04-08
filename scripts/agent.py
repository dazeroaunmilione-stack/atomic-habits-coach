import os
import re
import json
from dotenv import load_dotenv
import anthropic
from openai import OpenAI
from pinecone import Pinecone

# === PATH ===
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

try:
    pc = Pinecone(api_key=get_secret('PINECONE_API_KEY'))
    pinecone_index = pc.Index('atomic-habits-knowledge')
    PINECONE_AVAILABLE = True
except Exception as e:
    print(f"[init] Pinecone non disponibile: {e}")
    PINECONE_AVAILABLE = False
    pinecone_index = None

# === CARICA FILES ===
with open(os.path.join(OUTPUT_DIR, 'bdm_pre_gate.json'), 'r', encoding='utf-8') as f:
    BDM_PRE = json.load(f)

with open(os.path.join(OUTPUT_DIR, 'bdm_post_gate.json'), 'r', encoding='utf-8') as f:
    BDM_POST = json.load(f)

with open(os.path.join(BASE_DIR, 'system_prompt.txt'), 'r', encoding='utf-8') as f:
    SYSTEM_PROMPT = f.read()

# === LOG STRUTTURATO ===
def log(tag, msg):
    print(f"[{tag}] {msg}")

# === SESSIONE ===
_CLI_SESSION = None

def _default_session():
    return {
        'gate': 0,
        'conversation': [],
        'areas_status': {},
        'diagnosis': None,
        'micro_gate_result': None,
        'retrieval_done': False,
        'retrieved_modules': None,
    }

def get_session():
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
    def __getitem__(self, key): return get_session()[key]
    def __setitem__(self, key, value): get_session()[key] = value
    def __contains__(self, key): return key in get_session()
    def get(self, key, default=None): return get_session().get(key, default)

session = _SessionProxy()

# === POST-PROCESSING ===
def strip_process_blocks(text):
    cleaned = re.sub(r'<process[^>]*>.*?</process>', '', text, flags=re.DOTALL)
    cleaned = re.sub(r'<process[^>]*>.*', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<reasoning[^>]*>.*?</reasoning>', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<diagnosi[^>]*>.*?</diagnosi>', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<gate[^>]*>.*?</gate>', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<check[^>]*>.*?</check>', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

# === HELPER: chiamata Claude compatta ===
def claude_json_call(prompt, max_tokens=512):
    """Chiama Claude con un prompt e restituisce JSON parsed."""
    try:
        response = claude.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r'```json|```', '', raw).strip()
        return json.loads(raw)
    except Exception as e:
        log("claude_json_call", f"Errore: {e}")
        return None

# =========================================================================
# GATE 0→1: INQUIRY INIZIALE
# =========================================================================

def assess_area_coverage():
    """Valuta la copertura delle 5 aree obbligatorie."""
    s = get_session()
    if not s['conversation']:
        return {}

    conversation_text = "\n".join([
        f"{'Utente' if m['role'] == 'user' else 'Coach'}: {m['content']}"
        for m in s['conversation']
    ])

    result = claude_json_call(f"""Analizza questa conversazione di coaching e classifica lo stato di raccolta delle 5 aree obbligatorie.

CONVERSAZIONE:
{conversation_text}

Le 5 aree sono:
1. stato_attuale: storia recente del comportamento
2. punto_rottura: primo punto reale in cui la catena si rompe
3. contesto: ambiente, attriti, trigger, segnali esterni
4. significato: motivazione, identità, reward rivali, resistenze interne
5. tentativi: cosa è già stato provato, fallimenti, vincoli, profilo di aderenza

Per ciascuna area, restituisci uno di questi stati:
- "coperta": informazione sufficiente e discriminante
- "mancante": area non toccata
- "troppo_generica": informazione troppo vaga
- "ambigua": informazione contraddittoria
- "insufficiente": qualcosa c'è ma non basta

Restituisci SOLO JSON:
{{
  "stato_attuale": "stato",
  "punto_rottura": "stato",
  "contesto": "stato",
  "significato": "stato",
  "tentativi": "stato",
  "gate_ready": true/false
}}

"gate_ready" è true SOLO se TUTTE e 5 le aree sono "coperta".""")

    if result:
        s['areas_status'] = {k: v for k, v in result.items() if k != 'gate_ready'}
        log("assess", f"Aree: {s['areas_status']} | gate_ready: {result.get('gate_ready')}")
        return result
    return {}

# =========================================================================
# GATE 2→3: MICRO-GATE REALE (non conteggio turni)
# =========================================================================

def validate_micro_gate():
    """Verifica che la diagnosi differenziale sia realmente completata.
    Restituisce True solo se l'agente può articolare:
    1. Ipotesi dominante e perché batte la rivale
    2. Famiglia tecnica e perché batte le alternative
    3. Punto di rottura specifico"""
    s = get_session()

    conversation_text = "\n".join([
        f"{'Utente' if m['role'] == 'user' else 'Coach'}: {m['content']}"
        for m in s['conversation']
    ])

    result = claude_json_call(f"""Analizza questa conversazione di coaching sul behavior change.

CONVERSAZIONE:
{conversation_text}

BDM PATTERN DISPONIBILI (per riferimento):
{json.dumps([{{'id': p['diagnosis_id'], 'pattern': p['problem_pattern'], 'sintomo': p['symptom_description']}} for p in BDM_PRE], ensure_ascii=False)}

Valuta se il Coach ha raccolto materiale sufficiente per completare una diagnosi differenziale reale.
Il micro-gate è superato SOLO se dalla conversazione emergono TUTTI questi elementi:

1. IPOTESI DOMINANTE: una causa principale chiara e specifica del blocco
2. IPOTESI RIVALE: almeno una causa alternativa considerata e un motivo per cui è meno probabile
3. PUNTO DI ROTTURA: il momento/contesto specifico in cui il comportamento si rompe
4. FAMIGLIA TECNICA: la categoria di intervento più coerente
5. SUFFICIENZA: il materiale raccolto è abbastanza per escludere almeno una alternativa

Restituisci SOLO JSON:
{{
  "dominant_hypothesis": "descrizione causa dominante o null",
  "rival_hypothesis": "descrizione causa rivale o null",
  "breakpoint": "descrizione punto di rottura o null",
  "dominant_bdm_id": "BD01-BD30 se identificabile o null",
  "rival_bdm_id": "BD01-BD30 se identificabile o null",
  "tech_family": "famiglia tecnica dominante o null",
  "gate_passed": true/false,
  "reason": "perché il gate è passato o cosa manca"
}}""", max_tokens=800)

    if result:
        s['micro_gate_result'] = result
        passed = result.get('gate_passed', False)
        log("micro_gate", f"Passato: {passed} | Motivo: {result.get('reason', '-')}")
        if passed:
            s['diagnosis'] = {
                'dominant': result.get('dominant_hypothesis'),
                'rival': result.get('rival_hypothesis'),
                'dominant_bdm': result.get('dominant_bdm_id'),
                'rival_bdm': result.get('rival_bdm_id'),
            }
        return passed
    return False

# =========================================================================
# RETRIEVAL
# =========================================================================

def get_embedding(text):
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000]
    )
    return response.data[0].embedding

def retrieve_modules(query, top_k=5, filter_metadata=None):
    if not PINECONE_AVAILABLE:
        log("retrieval", "Pinecone non disponibile, skip retrieval")
        return []
    try:
        embedding = get_embedding(query)
        results = pinecone_index.query(
            vector=embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_metadata
        )
        return results.matches
    except Exception as e:
        log("retrieval", f"Errore Pinecone: {e}")
        return []

def retrieve_modules_paired(dominant_query, rival_query, top_k=3):
    dominant = retrieve_modules(dominant_query, top_k)
    rival = retrieve_modules(rival_query, top_k)
    return dominant, rival

def get_recommended_modules_from_bdm(bdm_id):
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
        lines.append(f"  Contenuto: {meta.get('text_preview', '')[:500]}")
    return '\n'.join(lines)

# =========================================================================
# RETRIEVAL ESECUZIONE (diagnosis-constrained)
# =========================================================================

def run_retrieval_if_needed():
    s = get_session()
    if s['retrieval_done'] or s['gate'] < 3:
        return

    diagnosis = s.get('diagnosis')
    if not diagnosis or not diagnosis.get('dominant'):
        log("retrieval", "Nessuna diagnosi disponibile, skip")
        return

    dominant_query = diagnosis['dominant']
    rival_query = diagnosis.get('rival', dominant_query)

    # Retrieval paired: moduli per ipotesi dominante + rivale
    dominant_modules, rival_modules = retrieve_modules_paired(
        dominant_query, rival_query, top_k=4
    )

    # Retrieval BDM-recommended: moduli specifici raccomandati dal pattern
    bdm_recommended = []
    dominant_bdm = diagnosis.get('dominant_bdm')
    if dominant_bdm:
        recommended_ids = get_recommended_modules_from_bdm(dominant_bdm)
        log("retrieval", f"BDM {dominant_bdm} raccomanda moduli: {recommended_ids}")
        for mod_id in recommended_ids[:3]:
            try:
                filtered = retrieve_modules(
                    dominant_query, top_k=1,
                    filter_metadata={"module_id": int(mod_id)} if mod_id.isdigit() else None
                )
                bdm_recommended.extend(filtered)
            except Exception:
                pass

    s['retrieval_done'] = True
    s['retrieved_modules'] = {
        'dominant': dominant_modules,
        'rival': rival_modules,
        'bdm_recommended': bdm_recommended,
    }
    log("retrieval", f"Completato: {len(dominant_modules)} dominant, {len(rival_modules)} rival, {len(bdm_recommended)} bdm")

# =========================================================================
# GATE LOGIC
# =========================================================================

def check_gate_advancement(user_message):
    """Chiamata DOPO che il messaggio utente è stato aggiunto alla conversazione."""
    s = get_session()

    # Aggiungi il messaggio utente PRIMA del check (così i conteggi sono corretti)
    # NOTA: il messaggio viene aggiunto qui temporaneamente per il check,
    # poi viene ri-aggiunto alla fine di chat() — preveniamo duplicati
    temp_added = False
    if not s['conversation'] or s['conversation'][-1].get('content') != user_message:
        s['conversation'].append({'role': 'user', 'content': user_message})
        temp_added = True

    user_turns = [m for m in s['conversation'] if m['role'] == 'user']

    # Gate 0→1: primo turno
    if s['gate'] == 0:
        s['gate'] = 1
        log("gate", "0 → 1: primo messaggio ricevuto")
        if temp_added: s['conversation'].pop()
        return

    # Gate 1→2: verifica copertura aree dopo almeno 2 turni utente
    if s['gate'] == 1 and len(user_turns) >= 2:
        assessment = assess_area_coverage()
        if assessment.get('gate_ready'):
            s['gate'] = 2
            log("gate", "1 → 2: tutte le aree coperte")
        else:
            log("gate", f"1: aree incomplete — {s.get('areas_status', {})}")

    # Gate 2→3: MICRO-GATE REALE
    if s['gate'] == 2 and len(user_turns) >= 3:
        passed = validate_micro_gate()
        if passed:
            s['gate'] = 3
            log("gate", "2 → 3: micro-gate SUPERATO — diagnosi validata")
        else:
            reason = s.get('micro_gate_result', {}).get('reason', 'motivo sconosciuto')
            log("gate", f"2: micro-gate NON superato — {reason}")

    # Rimuovi il messaggio temporaneo (verrà aggiunto alla fine di chat())
    if temp_added: s['conversation'].pop()

# =========================================================================
# COSTRUZIONE PROMPT
# =========================================================================

def build_messages(user_input):
    s = get_session()

    gate_context = f"\n\n=== STATO CORRENTE SESSIONE ===\nGate attivo: {s['gate']}\n"

    if s.get('areas_status'):
        gate_context += "\nStato aree di raccolta:\n"
        for area, stato in s['areas_status'].items():
            gate_context += f"  {area}: {stato}\n"

        incomplete = [a for a, st in s['areas_status'].items() if st != 'coperta']
        if incomplete and s['gate'] < 2:
            gate_context += f"\n⛔ BLOCCO ATTIVO: le seguenti aree NON sono ancora coperte: {', '.join(incomplete)}.\n"
            gate_context += "NON PUOI diagnosticare, prescrivere, suggerire tecniche o orientare verso soluzioni.\n"
            gate_context += "Puoi SOLO fare domande di approfondimento sulle aree mancanti. NIENT'ALTRO.\n"

    if s['gate'] == 2:
        gate_context += "\nHai accesso al BDM pre-gate. Puoi usarlo per shortlist diagnostica ma NON per prescrivere tecniche.\n"
        gate_context += format_bdm_for_prompt(2)

        # Se micro-gate tentato ma fallito, mostra il motivo
        mgr = s.get('micro_gate_result')
        if mgr and not mgr.get('gate_passed'):
            gate_context += f"\n\n=== MICRO-GATE NON SUPERATO ===\nMotivo: {mgr.get('reason', '-')}\nDevi continuare l'inquiry o la diagnosi prima di prescrivere.\n"

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

# =========================================================================
# ERRORI
# =========================================================================

_ERROR_MESSAGES = {
    'api': "Il Coach non è disponibile in questo momento. Riprova tra qualche secondo.",
    'timeout': "La risposta sta impiegando troppo tempo. Riprova.",
    'overload': "Il servizio è temporaneamente sovraccarico. Attendi un momento e riprova.",
    'generic': "Si è verificato un problema temporaneo. Riprova."
}

# =========================================================================
# LOOP PRINCIPALE
# =========================================================================

def chat(user_input):
    s = get_session()

    try:
        check_gate_advancement(user_input)
    except Exception as e:
        log("gate", f"Errore: {e}")

    try:
        system, messages = build_messages(user_input)
    except Exception as e:
        log("build_messages", f"Errore: {e}")
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
        log("claude API", f"Errore {e.status_code}: {e.message}")
        return _ERROR_MESSAGES['api']
    except Exception as e:
        log("chat", f"Errore inatteso: {e}")
        return _ERROR_MESSAGES['generic']

    assistant_reply = strip_process_blocks(assistant_reply)

    # Aggiungi alla conversazione (evita duplicati dal gate check)
    if not s['conversation'] or s['conversation'][-1].get('content') != user_input:
        s['conversation'].append({'role': 'user', 'content': user_input})
    s['conversation'].append({'role': 'assistant', 'content': assistant_reply})

    return assistant_reply

# =========================================================================
# INTERFACCIA CLI
# =========================================================================

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
            print(f"\n[Gate: {s['gate']} | Retrieval: {s['retrieval_done']} | Diagnosi: {'Sì' if s.get('diagnosis') else 'No'}]\n")
        except KeyboardInterrupt:
            print("\nInterrotto.")
            break
