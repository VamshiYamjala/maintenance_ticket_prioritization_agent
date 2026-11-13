"""
Pydantic request/response schemas for the Maintenance Ticket Prioritization API.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

AssetType = Literal["solar", "wind", "hydro", "grid"]


class TriageRequest(BaseModel):
    ticket_id: str | None = Field(default=None, max_length=40)
    asset_type: AssetType = Field(..., description="One of: solar, wind, hydro, grid")
    description: str = Field(..., min_length=5, max_length=2000, description="Free-text maintenance ticket")

    @field_validator("description")
    @classmethod
    def check_not_blank(cls, v: str) -> str:
        if not v or len(v.strip()) < 5:
            raise ValueError("description must contain at least 5 non-whitespace characters")
        return v.strip()


class LegacyRunQuery(BaseModel):
    """Backward-compatible schema for starter POST /api/run."""

    text: str = Field(default="", max_length=2000)
    description: str | None = Field(default=None, max_length=2000)
    asset_type: AssetType = Field(default="solar")
    ticket_id: str | None = Field(default=None, max_length=40)

    def resolved_description(self) -> str:
        val = (self.description if self.description is not None else self.text).strip()
        if len(val) < 5:
            raise ValueError("Ticket text must contain at least 5 non-whitespace characters")
        return val


class BatchTriageRequest(BaseModel):
    tickets: list[TriageRequest] = Field(..., min_length=1, max_length=100)
