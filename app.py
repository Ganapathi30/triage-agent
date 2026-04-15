import streamlit as st
from agent import TriageAgent
from symptom_extractor import extract_symptoms
from triage_engine import classify_urgency

# --- UI CONFIGURATION ---
st.set_page_config(
    page_title="Triage AI | Clinical Intake",
    page_icon="🩺",
    layout="centered"
)

# Custom CSS for a "Chatbot App" feel
st.markdown("""
    <style>
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .report-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        border-left: 5px solid #ff4b4b;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: Patient Status & Disclaimer ---
with st.sidebar:
    st.header("Triage Console")
    st.info("**Administrative Use Only**\n\nThis tool is designed for intake prioritization and does not provide medical diagnoses.")
    
    if "agent" in st.session_state:
        status = "Complete" if st.session_state.agent.is_collection_complete else "In Progress"
        st.write(f"**Session Status:** {status}")
    
    if st.button("Clear Session / New Patient", use_container_width=True):
        st.session_state.agent.reset()
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Hello! I am the clinical triage assistant. To begin, please tell me the patient's age and gender."
        }]
        st.rerun()

# --- MAIN UI ---
st.title("Clinical Triage Assistant")
st.divider()

# Initialize session state
if "agent" not in st.session_state:
    st.session_state.agent = TriageAgent(model_name="llama3:8b")
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I am the clinical triage assistant. To begin evaluating the patient's urgency, please tell me the patient's age and gender."
        }
    ]

# Display chat history with clean icons
for message in st.session_state.messages:
    avatar = "🩺" if message["role"] == "assistant" else "👤"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# --- CHAT LOGIC ---
if not st.session_state.agent.is_collection_complete:
    prompt = st.chat_input("Type patient symptoms or response here...")

    if prompt:
        # User message
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Process logic
        with st.spinner("Analyzing clinical priority..."):
            response_text = st.session_state.agent.process_message(prompt)

        # Assistant response
        with st.chat_message("assistant", avatar="🩺"):
            if st.session_state.agent.is_collection_complete:
                # Run the triage engine
                profile = extract_symptoms(response_text)
                triage_result = classify_urgency(profile)
                final_output = st.session_state.agent.format_final_output(triage_result, profile)
                
                # Render in a high-visibility container
                st.markdown("### 📋 Final Triage Report")
                st.markdown(final_output)
                
                st.session_state.messages.append({"role": "assistant", "content": f"### Triage Report Generated\n{final_output}"})
            else:
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

# Final call to action if complete
if st.session_state.agent.is_collection_complete:
    st.success("Intake session completed. Please review the report above.")