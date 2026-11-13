# AI Agent for Maintenance Ticket Prioritization
**Greenko Operations & Maintenance (O&M) Intelligence Platform**

An enterprise-grade, offline-capable, safety-first hybrid NLP and rule/tool-based triage agent that classifies incoming maintenance tickets for renewable-energy assets (Solar, Wind, Hydro, Grid), enforces deterministic safety guardrails, retrieves runbook standard operating procedures (SOPs), calculates a transparent 0–100 priority score, routes tickets with strict SLAs, and logs a full 9-step execution trace.

---

## 1. Unified Architecture & Key Capabilities

The entire application runs under a **single unified project** (serving both the enterprise light-theme web UI and the Python FastAPI / scikit-learn ML pipeline):

- **Multi-Class Fault Classification:** 10 renewable-energy categories (inverter thermal, gearbox vibration, pitch system, data gap, statutory compliance, grid curtailment, transformer fault, tracker fault, communication loss, safety incident).
- **Ordinal Severity Scoring:** `low`, `medium`, `high`, `critical` with explicit error sign conventions (`error = predicted - actual`; negative error = dangerous under-triage).
- **Deterministic Safety Guardrail:** Escalate-only rules with a 15-character negation window (`"no smoke"`, `"no alarm"`) that immediately escalate fire, smoke, arc flash, and trip hazards.
- **Runbook Knowledge Retrieval:** TF-IDF cosine similarity search over local domain procedures (`data/runbook.json`), attaching probable causes to check and next actions.
- **Transparent Mathematical Priority:** Weighted 0–100 score factoring severity (45%), asset criticality (20%), generation loss risk (20%), safety flag (10%), and repeat fault count (5%).
- **Confidence Gate:** Flags `needs_human_review = true` when category confidence < 0.45 or top-2 margin < 0.12.
- **Unified Vercel Serverless Architecture:** Python ASGI serverless entrypoint (`api/index.py`) serving the frontend and all `/api/*` endpoints from a single public domain.

---

## 2. Quick Local Setup & Run Commands

### A. Clone and Set Up Virtual Environment (PowerShell)
```powershell
git clone https://github.com/VamshiYamjala/maintenance_ticket_prioritization_agent.git
cd maintenance_ticket_prioritization_agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

### B. Run Automated Unit & API Tests
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
*(Runs 5 unit and integration tests covering priority bounds, guardrail escalation, negation logic, fallback handling, and golden demo ticket outputs).*

### C. Run Model Training & Offline Evaluation
```powershell
.\.venv\Scripts\python.exe -m backend.evaluate
```
*(Generates 5-fold stratified cross-validation, model comparison benchmarks, confusion matrices, and ablation analysis, saving results to `docs/evaluation_results.json`).*

### D. Start the Local Server (UI + API at `http://127.0.0.1:8000/`)
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser.

---

## 3. API Endpoints

All endpoints use same-origin relative paths:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the enterprise single-page web application (`frontend/index.html`) |
| `GET` | `/api/health` | Application health and model readiness check |
| `GET` | `/api/demo` | Retrieves case study overview and rehearsed demo tickets |
| `POST` | `/api/triage` | Primary triage endpoint with Pydantic validation and 9-step agent trace |
| `POST` | `/api/run` | Starter-compatible triage endpoint |
| `POST` | `/api/batch` | Batch triage for a list of tickets (JSON payload) |
| `POST` | `/api/batch-csv` | Batch triage for an uploaded CSV file (`asset_type`, `description`) |
| `POST` | `/api/reports/ticket-pdf` | Generates and downloads an official 5-page enterprise PDF assessment report with full 9-step audit trace |
| `GET` | `/api/metrics` | Serves real offline evaluation metrics and benchmark tables |

---

## 4. AI-Generated Maintenance Assessment PDF Report Feature

The platform includes an enterprise-grade PDF report generation module (`backend/pdf_generator.py`) built using **Python ReportLab**. It renders an official, multi-section A4 industrial maintenance assessment document using real data from the current AI triage execution.

