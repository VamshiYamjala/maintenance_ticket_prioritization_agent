# AI Agent for Maintenance Ticket Prioritization

**Domain:** Renewable-Energy Operations & Maintenance (Solar, Wind, Hydro, Grid)  
**Stack:** FastAPI, scikit-learn, pandas, NumPy, joblib, Pydantic, pytest, plain HTML/CSS/JS, Railway (`Procfile`)

An offline-capable, safety-first hybrid NLP + rule/tool-based triage agent that classifies incoming O&M maintenance tickets, escalates hazardous faults deterministically, retrieves probable root causes and next actions from a local runbook, computes a transparent priority score, routes tickets with an SLA, and records a step-by-step agent trace.

---

## 1. Setup & Run Commands (PowerShell & Bash)

### Create Virtual Environment & Install Dependencies
**PowerShell (Windows):**
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Bash (Linux/macOS):**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Generate Synthetic Data, Train & Evaluate (Reproducible, Seed=42)
```powershell
.\.venv\Scripts\python.exe data\generate_synthetic_data.py
.\.venv\Scripts\python.exe -m backend.evaluate
```
*(In bash, replace `.\.venv\Scripts\python.exe` with `python`.)*

### Run Unit & API Tests
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### Start the App Locally (API + Frontend UI)
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000/` in your browser.

### Deployment (Render Primary; `Procfile` Kept for Railway)
See [DEPLOYMENT.md](DEPLOYMENT.md) for the platform size analysis, `render.yaml` / `.python-version` (`3.12.3`) configuration, and click-by-click Render deployment steps. See [STATUS_AND_TEST_REPORT.md](STATUS_AND_TEST_REPORT.md) for the full PowerShell test guide.

---

## 2. Dataset Note (Bundled vs Synthetic vs Challenge Set)

- **`data/maintenance_tickets.csv`** (untouched): 6 bundled starter rows (`solar`, `wind`, `hydro`, `grid`). Far too small to train or evaluate fairly on its own.
- **`data/maintenance_tickets_synthetic.csv`** (clearly labelled **SYNTHETIC**, `seed=42`): 420 generated tickets across 10 O&M categories (`inverter_thermal`, `gearbox_vibration`, `inspection_compliance`, `data_gap`, `pitch_system`, `grid_curtailment`, `transformer_fault`, `tracker_fault`, `communication_loss`, `safety_incident`) and 4 severities (`low`, `medium`, `high`, `critical`), with varied domain abbreviations (`WTG`, `SCADA`, `ICR`, `MPPT`, `RTU`), casing, and realistic typos.
- **`data/challenge_tickets.csv`**: 30 hand-written tickets (never used in training) testing paraphrasing, typos, multi-issue tickets, and negations (e.g., `"no alarm present"`).

---

## 3. Inputs, Outputs & Architecture

- **Input:** `asset_type` (`solar` | `wind` | `hydro` | `grid`), `description` (5–2000 chars), optional `ticket_id`.
- **Agent Tool Pipeline:**
  1. `normalize_and_extract` — cleans text and extracts equipment IDs (`WTG-12`, `Inverter 4`, `TX-2`) and site hints (`Block 2`, `ICR-2`) via regex.
  2. `classify_ticket` — TF-IDF (word 1–2 n-grams + char_wb 3–5 n-grams) + `asset_type` One-Hot Encoding -> `LogisticRegression(C=2.0, class_weight="balanced")`.
  3. `safety_guardrail` — deterministic, **escalate-only** hazard rules (smoke, fire, arc flash, oil leak, overspeed, etc.). Never downgrades ML severity.
  4. `lookup_runbook` — TF-IDF cosine similarity retrieval over `data/runbook.json` for probable causes to check and next actions.
  5. `check_duplicates` — token Jaccard similarity (>= 0.65) against recent tickets.
  6. `compute_priority` — transparent weighted score (0–100):  
     `100 * (0.45 * severity_weight + 0.20 * asset_criticality + 0.20 * generation_loss_risk + 0.10 * safety_flag + 0.05 * min(duplicate_count, 3) / 3)`
  7. `route_ticket` — assigns owner team and SLA (`critical: 1h`, `high: 4h`, `medium: 24h`, `low: 72h`).
  8. `confidence_gate` — sets `needs_human_review = true` when confidence is low or top-2 categories are close.
  9. `explanation_layer` — deterministic verified template by default (`LLM_PROVIDER=none`); optional OpenAI-compatible summary if configured via environment variables.

---

## 4. Real Evaluation Results (`docs/evaluation_results.json`)

- **Dataset (after deduplication):** 426 rows (6 bundled + 420 synthetic), split 80/20 stratified (340 train / 86 test), plus 30 hand-written challenge tickets.
- **5-Fold Cross-Validation (LogReg):**
  - Category Macro-F1: `1.0 ± 0.0`
  - Critical Recall: `0.9399 ± 0.0612`
  - Under-Triage Rate: `0.0352 ± 0.0257`
- **Model Comparison (Test Set / Challenge Set):**
  - Keyword + Majority Baseline: Test Cat F1 `0.8389`, Test Crit Recall `0.875`, Challenge Cat F1 `0.9048`, Challenge Under-Triage `0.3667`
  - **TF-IDF + LogisticRegression (Main):** Test Cat F1 `1.0`, Test Crit Recall `0.9375`, Challenge Cat F1 `0.8724`, Challenge Under-Triage `0.1333`
  - TF-IDF + LinearSVC: Test Cat F1 `1.0`, Test Crit Recall `0.9375`, Challenge Cat F1 `0.9314`, Challenge Under-Triage `0.1667`
  - TF-IDF + MultinomialNB: Test Cat F1 `1.0`, Test Crit Recall `0.625`, Challenge Cat F1 `0.9007`, Challenge Under-Triage `0.2`

---

## 5. Assumptions, Limitations & Production-Readiness Gaps

| Gap Area | Current Prototype State | Required for Production |
|---|---|---|
| **Training Data** | 6 bundled + 420 synthetic rows | Real historical CMMS tickets reviewed by O&M engineers |
| **Multi-Label Faults** | Single primary category per ticket | Multi-label classification for compound faults |
| **Duplicate Detection** | In-memory rolling buffer (last 50 tickets) | Persistent vector/database lookup in CMMS |
| **Auth & Audit Log** | Open API, console logging | SSO/RBAC, immutable triage & override audit trail |
| **Drift & Retraining** | Manual `python -m backend.evaluate` | Scheduled drift monitoring + human-feedback retraining loop |
| **Language** | English only | Multilingual/regional operator phrasing support |
