import streamlit as st
from agent import TriageAgent
from symptom_extractor import extract_symptoms
from triage_engine import classify_urgency

# Page config
st.set_page_config(
    page_title="Clinical Triage Assistant",
    page_icon="🏥",
    layout="centered"
)

st.title("Clinical Triage Assistant")
st.markdown("**(Non-Diagnostic) For Administrative / Intake Use Only**")

# Initialize session state
if "agent" not in st.session_state:
    st.session_state.agent = TriageAgent(model_name="llama3:8b")
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I am the clinical triage assistant. To begin evaluating the patient's urgency, please tell me the patient's age and gender."
        }
    ]

# Display chat history
for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Main interaction
if not st.session_state.agent.is_collection_complete:
    prompt = st.chat_input("Enter patient symptoms or answers...")

    if prompt:
        # Show user message
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append(
            {"role": "user", "content": prompt}
        )

        # 🔧 PROCESS FIRST (no chat container here)
        with st.spinner("Analyzing..."):
            response_text = st.session_state.agent.process_message(prompt)

        # 🧠 AFTER processing, render assistant message
        with st.chat_message("assistant"):

            if st.session_state.agent.is_collection_complete:

                profile = extract_symptoms(response_text)
                triage_result = classify_urgency(profile)

                final_output = st.session_state.agent.format_final_output(triage_result)

                st.markdown(final_output)
                st.session_state.messages.append(
                    {"role": "assistant", "content": final_output}
                )

            else:
                st.markdown(response_text)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response_text}
                )

# Reset flow
if st.session_state.agent.is_collection_complete:
    if st.button("Start New Patient Triage", type="primary"):
        st.session_state.agent.reset()
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I am the clinical triage assistant. To begin evaluating the patient's urgency, please tell me the patient's age and gender."
            }
        ]
        st.rerun()