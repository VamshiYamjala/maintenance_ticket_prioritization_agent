"""
===============================================================================
FILE: backend/triage.py
===============================================================================
1. WHAT THIS FILE DOES:
   Central orchestration workflow for maintenance ticket triage. It coordinates
   the full pipeline in order:
     1. Text preprocessing (cleaning & asset type integration)
     2. ML classification (TF-IDF + KNN category & baseline severity prediction)
     3. Deterministic safety evaluation (critical escalation rules)
     4. Engineering recommendations (root cause & action items)
     5. Departmental routing (team assignment)

2. WHY THIS FILE IS NEEDED:
   Keeps the FastAPI endpoints lightweight and separates business logic from
   web transport protocols. All components can be tested and explained cleanly.

3. WHICH OTHER FILES USE IT:
   - backend/app.py: Calls `triage_ticket()` when handling triage requests.
===============================================================================
"""

from __future__ import annotations

from typing import Any

from backend.classifier import TicketClassifier
from backend.preprocessing import prepare_input
from backend.recommendations import get_recommendation
from backend.routing import get_routing
from backend.severity import evaluate_severity

# Singleton classifier instance fitted in memory
_classifier: TicketClassifier | None = None


def get_classifier() -> TicketClassifier:
    """Return the singleton TicketClassifier instance, initializing if needed."""
    global _classifier
    if _classifier is None:
        _classifier = TicketClassifier()
    return _classifier


def triage_ticket(description: str, asset_type: str = "") -> dict[str, Any]:
    """
    Run the end-to-end triage process on an incoming ticket.

    Args:
        description: Free-form problem description.
        asset_type: Optional asset type (e.g. 'wind_turbine', 'solar_inverter').

    Returns:
        Structured dictionary containing category, severity, safety notes,
        recommendations, and team routing.
    """
    # Step 1: Preprocessing & input preparation
    combined_text = prepare_input(description, asset_type)

    # Step 2: ML classification via TF-IDF + KNN (cosine similarity)
    classifier = get_classifier()
    ml_result = classifier.predict(combined_text)
    category = ml_result["predicted_category"]
    base_severity = ml_result["predicted_severity"]
    confidence = ml_result["confidence"]

    # Step 3: Safety rule evaluation (escalates severity if safety hazards are detected)
    safety_result = evaluate_severity(combined_text, base_severity)
    final_severity = safety_result["final_severity"]
    escalated = safety_result["escalated"]
    safety_trigger = safety_result["safety_trigger"]

    # Step 4: Engineering recommendations lookup
    rec = get_recommendation(category)

    # Step 5: Departmental routing lookup
    team = get_routing(category)

    return {
        "category": category,
        "severity": final_severity,
        "initial_severity": base_severity,
        "escalated": escalated,
        "safety_trigger": safety_trigger,
        "confidence": confidence,
        "probable_cause": rec["probable_cause"],
        "recommended_action": rec["recommended_action"],
        "assigned_team": team,
        "processed_text": combined_text,
    }
