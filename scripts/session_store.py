"""
Session Store — persistenza sessioni per Atomic Habits Coach.
Backend: Supabase (se configurato), altrimenti fallback in-memory.

Tabelle richieste in Supabase:
    coach_sessions: id (uuid), title (text), created_at (timestamptz), gate (int), feedback_avg (float)
    coach_messages: id (uuid), session_id (uuid FK), role (text), content (text), created_at (timestamptz), feedback (int nullable)
"""

import os
import json
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


# =========================================================================
# SESSIONI
# =========================================================================

def create_session(title="Nuova sessione"):
    """Crea una nuova sessione. Restituisce session_id."""
    session_id = str(uuid.uuid4())

    if SUPABASE_AVAILABLE:
        try:
            _supabase.table('coach_sessions').insert({
                'id': session_id,
                'title': title[:100],
                'created_at': _now_iso(),
                'gate': 0,
                'feedback_avg': None,
            }).execute()
        except Exception as e:
            print(f"[session_store] Errore creazione sessione: {e}")
    else:
        _memory_sessions.append({
            'id': session_id,
            'title': title[:100],
            'created_at': _now_iso(),
            'gate': 0,
            'messages': [],
        })

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
            return []
    else:
        sorted_sessions = sorted(_memory_sessions, key=lambda s: s['created_at'], reverse=True)
        return [{'id': s['id'], 'title': s['title'], 'created_at': s['created_at'], 'gate': s['gate']}
                for s in sorted_sessions[:limit]]


def update_session(session_id, title=None, gate=None):
    """Aggiorna titolo o gate di una sessione."""
    if SUPABASE_AVAILABLE:
        try:
            data = {}
            if title is not None:
                data['title'] = title[:100]
            if gate is not None:
                data['gate'] = gate
            if data:
                _supabase.table('coach_sessions').update(data).eq('id', session_id).execute()
        except Exception as e:
            print(f"[session_store] Errore aggiornamento sessione: {e}")
    else:
        for s in _memory_sessions:
            if s['id'] == session_id:
                if title is not None:
                    s['title'] = title[:100]
                if gate is not None:
                    s['gate'] = gate
                break


def delete_session(session_id):
    """Elimina una sessione e i suoi messaggi."""
    if SUPABASE_AVAILABLE:
        try:
            _supabase.table('coach_messages').delete().eq('session_id', session_id).execute()
            _supabase.table('coach_sessions').delete().eq('id', session_id).execute()
        except Exception as e:
            print(f"[session_store] Errore eliminazione sessione: {e}")
    else:
        _memory_sessions[:] = [s for s in _memory_sessions if s['id'] != session_id]


# =========================================================================
# MESSAGGI
# =========================================================================

def save_message(session_id, role, content):
    """Salva un messaggio. Restituisce message_id."""
    msg_id = str(uuid.uuid4())

    if SUPABASE_AVAILABLE:
        try:
            _supabase.table('coach_messages').insert({
                'id': msg_id,
                'session_id': session_id,
                'role': role,
                'content': content,
                'created_at': _now_iso(),
                'feedback': None,
            }).execute()
        except Exception as e:
            print(f"[session_store] Errore salvataggio messaggio: {e}")
    else:
        for s in _memory_sessions:
            if s['id'] == session_id:
                s['messages'].append({
                    'id': msg_id,
                    'role': role,
                    'content': content,
                    'created_at': _now_iso(),
                    'feedback': None,
                })
                break

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
            return result.data or []
        except Exception as e:
            print(f"[session_store] Errore caricamento messaggi: {e}")
            return []
    else:
        for s in _memory_sessions:
            if s['id'] == session_id:
                return s['messages']
        return []


def save_feedback(message_id, feedback):
    """Salva feedback (1 = positivo, -1 = negativo) su un messaggio."""
    if SUPABASE_AVAILABLE:
        try:
            _supabase.table('coach_messages').update({
                'feedback': feedback
            }).eq('id', message_id).execute()
        except Exception as e:
            print(f"[session_store] Errore salvataggio feedback: {e}")
    else:
        for s in _memory_sessions:
            for m in s.get('messages', []):
                if m['id'] == message_id:
                    m['feedback'] = feedback
                    return
