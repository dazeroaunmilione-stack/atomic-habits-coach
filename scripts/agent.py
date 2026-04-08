import os
import re
import json
from datetime import datetime, timezone
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

# === TASSONOMIA ===
TAXONOMY_PATH = os.path.join(OUTPUT_DIR, 'taxonomy.json')
try:
    with open(TAXONOMY_PATH, 'r', encoding='utf-8') as f:
        TAXONOMY = json.load(f)
    TAXONOMY_AVAILABLE = True
except Exception as e:
    print(f"[init] Tassonomia non disponibile: {e}")
    TAXONOMY = {}
    TAXONOMY_AVAILABLE = False

# === LOG STRUTTURATO (conforme Retrieval Governance v1.0) ===
_RETRIEVAL_LOG = []

def log(tag, msg):
    print(f"[{tag}] {msg}")

def structured_log(event_type, gate, layer=None, view=None, fields_exposed=None,
                    reason=None, dominant_hypothesis=None, rival_plausible=None,
                    paired_retrieval=None, violation=None, next_action=None):
    """Log conforme alla Retrieval Governance v1.0 §9."""
    entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'event': event_type,
        'gate': gate,
        'layer': layer,
        'view': view,
        'fields_exposed': fields_exposed,
        'reason': reason,
        'dominant_hypothesis': dominant_hypothesis,
        'rival_plausible': rival_plausible,
        'paired_retrieval': paired_retrieval,
        'violation': violation,
        'next_action': next_action,
    }
    # Rimuovi None per pulizia
    entry = {k: v for k, v in entry.items() if v is not None}
    _RETRIEVAL_LOG.append(entry)
    log("audit", f"[{event_type}] gate={gate} layer={layer or '-'} → {next_action or 'continue'}")
    return entry

def get_retrieval_log():
    return _RETRIEVAL_LOG

# === SESSIONE ===
_CLI_SESSION = None

