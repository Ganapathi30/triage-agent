import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from services.triage_queue_store import load_triage_queue, save_triage_queue
from ui.triage_rules_editor import render_rules_editor
from ui.triage_session import render_triage_session


BASE_DIR = ROOT_DIR
RULES_PATH = BASE_DIR / "data" / "triage_rules.json"
QUEUE_PATH = BASE_DIR / "data" / "triage_queue.json"


st.set_page_config(
    page_title="Triage AI | Clinical Intake",
    page_icon="🩺",
    layout="centered"
)


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


with st.sidebar:
    st.header("Triage Console")
    st.info("**Administrative Use Only**\n\nThis tool is designed for intake prioritization and does not provide medical diagnoses.")

    page_choice = st.radio(
        "Menu",
        ["Triage Session", "Rule Editor"],
        index=0,
    )

    status_placeholder = st.empty()

    st.subheader("Current Shift Queue")
    queue_data = load_triage_queue(QUEUE_PATH)
    if queue_data:
        st.dataframe(queue_data, use_container_width=True, hide_index=True)
    else:
        st.caption("No patients triaged yet for this shift.")

    if st.button("Clear Shift Queue", use_container_width=True):
        save_triage_queue(QUEUE_PATH, [])
        st.rerun()

    if st.button("Clear Session / New Patient", use_container_width=True):
        st.session_state.agent.reset()
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Hello! I am the clinical triage assistant. To begin, please tell me the patient's age and gender."
        }]
        st.session_state.queue_logged = False
        st.rerun()

if page_choice == "Rule Editor":
    st.title("Triage Rule Editor")
    st.divider()
    render_rules_editor(RULES_PATH)
else:
    render_triage_session(QUEUE_PATH, status_placeholder)
