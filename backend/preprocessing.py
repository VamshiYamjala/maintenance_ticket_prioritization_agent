"""
Text normalization, equipment/site entity extraction, and dataset loading/deduplication
for renewable-energy O&M maintenance tickets.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

ALLOWED_ASSET_TYPES = ("solar", "wind", "hydro", "grid")
SEVERITY_LEVELS = ("low", "medium", "high", "critical")
SEVERITY_TO_INT = {"low": 0, "medium": 1, "high": 2, "critical": 3}
INT_TO_SEVERITY = {v: k for k, v in SEVERITY_TO_INT.items()}

# Regex patterns for renewable O&M equipment IDs and site/location hints
EQUIPMENT_PATTERNS = [
    r"\bWTG[-_\s]?\d+\b",
    r"\b(?:Central|String)?\s*Inverter[-_\s]?\d+\b",
    r"\bINV[-_\s]?\d+\b",
    r"\b(?:Power|Step-up|Main)?\s*Transformer\s*(?:TX|IDT)?[-_\s]?\d*\b",
    r"\b(?:TX|IDT|RTU|PLC|NCU|PSS|PPC)[-_\s]?\d+\b",
    r"\bSpillway\s+Gate[-_\s]?\d+\b",
    r"\bIntake\s+Valve[-_\s]?\d+\b",
    r"\bCombiner\s+Box[-_\s]?\d+\b",
    r"\bTracker\s+Row[-_\s]?\d+\b",
    r"\bTurbine[-_\s]?\d+\b",
    r"\bSwitchgear\s+(?:Panel|Bay)[-_\s]?\d+\b",
]

SITE_PATTERNS = [
    r"\bBlock[-_\s]?\d+\b",
    r"\bICR[-_\s]?\d+\b",
    r"\bFeeder(?:\s+Bay)?[-_\s]?\d+\b",
    r"\bSubstation[-_\s]?\d+\b",
    r"\bSite[-_\s]?\d+\b",
    r"\bRidge[-_\s]?\d+\b",
    r"\bSector[-_\s]?\d+\b",
    r"\b\d+(?:/\d+)?\s*kV\b",
]

NOISE_PREFIX_RE = re.compile(r"^(?:urgent:|shift note\s*-|scada alert:|field report:)\s*", re.IGNORECASE)
NOISE_SUFFIX_RE = re.compile(r"\s*(?:\[auto-ticket\]|--\s*logged by operator)\s*$", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Lowercase, strip boilerplate prefixes/suffixes, and normalize whitespace."""
    cleaned = text.strip()
    cleaned = NOISE_PREFIX_RE.sub("", cleaned)
    cleaned = NOISE_SUFFIX_RE.sub("", cleaned)
    cleaned = cleaned.lower()
    # Keep alphanumeric, hyphens, slashes, and spaces so IDs like wtg-12 or 33/220kv stay intact
    cleaned = re.sub(r"[^a-z0-9\s\-/]", " ", cleaned)
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def extract_entities(text: str) -> dict[str, Any]:
    """Extract equipment IDs and site/location hints from raw ticket text."""
    equipment_ids: list[str] = []
    for pat in EQUIPMENT_PATTERNS:
        for match in re.findall(pat, text, flags=re.IGNORECASE):
            val = WHITESPACE_RE.sub(" ", match).strip()
            if val and val.lower() not in {e.lower() for e in equipment_ids}:
                equipment_ids.append(val)

    site_hints: list[str] = []
    for pat in SITE_PATTERNS:
        for match in re.findall(pat, text, flags=re.IGNORECASE):
            val = WHITESPACE_RE.sub(" ", match).strip()
            if val and val.lower() not in {s.lower() for s in site_hints}:
                site_hints.append(val)

    return {
        "clean_text": normalize_text(text),
        "equipment_ids": equipment_ids,
        "site_hints": site_hints,
    }


def load_tickets(
    bundled_path: Path,
    synthetic_path: Path | None = None,
    include_synthetic: bool = True,
) -> pd.DataFrame:
    """
    Load bundled tickets (untouched) and optionally synthetic tickets,
    clean text, and de-duplicate near-identical descriptions to prevent leakage.
    """
    frames: list[pd.DataFrame] = []

    bundled_df = pd.read_csv(bundled_path, comment="#")
    bundled_df["data_source"] = "bundled"
    frames.append(bundled_df)

    if include_synthetic and synthetic_path is not None and synthetic_path.exists():
        syn_df = pd.read_csv(synthetic_path, comment="#")
        if "data_source" not in syn_df.columns:
            syn_df["data_source"] = "synthetic"
        frames.append(syn_df)

    df = pd.concat(frames, ignore_index=True)
    df["asset_type"] = df["asset_type"].astype(str).str.strip().str.lower()
    df["target_severity"] = df["target_severity"].astype(str).str.strip().str.lower()
    df["target_category"] = df["target_category"].astype(str).str.strip().str.lower()
    df["clean_text"] = df["description"].astype(str).apply(normalize_text)

    # De-duplicate on (asset_type, clean_text) keeping bundled rows first
    df = df.drop_duplicates(subset=["asset_type", "clean_text"], keep="first").reset_index(drop=True)
    return df
