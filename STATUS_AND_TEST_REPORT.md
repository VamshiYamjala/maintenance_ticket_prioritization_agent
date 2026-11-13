# STATUS_AND_TEST_REPORT.md

**Project:** AI Agent for Maintenance Ticket Prioritization (Greenko Renewable-Energy Assets)  
**Presenter:** Nagavamshi Yamjala (Vamshi)  
**Date:** 2026-11-12  
**Deployment Status:** `PENDING (user action)` — verified locally; Render deployment requires user GitHub/Render login.

---

## 1. Summary

The Maintenance Ticket Prioritization Agent is an offline-capable, safety-first hybrid NLP and rule/tool-based triage system built for control-room O&M analysts managing solar, wind, hydro, and grid assets. Given a free-text ticket and asset type, it normalizes text, extracts equipment/site IDs, predicts fault category and severity via TF-IDF + Logistic Regression, applies an escalate-only deterministic safety guardrail, retrieves probable causes and next actions from a local JSON runbook, computes a transparent 0–100 priority score, routes the ticket with an SLA, and flags uncertain cases for human review—recording every step in an agent trace. All core backend, ML evaluation, frontend UI, and automated tests are complete and verified locally; only live cloud deployment on Render remains pending user action.

---

## 2. Phase Status Table

| Phase | Scope | Status | Key Files | Evidence (Command + Real Result) |
|---|---|---|---|---|
| 1 | Problem framing | DONE | `PROJECTDOC.md` | Defined user, I/O, safety-first metrics |
| 2 | Data & preprocessing | DONE | `data/generate_synthetic_data.py`, `data/challenge_tickets.csv`, `backend/preprocessing.py` | `6` bundled + `420` synthetic + `30` challenge rows verified via pandas |
| 3 | Model, baseline & validation | DONE | `backend/train.py`, `backend/evaluate.py`, `docs/evaluation_results.json` | `.\.venv\Scripts\python.exe -m backend.evaluate` -> `5-fold CV Cat F1: 1.0 ± 0.0`, `Crit Recall: 0.9399 ± 0.0612` |
| 4 | Agent tools, priority & trace | DONE | `backend/agent.py`, `backend/priority.py`, `data/runbook.json` | 9-step trace returned on `POST /api/triage`; unit tests pass |
| 5 | Optional LLM explainer | DONE | `backend/llm_explainer.py`, `.env.example`, `.gitignore` | Off by default (`explanation_source: "template"`); 401 fallback verified |
| 6 | FastAPI backend | DONE | `backend/app.py`, `backend/schemas.py` | All 8 routes tested live on `127.0.0.1:8000` (`200` / `422` / `400`) |
| 7 | Control-room frontend UI | DONE | `frontend/index.html` | `GET /` returned `200` (`20638` bytes); relative `/api/*` fetch calls |
| 8 | Tests & golden outputs | DONE | `tests/test_triage.py`, `demo/golden_examples.json` | `.\.venv\Scripts\python.exe -m pytest -q` -> `5 passed in 2.29s` |
| 9 | Documentation | DONE | `README.md`, `PROJECTDOC.md`, `BUGFIX.md`, `STATUS_AND_TEST_REPORT.md` | Cross-checked against `docs/evaluation_results.json` |
| 10 | Deployment (Render primary) | PENDING (user action) | `render.yaml`, `.python-version`, `Procfile`, `DEPLOYMENT.md` | Clean-checkout `uvicorn` check passed (`status=ok`); live Render deploy awaits user |

---

## 3. Feature Inventory

### 3.1 API Endpoints (Tested Live on `http://127.0.0.1:8000`)

| Method | Path | Purpose | Real Request | Real Trimmed Response |
|---|---|---|---|---|
| `GET` | `/` | Serve single-page UI | `Invoke-WebRequest http://127.0.0.1:8000/` | `Status=200`, `Length=20638` |
| `GET` | `/api/health` | Health & model check | `Invoke-RestMethod http://127.0.0.1:8000/api/health` | `{"status":"ok","model_loaded":true,"eval_results_available":true}` |
| `GET` | `/api/demo` | Case study & 3 sample tickets | `Invoke-RestMethod http://127.0.0.1:8000/api/demo` | `status=ready`, `sample_count=3` |
| `POST` | `/api/run` | Starter-compatible triage | `{"text":"Inverter 4 tripping repeatedly...","asset_type":"solar"}` | `cat=inverter_thermal sev=high prio=77.8 trace_steps=9` |
| `POST` | `/api/triage` | Strict validated triage | `{"ticket_id":"DEMO-02","asset_type":"wind","description":"WTG-12 gearbox vibration spike..."}` | `cat=gearbox_vibration sev=critical prio=92.0 sla=1h team=Wind Mechanical & CMS Team` |
| `POST` | `/api/batch` | JSON list batch triage | `{"tickets":[DEMO-01, DEMO-02]}` | `batch_count=2` |
| `POST` | `/api/batch-csv` | CSV file batch triage | `file=@temp_batch.csv` (`CSV-1,solar,...`) | `csv_count=1 first_cat=inverter_thermal` |
| `GET` | `/api/metrics` | Saved evaluation JSON | `Invoke-RestMethod http://127.0.0.1:8000/api/metrics` | `total_rows=426 cv_f1=1.0` |

