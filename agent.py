from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from models import TriageResult

SYSTEM_PROMPT = """You are a Clinical Triage Assistant Agent. 
Your ONLY purpose is to collect patient symptoms and details to help prioritize them.
You MUST NOT provide medical diagnosis or disease predictions. Never say "you have X condition".
Ask short, prompt 1-line questions. ONE question at a time.
DO NOT use greetings or pleasantries (e.g., no "hello", "sorry you are experiencing this").
Just collect the following information: age, gender, symptoms, duration, severity, warning symptoms, and medical history.

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
    def __init__(self, model_name="llama3:8b"):
        self.llm = ChatOllama(model=model_name, temperature=0.1)
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

    def format_final_output(self, triage_result: TriageResult) -> str:
        color_map = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
        color = color_map.get(triage_result.urgency_level, "🟢")

        # LLM writes the empathetic reasoning based on our strict rule outputs
        reasoning_prompt = f"""
You must translate the following technical triage reasons into plain, non-clinical, empathetic bullet points.
Reasons: {triage_result.reasoning}

DO NOT give a diagnosis. Use cautious words like "may indicate", "suggests".
Output ONLY the bullet points, starting each with a hyphen.
"""
        try:
            expanded_reasons = self.llm.invoke([SystemMessage(content=reasoning_prompt)]).content
        except Exception as e:
            expanded_reasons = "\n".join(f"  - {r}" for r in triage_result.reasoning)

        # Fallback to direct reasons if LLM formatting failed
        if not "-" in expanded_reasons:
            expanded_reasons = "\n".join(f"  - {r}" for r in triage_result.reasoning)

        output = f"""{color} Urgency Level: **{triage_result.urgency_level}**

📋 Reasoning:
{expanded_reasons}

📍 Suggested Action:
  - {triage_result.suggested_action}

⚠️ Disclaimer:
  {triage_result.disclaimer}
"""
        return output