### Multi-Page Report Architecture:
1. **Page 1: Report Cover & Executive Summary:** Greenko Group O&M branding, unique report ID (`GKO-RPT-YYYYMMDD-XXXX`), ticket metadata, highlighted assessment card with priority score (0–100), fault category, final severity rating, safety escalation status, operational SLA, and executive disclaimer.
2. **Page 2: Ticket Details & AI Analysis:** Raw observation text, normalized clean text, extracted equipment/site entities, ML classification confidences, category probabilities, top contributing explainability tokens, and deterministic safety override checks.
3. **Page 3: Priority & Operational Routing:** Full mathematical breakdown of the 5-factor priority formula, component weights, SLA dispatch standards (Critical: 1h, High: 4h, Medium: 24h, Low: 72h), and historical duplicate defect analysis.
4. **Page 4: Runbook Standard Operating Procedure (SOP):** Retrieved runbook ID, matched fault category, candidate probable root causes for physical inspection, sequential troubleshooting steps, and statutory LOTO safety directives.
5. **Page 5: AI Agent Execution Trace & Audit Trail:** Structured table of all 9 agent workflow steps (`normalize_and_extract`, `classify_ticket`, `safety_guardrail`, `lookup_runbook`, `check_duplicates`, `compute_priority`, `route_ticket`, `confidence_gate`, `explanation_layer`), human review gate status, operational limitations, and formal plant engineering sign-off blocks.

### PDF Technical Design:
- **In-Memory Generation:** Generated in-memory via `io.BytesIO` buffers — no permanent files written to serverless storage.
- **Two-Pass Page Numbering:** Utilizes a custom `NumberedCanvas` to calculate total pages and render running headers and footers ("Page X of 5") with confidentiality labels.
- **Brand Aesthetic:** Professional Greenko industrial color palette (deep navy `#0F2D3A`, emerald green `#059669`, subtle table tints, clean typography).
- **UI Integration:** Direct "Download PDF Report" and "Print Report" action buttons in the web UI, plus instant PDF export from Session Ticket History.

---

## 5. Dataset Overview & Honest Evaluation

- **`data/maintenance_tickets.csv` (Untouched Bundled Data):** 6 starter rows across solar, wind, hydro, and grid.
- **`data/maintenance_tickets_synthetic.csv` (Synthetic Training Data):** 420 tickets generated with fixed seed (`seed=42`) incorporating realistic equipment IDs (`WTG-12`, `Inverter 4`), abbreviations (`SCADA`, `MPPT`, `RTU`), typos, and casing variations.
- **`data/challenge_tickets.csv` (Hand-Written Challenge Set):** 30 hand-written tickets testing negation, multi-issue descriptions, and paraphrasing that the model **never saw during training**.

### Benchmark Summary (`docs/evaluation_results.json`)

| Model Pipeline | Test Cat Macro-F1 | Test Crit Recall | Test Under-Triage | Challenge Cat F1 | Challenge Crit Recall | Challenge Under-Triage |
|---|---:|---:|---:|---:|---:|---:|
| Keyword Baseline | 0.8389 | 87.5% | 13.9% | 0.9048 | 28.6% | 36.7% |
| **TF-IDF + Logistic Regression (Selected)** | **1.0000** | **93.8%** | **5.8%** | **0.8724** | **57.1%** | **13.3%** |
| TF-IDF + LinearSVC | 1.0000 | 93.8% | 2.3% | 0.9314 | 57.1% | 16.7% |
| TF-IDF + MultinomialNB | 1.0000 | 62.5% | 18.6% | 0.9007 | 57.1% | 20.0% |

*Note: The 1.0 Category F1 on the test set reflects synthetic template separability. The 30-ticket challenge set (0.8724 F1, 13.3% under-triage) represents the honest generalisation performance.*

---

## 6. Deployment on Vercel

The application is fully configured for zero-configuration deployment to **Vercel**:

- **Framework:** FastAPI backend framework project with entrypoint `main:app` (configured in `pyproject.toml`).
- **Runtime:** Python 3.12 (pinned in `.python-version`).
- **Dependency Management:** Synchronized via `requirements.txt`, `pyproject.toml`, and `uv.lock`.
- **Instructions:** See [DEPLOYMENT.md](DEPLOYMENT.md) for click-by-click deployment steps from GitHub or via `npx vercel`.

---

## 7. Current Limitations & Production Roadmap

1. **Synthetic Training Data:** Prototype trained on 420 synthetic tickets; production requires historical CMMS records.
2. **Single-Label Classification:** Compound multi-fault tickets receive one primary category; secondary faults trigger human review.
3. **Session In-Memory Duplicates:** Duplicate check operates on an in-memory buffer; permanent deduplication requires database integration.
4. **Negation Sensitivity:** While the safety guardrail detects negation (`"no smoke"`), bag-of-words TF-IDF occasionally over-predicts severity on negated sentences.