### 3.2 Agent Tools (`backend/agent.py`)
1. `normalize_and_extract` — lowercases, strips noise, extracts equipment IDs (`WTG-12`, `Inverter 4`) and site hints (`Block 2`) via regex.
2. `classify_ticket` — predicts category, severity, probabilities, and top contributing n-grams.
3. `safety_guardrail` — deterministic, escalate-only hazard rules (`SAF-01-FIRE-ARC`, `SAF-02-CRITICAL-FAULT`, `SAF-03-HAZARD-ESCALATION`) with negation window.
4. `lookup_runbook` — TF-IDF cosine similarity over `data/runbook.json`.
5. `check_duplicates` — token Jaccard similarity (`>= 0.65`) over last 50 in-memory tickets.
6. `compute_priority` — weighted 0–100 score (`backend/priority.py`).
7. `route_ticket` — assigns owner team, SLA (`1h`/`4h`/`24h`/`72h`), and escalation tier.
8. `confidence_gate` — sets `needs_human_review = true` if confidence or top-2 margin is below threshold.
9. `explanation_layer` — verified template by default; optional LLM summary if configured.

### 3.3 UI Tabs (`frontend/index.html`)
- **Triage Console:** Asset selector, ticket textarea, 3 one-click demo buttons, severity/escalation/review badges, highlighted contributing terms, runbook causes/actions, 9-step agent trace.
- **Evaluation Metrics:** Fetches `/api/metrics` dynamically (5-fold CV KPIs, model comparison, ablation, severity confusion matrix).
- **Limitations & Formula:** Displays transparent priority formula and honest limitations.

### 3.4 Data Files (Verified by Code)
- `data/maintenance_tickets.csv`: **6 rows** (untouched bundled starter data), columns `['ticket_id', 'asset_type', 'description', 'target_severity', 'target_category']`.
- `data/maintenance_tickets_synthetic.csv`: **420 rows** (seeded synthetic, `seed=42`), columns `['ticket_id', 'asset_type', 'description', 'target_severity', 'target_category', 'data_source']`.
- `data/challenge_tickets.csv`: **30 rows** (hand-written, never used in training), columns `['ticket_id', 'asset_type', 'description', 'target_severity', 'target_category']`.

---

## 4. Evaluation Results (Fresh Run: `.\.venv\Scripts\python.exe -m backend.evaluate`)

> **Honesty Flag:** The `1.0` category Macro-F1 in 5-fold CV and on the 86-row test split comes from **template-generated synthetic data** (with noise/typos). The **30-ticket hand-written challenge set** (`0.8724` category Macro-F1, `0.1333` under-triage) is the honest generalisation number.

### 4.1 5-Fold Stratified Cross-Validation (LogReg, 426 deduplicated rows)
- **Category Accuracy / Macro-F1:** `1.0000 ± 0.0000` — separates all 10 synthetic categories cleanly across folds.
- **Severity Accuracy:** `0.9320 ± 0.0342` — consistent severity prediction with low fold-to-fold variance.
- **Severity Macro-F1:** `0.9319 ± 0.0340` — balanced performance across all 4 severity levels.
- **Critical Recall:** `0.9399 ± 0.0612` — catches ~94% of true critical tickets on average.
- **Under-Triage Rate:** `0.0352 ± 0.0257` — ~3.5% of tickets are predicted lower than true severity.

### 4.2 Model Comparison (86-Row Test Set & 30-Row Challenge Set)

| Model | Test Cat F1 | Test Sev Acc | Test Crit Recall | Test Under-Triage | Test Over-Triage | Challenge Cat F1 | Challenge Crit Recall | Challenge Under-Triage | Challenge Over-Triage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Keyword + Majority Baseline | 0.8389 | 0.6395 | 0.8750 | 0.1395 | 0.2209 | 0.9048 | 0.2857 | 0.3667 | 0.2000 |
| **TF-IDF + LogisticRegression (Main)** | **1.0000** | **0.9070** | **0.9375** | **0.0581** | **0.0349** | **0.8724** | **0.5714** | **0.1333** | **0.3000** |
| TF-IDF + LinearSVC | 1.0000 | 0.9651 | 0.9375 | 0.0233 | 0.0116 | 0.9314 | 0.5714 | 0.1667 | 0.2000 |
| TF-IDF + MultinomialNB | 1.0000 | 0.7442 | 0.6250 | 0.1860 | 0.0698 | 0.9007 | 0.5714 | 0.2000 | 0.3000 |

