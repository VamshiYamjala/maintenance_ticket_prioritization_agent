"""
===============================================================================
FILE: backend/priority.py
===============================================================================
1. WHAT THIS FILE DOES:
   Calculates a transparent, weighted 0 to 100 priority score for maintenance
   tickets and assigns an appropriate operations engineering team, escalation tier,
   and Service Level Agreement (SLA) response window.

2. WHY THIS FILE IS NEEDED:
   In renewable power plants (Solar, Wind, Hydro, Grid), raw machine learning
   severity predictions alone cannot decide dispatch order. A low-severity issue
   on a critical main grid transformer or repeat nuisance tripping must be handled
   before a medium-severity issue on an auxiliary sensor. This file provides the
   deterministic business logic that turns technical severity into an actionable
   prioritization score and dispatch schedule.

3. WHICH OTHER FILES USE IT:
   - backend/agent.py: Calls `compute_priority()` in Step 6 and `route_ticket()` in Step 7.
   - backend/pdf_generator.py: Displays the formula breakdown and weights in Page 3 of the PDF report.
   - tests/test_triage.py: Tests priority score bounds and monotonicity.

4. WHAT INPUT IT RECEIVES:
   - Severity level ('low', 'medium', 'high', 'critical')
   - Asset criticality rating (0.0 to 1.0 from runbook)
   - Generation loss risk rating (0.0 to 1.0 from runbook)
   - Safety override flag (True / False from safety guardrails)
   - Duplicate count (integer of repeat recent tickets)

5. WHAT OUTPUT IT PRODUCES:
   - A dictionary with the computed priority score (0.0 to 100.0), the human-readable
     formula text, and an exact component breakdown dictionary.
   - A routing dictionary with assigned team, SLA hours, SLA label, and escalation tier.
===============================================================================
"""

from __future__ import annotations

from typing import Any

# =============================================================================
# WEIGHTS & CONSTANTS
# =============================================================================

# Severity baseline weights: converts ordinal text labels into continuous weights (0.0 - 1.0)
SEVERITY_WEIGHTS: dict[str, float] = {
    "low": 0.25,
    "medium": 0.50,
    "high": 0.75,
    "critical": 1.00,
}

# Operational SLA response windows based on plant severity
SLA_HOURS_BY_SEVERITY: dict[str, int] = {
    "critical": 1,   # 1 Hour: Emergency dispatch for active fire, arc flash, or plant trip
    "high": 4,       # 4 Hours: Same-shift engineering dispatch for impending trips or high heat
    "medium": 24,    # 24 Hours: Next scheduled shift dispatch for telemetry gaps or scheduled PM
    "low": 72,       # 72 Hours: Routine walkdown backlog for minor cosmetic/documentation tags
}

# Human-readable mathematical formula text displayed in API and PDF reports
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
    """
    1. WHAT IT DOES:
       Calculates a deterministic priority score between 0.0 and 100.0 using five
       weighted factors, and returns the individual component score contributions.

    2. WHY WE NEED IT:
       Provides complete transparency to control-room operators and auditors.
       Unlike black-box AI scores, every point in this score can be traced back
       to a specific physical or operational factor.

    3. PARAMETERS:
       - severity (str): 'low', 'medium', 'high', or 'critical' (from ML or safety guardrail).
       - asset_criticality (float): 0.0 to 1.0 representing equipment hierarchy in power train.
       - generation_loss_risk (float): 0.0 to 1.0 representing active MWh loss or curtailment.
       - safety_flag (bool): True if safety hazard detected; False otherwise.
       - duplicate_count (int): Number of matching recent tickets (default: 0).

    4. RETURNS:
       dict: {
           "priority_score": float (rounded to 1 decimal, e.g., 77.8),
           "formula": str (formula string),
           "components": {
               "severity_weight": float,
               "asset_criticality": float,
               "generation_loss_risk": float,
               "safety_flag": int (0 or 1),
               "duplicate_factor": float
           }
       }

    5. HOW IT WORKS INTERNALLY:
       Step 1: Map severity string to baseline weight (low=0.25, med=0.50, high=0.75, crit=1.00).
       Step 2: Clamp asset_criticality and generation_loss_risk to [0.0, 1.0] to prevent overflow.
       Step 3: Convert safety_flag to 1.0 (hazard) or 0.0 (safe).
       Step 4: Scale duplicate_count: min(count, 3) / 3.0 gives 0.0, 0.33, 0.67, or 1.00.
       Step 5: Multiply each factor by its respective weight (45%, 20%, 20%, 10%, 5%).
       Step 6: Sum terms, multiply by 100, and round to 1 decimal place.

       NUMERICAL EXAMPLE:
       - severity = "high" (weight = 0.75) -> 0.45 * 0.75 = 0.3375 (33.75 pts)
       - asset_criticality = 0.85          -> 0.20 * 0.85 = 0.1700 (17.00 pts)
       - generation_loss_risk = 0.85       -> 0.20 * 0.85 = 0.1700 (17.00 pts)
       - safety_flag = True (1.0)          -> 0.10 * 1.00 = 0.1000 (10.00 pts)
       - duplicate_count = 0 (0.0)         -> 0.05 * 0.00 = 0.0000 ( 0.00 pts)
       - Total = 100 * (0.7775) = 77.8 / 100.

    6. CALLED BY:
       - `backend/agent.py::TicketTriageAgent.run()` during Step 6.
       - `tests/test_triage.py` for automated boundary and monotonicity testing.
    """
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
    """
    1. WHAT IT DOES:
       Determines the responsible maintenance team, dispatch SLA window, and
       internal escalation tier based on asset type, severity, and priority score.

    2. WHY WE NEED IT:
       Ensures maintenance tickets are immediately routed to the right specialized team
       (e.g., Solar Electrical vs Wind Mechanical vs Grid High-Voltage) with a legally
       and operationally enforceable deadline.

    3. PARAMETERS:
       - category (str): Fault category (e.g. 'inverter_thermal', 'gearbox_vibration').
       - asset_type (str): Renewable asset family ('solar', 'wind', 'hydro', 'grid').
       - severity (str): Final severity rating ('low', 'medium', 'high', 'critical').
       - priority_score (float): Calculated 0–100 priority score.
       - runbook_owner (str | None): Specific team defined in data/runbook.json (if matched).

    4. RETURNS:
       dict: {
           "owner_team": str (e.g. "Solar O&M Electrical Team"),
           "sla_hours": int (1, 4, 24, or 72),
           "sla_label": str (e.g. "Respond within 4 hours"),
           "escalation_tier": str (e.g. "Tier-2 Same-Shift Engineering")
       }

    5. HOW IT WORKS INTERNALLY:
       Step 1: Looks up SLA hours from SLA_HOURS_BY_SEVERITY mapping.
       Step 2: Uses the runbook_owner if available, otherwise generates a fallback
               team name from asset_type (e.g., "Solar O&M Operations Team").
       Step 3: Assigns an escalation tier based on severity and priority threshold:
               - Critical or Priority >= 85: Tier-1 Immediate Dispatch (1 Hour)
               - High or Priority >= 65: Tier-2 Same-Shift Engineering (4 Hours)
               - Medium: Tier-3 Scheduled Maintenance (24 Hours)
               - Low: Tier-4 Routine Backlog (72 Hours)

    6. CALLED BY:
       - `backend/agent.py::TicketTriageAgent.run()` during Step 7.
    """
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
