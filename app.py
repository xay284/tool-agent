"""Streamlit chat UI showing the agent's tool calls."""
import streamlit as st

from agent import MODEL, run_agent, save_trace

st.set_page_config(page_title="Tool-Using Agent", page_icon="🛠️")
st.title("🛠️ Tool-Using Agent")
st.caption(f"Model: {MODEL} · tools: calculator, weather, currency, Wikipedia")

if "history" not in st.session_state:
    st.session_state.history = []   # text-only turns sent to the model
    st.session_state.display = []   # turns + traces for the UI

for turn in st.session_state.display:
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])
        if turn.get("trace"):
            with st.expander(f"Tool calls ({len(turn['trace'])})"):
                st.json(turn["trace"])

if prompt := st.chat_input("Ask something, e.g. 'Weather in Tunis and 250 EUR in TND?'"):
    st.session_state.display.append({"role": "user", "content": prompt})
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer, trace = run_agent(st.session_state.history)
        st.markdown(answer)
        if trace:
            with st.expander(f"Tool calls ({len(trace)})"):
                st.json(trace)
    save_trace(prompt, answer, trace)
    st.session_state.history.append({"role": "assistant", "content": answer})
    st.session_state.display.append({"role": "assistant", "content": answer, "trace": trace})