### 4.3 Feature Ablation (LogReg)
- **Full (`word + char + asset_type`):** Test Cat F1 `1.0000`, Challenge Cat F1 `0.8724`, Challenge Sev F1 `0.5576`.
- **No `asset_type` (`word + char`):** Test Cat F1 `1.0000`, Challenge Cat F1 `0.9314`, Challenge Sev F1 `0.6277`.
- **No `char` n-grams (`word + asset_type`):** Test Cat F1 `1.0000`, Challenge Cat F1 `0.7974`, Challenge Sev F1 `0.5965`. *(Plain words: removing character n-grams hurts typo robustness on the challenge set by 7.5 F1 points.)*

### 4.4 Challenge-Set Failure Hypotheses
- **`CHG-04`** (*"No power values appearing on SCADA screen for Block 5 since 6am though inverters are exporting"*): Actual `data_gap`, predicted `inverter_thermal`. **Hypothesis:** Word `"inverters"` carried strong TF-IDF weight toward `inverter_thermal`.
- **`CHG-07`** (*"Oil dripping steadily from Main Transformer TX-2 radiator flange and Buchholz gas alert active"*): Actual `critical`, ML predicted `high` (`severity_error = -1`). **Hypothesis:** Synthetic training used `"oil leak"`, not `"oil dripping"`; `safety_guardrail` still catches `"buchholz"` for at least `high`.
- **`CHG-11`** (*"Inverter 2 fan checked; no alarm present and heatsink temp normal after cleaning filter"*): Actual `low`, predicted `high` (`severity_error = +2`). **Hypothesis:** Bag-of-words TF-IDF matched `"alarm"` and `"heatsink temp"` without understanding the negation `"no alarm present"`.

---

## 5. Known Limitations and Open Issues

- Live Render deployment is `PENDING (user action)`.
- Training relies on synthetic tickets (only 6 real bundled rows).
- Single-label primary category assumption for multi-issue tickets.
- TF-IDF bag-of-words is sensitive to negation (`CHG-11`).
- Duplicate detection uses an in-memory rolling buffer (50 tickets), not a persistent CMMS DB.

---

## 6. Changes Since Last Report

- Added Render deployment configuration: `.python-version` (`3.12.3`), `render.yaml`, `DEPLOYMENT.md`, and `STATUS_AND_TEST_REPORT.md`.
- Updated `PROJECTDOC.md` Phase 10 and `README.md` for Render (keeping `Procfile` intact).
- No unexpected errors occurred (`BUGFIX.md` unchanged for Part A).

---

## 7. How to Test It (Windows PowerShell Guide)

### A. Setup from Scratch
```powershell
git clone https://github.com/VamshiYamjala/<your-repo-name>.git
cd <your-repo-name>
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```
- **Expected:** Virtual environment created and all packages installed with exit code `0`. No API key is needed in `.env`.
- **If it fails:** Check `python --version` (requires Python 3.12.x for pinned `numpy==1.26.4` / `scikit-learn==1.5.1`).

### B. Automated Tests
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
- **Expected:** `5 passed` (proves priority formula bounds/monotonicity, escalate-only guardrail + negation, missing LLM key fallback, Pydantic 422 validation + 3 demo tickets, and CSV missing-column 400 error).
- **If it fails:** Read the failing assertion to see which module (`priority`, `agent`, `llm_explainer`, or `app`) regressed.

### C. Evaluation Reproduction
```powershell
.\.venv\Scripts\python.exe -m backend.evaluate
```
- **Expected:** Prints CV and model comparison summary; saves `docs/evaluation_results.json` and `models/*.joblib`.
- **If it fails:** Ensure `data/maintenance_tickets_synthetic.csv` exists (or run `.\.venv\Scripts\python.exe data\generate_synthetic_data.py` first).

### D. API Tests (Start Server First in Terminal 1)
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```
Run in Terminal 2:
```powershell
# 1. Health
Invoke-RestMethod http://127.0.0.1:8000/api/health

# 2. Starter-compatible /api/run
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/run -ContentType "application/json" -Body '{"text":"Inverter 4 tripping repeatedly after noon, high temperature alarm visible at Block 2","asset_type":"solar"}'

# 3. Three demo tickets via /api/triage
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/triage -ContentType "application/json" -Body '{"ticket_id":"DEMO-01","asset_type":"solar","description":"Inverter 4 tripping repeatedly after noon, high temperature alarm visible at Block 2"}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/triage -ContentType "application/json" -Body '{"ticket_id":"DEMO-02","asset_type":"wind","description":"WTG-12 gearbox vibration spike with loud grinding noise and metallic debris suspected"}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/triage -ContentType "application/json" -Body '{"ticket_id":"DEMO-03","asset_type":"grid","description":"Arc flash sparks observed inside 33kV switchgear bay 1 during switching; area evacuated"}'

