"""
===============================================================================
FILE: backend/preprocessing.py
===============================================================================
1. WHAT THIS FILE DOES:
   Handles all text normalization, regular expression entity extraction (equipment IDs
   and site/location hints), ordinal severity label encodings, and dataset loading/deduplication
   for renewable-energy maintenance tickets.

2. WHY THIS FILE IS NEEDED:
   Plant operators write tickets in varied formats with noisy prefixes ("SCADA Alert:",
   "urgent:"), casing inconsistencies, and irregular whitespace. This module standardizes
   free-text descriptions so the machine learning model can extract clean n-grams while
   retaining vital technical codes like 'WTG-12' and '33kV'. It also prevents data leakage
   during model evaluation by deduplicating training data.

3. WHICH OTHER FILES USE IT:
   - backend/agent.py: Uses `extract_entities()` in Step 1 and `normalize_text()`.
   - backend/train.py: Uses `load_tickets()` to ingest and clean training CSV files.
   - backend/evaluate.py: Uses `load_tickets()`, `SEVERITY_LEVELS`, and `SEVERITY_TO_INT`.
   - backend/app.py: Uses `ALLOWED_ASSET_TYPES` to validate user requests.

4. WHAT INPUT IT RECEIVES:
   - Raw ticket strings from API requests or CSV rows.
   - File paths to `data/maintenance_tickets.csv` and `data/maintenance_tickets_synthetic.csv`.

5. WHAT OUTPUT IT PRODUCES:
   - Cleaned, normalized text strings.
   - Extracted entity lists: `equipment_ids` and `site_hints`.
   - Deduplicated Pandas DataFrame for model training and cross-validation.
===============================================================================
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

# Supported renewable energy sectors
ALLOWED_ASSET_TYPES = ("solar", "wind", "hydro", "grid")

# Ordinal severity levels and mapping dictionaries
SEVERITY_LEVELS = ("low", "medium", "high", "critical")
SEVERITY_TO_INT = {"low": 0, "medium": 1, "high": 2, "critical": 3}
INT_TO_SEVERITY = {v: k for k, v in SEVERITY_TO_INT.items()}

# =============================================================================
# REGEX PATTERNS FOR TECHNICAL ENTITY EXTRACTION
# =============================================================================

# Regex patterns matching renewable equipment tags (Wind Turbines, Inverters, Transformers, etc.)
EQUIPMENT_PATTERNS = [
    r"\bWTG[-_\s]?\d+\b",                                                # e.g. WTG-12, WTG 04
    r"\b(?:Central|String)?\s*Inverter[-_\s]?\d+\b",                     # e.g. Inverter 4, Central Inverter 02
    r"\bINV[-_\s]?\d+\b",                                                # e.g. INV-03
    r"\b(?:Power|Step-up|Main)?\s*Transformer\s*(?:TX|IDT)?[-_\s]?\d*\b", # e.g. Main Transformer TX-01
    r"\b(?:TX|IDT|RTU|PLC|NCU|PSS|PPC)[-_\s]?\d+\b",                     # e.g. RTU-02, PLC-01, NCU-5
    r"\bSpillway\s+Gate[-_\s]?\d+\b",                                    # e.g. Spillway Gate 2
    r"\bIntake\s+Valve[-_\s]?\d+\b",                                     # e.g. Intake Valve 1
    r"\bCombiner\s+Box[-_\s]?\d+\b",                                     # e.g. Combiner Box 14
    r"\bTracker\s+Row[-_\s]?\d+\b",                                      # e.g. Tracker Row 10
    r"\bTurbine[-_\s]?\d+\b",                                            # e.g. Turbine 3
    r"\bSwitchgear\s+(?:Panel|Bay)[-_\s]?\d+\b",                         # e.g. Switchgear Bay 1
]

# Regex patterns matching physical site locations, bays, and voltage ratings
SITE_PATTERNS = [
    r"\bBlock[-_\s]?\d+\b",            # e.g. Block 2, Block-04
    r"\bICR[-_\s]?\d+\b",              # Inverter Control Room: e.g. ICR-02
    r"\bFeeder(?:\s+Bay)?[-_\s]?\d+\b",# e.g. Feeder 3, Feeder Bay 1
    r"\bSubstation[-_\s]?\d+\b",        # e.g. Substation 2
    r"\bSite[-_\s]?\d+\b",              # e.g. Site 1
    r"\bRidge[-_\s]?\d+\b",             # Wind farm ridge: e.g. Ridge 4
    r"\bSector[-_\s]?\d+\b",            # e.g. Sector 2
    r"\b\d+(?:/\d+)?\s*kV\b",           # Voltage rating: e.g. 33kV, 33/220kV, 400 kV
]

# Noise stripping patterns: removes common automated logging prefixes and suffixes
NOISE_PREFIX_RE = re.compile(r"^(?:urgent:|shift note\s*-|scada alert:|field report:)\s*", re.IGNORECASE)
NOISE_SUFFIX_RE = re.compile(r"\s*(?:\[auto-ticket\]|--\s*logged by operator)\s*$", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    r"""
    1. WHAT IT DOES:
       Cleans raw text by stripping logging prefixes/suffixes, converting to lowercase,
       removing unneeded special characters, and collapsing whitespace.

    2. WHY WE NEED IT:
       Ensures that the TF-IDF feature extractor sees standardized words. For example:
       "SCADA Alert: Inverter 4 Tripping!!" and "inverter 4 tripping" become identical.

    3. PARAMETERS:
       - text (str): Raw ticket description string.

    4. RETURNS:
       str: Cleaned, normalized lowercase string.

    5. HOW IT WORKS INTERNALLY:
       Step 1: Strip outer whitespace.
       Step 2: Remove noise prefixes (e.g. "urgent:", "scada alert:") using regex.
       Step 3: Remove noise suffixes (e.g. "[auto-ticket]") using regex.
       Step 4: Convert entire string to lowercase.
       Step 5: Retain alphanumeric characters, hyphens, and slashes [a-z0-9\s\-/],
               replacing punctuation like commas and exclamation marks with spaces.
               (Retaining '-' and '/' is vital so technical tags like 'wtg-12' and '33/220kv' survive).
       Step 6: Collapse consecutive whitespace into single spaces and strip edges.

    6. CALLED BY:
       - `extract_entities()` during Step 1 of agent triage.
       - `load_tickets()` during dataset ingestion.
    """
    cleaned = text.strip()
    cleaned = NOISE_PREFIX_RE.sub("", cleaned)
    cleaned = NOISE_SUFFIX_RE.sub("", cleaned)
    cleaned = cleaned.lower()
    # Keep alphanumeric, hyphens, slashes, and spaces so IDs like wtg-12 or 33/220kv stay intact
    cleaned = re.sub(r"[^a-z0-9\s\-/]", " ", cleaned)
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def extract_entities(text: str) -> dict[str, Any]:
    """
    1. WHAT IT DOES:
       Extracts specific equipment identifiers and geographic site/bay location hints
       from free-text descriptions using domain-specific regex patterns.

    2. WHY WE NEED IT:
       Enables the system to identify the exact physical asset in question (e.g. 'Inverter 4',
       'Block 2') for work-order dispatch without requiring strict drop-down form fields.

    3. PARAMETERS:
       - text (str): Raw input ticket description.

    4. RETURNS:
       dict: {
           "clean_text": str (normalized description),
           "equipment_ids": list[str] (e.g. ["Inverter 4"]),
           "site_hints": list[str] (e.g. ["Block 2"])
       }

    5. HOW IT WORKS INTERNALLY:
       Step 1: Iterates through `EQUIPMENT_PATTERNS`, running case-insensitive regex search.
               Deduplicates matched strings in a case-insensitive manner.
       Step 2: Iterates through `SITE_PATTERNS` to extract plant blocks, feeder bays, or voltage ratings.
       Step 3: Normalizes the raw text using `normalize_text()`.
       Step 4: Returns the composite dictionary.

    6. CALLED BY:
       - `backend/agent.py::TicketTriageAgent.normalize_and_extract()` (Tool Step 1).
    """
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
    1. WHAT IT DOES:
       Loads the bundled seed dataset and synthetic dataset, standardizes labels,
       applies text cleaning, and performs deduplication.

    2. WHY WE NEED IT:
       Creates the clean training dataset of 426 deduplicated tickets. Deduplicating on
       (asset_type, clean_text) is critical to prevent identical descriptions from appearing
       in both train and validation folds (preventing synthetic data leakage).

    3. PARAMETERS:
       - bundled_path (Path): Path to `data/maintenance_tickets.csv` (6 seed rows).
       - synthetic_path (Path | None): Path to `data/maintenance_tickets_synthetic.csv`.
       - include_synthetic (bool): Whether to merge synthetic rows (default: True).

    4. RETURNS:
       pd.DataFrame: Merged, cleaned, deduplicated DataFrame with columns:
                     ['ticket_id', 'asset_type', 'description', 'target_severity',
                      'target_category', 'data_source', 'clean_text'].

    5. HOW IT WORKS INTERNALLY:
       Step 1: Read bundled CSV (ignoring lines starting with '#'). Mark data_source='bundled'.
       Step 2: Read synthetic CSV if present. Mark data_source='synthetic'.
       Step 3: Concatenate both dataframes.
       Step 4: Strip and lowercase 'asset_type', 'target_severity', and 'target_category'.
       Step 5: Apply `normalize_text` to generate 'clean_text'.
       Step 6: Drop duplicates on ['asset_type', 'clean_text'], keeping bundled rows first.

    6. CALLED BY:
       - `backend/train.py::train_and_save_models()`
       - `backend/evaluate.py::evaluate_all()`
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
