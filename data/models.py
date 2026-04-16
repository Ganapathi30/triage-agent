from pydantic import BaseModel, Field
from typing import Optional, List, Literal

class SymptomProfile(BaseModel):
    age: int = Field(..., description="Age of the patient")
    gender: Optional[str] = Field(None, description="Gender of the patient")
    primary_symptoms: List[str] = Field(..., description="List of primary symptoms reported")
    duration_hours: int = Field(..., description="Duration of symptoms in hours")
    severity: Literal["mild", "moderate", "severe"] = Field(..., description="Severity of the symptoms")
    warning_symptoms: List[str] = Field(default_factory=list, description="Any specific high-risk warning symptoms like chest pain, breathing issues, or bleeding")
    medical_history: Optional[str] = Field(None, description="Relevant medical history")

class TriageResult(BaseModel):
    urgency_level: Literal["HIGH", "MEDIUM", "LOW"]
    reasoning: List[str]
    suggested_action: str
    disclaimer: str = "This triage assistant does not diagnose, prescribe, or replace medical professionals. Please escalate to a clinician immediately for HIGH urgency cases."
