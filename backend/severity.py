"""
Severity scoring and safety escalation module.

Responsible for:
- Mapping discrete text severities ('low', 'medium', 'high', 'critical')
  to standardized numeric scores (1, 2, 3, 4).
- Applying simple, transparent, escalate-only safety rules.
- Ensuring safety hazards (fire, smoke, arc flash) escalate to Critical
  while respecting negation boundaries ('no smoke observed').
"""

from __future__ import annotations

# Standardized ordinal numeric score mapping (Phase 5.5)
SEVERITY_NUMERIC_SCORES: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

# Critical safety hazard keywords that trigger emergency escalation
CRITICAL_HAZARD_KEYWORDS: list[str] = [
    "smoke",
    "fire",
    "arc flash",
    "explosion",
    "electric shock",
    "burning",
    "evacuated",
    "gas trip",
    "sparks",
]

# Negation prefixes checked in a 15-character window preceding a hazard keyword
NEGATION_TOKENS: tuple[str, ...] = ("no ", "not ", "without ", "absent ", "no sign of ")


def _is_hazard_present_and_unnegated(text_lower: str, keyword: str) -> bool:
    """
    Checks if a hazard keyword is present in text without being negated by a preceding token.
    For example:
    - 'smoke detected inside cabinet' -> True (escalate)
    - 'routine walkdown; no smoke observed' -> False (negated by 'no ', do not escalate)
    """
    start_pos = 0
    while True:
        idx = text_lower.find(keyword, start_pos)
        if idx == -1:
            return False

        # Look back up to 15 characters immediately preceding the keyword
        prefix_window = text_lower[max(0, idx - 15) : idx]
        if any(neg in prefix_window for neg in NEGATION_TOKENS):
            # Negation found for this occurrence, look for another occurrence later in string
            start_pos = idx + len(keyword)
            continue

        return True


def assess_severity(ml_predicted_severity: str, description: str) -> tuple[str, int, bool, str]:
    """
    Calculates final severity and numeric score by combining the ML prediction
    with deterministic safety escalation rules.

    Policy:
    - Safety rules can ONLY escalate severity (e.g. Medium -> Critical).
    - Safety rules NEVER lower or downgrade an ML prediction.

    Args:
        ml_predicted_severity: Initial severity from the KNN classifier ('low', 'medium', 'high', 'critical').
        description: Raw or normalized ticket description.

    Returns:
        tuple of (final_severity: str, numeric_score: int, safety_escalated: bool, reason: str)
    """
    normalized_ml_sev = ml_predicted_severity.strip().lower()
    initial_score = SEVERITY_NUMERIC_SCORES.get(normalized_ml_sev, 2)

    text_lower = description.lower()
    safety_escalated = False
    escalation_reason = ""

    # Check for unnegated critical hazard keywords
    for kw in CRITICAL_HAZARD_KEYWORDS:
        if _is_hazard_present_and_unnegated(text_lower, kw):
            safety_escalated = True
            escalation_reason = f"Active safety hazard detected ('{kw}') without negation."
            break

    # Escalate-only logic
    if safety_escalated:
        final_severity = "critical"
        final_score = 4
    else:
        final_severity = normalized_ml_sev
        final_score = initial_score

    return final_severity, final_score, safety_escalated, escalation_reason


def evaluate_severity(description: str, ml_predicted_severity: str) -> dict[str, Any]:
    """
    Convenience wrapper returning structured dictionary with escalation details.
    """
    final_sev, score, escalated, reason = assess_severity(ml_predicted_severity, description)
    return {
        "final_severity": final_sev,
        "numeric_score": score,
        "escalated": escalated,
        "safety_trigger": reason if escalated else None,
    }
