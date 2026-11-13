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
| `GET` | `/api/metrics` | Serves real offline evaluation metrics and benchmark tables |

---

## 4. Dataset Overview & Honest Evaluation

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

## 5. Deployment on Vercel

The application is fully configured for zero-configuration deployment to **Vercel**:

- **Vercel Config:** `vercel.json` and `pyproject.toml` (`[tool.vercel] entrypoint = "api/index.py"`).
- **Runtime:** Python 3.12 (pinned in `.python-version`).
- **Instructions:** See [DEPLOYMENT.md](DEPLOYMENT.md) for click-by-click deployment steps from GitHub or via `npx vercel`.

---

## 6. Current Limitations & Production Roadmap

1. **Synthetic Training Data:** Prototype trained on 420 synthetic tickets; production requires historical CMMS records.
2. **Single-Label Classification:** Compound multi-fault tickets receive one primary category; secondary faults trigger human review.
3. **Session In-Memory Duplicates:** Duplicate check operates on an in-memory buffer; permanent deduplication requires database integration.
4. **Negation Sensitivity:** While the safety guardrail detects negation (`"no smoke"`), bag-of-words TF-IDF occasionally over-predicts severity on negated sentences.
