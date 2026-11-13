"""
Transparent priority scoring and routing rules for renewable-energy O&M tickets.
"""

from __future__ import annotations

from typing import Any

SEVERITY_WEIGHTS: dict[str, float] = {
    "low": 0.25,
    "medium": 0.50,
    "high": 0.75,
    "critical": 1.00,
}

SLA_HOURS_BY_SEVERITY: dict[str, int] = {
    "critical": 1,
    "high": 4,
    "medium": 24,
    "low": 72,
}

PRIORITY_FORMULA_TEXT = (
    "priority_score = 100 * (0.45 * severity_weight + 0.20 * asset_criticality "
    "+ 0.20 * generation_loss_risk + 0.10 * safety_flag + 0.05 * min(duplicate_count, 3) / 3)"
)


def compute_priority(
    severity: str,
    asset_criticality: float,
    generation_loss_risk: float,
    safety_flag: bool,
    duplicate_count: int = 0,
) -> dict[str, Any]:
    """Compute a transparent 0-100 priority score and return component breakdown."""
    sev_w = SEVERITY_WEIGHTS.get(severity.lower(), 0.50)
    crit = max(0.0, min(1.0, float(asset_criticality)))
    gen_risk = max(0.0, min(1.0, float(generation_loss_risk)))
    saf = 1.0 if safety_flag else 0.0
    dup = min(max(0, int(duplicate_count)), 3) / 3.0

    score = 100.0 * (
        0.45 * sev_w
        + 0.20 * crit
        + 0.20 * gen_risk
        + 0.10 * saf
        + 0.05 * dup
    )
    score = round(score, 1)

    return {
        "priority_score": score,
        "formula": PRIORITY_FORMULA_TEXT,
        "components": {
            "severity_weight": sev_w,
            "asset_criticality": round(crit, 2),
            "generation_loss_risk": round(gen_risk, 2),
            "safety_flag": int(saf),
            "duplicate_factor": round(dup, 2),
        },
    }


def route_ticket(
    category: str,
    asset_type: str,
    severity: str,
    priority_score: float,
    runbook_owner: str | None = None,
) -> dict[str, Any]:
    """Assign owner team and SLA target based on category, asset type, and severity."""
    sev = severity.lower()
    sla_hours = SLA_HOURS_BY_SEVERITY.get(sev, 24)
    team = runbook_owner or f"{asset_type.capitalize()} O&M Operations Team"

    if sev == "critical" or priority_score >= 85.0:
        escalation_tier = "Tier-1 Immediate Dispatch"
    elif sev == "high" or priority_score >= 65.0:
        escalation_tier = "Tier-2 Same-Shift Engineering"
    elif sev == "medium":
        escalation_tier = "Tier-3 Scheduled Maintenance"
    else:
        escalation_tier = "Tier-4 Routine Backlog"

    return {
        "owner_team": team,
        "sla_hours": sla_hours,
        "sla_label": f"Respond within {sla_hours} hour{'s' if sla_hours != 1 else ''}",
        "escalation_tier": escalation_tier,
    }
