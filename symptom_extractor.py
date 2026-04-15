import json
import re
from typing import Dict, Any
from models import SymptomProfile

def _robust_json_parse(text: str) -> Dict[str, Any]:
    text = text.replace('```json', '').replace('```', '')
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except:
        return {}

def extract_symptoms(llm_output: str) -> SymptomProfile:
    """
    Parses LLM JSON or raw text to extract required fields safely.
    Falls back to safe defaults if extraction fails.
    """

    data = _robust_json_parse(llm_output)
    
    # Default safe fallbacks
    age = data.get("age", 0)
    gender = data.get("gender")
    
    primary_symptoms = data.get("primary_symptoms", [])
    if isinstance(primary_symptoms, str):
        primary_symptoms = [primary_symptoms]
    elif not primary_symptoms:
         primary_symptoms = ["unspecified"]
         
    duration_hours = data.get("duration_hours", 0)
    
    severity_raw = str(data.get("severity", "mild")).lower()
    severity = "mild"
    if "severe" in severity_raw or "bad" in severity_raw:
        severity = "severe"
    elif "moderate" in severity_raw:
        severity = "moderate"
        
    warning_symptoms = data.get("warning_symptoms", [])
    if isinstance(warning_symptoms, str):
        warning_symptoms = [warning_symptoms]

    medical_history = data.get("medical_history")

    return SymptomProfile(
        age=age,
        gender=gender,
        primary_symptoms=primary_symptoms,
        duration_hours=duration_hours,
        severity=severity,
        warning_symptoms=warning_symptoms,
        medical_history=medical_history
    )
