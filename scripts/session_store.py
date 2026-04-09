"""
Session Store — persistenza sessioni per Atomic Habits Coach.
Backend: Supabase (se configurato), altrimenti fallback in-memory.

Tabelle richieste in Supabase:
    coach_sessions: id (uuid), title (text), created_at (timestamptz), gate (int), feedback_avg (float)
    coach_messages: id (uuid), session_id (uuid FK), role (text), content (text), created_at (timestamptz), feedback (int nullable)
"""

import os
import uuid
from datetime import datetime, timezone

# === SUPABASE SETUP ===
_supabase = None
SUPABASE_AVAILABLE = False

def _get_secret(key):
    try:
        import streamlit as st
        return st.secrets.get(key)
    except Exception:
        return os.getenv(key)

try:
    _url = _get_secret('SUPABASE_URL')
    _key = _get_secret('SUPABASE_SERVICE_KEY') or _get_secret('SUPABASE_KEY')
    if _url and _key:
        from supabase import create_client
        _supabase = create_client(_url, _key)
        SUPABASE_AVAILABLE = True
        print("[session_store] Supabase connesso")
    else:
        print("[session_store] Supabase non configurato — modalita in-memory")
except Exception as e:
    print(f"[session_store] Supabase non disponibile: {e}")

# === IN-MEMORY FALLBACK ===
_memory_sessions = []  # [{id, title, created_at, gate, messages: [...]}]


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _find_memory_session(session_id):
    """Trova sessione in-memory per id."""
    for s in _memory_sessions:
        if s['id'] == session_id:
            return s
    return None


def _ensure_memory_session(session_id, title="Sessione recuperata"):
    """Assicura che esista una sessione in-memory (crea se manca). Fix #7."""
    s = _find_memory_session(session_id)
    if not s:
        s = {
            'id': session_id,
            'title': title,
            'created_at': _now_iso(),
            'gate': 0,
            'messages': [],
        }
        _memory_sessions.append(s)
    return s


# =========================================================================
# SESSIONI
# =========================================================================

def create_session(title="Nuova sessione"):
    """Crea una nuova sessione. Restituisce session_id."""
    session_id = str(uuid.uuid4())
    safe_title = str(title or "Nuova sessione")[:100]  # Fix validazione

    if SUPABASE_AVAILABLE:
        try:
            _supabase.table('coach_sessions').insert({
                'id': session_id,
                'title': safe_title,
                'created_at': _now_iso(),
                'gate': 0,
                'feedback_avg': None,
            }).execute()
        except Exception as e:
            print(f"[session_store] Errore Supabase creazione sessione: {e} — fallback in-memory")
            # Fix #7: fallback in-memory se Supabase fallisce
            _ensure_memory_session(session_id, safe_title)
    else:
        _ensure_memory_session(session_id, safe_title)

    return session_id


def list_sessions(limit=20):
    """Lista sessioni recenti (piu recenti prima)."""
    if SUPABASE_AVAILABLE:
        try:
            result = _supabase.table('coach_sessions') \
                .select('id, title, created_at, gate') \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            return result.data or []
        except Exception as e:
            print(f"[session_store] Errore lista sessioni: {e}")
            # Fix #7: fallback a in-memory
    # In-memory (sia come default che come fallback)
    sorted_sessions = sorted(_memory_sessions, key=lambda s: s['created_at'], reverse=True)
    return [{'id': s['id'], 'title': s['title'], 'created_at': s['created_at'], 'gate': s['gate']}
            for s in sorted_sessions[:limit]]


def update_session(session_id, title=None, gate=None):
    """Aggiorna titolo o gate di una sessione."""
    if SUPABASE_AVAILABLE:
        try:
            data = {}
            if title is not None:
                data['title'] = str(title)[:100]
            if gate is not None:
                data['gate'] = gate
            if data:
                _supabase.table('coach_sessions').update(data).eq('id', session_id).execute()
                return
        except Exception as e:
            print(f"[session_store] Errore aggiornamento sessione: {e}")
    # Fallback in-memory
    s = _find_memory_session(session_id)
    if s:
        if title is not None:
            s['title'] = str(title)[:100]
        if gate is not None:
            s['gate'] = gate


def delete_session(session_id):
    """Elimina una sessione e i suoi messaggi."""
    if SUPABASE_AVAILABLE:
        try:
            _supabase.table('coach_messages').delete().eq('session_id', session_id).execute()
            _supabase.table('coach_sessions').delete().eq('id', session_id).execute()
        except Exception as e:
            print(f"[session_store] Errore eliminazione sessione: {e}")
    # Rimuovi anche da in-memory (sempre, per pulizia)
    _memory_sessions[:] = [s for s in _memory_sessions if s['id'] != session_id]


# =========================================================================
# MESSAGGI
# =========================================================================

def save_message(session_id, role, content):
    """Salva un messaggio. Restituisce message_id."""
    msg_id = str(uuid.uuid4())
    msg_data = {
        'id': msg_id,
        'role': role,
        'content': content,
        'created_at': _now_iso(),
        'feedback': None,
    }

    saved_to_db = False
    if SUPABASE_AVAILABLE:
        try:
            _supabase.table('coach_messages').insert({
                **msg_data,
                'session_id': session_id,
            }).execute()
            saved_to_db = True
        except Exception as e:
            print(f"[session_store] Errore Supabase salvataggio messaggio: {e} — fallback in-memory")

    # Fix #7: salva sempre anche in-memory come backup
    if not saved_to_db:
        s = _ensure_memory_session(session_id)
        s['messages'].append(msg_data)

    return msg_id


def load_messages(session_id):
    """Carica tutti i messaggi di una sessione (ordine cronologico)."""
    if SUPABASE_AVAILABLE:
        try:
            result = _supabase.table('coach_messages') \
                .select('id, role, content, created_at, feedback') \
                .eq('session_id', session_id) \
                .order('created_at') \
                .execute()
            if result.data:
                return result.data
        except Exception as e:
            print(f"[session_store] Errore caricamento messaggi: {e}")
    # Fallback in-memory
    s = _find_memory_session(session_id)
    if s:
        return s.get('messages', [])
    return []


def save_feedback(message_id, feedback):
    """Salva feedback (1 = positivo, -1 = negativo) su un messaggio.
    Restituisce True se salvato con successo."""
    # Validazione tipo
    if feedback not in (1, -1, None):
        print(f"[session_store] Feedback non valido: {feedback}")
        return False

    if SUPABASE_AVAILABLE:
        try:
            _supabase.table('coach_messages').update({
                'feedback': feedback
            }).eq('id', message_id).execute()
            return True
        except Exception as e:
            print(f"[session_store] Errore salvataggio feedback: {e}")

    # Fallback in-memory
    for s in _memory_sessions:
        for m in s.get('messages', []):
            if m['id'] == message_id:
                m['feedback'] = feedback
                return True
    return False
