"""
Preprocessing module for maintenance ticket text.

Responsible for:
- Converting text to lowercase
- Stripping leading and trailing whitespace
- Normalizing multiple spaces
- Optionally prepending asset type for context
- Retaining technical alphanumeric tokens, equipment IDs, and hazard negations
"""

from __future__ import annotations

import re

# Regex pattern to collapse consecutive whitespace into a single space
WHITESPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """
    Cleans and normalizes raw maintenance ticket description text.

    Args:
        text: Raw description string submitted by operator or technician.

    Returns:
        Cleaned, lowercased string with standardized whitespace.
    """
    if not text:
        return ""

    # Convert to lowercase for consistent case-insensitive matching
    cleaned = text.strip().lower()

    # Collapse multiple spaces, newlines, and tabs into a single space
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()

    return cleaned


def prepare_input(description: str, asset_type: str | None = None) -> str:
    """
    Prepares input text for the TF-IDF vectorizer by combining asset type
    and description where available.

    Args:
        description: The maintenance ticket observation text.
        asset_type: Optional asset type ('solar', 'wind', 'hydro', 'grid').

    Returns:
        Combined normalized string (e.g. 'solar inverter 4 tripping repeatedly').
    """
    desc_cleaned = clean_text(description)

    if asset_type and asset_type.strip():
        asset_cleaned = clean_text(asset_type)
        return f"{asset_cleaned} {desc_cleaned}".strip()

    return desc_cleaned