def _default_session():
    return {
        'gate': 0,
        'conversation': [],
        'areas_status': {},
        'bdm_mapping': None,
        'diagnosis': None,
        'micro_gate_result': None,
        'retrieval_done': False,
        'retrieved_modules': None,
        'validation_history': [],
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

# === NORMALIZZAZIONE TASSONOMICA ===
def normalize_with_taxonomy(user_text):
    """Normalizza il linguaggio dell'utente usando il vocabolario controllato.
    Restituisce hints sui domini e BDM patterns probabili basati sulle frasi chiave."""
    if not TAXONOMY_AVAILABLE or not TAXONOMY.get('user_language_mapping'):
        return None

    user_lower = user_text.lower()
    matches = []
    for phrase, mapping in TAXONOMY['user_language_mapping'].items():
        if phrase in user_lower:
            matches.append({
                'phrase': phrase,
                'domain': mapping['domain'],
                'stage': mapping['stage'],
                'bdm_hint': mapping.get('bdm_hint'),
            })

    if matches:
        log("taxonomy", f"Normalizzato: {[m['phrase'] + ' → ' + m['domain'] for m in matches]}")
    return matches if matches else None


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
# GATE 1→2: BDM MAPPING OBBLIGATORIO
# =========================================================================

def map_bdm_patterns():
    """Mappa OBBLIGATORIAMENTE il caso su 2-3 pattern BDM con scoring.
    Questo non è opzionale: l'agente DEVE identificare i pattern più
    probabili e giustificare perché il primo batte il secondo."""
    s = get_session()

    conversation_text = "\n".join([
        f"{'Utente' if m['role'] == 'user' else 'Coach'}: {m['content']}"
        for m in s['conversation']
    ])

    bdm_summary = json.dumps([{
        'id': p['diagnosis_id'],
        'pattern': p['problem_pattern'],
        'sintomo': p['symptom_description'],
        'esclude': p.get('disconfirming_signals', ''),
        'rivale_vicina': p.get('nearest_rival_pattern', ''),
        'rivale_cross': p.get('cross_family_rival_pattern', ''),
    } for p in BDM_PRE], ensure_ascii=False)

    result = claude_json_call(f"""Sei un diagnostico esperto di behavior change. Analizza questa conversazione e mappa il caso sui pattern BDM più probabili.

CONVERSAZIONE:
{conversation_text}

CATALOGO BDM (30 pattern):
{bdm_summary}

ISTRUZIONI:
1. Identifica i 3 pattern BDM più probabili per questo caso
2. Per ciascuno assegna un punteggio di probabilità (0-100)
3. Per il pattern dominante, spiega PERCHÉ batte il secondo
4. Per il secondo, spiega cosa lo renderebbe dominante (quale evidenza manca)
5. Per il terzo (cross-family), spiega perché è meno probabile ma non escludibile

Restituisci SOLO JSON:
{{
  "patterns": [
    {{
      "bdm_id": "BD__",
      "pattern_name": "nome del pattern",
      "probability": 0-100,
      "evidence": "evidenze dalla conversazione che supportano questo pattern",
      "against": "evidenze che lo indeboliscono"
    }},
    {{
      "bdm_id": "BD__",
      "pattern_name": "nome del pattern",
      "probability": 0-100,
      "evidence": "evidenze",
      "against": "evidenze contrarie"
    }},
    {{
      "bdm_id": "BD__",
      "pattern_name": "nome del pattern",
      "probability": 0-100,
      "evidence": "evidenze",
      "against": "evidenze contrarie"
    }}
  ],
  "dominant_beats_rival": "perché il primo pattern batte il secondo su questo caso specifico",
  "rival_would_win_if": "cosa dovrebbe emergere per ribaltare la classifica",
  "cross_family_excluded_because": "perché il terzo pattern è meno probabile"
}}""", max_tokens=1200)

    if result and result.get('patterns'):
        s['bdm_mapping'] = result
        patterns = result['patterns']
        log("bdm_mapping", f"Top 3: {[p['bdm_id'] + ' (' + str(p['probability']) + '%)' for p in patterns]}")
        log("bdm_mapping", f"Dominante batte rivale: {result.get('dominant_beats_rival', '-')[:100]}")
        return result

    log("bdm_mapping", "FALLITO — nessun pattern identificato")
    return None

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

    # === RETRIEVAL A 3 CANALI (conforme Governance §8) ===

    # Canale 1: moduli che SUPPORTANO la diagnosi dominante
    dominant_modules = retrieve_modules(dominant_query, top_k=4)

    # Canale 2: moduli per TESTARE la rivale (cosa la supporterebbe)
    rival_modules = retrieve_modules(rival_query, top_k=3)

    # Canale 3: DISCONFIRMING — moduli che potrebbero SMENTIRE la dominante
    # Costruiamo una query che cerca evidenze CONTRO la diagnosi dominante
    dominant_bdm = diagnosis.get('dominant_bdm')
    disconfirming_query = ""
    if dominant_bdm:
        for p in BDM_PRE:
            if p.get('diagnosis_id') == dominant_bdm:
                disconfirm_signals = p.get('disconfirming_signals', '')
                not_explained = p.get('what_this_pattern_does_not_explain', '')
                disconfirming_query = f"{disconfirm_signals} {not_explained}".strip()
                break

    disconfirming_modules = []
    if disconfirming_query:
        disconfirming_modules = retrieve_modules(disconfirming_query, top_k=2)
        log("retrieval", f"Disconfirming: query='{disconfirming_query[:80]}...' → {len(disconfirming_modules)} moduli")

    # Retrieval BDM-recommended: moduli specifici raccomandati dal pattern
    bdm_recommended = []
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

    # === NORMALIZZAZIONE TASSONOMICA del retrieval ===
    taxonomy_context = ""
    if TAXONOMY_AVAILABLE and s.get('bdm_mapping'):
        top_pattern = s['bdm_mapping']['patterns'][0]
        bdm_id = top_pattern['bdm_id']
        # Trova il dominio tassonomico del pattern dominante
        for p in BDM_POST:
            if p.get('diagnosis_id') == bdm_id:
                phase = p.get('likely_behavior_phase', '')
                broken_law = p.get('broken_law', '')
                if phase and phase in TAXONOMY.get('primary_domain', {}):
                    taxonomy_context = f"Dominio tassonomico: {phase} — {TAXONOMY['primary_domain'].get(phase, '')}"
                break

    s['retrieval_done'] = True
    s['retrieved_modules'] = {
        'dominant': dominant_modules,
        'rival': rival_modules,
        'disconfirming': disconfirming_modules,
        'bdm_recommended': bdm_recommended,
        'taxonomy_context': taxonomy_context,
    }

    # Log strutturato conforme Governance §9
    structured_log(
        event_type='retrieval_completed',
        gate=s['gate'],
        layer='Knowledge',
        view='pinecone_paired_retrieval',
        reason='diagnosis-constrained retrieval',
        dominant_hypothesis=dominant_query[:100],
        rival_plausible=True if rival_query != dominant_query else False,
        paired_retrieval=True,
        next_action='continue_to_composition',
    )

    log("retrieval", f"Completato: {len(dominant_modules)} dominant, {len(rival_modules)} rival, {len(disconfirming_modules)} disconfirm, {len(bdm_recommended)} bdm")

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

    # Gate 0→1: primo turno + normalizzazione tassonomica
    if s['gate'] == 0:
        # Tassonomia a Gate 0: boundary check terminologico (Governance §4)
        tax_hints = normalize_with_taxonomy(user_message)
        if tax_hints:
            s['taxonomy_hints'] = tax_hints
            structured_log('taxonomy_boundary_check', gate=0, layer='Tassonomia',
                           reason='normalizzazione primo turno',
                           next_action='continue_inquiry')
        s['gate'] = 1
        log("gate", "0 → 1: primo messaggio ricevuto")
        if temp_added: s['conversation'].pop()
        return

    # Gate 1→2: verifica copertura aree dopo almeno 2 turni utente
    if s['gate'] == 1 and len(user_turns) >= 2:
        assessment = assess_area_coverage()
        if assessment.get('gate_ready'):
            # BDM MAPPING OBBLIGATORIO: mappa il caso su 2-3 pattern prima di avanzare
            bdm_result = map_bdm_patterns()
            if bdm_result:
                s['gate'] = 2
                structured_log('gate_advance', gate=2, layer='BDM',
                               view='bdm_core_pre_gate',
                               reason='aree coperte + BDM mapping completato',
                               next_action='continue_diagnosis')
                log("gate", "1 → 2: aree coperte + BDM mapping completato")
            else:
                log("gate", "1: aree coperte ma BDM mapping fallito — resta in gate 1")
        else:
            log("gate", f"1: aree incomplete — {s.get('areas_status', {})}")

    # Gate 2→3: MICRO-GATE REALE
    if s['gate'] == 2 and len(user_turns) >= 3:
        passed = validate_micro_gate()
        if passed:
            s['gate'] = 3
            diagnosis = s.get('diagnosis', {})
            structured_log('gate_advance', gate=3,
                           layer='BDM+Knowledge',
                           view='bdm_post_gate_guidance + Knowledge',
                           reason='micro-gate superato',
                           dominant_hypothesis=diagnosis.get('dominant', '')[:100],
                           rival_plausible=bool(diagnosis.get('rival')),
                           next_action='retrieval_then_composition')
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

    # Tassonomia a Gate 0-1: boundary check terminologico (Governance §4)
    if s['gate'] <= 1 and s.get('taxonomy_hints'):
        gate_context += "\n=== BOUNDARY CHECK TASSONOMICO (solo orientamento, NON diagnosi) ===\n"
        gate_context += "Le seguenti frasi dell'utente sono state normalizzate. Usale SOLO per orientare le domande, NON per diagnosticare.\n"
        for hint in s['taxonomy_hints']:
            gate_context += f"  \"{hint['phrase']}\" → dominio: {hint['domain']}, fase: {hint['stage']}"
            if hint.get('bdm_hint'):
                gate_context += f", pattern possibile: {hint['bdm_hint']}"
            gate_context += "\n"
        gate_context += "RICORDA: questa normalizzazione NON è una diagnosi. Serve solo a formulare domande migliori.\n"

    if s['gate'] == 2:
        gate_context += "\nHai accesso al BDM pre-gate. Puoi usarlo per shortlist diagnostica ma NON per prescrivere tecniche.\n"
        gate_context += format_bdm_for_prompt(2)

        # BDM MAPPING OBBLIGATORIO — iniettato come struttura vincolante
        bdm_map = s.get('bdm_mapping')
        if bdm_map and bdm_map.get('patterns'):
            gate_context += "\n\n=== MAPPING BDM OBBLIGATORIO (struttura vincolante) ===\n"
            gate_context += "Il caso è stato mappato sui seguenti pattern. La tua diagnosi DEVE partire da qui.\n"
            gate_context += "NON puoi ignorare questo mapping. NON puoi proporre una diagnosi che non sia ancorata a questi pattern.\n\n"
            for i, p in enumerate(bdm_map['patterns']):
                rank = ['DOMINANTE', 'RIVALE VICINA', 'RIVALE CROSS-FAMILY'][i] if i < 3 else f'PATTERN {i+1}'
                gate_context += f"  {rank}: {p['bdm_id']} — {p['pattern_name']} (probabilità: {p['probability']}%)\n"
                gate_context += f"    Evidenze a favore: {p['evidence']}\n"
                gate_context += f"    Evidenze contro: {p['against']}\n\n"
            gate_context += f"  Perché il dominante batte il rivale: {bdm_map.get('dominant_beats_rival', '-')}\n"
            gate_context += f"  Il rivale vincerebbe se: {bdm_map.get('rival_would_win_if', '-')}\n"
            gate_context += f"  Cross-family escluso perché: {bdm_map.get('cross_family_excluded_because', '-')}\n"
            gate_context += "\nLa tua diagnosi differenziale deve CONFERMARE o RIBALTARE questa classifica con evidenze dalla conversazione.\n"

        # Se micro-gate tentato ma fallito, mostra il motivo
        mgr = s.get('micro_gate_result')
        if mgr and not mgr.get('gate_passed'):
            gate_context += f"\n\n=== MICRO-GATE NON SUPERATO ===\nMotivo: {mgr.get('reason', '-')}\nDevi continuare l'inquiry o la diagnosi prima di prescrivere.\n"

    if s['gate'] >= 3:
        gate_context += "\nMicro-gate superato. Hai accesso a BDM completo e Knowledge base.\n"
        gate_context += format_bdm_for_prompt(3)

        # Inietta anche BDM mapping in gate 3 per coerenza
        bdm_map = s.get('bdm_mapping')
        if bdm_map and bdm_map.get('patterns'):
            gate_context += "\n\n=== MAPPING BDM (riferimento per la prescrizione) ===\n"
            for i, p in enumerate(bdm_map['patterns']):
                rank = ['DOMINANTE', 'RIVALE', 'CROSS-FAMILY'][i] if i < 3 else f'PATTERN {i+1}'
                gate_context += f"  {rank}: {p['bdm_id']} — {p['pattern_name']} ({p['probability']}%)\n"

        run_retrieval_if_needed()

        if s.get('retrieved_modules'):
            rm = s['retrieved_modules']

            # Contesto tassonomico
            if rm.get('taxonomy_context'):
                gate_context += f"\n\n=== CONTESTO TASSONOMICO ===\n{rm['taxonomy_context']}\n"

            if rm.get('bdm_recommended'):
                gate_context += "\n=== MODULI RACCOMANDATI DAL BDM PER IL PATTERN DOMINANTE ===\n"
                gate_context += format_retrieved_modules(rm['bdm_recommended'])
            gate_context += "\n" + format_retrieved_modules(rm['dominant'])
            gate_context += "\n=== MODULI PER TESTARE IPOTESI RIVALE ===\n"
            gate_context += format_retrieved_modules(rm['rival'])

            # Canale disconfirming (Governance §8)
            if rm.get('disconfirming'):
                gate_context += "\n\n=== MODULI DISCONFIRMING (possono INDEBOLIRE la diagnosi dominante) ===\n"
                gate_context += "ATTENZIONE: se questi moduli sono più pertinenti di quelli dominanti, "
                gate_context += "la diagnosi potrebbe essere sbagliata. Valuta prima di prescrivere.\n"
                gate_context += format_retrieved_modules(rm['disconfirming'])

    full_system = SYSTEM_PROMPT + gate_context

    messages = s['conversation'].copy()
    messages.append({'role': 'user', 'content': user_input})

    return full_system, messages

# =========================================================================
# VALIDATORE POST-RISPOSTA (5 criteri di qualità)
# =========================================================================

def validate_response(user_input, assistant_reply):
    """Seconda chiamata Claude che valida la risposta contro 5 criteri.
    Se fallisce 2+ criteri, la risposta viene rigenerata.
    Restituisce (is_valid, feedback, scores)."""
    s = get_session()

    # Valida solo risposte in gate 3 (quando c'è prescrizione)
    if s['gate'] < 3:
        return True, None, None

    bdm_map = s.get('bdm_mapping', {})
    bdm_context = ""
    if bdm_map and bdm_map.get('patterns'):
        bdm_context = f"Pattern dominante: {bdm_map['patterns'][0]['bdm_id']} — {bdm_map['patterns'][0]['pattern_name']}"

    diagnosis = s.get('diagnosis', {})
    diag_context = ""
    if diagnosis:
        diag_context = f"Diagnosi: {diagnosis.get('dominant', 'N/A')} | Rivale: {diagnosis.get('rival', 'N/A')}"

    result = claude_json_call(f"""Sei un quality checker per un AI Coach di behavior change. Valuta questa risposta contro 5 criteri.

DOMANDA DELL'UTENTE:
{user_input}

RISPOSTA DEL COACH:
{assistant_reply}

CONTESTO DIAGNOSTICO:
{bdm_context}
{diag_context}

VALUTA CIASCUN CRITERIO (1-10):

1. SPECIFICITÀ: La tecnica è specifica per QUESTO caso? O è un consiglio generico che andrebbe bene per chiunque?
   (1 = consiglio generico da libro, 10 = intervento cucito sul caso)

2. INTERCAMBIABILITÀ: Se cambiassi il caso ma tenessi la stessa risposta, funzionerebbe ugualmente?
   (1 = identica per qualsiasi caso, 10 = impossibile da riciclare)

3. PUNTO DI ROTTURA: Il punto specifico dove il comportamento si rompe è affrontato direttamente?
   (1 = ignorato, 10 = è il centro dell'intervento)

4. PROTEZIONE FALLIMENTO: C'è una strategia concreta per quando l'intervento potrebbe fallire?
   (1 = nessuna, 10 = recovery chiaro e realistico)

5. VERIFICABILITÀ: L'utente può capire entro 7 giorni se sta funzionando?
   (1 = nessun criterio, 10 = indicatore chiaro e osservabile)

Restituisci SOLO JSON:
{{
  "scores": {{
    "specificita": 1-10,
    "intercambiabilita": 1-10,
    "punto_rottura": 1-10,
    "protezione_fallimento": 1-10,
    "verificabilita": 1-10
  }},
  "media": 1-10,
  "criteri_falliti": ["nomi dei criteri con score < 6"],
  "feedback": "cosa manca o va migliorato nella risposta (max 2 frasi)",
  "is_valid": true/false
}}

La risposta è valida (is_valid=true) se al massimo 1 criterio è sotto 6 E la media è >= 6.""", max_tokens=600)

    if result:
        is_valid = result.get('is_valid', True)
        scores = result.get('scores', {})
        media = result.get('media', 0)
        failed = result.get('criteri_falliti', [])
        feedback = result.get('feedback', '')

        s['validation_history'].append({
            'scores': scores,
            'media': media,
            'failed': failed,
            'is_valid': is_valid,
        })

        log("validator", f"Media: {media}/10 | Falliti: {failed} | Valido: {is_valid}")
        if feedback:
            log("validator", f"Feedback: {feedback[:150]}")

        return is_valid, feedback, scores

    log("validator", "Errore nella validazione — accetta risposta")
    return True, None, None


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

    # === VALIDATORE POST-RISPOSTA ===
    # Valida solo in gate 3 (quando c'è prescrizione reale)
    if s['gate'] >= 3:
        is_valid, feedback, scores = validate_response(user_input, assistant_reply)

        if not is_valid and feedback:
            log("validator", "Risposta BOCCIATA — rigenero con feedback")

            # Rigenera con il feedback del validatore iniettato
            try:
                regen_system, regen_messages = build_messages(user_input)
                regen_system += f"\n\n=== FEEDBACK VALIDATORE (la tua risposta precedente è stata bocciata) ===\n"
                regen_system += f"Problemi: {feedback}\n"
                regen_system += "Riscrivi la risposta correggendo questi problemi. Non ripetere gli stessi errori.\n"

                regen_response = claude.messages.create(
                    model="claude-sonnet-4-5",
                    max_tokens=4096,
                    system=regen_system,
                    messages=regen_messages
                )
                assistant_reply = strip_process_blocks(regen_response.content[0].text)
                log("validator", "Risposta RIGENERATA con successo")
            except Exception as e:
                log("validator", f"Errore rigenerazione: {e} — uso risposta originale")

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
            bdm_info = ""
            if s.get('bdm_mapping') and s['bdm_mapping'].get('patterns'):
                top = s['bdm_mapping']['patterns'][0]
                bdm_info = f" | BDM: {top['bdm_id']} ({top['probability']}%)"
            val_info = ""
            if s.get('validation_history'):
                last = s['validation_history'][-1]
                val_info = f" | Qualità: {last['media']}/10"
            print(f"\n[Gate: {s['gate']}{bdm_info} | Retrieval: {s['retrieval_done']} | Diagnosi: {'Sì' if s.get('diagnosis') else 'No'}{val_info}]\n")
        except KeyboardInterrupt:
            print("\nInterrotto.")
            break
