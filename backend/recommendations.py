"""
Recommendations module mapping ticket categories to domain-specific
probable root causes and recommended next maintenance actions.

Maps all 6 categories present in the original dataset:
1. inverter_thermal
2. gearbox_vibration
3. inspection_compliance
4. data_gap
5. pitch_system
6. grid_curtailment
"""

from __future__ import annotations

RECOMMENDATIONS_CATALOG: dict[str, dict[str, str]] = {
    "inverter_thermal": {
        "probable_root_cause": (
            "Clogged air intake filters, cooling blower fan failure, or degraded thermal paste on IGBT modules."
        ),
        "recommended_next_action": (
            "Inspect cabinet air filters, verify cooling fan rotation, and perform an infrared thermal scan on power terminals."
        ),
    },
    "gearbox_vibration": {
        "probable_root_cause": (
            "High-speed shaft bearing spalling, gear tooth wear, or drive train coupling misalignment."
        ),
        "recommended_next_action": (
            "Review CMS vibration spectrum in SCADA, inspect magnetic chip detector, and collect oil sample for ferrography."
        ),
    },
    "inspection_compliance": {
        "probable_root_cause": (
            "Statutory inspection window overdue, incomplete regulatory checklist, or pending safety sign-off."
        ),
        "recommended_next_action": (
            "Dispatch certified compliance technician to complete physical checklist, inspect safety mechanisms, and file formal audit log."
        ),
    },
    "data_gap": {
        "probable_root_cause": (
            "Communication gateway timeout, RTU power supply interruption, severed serial/fiber cable, or historian service freeze."
        ),
        "recommended_next_action": (
            "Ping RTU gateway, verify 24V DC auxiliary power supply, and restart SCADA historian polling service."
        ),
    },
    "pitch_system": {
        "probable_root_cause": (
            "Hydraulic proportional valve sticking, pitch drive motor thermal overload, or backup capacitor bank fault."
        ),
        "recommended_next_action": (
            "Execute automated pitch calibration routine, inspect hydraulic cylinder seals for leaks, and verify emergency feathering speed."
        ),
    },
    "grid_curtailment": {
        "probable_root_cause": (
            "SLDC/LDC curtailment dispatch instruction not ingested by Power Plant Controller (PPC), or SCADA telemetry mismatch."
        ),
        "recommended_next_action": (
            "Verify active power setpoint with SLDC grid dispatcher and cross-reference PPC controller limits with substation meters."
        ),
    },
}

DEFAULT_RECOMMENDATION: dict[str, str] = {
    "probable_root_cause": "Unspecified operational anomaly or sensor deviation.",
    "recommended_next_action": "Conduct visual inspection of equipment and cross-reference SCADA diagnostic alarm logs.",
}


def get_recommendations(category: str) -> dict[str, str]:
    """
    Retrieves probable root cause and recommended next action for a given category.

    Args:
        category: Predicted maintenance fault category string.

    Returns:
        Dictionary with 'probable_cause' and 'recommended_action'.
    """
    key = category.strip().lower()
    raw = RECOMMENDATIONS_CATALOG.get(key, DEFAULT_RECOMMENDATION)
    return {
        "probable_cause": raw.get("probable_root_cause", ""),
        "recommended_action": raw.get("recommended_next_action", ""),
        "probable_root_cause": raw.get("probable_root_cause", ""),
        "recommended_next_action": raw.get("recommended_next_action", ""),
    }


# Convenient alias
get_recommendation = get_recommendations
