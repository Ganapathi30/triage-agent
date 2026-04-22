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

FINAL_FORMAT_PROMPT = """You are a clinical triage report formatter.
You receive structured triage data and must output a concise, non-diagnostic report.
Never provide a diagnosis or disease name. Avoid statements like "you have X" or "likely X".
Generate the reasoning from the reported symptoms, duration, severity, warning signs, and medical history.
Explain urgency in plain, non-diagnostic terms (e.g., "symptoms and duration warrant faster assessment").
Do not mention any internal rules or scoring systems.
Use the exact output format below, with no extra sections and no JSON.

FORMAT:
<emoji> Urgency Level: <LEVEL>

Reasoning (Non-diagnostic):
- <bullet>
- <bullet>

Suggested Action:
- <action>

Disclaimer:
<disclaimer>
"""


class FinalFormattingAgent:
    def __init__(self, model_name: str = "llama3.2:3b-instruct-q4_K_M"):
        self.llm = ChatOllama(model=model_name, temperature=0.2)

    def _build_payload(self, triage_result: TriageResult, profile: SymptomProfile, emoji: str) -> str:
        return (
            "Urgency Emoji: {emoji}\n"
            "Urgency Level: {level}\n"
            "Symptoms: {symptoms}\n"
            "Duration (hours): {duration}\n"
            "Severity: {severity}\n"
            "Warning Symptoms: {warnings}\n"
            "Medical History: {history}\n"
            "Notes: Derive reasoning from symptoms, duration, severity, warning signs, and medical history only.\n"
            "Suggested Action: {action}\n"
            "Disclaimer: {disclaimer}\n"
        ).format(
            emoji=emoji,
            level=triage_result.urgency_level,
            symptoms=", ".join(profile.primary_symptoms or []),
            duration=profile.duration_hours,
            severity=profile.severity,
            warnings=", ".join(profile.warning_symptoms or []),
            history=profile.medical_history or "none",
            action=triage_result.suggested_action,
            disclaimer=triage_result.disclaimer,
        )

    def format(self, triage_result: TriageResult, profile: SymptomProfile, emoji: str) -> str:
        payload = self._build_payload(triage_result, profile, emoji)

        response = self.llm.invoke([
            SystemMessage(content=FINAL_FORMAT_PROMPT),
            HumanMessage(content=payload),
        ])
        return response.content

    def format_stream(self, triage_result: TriageResult, profile: SymptomProfile, emoji: str):
        payload = self._build_payload(triage_result, profile, emoji)

        for chunk in self.llm.stream([
            SystemMessage(content=FINAL_FORMAT_PROMPT),
            HumanMessage(content=payload),
        ]):
            text = getattr(chunk, "content", "")
            if text:
                yield text

class TriageAgent:
    def __init__(self, model_name="llama3:8b", formatter_model_name="llama3.2:3b-instruct-q4_K_M"):
        self.llm = ChatOllama(model=model_name, temperature=0.1, alive=-1)
        self.formatter = FinalFormattingAgent(model_name=formatter_model_name)
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
        try:
                        color_map = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
                        color = color_map.get(triage_result.urgency_level, "🟢")
                        return self.formatter.format(triage_result, profile, color)
        except Exception as exc:
                return f"Formatter model error: {exc}"

    def format_final_output_stream(self, triage_result: TriageResult, profile: SymptomProfile):
        color_map = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
        color = color_map.get(triage_result.urgency_level, "🟢")
        try:
            yield from self.formatter.format_stream(triage_result, profile, color)
        except Exception as exc:
            yield f"Formatter model error: {exc}"