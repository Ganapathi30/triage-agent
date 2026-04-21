import json
from pathlib import Path

from data.models import SymptomProfile, TriageResult

def load_rules(filepath=None):
    if filepath is None:
        filepath = Path(__file__).resolve().parents[1] / "data" / "triage_rules.json"
    with Path(filepath).open("r", encoding="utf-8") as handle:
        return json.load(handle)

def _bump_urgency(current_urgency, bump_levels):
    levels = ["LOW", "MEDIUM", "HIGH"]
    current_idx = levels.index(current_urgency)
    new_idx = min(len(levels) - 1, current_idx + bump_levels)
    return levels[new_idx]


def _normalize_symptoms(symptoms):
    return [s.strip().lower() for s in symptoms if isinstance(s, str) and s.strip()]


def _expand_match_symptoms(rule, symptom_groups):
    expanded = []
    for symptom in rule.get("match_symptoms", []):
        if isinstance(symptom, str) and symptom:
            expanded.append(symptom.lower())
    for group_name in rule.get("match_symptom_groups", []):
        expanded.extend(symptom_groups.get(group_name, []))
    return [s for s in expanded if s]


def _matches_symptoms(required, symptom_text, match_all):
    if not required:
        return False
    if match_all:
        return all(req in symptom_text for req in required)
    return any(req in symptom_text for req in required)


def _has_severity_constraint(rule):
    severity = rule.get("severity")
    if not isinstance(severity, str):
        return False
    return severity.strip().lower() not in ("", "none")

def classify_urgency(profile: SymptomProfile, rules_data=None) -> TriageResult:
    if rules_data is None:
        rules_data = load_rules()

    urgency = "LOW"
    reasons = []
    reasons_seen = set()

    symptoms = _normalize_symptoms(profile.primary_symptoms)
    symptom_text = " | ".join(symptoms)
    warning_keywords = [kw.lower() for kw in rules_data.get("warning_keywords", []) if isinstance(kw, str)]
    symptom_groups = {
        name: [s.lower() for s in group if isinstance(s, str)]
        for name, group in rules_data.get("symptom_groups", {}).items()
    }

    # Check warning keywords explicitly against primary_symptoms
    has_warning_keyword = any(kw in symptom_text for kw in warning_keywords)
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

        elif rule.get("match_symptoms") or rule.get("match_symptom_groups"):
            required = _expand_match_symptoms(rule, symptom_groups)
            matched = _matches_symptoms(required, symptom_text, rule.get("match_all_symptoms", False))
            if matched and _has_severity_constraint(rule):
                matched = profile.severity == rule["severity"]
            if matched and rule.get("min_duration_hours"):
                matched = profile.duration_hours >= rule["min_duration_hours"]

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
        for r in rule_reasons:
            if r not in reasons_seen:
                reasons.append(r)
                reasons_seen.add(r)
    else:
        reasons.append("Mild symptoms with no warning flags.")
        reasons_seen.add("Mild symptoms with no warning flags.")

    # Modifiers
    history = str(profile.medical_history).lower() if profile.medical_history else ""
    for mod in rules_data.get("modifiers", []):
        bumped = False
        if "medical_history_keywords" in mod and history:
            if any(kw in history for kw in mod["medical_history_keywords"]):
                if "symptom_keywords" in mod:
                    if any(kw in symptom_text for kw in mod["symptom_keywords"]):
                        bumped = True
                else:
                    bumped = True
        if not bumped and "max_age" in mod and profile.age <= mod["max_age"]:
            bumped = True
        if not bumped and "min_age" in mod and profile.age >= mod["min_age"]:
            bumped = True
        if not bumped and "min_duration_hours" in mod and profile.duration_hours >= mod["min_duration_hours"]:
            bumped = True

        if bumped:
            old_urgency = urgency
            urgency = _bump_urgency(urgency, mod["bump_levels"])
            if old_urgency != urgency or urgency == "HIGH":
                if mod["reason"] not in reasons_seen:
                    reasons.append(mod["reason"])
                    reasons_seen.add(mod["reason"])

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