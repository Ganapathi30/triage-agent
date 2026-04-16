import json
import os
import pytest
from data.models import SymptomProfile
from services.triage_engine import classify_urgency

@pytest.fixture
def sample_cases():
    filepath = os.path.join(os.path.dirname(__file__), "..", "mock_data", "sample_cases.json")
    with open(filepath, "r") as f:
        cases = json.load(f)
    return cases

def test_triage_engine_with_mock_data(sample_cases):
    for case in sample_cases:
        profile = SymptomProfile(
            age=case["age"],
            gender=case.get("gender"),
            primary_symptoms=case["primary_symptoms"],
            duration_hours=case["duration_hours"],
            severity=case["severity"],
            warning_symptoms=case.get("warning_symptoms", []),
            medical_history=case.get("medical_history")
        )
        result = classify_urgency(profile)
        
        assert result.urgency_level == case["expected_urgency"], f"Failed case {case['case_id']}: Expected {case['expected_urgency']}, got {result.urgency_level}"

def test_missing_fields_gracefully():
    # Test that minimal required fields process properly
    profile = SymptomProfile(
        age=30,
        primary_symptoms=["mild pain"],
        duration_hours=2,
        severity="mild"
    )
    result = classify_urgency(profile)
    assert result.urgency_level == "LOW"
