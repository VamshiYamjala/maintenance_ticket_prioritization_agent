"""
Routing module assigning the appropriate maintenance engineering team
based on the predicted ticket category.

Covers the 6 categories in the original dataset:
- inverter_thermal      -> Solar Maintenance Team
- gearbox_vibration     -> Wind Turbine Maintenance Team
- inspection_compliance -> Compliance Team
- data_gap              -> SCADA Team
- pitch_system          -> Wind Turbine Maintenance Team
- grid_curtailment      -> Grid Operations Team

Note: These represent organizational responsibility routing recommendations,
not real-time external physical technician dispatches.
"""

from __future__ import annotations

CATEGORY_TO_TEAM_MAP: dict[str, str] = {
    "inverter_thermal": "Solar Maintenance Team",
    "gearbox_vibration": "Wind Turbine Maintenance Team",
    "inspection_compliance": "Compliance Team",
    "data_gap": "SCADA Team",
    "pitch_system": "Wind Turbine Maintenance Team",
    "grid_curtailment": "Grid Operations Team",
}

DEFAULT_TEAM = "General O&M Operations Team"


def get_assigned_team(category: str) -> str:
    """
    Returns the designated maintenance team for a predicted fault category.

    Args:
        category: Predicted fault category string.

    Returns:
        Name of the responsible maintenance team.
    """
    key = category.strip().lower()
    return CATEGORY_TO_TEAM_MAP.get(key, DEFAULT_TEAM)


# Convenient alias
get_routing = get_assigned_team
