import json
import os
from models import SymptomProfile, TriageResult

def load_rules(filepath=None):
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), "triage_rules.json")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def _bump_urgency(current_urgency, bump_levels):
    levels = ["LOW", "MEDIUM", "HIGH"]
    current_idx = levels.index(current_urgency)
    new_idx = min(len(levels) - 1, current_idx + bump_levels)
    return levels[new_idx]

def classify_urgency(profile: SymptomProfile, rules_data=None) -> TriageResult:
    print(profile)
    if rules_data is None:
        rules_data = load_rules()
        
    urgency = "LOW"
    reasons = []
    
    # Check warning keywords explicitly against primary_symptoms
    has_warning_keyword = any(
        kw in symptom.lower() 
        for kw in rules_data.get("warning_keywords", []) 
        for symptom in profile.primary_symptoms
    )
    if profile.warning_symptoms:
        has_warning_keyword = True
        
    # Evaluate Rules (find highest matching urgency)
    matched_level = "LOW"
    rule_reasons = []
    
    level_weight = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

    def update_match(candidate_level, reason):
        nonlocal matched_level
        if level_weight[candidate_level] > level_weight[matched_level]:
            matched_level = candidate_level
        rule_reasons.append(reason)
        
    for rule in rules_data.get("rules", []):
        matched = False
        
        if rule.get("match_warning_symptoms") and has_warning_keyword:
            matched = True
            
        elif rule.get("match_symptoms"):
            matches = [s.lower() for s in profile.primary_symptoms]
            
            is_match = False
            if rule.get("match_all_symptoms"):
                is_match = all(any(req_s.lower() in r_s.lower() for r_s in matches) for req_s in rule.get("match_symptoms", []))
            else:
                is_match = any(any(req_s.lower() in r_s.lower() for r_s in matches) for req_s in rule.get("match_symptoms", []))
            if is_match:
                matched = True

        elif rule.get("severity") and rule.get("min_duration_hours"):
            if profile.severity == rule["severity"] and profile.duration_hours >= rule["min_duration_hours"]:
                matched = True
                
        elif rule.get("severity"):
            if profile.severity == rule["severity"]:
                matched = True
                
        if matched:
            update_match(rule["urgency"], rule["reason"])

    urgency = matched_level
    if rule_reasons:
        # Avoid duplicate reasons
        for r in rule_reasons:
            if r not in reasons:
                reasons.append(r)
    else:
        reasons.append("Mild symptoms with no warning flags.")

    # Modifiers
    for mod in rules_data.get("modifiers", []):
        bumped = False
        if "max_age" in mod and profile.age <= mod["max_age"]:
            bumped = True
        elif "min_age" in mod and profile.age >= mod["min_age"]:
            bumped = True
        elif "min_duration_hours" in mod and profile.duration_hours >= mod["min_duration_hours"]:
            bumped = True
            
        if bumped:
            old_urgency = urgency
            urgency = _bump_urgency(urgency, mod["bump_levels"])
            if old_urgency != urgency or urgency == "HIGH": 
                # Record reason if it actively bumped or if it's already high
                if mod["reason"] not in reasons:
                    reasons.append(mod["reason"])

    # Set suggested action
    if urgency == "HIGH":
        action = "Escort patient to triage immediately. Do not wait."
    elif urgency == "MEDIUM":
        action = "Escort patient to the waiting room and alert the triage nurse for a priority assessment."
    else:
        action = "Have the patient take a seat in the waiting room for standard assessment."

    return TriageResult(
        urgency_level=urgency,
        reasoning=reasons,
        suggested_action=action
    )