# 4. Validation errors (expect HTTP 422)
curl.exe -s -o NUL -w "empty=%{http_code}\n" -X POST http://127.0.0.1:8000/api/triage -H "Content-Type: application/json" -d '{"asset_type":"solar","description":"   "}'
curl.exe -s -o NUL -w "overlong=%{http_code}\n" -X POST http://127.0.0.1:8000/api/triage -H "Content-Type: application/json" -d "{`"asset_type`":`"solar`",`"description`":`"$('x'*2005)`"}"
curl.exe -s -o NUL -w "bad_asset=%{http_code}\n" -X POST http://127.0.0.1:8000/api/triage -H "Content-Type: application/json" -d '{"asset_type":"nuclear","description":"Turbine fault"}'

# 5. Batch JSON & CSV
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/batch -ContentType "application/json" -Body '{"tickets":[{"asset_type":"solar","description":"Inverter 4 tripping repeatedly"},{"asset_type":"wind","description":"WTG-12 gearbox vibration spike"}]}'
"ticket_id,asset_type,description`nCSV-1,solar,Inverter 4 tripping repeatedly after noon" | Set-Content temp_batch.csv -Encoding UTF8
curl.exe -s -F "file=@temp_batch.csv" http://127.0.0.1:8000/api/batch-csv
Remove-Item temp_batch.csv -Force

# 6. Metrics
Invoke-RestMethod http://127.0.0.1:8000/api/metrics | Select-Object -ExpandProperty cross_validation
```

### E. UI Manual Test Checklist
1. Open `http://127.0.0.1:8000/`.
2. Click **Demo 1: Solar Inverter**, **Demo 2: Wind Gearbox**, and **Demo 3: Grid Arc Flash** — verify severity badge, priority score, SLA, owner team, highlighted terms, runbook causes/actions, and 9-step trace.
3. Click **Evaluation Metrics** tab — verify comparison table, ablation table, and confusion matrix load without errors.
4. Click **Limitations & Formula** tab — verify formula and limitations render.
5. Submit `<5` characters — verify red error banner appears cleanly; check responsive layout at phone width (~375px) in DevTools.

### F. Failure-Mode Tests
- **No LLM key:** Default `LLM_PROVIDER=none` returns `explanation_source: "template"`. With invalid OpenAI key, retries once on `401` and falls back to `"template"`.
- **Missing model file:** Removing `models/` triggers `TicketTriageAgent.from_disk()` auto-training on startup (`CLEAN_CHECKOUT_HEALTH` verified).
- **Bad CSV:** Uploading a CSV missing `asset_type` returns `400 CSV missing required columns: ['asset_type']`.

### G. Deployed-App Test (After Render Deploy)
Replace `<RENDER_URL>` with your live Render URL (wait ~50–60s on the very first request if the free instance slept):
```powershell
Invoke-RestMethod https://<RENDER_URL>/api/health
Invoke-RestMethod -Method Post -Uri https://<RENDER_URL>/api/triage -ContentType "application/json" -Body '{"ticket_id":"DEMO-01","asset_type":"solar","description":"Inverter 4 tripping repeatedly after noon, high temperature alarm visible at Block 2"}'
```

### H. Pass/Fail Table

| Check | Result | Observed Output |
|---|---|---|
| `python -m backend.evaluate` | PASS | `5-fold CV Cat F1: 1.0`, `Crit Recall: 0.9399`, `Challenge Cat F1: 0.8724` |
| `python -m pytest -q` | PASS | `5 passed in 2.29s` |
| `GET /` & `GET /api/health` | PASS | `200`, `{"status":"ok","model_loaded":true,"eval_results_available":true}` |
| `GET /api/demo` & `POST /api/run` | PASS | `sample_count=3`, `cat=inverter_thermal sev=high prio=77.8` |
| `POST /api/triage` (3 demos) | PASS | `DEMO-01: high`, `DEMO-02: critical`, `DEMO-03: critical` |
| `422` validation (empty/asset) | PASS | `empty_status=422`, `invalid_asset_status=422` |
| `POST /api/batch` & `/api/batch-csv` | PASS | `batch_count=2`, `csv_count=1` |
| `GET /api/metrics` | PASS | `total_rows=426`, `cv_f1=1.0` |
| Clean-checkout startup (no `models/`) | PASS | Auto-trained at startup, `status=ok`, `gearbox_vibration / critical` |
| Live Render URL checks | NOT RUN | Pending user GitHub push & Render deploy |
