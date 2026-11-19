"""
===============================================================================
FILE: backend/schemas.py
===============================================================================
1. WHAT THIS FILE DOES:
   Defines Pydantic data models for validating incoming ticket requests and
   formatting API responses.

2. WHY THIS FILE IS NEEDED:
   Ensures incoming request payloads have required fields, validates input
   cleanliness, and provides clean API documentation and contracts.
===============================================================================
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, model_validator


class TicketQuery(BaseModel):
    """
    Request model for ticket triage.
    Supports both:
      - Assignment standard: `{"text": "high bearing temp..."}`
      - Detailed format: `{"description": "...", "asset_type": "wind_turbine", "ticket_id": "T001"}`
    """
    text: str = Field(default="", description="Ticket problem text")
    description: str = Field(default="", description="Alternative field for ticket problem text")
    asset_type: str = Field(default="", description="Optional asset type (e.g. wind_turbine, solar_inverter)")
    ticket_id: str | None = Field(default=None, description="Optional ticket tracking ID")

    @model_validator(mode="after")
    def resolve_text(self) -> TicketQuery:
        """Ensure either `text` or `description` is provided and non-empty."""
        primary = self.text.strip() or self.description.strip()
        if not primary or len(primary) < 3:
            raise ValueError("Ticket text/description must contain at least 3 characters.")
        self.text = primary
        self.description = primary
        return self


class TriageResponse(BaseModel):
    """Structured response model returned by the triage API."""
    ticket_id: str | None = None
    category: str
    severity: str
    initial_severity: str
    escalated: bool
    safety_trigger: str | None = None
    confidence: float
    probable_cause: str
    recommended_action: str
    assigned_team: str
    processed_text: str
