"""
===============================================================================
FILE: backend/schemas.py
===============================================================================
1. WHAT THIS FILE DOES:
   Defines the Pydantic data validation models and type definitions for incoming
   API requests (single-ticket triage, legacy run query, and batch list requests).

2. WHY THIS FILE IS NEEDED:
   FastAPI uses Pydantic to automatically inspect, parse, sanitize, and validate
   incoming HTTP JSON payloads. If a user sends invalid asset types or blanks,
   Pydantic rejects the request with HTTP 422 Unprocessable Entity before it can
   reach internal business logic, protecting the server from malformed data and crashes.

3. WHICH OTHER FILES USE IT:
   - backend/app.py: Uses `TriageRequest`, `LegacyRunQuery`, and `BatchTriageRequest`
     in route signatures.
   - tests/test_triage.py: Tests validation error handling with empty and overlong inputs.

4. WHAT INPUT IT RECEIVES:
   - Raw JSON dictionaries from incoming HTTP POST requests.

5. WHAT OUTPUT IT PRODUCES:
   - Validated Python Pydantic model instances with verified types and attributes.
===============================================================================
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Strict literal type restricting asset input to the 4 supported plant sectors
AssetType = Literal["solar", "wind", "hydro", "grid"]


class TriageRequest(BaseModel):
    """
    Primary request schema for POST /api/triage.

    Fields:
    - ticket_id: Optional string identifier (e.g. "TKT-1049"). Max 40 characters.
    - asset_type: One of 'solar', 'wind', 'hydro', or 'grid'.
    - description: Free-text observation. Must contain between 5 and 2000 characters.

    Validation:
    - `check_not_blank`: Ensures the string is not just whitespace.
    """
    ticket_id: str | None = Field(default=None, max_length=40, description="Optional ticket ID")
    asset_type: AssetType = Field(..., description="One of: solar, wind, hydro, grid")
    description: str = Field(..., min_length=5, max_length=2000, description="Free-text maintenance ticket")

    @field_validator("description")
    @classmethod
    def check_not_blank(cls, v: str) -> str:
        """Reject empty or whitespace-only descriptions."""
        if not v or len(v.strip()) < 5:
            raise ValueError("description must contain at least 5 non-whitespace characters")
        return v.strip()


class LegacyRunQuery(BaseModel):
    """
    Backward-compatible schema for the starter project endpoint POST /api/run.
    Supports either `description` or `text` field.
    """
    text: str = Field(default="", max_length=2000)
    description: str | None = Field(default=None, max_length=2000)
    asset_type: AssetType = Field(default="solar")
    ticket_id: str | None = Field(default=None, max_length=40)

    def resolved_description(self) -> str:
        """Extract whichever field was populated by the client and validate."""
        val = (self.description if self.description is not None else self.text).strip()
        if len(val) < 5:
            raise ValueError("Ticket text must contain at least 5 non-whitespace characters")
        return val


class BatchTriageRequest(BaseModel):
    """
    Request schema for bulk JSON triage POST /api/batch.
    Enforces a list of at least 1 and at most 100 tickets per request to prevent server overload.
    """
    tickets: list[TriageRequest] = Field(..., min_length=1, max_length=100)
