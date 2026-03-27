import streamlit as st
from agent import chat, session

st.set_page_config(
    page_title="Atomic Habits AI Coach",
    page_icon="🧠",
    layout="centered"
)

st.title("🧠 Atomic Habits AI Coach")
st.caption("Sistema di behavior change basato su Atomic Habits")

with st.sidebar:
    st.header("Sessione")
    st.metric("Gate corrente", session['gate'])
    st.metric("Turni", len(session['conversation'])//2)
    if st.button("🔄 Nuovo caso"):
        session['conversation'] = []
        session['gate'] = 0
        session['retrieval_done'] = False
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Descrivi il comportamento su cui vuoi lavorare..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Elaborazione..."):
            reply = chat(prompt)
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()