"""
Unit and integration tests for the AI-Generated Maintenance Ticket PDF Report feature.
"""

from __future__ import annotations

import re
from fastapi.testclient import TestClient

from backend.agent import TicketTriageAgent
from backend.app import app
from backend.pdf_generator import generate_maintenance_report_pdf, generate_report_id


client = TestClient(app)


def count_pdf_pages(pdf_bytes: bytes) -> int:
    """Helper to count /Page dictionary objects in the generated PDF."""
    return len(re.findall(rb"/Type\s*/Page\b", pdf_bytes))


def test_report_id_format():
    rep_id = generate_report_id()
    assert rep_id.startswith("GKO-RPT-")
    assert len(rep_id) >= 18


def test_pdf_solar_inverter_case():
    agent = TicketTriageAgent.from_disk()
    res = agent.run(
        description="Inverter 4 tripping repeatedly after noon, high temperature alarm visible at Block 2",
        asset_type="solar",
        ticket_id="TEST-SOLAR-01",
    )
    pdf_bytes = generate_maintenance_report_pdf(res)
    assert len(pdf_bytes) > 5000
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes
    assert count_pdf_pages(pdf_bytes) == 5


def test_pdf_wind_gearbox_case():
    agent = TicketTriageAgent.from_disk()
    res = agent.run(
        description="WTG-12 gearbox vibration spike with loud grinding noise and metallic debris suspected",
        asset_type="wind",
        ticket_id="TEST-WIND-02",
    )
    pdf_bytes = generate_maintenance_report_pdf(res)
    assert len(pdf_bytes) > 5000
    assert count_pdf_pages(pdf_bytes) == 5


def test_pdf_grid_arc_flash_case():
    agent = TicketTriageAgent.from_disk()
    res = agent.run(
        description="Arc flash sparks observed inside 33kV switchgear bay 1 during switching; area evacuated",
        asset_type="grid",
        ticket_id="TEST-GRID-03",
    )
    assert res["severity"] == "critical"

    pdf_bytes = generate_maintenance_report_pdf(res)
    assert len(pdf_bytes) > 5000
    assert count_pdf_pages(pdf_bytes) == 5


def test_pdf_human_review_ticket():
    agent = TicketTriageAgent.from_disk()
    # Ambiguous short description that may trigger low confidence or review
    res = agent.run(
        description="strange sound noticed somewhere in the plant area yesterday morning",
        asset_type="hydro",
        ticket_id="TEST-REVIEW-04",
    )
    pdf_bytes = generate_maintenance_report_pdf(res)
    assert len(pdf_bytes) > 5000
    assert count_pdf_pages(pdf_bytes) == 5


def test_pdf_missing_optional_fields():
    # Bare minimal dictionary with missing optional fields
    sparse_data = {
        "ticket_id": "SPARSE-05",
        "asset_type": "solar",
        "category": "inverter_thermal",
        "severity": "medium",
        "priority_score": 55.0,
    }
    pdf_bytes = generate_maintenance_report_pdf(sparse_data)
    assert len(pdf_bytes) > 3000
    assert count_pdf_pages(pdf_bytes) == 5


def test_pdf_special_characters_escaping():
    # Ticket containing XML special chars: <, >, &, ", '
    sparse_data = {
        "ticket_id": "SPEC-CHAR & <TAG> 'QUOTES'",
        "asset_type": "wind",
        "category": "gearbox_mechanical & electrical",
        "severity": "high",
        "priority_score": 80.5,
        "description": "Alarm <ALM-99> & temp > 85°C with 'grinding' & \"sparking\" sounds",
    }
    pdf_bytes = generate_maintenance_report_pdf(sparse_data)
    assert len(pdf_bytes) > 3000
    assert count_pdf_pages(pdf_bytes) == 5


def test_fastapi_pdf_endpoint_success():
    triage_payload = {
        "ticket_id": "API-TKT-9001",
        "asset_type": "solar",
        "description": "Inverter 4 tripping repeatedly after noon, high temperature alarm visible at Block 2",
    }
    triage_resp = client.post("/api/triage", json=triage_payload)
    assert triage_resp.status_code == 200
    triage_data = triage_resp.json()

    # Call PDF endpoint
    pdf_resp = client.post("/api/reports/ticket-pdf", json=triage_data)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in pdf_resp.headers["content-disposition"]
    assert "Maintenance_Report_API-TKT-9001_" in pdf_resp.headers["content-disposition"]
    assert pdf_resp.content.startswith(b"%PDF-")
    assert count_pdf_pages(pdf_resp.content) == 5


def test_fastapi_pdf_endpoint_validation_error():
    # Empty payload should return 400
    resp = client.post("/api/reports/ticket-pdf", json={})
    assert resp.status_code == 400
