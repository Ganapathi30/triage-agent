from datetime import datetime
from pathlib import Path

import streamlit as st
from agent import TriageAgent
from symptom_extractor import extract_symptoms
from triage_engine import classify_urgency
from triage_queue_store import append_triage_entry


def render_triage_session(queue_path: Path, status_placeholder=None) -> None:
    st.title("Clinical Triage Assistant")
    st.divider()

    if "agent" not in st.session_state:
        st.session_state.agent = TriageAgent(model_name="llama3:8b")
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I am the clinical triage assistant. To begin evaluating the patient's urgency, please tell me the patient's age and gender."
            }
        ]
        st.session_state.queue_logged = False

    for message in st.session_state.messages:
        avatar = "🩺" if message["role"] == "assistant" else "👤"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    if not st.session_state.agent.is_collection_complete:
        prompt = st.chat_input("Type patient symptoms or response here...")

        if prompt:
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.spinner("Analyzing clinical priority..."):
                response_text = st.session_state.agent.process_message(prompt)

            with st.chat_message("assistant", avatar="🩺"):
                if st.session_state.agent.is_collection_complete:
                    st.info("Symptom collection complete, analysing priority...")
                    profile = extract_symptoms(response_text)
                    triage_result = classify_urgency(profile)
                    final_output = st.session_state.agent.format_final_output(triage_result, profile)

                    if not st.session_state.get("queue_logged", False):
                        entry = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "urgency": triage_result.urgency_level,
                            "primary_symptom": ", ".join(profile.primary_symptoms or ["unspecified"]),
                        }
                        append_triage_entry(queue_path, entry)
                        st.session_state.queue_logged = True

                    st.markdown("### 📋 Final Triage Report")
                    st.markdown(final_output)

                    st.session_state.messages.append({"role": "assistant", "content": f"### Triage Report Generated\n{final_output}"})
                else:
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})

    if st.session_state.agent.is_collection_complete:
        st.success("Intake session completed. Please review the report above.")

    if status_placeholder is not None and "agent" in st.session_state:
        status = "Complete" if st.session_state.agent.is_collection_complete else "In Progress"
        status_placeholder.write(f"**Session Status:** {status}")
