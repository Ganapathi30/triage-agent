import json
from pathlib import Path

import streamlit as st


def _load_rules(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_csv_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def _clean_rule_row(row: dict) -> dict:
    cleaned = {}
    rule_id = str(row.get("id", "")).strip()
    if rule_id:
        cleaned["id"] = rule_id
    if row.get("match_warning_symptoms"):
        cleaned["match_warning_symptoms"] = True
    match_symptoms = _parse_csv_list(row.get("match_symptoms"))
    if match_symptoms:
        cleaned["match_symptoms"] = match_symptoms
    match_groups = _parse_csv_list(row.get("match_symptom_groups"))
    if match_groups:
        cleaned["match_symptom_groups"] = match_groups
    if row.get("match_all_symptoms"):
        cleaned["match_all_symptoms"] = True
    min_duration = row.get("min_duration_hours")
    if isinstance(min_duration, (int, float)) and min_duration >= 0:
        cleaned["min_duration_hours"] = int(min_duration)
    severity = str(row.get("severity", "")).strip().lower()
    if severity:
        cleaned["severity"] = severity
    urgency = str(row.get("urgency", "")).strip().upper()
    if urgency:
        cleaned["urgency"] = urgency
    reason = str(row.get("reason", "")).strip()
    if reason:
        cleaned["reason"] = reason
    return cleaned


def _clean_modifier_row(row: dict) -> dict:
    cleaned = {}
    modifier_id = str(row.get("id", "")).strip()
    if modifier_id:
        cleaned["id"] = modifier_id
    history = _parse_csv_list(row.get("medical_history_keywords"))
    if history:
        cleaned["medical_history_keywords"] = history
    symptoms = _parse_csv_list(row.get("symptom_keywords"))
    if symptoms:
        cleaned["symptom_keywords"] = symptoms
    for key in ("max_age", "min_age", "min_duration_hours", "bump_levels"):
        value = row.get(key)
        if isinstance(value, (int, float)) and value >= 0:
            cleaned[key] = int(value)
    reason = str(row.get("reason", "")).strip()
    if reason:
        cleaned["reason"] = reason
    return cleaned


def render_rules_editor(rules_path: Path) -> None:
    st.subheader("Triage Rule Editor")
    st.caption("Admins can update triage rules here. Changes save directly to triage_rules.json.")

    rules_data = _load_rules(rules_path)

    warning_keywords_table = [
        {"keyword": keyword}
        for keyword in rules_data.get("warning_keywords", [])
    ]
    symptom_groups_table = [
        {"group": group_name, "symptoms": ", ".join(symptoms)}
        for group_name, symptoms in rules_data.get("symptom_groups", {}).items()
    ]
    rules_table = [
        {
            "id": rule.get("id"),
            "match_warning_symptoms": rule.get("match_warning_symptoms", False),
            "match_symptom_groups": ", ".join(rule.get("match_symptom_groups", [])),
            "match_symptoms": ", ".join(rule.get("match_symptoms", [])),
            "match_all_symptoms": rule.get("match_all_symptoms", False),
            "min_duration_hours": rule.get("min_duration_hours"),
            "severity": rule.get("severity"),
            "urgency": rule.get("urgency"),
            "reason": rule.get("reason"),
        }
        for rule in rules_data.get("rules", [])
    ]
    modifiers_table = [
        {
            "id": modifier.get("id"),
            "medical_history_keywords": ", ".join(modifier.get("medical_history_keywords", [])),
            "symptom_keywords": ", ".join(modifier.get("symptom_keywords", [])),
            "max_age": modifier.get("max_age"),
            "min_age": modifier.get("min_age"),
            "min_duration_hours": modifier.get("min_duration_hours"),
            "bump_levels": modifier.get("bump_levels"),
            "reason": modifier.get("reason"),
        }
        for modifier in rules_data.get("modifiers", [])
    ]

    edited_warning_keywords = st.data_editor(
        warning_keywords_table,
        num_rows="dynamic",
        use_container_width=True,
        key="warning_keywords_editor",
    )
    edited_symptom_groups = st.data_editor(
        symptom_groups_table,
        num_rows="dynamic",
        use_container_width=True,
        key="symptom_groups_editor",
    )
    edited_rules = st.data_editor(
        rules_table,
        num_rows="dynamic",
        use_container_width=True,
        key="rules_editor",
    )
    edited_modifiers = st.data_editor(
        modifiers_table,
        num_rows="dynamic",
        use_container_width=True,
        key="modifiers_editor",
    )

    if st.button("Save Rule Changes", type="primary"):
        cleaned_rules = []
        for row in edited_rules:
            cleaned = _clean_rule_row(row)
            if cleaned:
                cleaned_rules.append(cleaned)
        cleaned_modifiers = []
        for row in edited_modifiers:
            cleaned = _clean_modifier_row(row)
            if cleaned:
                cleaned_modifiers.append(cleaned)
        updated_rules = {
            "warning_keywords": [
                row.get("keyword").strip()
                for row in edited_warning_keywords
                if isinstance(row.get("keyword"), str) and row.get("keyword").strip()
            ],
            "symptom_groups": {
                row.get("group").strip(): _parse_csv_list(row.get("symptoms"))
                for row in edited_symptom_groups
                if isinstance(row.get("group"), str) and row.get("group").strip()
            },
            "rules": cleaned_rules,
            "modifiers": cleaned_modifiers,
        }
        with rules_path.open("w", encoding="utf-8") as handle:
            json.dump(updated_rules, handle, indent=2)
        st.success("Triage rules updated.")
