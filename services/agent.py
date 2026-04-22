from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from data.models import SymptomProfile, TriageResult

SYSTEM_PROMPT = """You are a Clinical Triage Assistant Agent. 
Your ONLY purpose is to collect patient symptoms and details to help prioritize them.
You MUST NOT provide medical diagnosis or disease predictions. Never say "you have X condition".
Ask short, prompt 1-line questions. ONE question at a time, if many details are provided in a single response, do not ask that question again.
DO NOT use greetings or pleasantries (e.g., no "hello", "sorry you are experiencing this").
DO NOT repeat previous questions. DO NOT echo the user's input. Wait for the user to answer, then ask ONLY the next required question.
Just collect the following information: age, gender, symptoms, duration, severity(Mild/Moderate/Severe), warning symptoms, and medical history.

Important collection rules:
1) The user may provide multiple required fields in a single message. Always extract ALL fields present in each user message before asking anything else.
2) Never ask for a field that has already been provided earlier in the conversation.
3) If the user says "I already said" or similar, use previously provided details and ask only for still-missing fields.
4) Ask follow-up questions ONLY for missing required fields.
5) Do not ask for the same field twice unless the value is truly missing or contradictory.
6) Do not ask any questions other than the required fields.
7) Duration should be normalized to duration_hours in JSON.

If critical fields are missing, ask follow-up 1-line questions.

ONCE ALL required fields are collected, you MUST output a JSON object containing the extracted data, wrapped in ```json ... ``` tags, and NO OTHER TEXT. Do not output JSON until you have the required fields.
Example JSON:
```json
{
  "age": 45,
  "gender": "Male",
  "primary_symptoms": ["headache"],
  "duration_hours": 24,
  "severity": "mild",
  "warning_symptoms": [],
  "medical_history": "none"
}
```
"""

class TriageAgent:
    def __init__(self, model_name="llama3:8b", formatter_model_name="llama3.2:3b-instruct-q4_K_M"):
        self.llm = ChatOllama(model=model_name, temperature=0.1, alive=-1)
        self.reset()

    def reset(self):
        self.conversation_history = [SystemMessage(content=SYSTEM_PROMPT)]
        self.is_collection_complete = False

    def process_message(self, user_msg: str) -> str:
        self.conversation_history.append(HumanMessage(content=user_msg))
        response = self.llm.invoke(self.conversation_history)
        ai_text = response.content

        # Determine if json is outputted
        if "```json" in ai_text or ('{' in ai_text and '"age"' in ai_text.lower() and '"severity"' in ai_text.lower()):
            self.is_collection_complete = True
            return ai_text

        self.conversation_history.append(AIMessage(content=ai_text))
        return ai_text

    def format_final_output(self, triage_result: TriageResult, profile: SymptomProfile) -> str:
        color_map = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
        color = color_map.get(triage_result.urgency_level, "🟢")

        context_reasons = [
            f"Reported symptoms: {', '.join(profile.primary_symptoms or ['unspecified'])}.",
            f"Symptom duration: {profile.duration_hours} hour(s).",
            f"Reported severity: {profile.severity.capitalize()}.",
        ]

        if profile.warning_symptoms:
            context_reasons.append(
                f"Warning signs noted: {', '.join(profile.warning_symptoms)}."
            )
        else:
            context_reasons.append("No warning signs were reported.")

        if profile.medical_history and str(profile.medical_history).strip().lower() not in {"none", "no", "nil"}:
            context_reasons.append(f"Relevant medical history: {profile.medical_history}.")
        else:
            context_reasons.append("No significant medical history was reported.")

        reasoning = triage_result.reasoning or [
            "Urgency assigned using collected symptom details and safety checks."
        ]
        reasoning.extend(context_reasons)
        reasoning_block = "\n".join(f"- {line}" for line in reasoning)

        return (
            f"{color} Urgency Level: {triage_result.urgency_level}\n\n"
            "Reasoning (Non-diagnostic):\n"
            f"{reasoning_block}\n\n"
            "Suggested Action:\n"
            f"- {triage_result.suggested_action}\n\n"
            "Disclaimer:\n"
            f"{triage_result.disclaimer}"
        )