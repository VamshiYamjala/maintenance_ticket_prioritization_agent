"""
Unit and API integration tests for the Maintenance Ticket Prioritization Agent.
Run with: pytest -q
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.agent import TicketTriageAgent
from backend.app import app
from backend.priority import compute_priority


def test_priority_formula_monotonic_and_bounded():
    low_p = compute_priority("low", 0.5, 0.3, safety_flag=False, duplicate_count=0)
    crit_p = compute_priority("critical", 0.95, 0.90, safety_flag=True, duplicate_count=2)
    assert 0.0 <= low_p["priority_score"] <= 100.0
    assert 0.0 <= crit_p["priority_score"] <= 100.0
    assert crit_p["priority_score"] > low_p["priority_score"]


def test_guardrail_escalates_only_never_downgrades():
    agent = TicketTriageAgent.from_disk()
    # Even if ML predicts 'low', smoke/arc flash must escalate to 'critical'
    esc = agent.safety_guardrail("Smoke and arc flash sparks in combiner box", ml_severity="low")
    assert esc["final_severity"] == "critical"
    assert esc["escalated"] is True

    # If ML already predicted 'critical', an 'oil leak' (min high) must NOT downgrade it
    no_down = agent.safety_guardrail("Minor oil leak observed", ml_severity="critical")
    assert no_down["final_severity"] == "critical"
    assert no_down["escalated"] is False

    # Negated hazard must not trigger escalation
    neg = agent.safety_guardrail("Routine check; no smoke and no alarm present", ml_severity="low")
    assert neg["final_severity"] == "low"
    assert neg["escalated"] is False


def test_llm_fallback_when_key_missing(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    agent = TicketTriageAgent.from_disk()
    res = agent.run("Inverter 4 tripping repeatedly after noon", "solar")
    assert res["explanation_source"] == "template"
    assert len(res["explanation"]) > 20


def test_api_validation_and_demo_tickets():
    with TestClient(app) as client:
        h = client.get("/api/health")
        assert h.status_code == 200
        assert h.json()["status"] == "ok"

        # Empty / short description -> 422
        bad_empty = client.post("/api/triage", json={"asset_type": "solar", "description": "  "})
        assert bad_empty.status_code == 422

        # Unknown asset_type -> 422
        bad_asset = client.post("/api/triage", json={"asset_type": "nuclear", "description": "Turbine fault"})
        assert bad_asset.status_code == 422

        # Overlong description -> 422
        bad_long = client.post("/api/triage", json={"asset_type": "solar", "description": "x" * 2005})
        assert bad_long.status_code == 422

        # Three golden demo tickets
        d1 = client.post("/api/triage", json={
            "ticket_id": "DEMO-01",
            "asset_type": "solar",
            "description": "Inverter 4 tripping repeatedly after noon, high temperature alarm visible at Block 2",
        })
        assert d1.status_code == 200
        j1 = d1.json()
        assert j1["category"] == "inverter_thermal"
        assert j1["severity"] in ("high", "critical")
        assert len(j1["agent_trace"]) == 9

        d2 = client.post("/api/triage", json={
            "ticket_id": "DEMO-02",
            "asset_type": "wind",
            "description": "WTG-12 gearbox vibration spike with loud grinding noise and metallic debris suspected",
        })
        assert d2.status_code == 200
        j2 = d2.json()
        assert j2["category"] == "gearbox_vibration"
        assert j2["severity"] == "critical"

        d3 = client.post("/api/triage", json={
            "ticket_id": "DEMO-03",
            "asset_type": "grid",
            "description": "Arc flash sparks observed inside 33kV switchgear bay 1 during switching; area evacuated",
        })
        assert d3.status_code == 200
        j3 = d3.json()
        assert j3["category"] == "safety_incident"
        assert j3["severity"] == "critical"


def test_batch_csv_missing_columns():
    with TestClient(app) as client:
        resp = client.post(
            "/api/batch-csv",
            files={"file": ("bad.csv", b"ticket_id,notes\n1,hello\n", "text/csv")},
        )
        assert resp.status_code == 400
        assert "missing required columns" in resp.json()["detail"].lower()
