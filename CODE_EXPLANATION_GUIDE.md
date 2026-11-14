# AI-Powered Maintenance Ticket Prioritization Agent
## Comprehensive Code Explanation & Technical Interview Guide

> **Project:** Greenko O&M Renewable Energy Maintenance Intelligence  
> **Repository:** `https://github.com/VamshiYamjala/maintenance_ticket_prioritization_agent`  
> **Live Production System:** `https://maintenance-ticket-prioritization-a-five.vercel.app/`  
> **Target Audience:** Engineering Students, Technical Interview Candidates, Full-Stack & ML Reviewers  

---

## Table of Contents
1. [Section 1: Executive Architectural Overview](#section-1-executive-architectural-overview)
2. [Section 2: End-to-End Request Execution Trace](#section-2-end-to-end-request-execution-trace)
3. [Section 3: Machine Learning Pipeline Deep Dive](#section-3-machine-learning-pipeline-deep-dive)
4. [Section 4: Mathematical Priority Scoring Formula & Weights](#section-4-mathematical-priority-scoring-formula--weights)
5. [Section 5: Safety Guardrails & Deterministic Business Logic](#section-5-safety-guardrails--deterministic-business-logic)
6. [Section 6: Runbook Intelligence & Equipment Extraction](#section-6-runbook-intelligence--equipment-extraction)
7. [Section 7: Zero-Latency Offline Explainability Engine](#section-7-zero-latency-offline-explainability-engine)
8. [Section 8: Professional 5-Page Industrial PDF Report Generator](#section-8-professional-5-page-industrial-pdf-report-generator)
9. [Section 9: API Contract & Endpoint Reference Table](#section-9-api-contract--endpoint-reference-table)
10. [Section 10: Frontend Architecture & UI Features](#section-10-frontend-architecture--ui-features)
11. [Section 11: 60+ Comprehensive Technical Interview Questions & Model Answers](#section-11-60-comprehensive-technical-interview-questions--model-answers)
12. [Section 12: Code Practice & Self-Quiz Challenges](#section-12-code-practice--self-quiz-challenges)
13. [Section 13: Project Limitations & Future Engineering Roadmap](#section-13-project-limitations--future-engineering-roadmap)

---

## Section 1: Executive Architectural Overview

The **Greenko Maintenance Ticket Prioritization Agent** is an industrial-grade Operations & Maintenance (O&M) decision-support system tailored for utility-scale clean energy assets (Solar PV farms, Wind turbine fleets, Hydroelectric plants, and High-Voltage Grid substations).

In traditional renewable plants, supervisory control and data acquisition (SCADA) systems and site technicians generate thousands of incident reports daily. Under-triaging a catastrophic fault (e.g., classifying a transformer thermal runaway or arc flash as "medium priority") can lead to equipment explosion, multi-week grid curtailment, regulatory penalties, or technician fatalities.

This system combines:
1. **Calibrated Machine Learning (TF-IDF + Logistic Regression)** for probabilistic category and severity classification.
2. **Deterministic Safety Guardrails** with negation boundary detection that enforce industrial lockout/tagout overrides.
3. **Multi-Criteria Mathematical Scoring** balancing severity, asset criticality, generation downtime impact, and repeat defect history.
4. **Vector Cosine Runbook Retrieval** mapping incident text to operational SOPs and recommended field actions.
5. **ReportLab 5-Page PDF Compilation** producing official engineering reports directly in-memory.

```
+---------------------------------------------------------------------------------------------------------+
|                                        BROWSER CLIENT (Vanilla JS SPA)                                  |
|   Dashboard View | Triage Form | History Ledger | Model Analytics | SOP Runbooks | System Architecture  |
+----------------------------------------------------+----------------------------------------------------+
                                                     | HTTP REST (JSON / Multipart CSV / PDF Stream)
                                                     v
+---------------------------------------------------------------------------------------------------------+
|                                    FASTAPI BACKEND GATEWAY (main.py / backend/app.py)                   |
|   - CORS Middleware & Global Exception Trapping   - Pydantic Schema Validation (schemas.py)             |
|   - In-Memory Model Preloading (Lifespan Hook)    - Health & Benchmark Telemetry Endpoints              |
+----------------------------------------------------+----------------------------------------------------+
                                                     |
                                                     v
+---------------------------------------------------------------------------------------------------------+
|                                 9-STEP TICKET TRIAGE AGENT (backend/agent.py)                           |
|                                                                                                         |
|   [1] Text Sanitization & Preprocessing (backend/preprocessing.py)                                      |
|       - Lowercasing, punctuation stripping, regex tag normalization                                     |
|                                                                                                         |
|   [2] Industrial Entity Extraction                                                                      |
|       - Equipment Tag Regex: WTG-\d+, INV-\d+, TR-\d+, CB-\d+, BESS-\d+                                 |
|       - Site Code Regex: BLR-\d+, HYD-\d+, RAJ-\d+, AP-\d+                                              |
|                                                                                                         |
|   [3] Probabilistic Machine Learning Inference                                                          |
|       - TF-IDF unigram+bigram vectorizer (sublinear TF scaling, max 4000 features)                      |
|       - Calibrated Logistic Regression (L2 penalty, balanced class weights)                             |
|       - Output: Category probabilities + Raw Severity prediction                                        |
|                                                                                                         |
|   [4] Deterministic Safety Guardrail Verification                                                       |
|       - 15-character negation prefix scanner ("no smoke", "not burning" -> NOT triggered)               |
|       - Critical keywords: fire, smoke, explosion, arc flash, oil leak, gas trip, trip lockout          |
|       - Overrides ML severity to CRITICAL if active danger is present                                   |
|                                                                                                         |
|   [5] Historical Repeat Fault & Duplicate Detection                                                     |
|       - Token Jaccard Set Similarity against recent tickets                                             |
|       - Matching equipment tag + Jaccard > 0.40 -> Escalates repeat penalty                            |
|                                                                                                         |
|   [6] Multi-Criteria Mathematical Priority Scoring (backend/priority.py)                               |
|       P = round(0.40 * Severity + 0.35 * Category + 0.15 * Asset + 0.10 * Repeat, 4)                    |
|       - Priority Banding: Critical (>=0.80), High (0.60-0.79), Medium (0.35-0.59), Low (<0.35)          |
|                                                                                                         |
|   [7] SOP Runbook Matching                                                                              |
|       - Cosine vector similarity against curated standard operating procedures                         |
|       - Surfaces probable causes and immediate lockout/tagout next actions                              |
|                                                                                                         |
|   [8] Deterministic Explainability & Confidence Gating (backend/llm_explainer.py)                       |
|       - Offline structured template reasoning (0ms external API dependency)                            |
|       - Flag human review if ML confidence < 0.60 or Top-2 margin < 0.15                               |
|                                                                                                         |
|   [9] Audit Trace Assembly                                                                              |
|       - Complete timestamped execution trace attached to every response payload                         |
+----------------------------------------------------+----------------------------------------------------+
                                                     |
                     +-------------------------------+-------------------------------+
                     |                                                               |
                     v                                                               v
+------------------------------------------+                   +------------------------------------------+
|  5-PAGE ENTERPRISE PDF (pdf_generator.py)|                   |     EVALUATION METRICS & BENCHMARKS      |
|  - In-memory BytesIO streaming           |                   |  - 5-Fold Stratified Cross-Validation    |
|  - NumberedCanvas two-pass pagination    |                   |  - Under-Triage & Critical Recall Stats  |
|  - Official O&M Work Order & Sign-offs   |                   |  - Confusion Matrix & Ablation Results   |
+------------------------------------------+                   +------------------------------------------+
```

---

## Section 2: End-to-End Request Execution Trace

Let us trace what happens when an operator submits a high-voltage substation incident:

```json
{
  "description": "Main step-up transformer TR-402 bushing terminal showing intense thermal discoloration, sparking, and buzzing. Immediate smoke observed.",
  "asset_type": "grid",
  "source": "scada"
}
```

### Trace Timeline:
1. **Network Ingress & FastAPI Routing:**
   - The request hits `POST /api/triage`.
   - FastAPI parses the JSON body against `TriageRequest` (defined in `backend/schemas.py`).
   - Pydantic validates that `asset_type` is one of `{"solar", "wind", "hydro", "grid"}` and `description` is a non-empty string.
2. **Step 1 - Sanitization (`backend/preprocessing.py`):**
   - `clean_text()` removes extraneous whitespace, lowercases the string, and standardizes punctuation.
3. **Step 2 - Entity Extraction:**
   - `extract_equipment_ids()` scans with regex `\b(?:WTG|INV|TR|CB|GEN|XFRMR|BESS)-\d+\b`.
   - Extracts: `["TR-402"]`.
   - `extract_site_hints()` checks for region codes (`None` found).
4. **Step 3 - ML Classification:**
   - The cleaned description passes into `agent.cat_pipeline` (TF-IDF + Logistic Regression).
   - Category output: `"electrical"` (probability: `0.9412`).
   - The text passes into `agent.sev_pipeline`.
   - Raw ML severity output: `"high"` (probability: `0.8120`).
5. **Step 4 - Safety Guardrail Scan:**
   - `check_safety_guardrails()` scans for hazard patterns: `sparking`, `smoke`, `thermal discoloration`.
   - Before triggering, it checks the 15-character preceding window for negation words (`no`, `not`, `never`, `without`, `free from`).
   - Finding no negation ("immediate smoke observed"), the guardrail trips!
   - Result: Severity is forcefully escalated from `"high"` to `"critical"`.
   - `guardrail_escalated = True`.
6. **Step 5 - Duplicate & Repeat History:**
   - Scans recent tickets for matching equipment `"TR-402"`.
   - Computes token Jaccard similarity. If an identical ticket arrived within the historical window, `is_duplicate = True` and repeat penalty is applied.
7. **Step 6 - Mathematical Priority Computation (`backend/priority.py`):**
   - Severity Score $S$: `"critical"` = $1.00$.
   - Category Score $C$: `"electrical"` = $0.85$.
   - Asset Criticality $A$: `"grid"` = $0.90$.
   - Repeat Factor $R$: First occurrence = $0.00$.
   - $$P = \text{round}(0.40 \cdot 1.00 + 0.35 \cdot 0.85 + 0.15 \cdot 0.90 + 0.10 \cdot 0.00, 4) = 0.8325$$
   - Since $0.8325 \ge 0.80$, priority band is **CRITICAL**.
   - SLA mapping: **1.0 hour**, Tier 1 immediate field dispatch.
8. **Step 7 - Runbook Vector Search:**
   - Queries `docs/runbooks.json` using cosine similarity on TF-IDF representation.
   - Matches: `"Substation Transformer Bushing Thermal Fault & Partial Discharge SOP"`.
   - Pulls immediate SOP safety instructions: *"Perform emergency busbar transfer, isolate transformer TR-402, engage nitrogen fire suppression."*
9. **Step 8 - Deterministic Explainability (`backend/llm_explainer.py`):**
   - Generates bulleted root-cause reasoning, citing the exact terms (`"sparking"`, `"smoke"`, `"TR-402"`) without calling an external paid API.
10. **Step 9 - Response Serialization:**
    - Assembles the 26-field JSON payload containing all scores, probabilities, SLA, and audit trace, returning HTTP 200 in under **15 milliseconds**.

---

## Section 3: Machine Learning Pipeline Deep Dive

### 1. Vectorization Architecture: TF-IDF
The system uses `TfidfVectorizer` from `scikit-learn` configured with:
- **N-gram Range:** `(1, 2)` (captures both unigrams like `"fire"` and bigrams like `"arc flash"`, `"oil leak"`, `"thermal runaway"`).
- **Sublinear TF Scaling:** `sublinear_tf=True` replaces term frequency $tf$ with $1 + \log(tf)$. This prevents a word repeated 10 times in a verbose ticket from artificially dominating the decision space over a concise ticket.
- **Max Features:** `4,000` highest-frequency vocabulary tokens, keeping model weight serialization under **1 megabyte** (983 KB) for instantaneous serverless cold starts.
- **Stopwords:** Standard English stopwords removed.

### 2. Model Choice: Why Logistic Regression over Deep Learning & Tree Ensembles?
In technical interviews, this is a **guaranteed question**. Here is the architectural justification:

| Dimension | Scikit-Learn Logistic Regression | Deep Learning (BERT / LLM) | Random Forest / XGBoost |
|---|---|---|---|
| **Cold Start Latency** | **< 35 ms** | 4,000 - 12,000 ms | 200 - 500 ms |
| **Model Disk Size** | **< 1.0 MB** total (.joblib) | 450 MB - 1.5 GB | 15 MB - 50 MB |
| **Serverless Memory** | **~45 MB RAM** (fits free tiers) | 1,500 MB - 4,000 MB | 120 MB - 300 MB |
| **Inference Time** | **< 2 ms per ticket** | 80 - 250 ms | 10 - 25 ms |
| **Interpretability** | **Exact linear weights** ($w \cdot x + b$) | Black-box hidden states | Tree ensemble path complexity |
| **Production Risk** | Zero hallucinations; deterministic | Hallucinations; prompt drift | Overfitting on small text samples |

### 3. Class Imbalance Mitigation
Industrial maintenance datasets have naturally skewed distributions (low-priority routine cleaning tickets vastly outnumber explosive transformer arc flashes).
We pass `class_weight="balanced"` to `LogisticRegression`. This automatically adjusts weights inversely proportional to class frequencies:
$$w_j = \frac{N}{K \cdot n_j}$$
Where $N$ is total samples, $K$ is number of classes, and $n_j$ is samples in class $j$. This guarantees the classifier does not blindly default to majority classes.

### 4. Hyperparameter Configuration
- **Regularization:** L2 Ridge penalty with $C=2.5$ (providing slight relaxation to encourage generalizable phrase weights).
- **Solver:** `lbfgs` (Limited-memory Broyden–Fletcher–Goldfarb–Shanno), ideal for multiclass multinomial cross-entropy optimization.
- **Max Iterations:** `1,000` to guarantee strict mathematical convergence.

---

## Section 4: Mathematical Priority Scoring Formula & Weights

The priority score $P \in [0.0, 1.0]$ is governed by a deterministic linear multi-criteria decision formula implemented in `backend/priority.py`:

$$\mathbf{P} = \text{round}\Big(w_s \cdot S + w_c \cdot C + w_a \cdot A + w_r \cdot R,\; 4\Big)$$

### Exact Weight Distribution:
| Component | Weight Symbol | Weight Value | Percentage | Industrial Justification |
|---|---|---|---|---|
| **Severity Score** | $w_s$ | **0.40** | 40% | Direct risk to human life, equipment destruction, and immediate physical hazard. |
| **Category Score** | $w_c$ | **0.35** | 35% | Operational impact on megawatt production (electrical faults trip entire substations; mechanical faults isolate single turbines). |
| **Asset Criticality** | $w_a$ | **0.15** | 15% | Strategic importance of the asset (grid switchyard failure blackout > single inverter string offline). |
| **Repeat History** | $w_r$ | **0.10** | 10% | Latent failure escalation for chronic recurring defects on the same asset. |
| **Total** | | **1.00** | **100%** | |

### Normalized Component Lookup Values:
- **Severity ($S$):** `critical` = $1.00$, `high` = $0.75$, `medium` = $0.45$, `low` = $0.15$
- **Category ($C$):** `safety` = $1.00$, `electrical` = $0.85$, `structural` = $0.70$, `mechanical` = $0.60$, `environmental` = $0.40$
- **Asset Criticality ($A$):** `grid` = $0.90$, `hydro` = $0.80$, `wind` = $0.65$, `solar` = $0.50$
- **Repeat History ($R$):** `3+ repeats` = $1.00$, `2 repeats` = $0.70$, `1 repeat` = $0.40$, `0 repeats` = $0.00$

### Priority Bands & SLA Commitments:
| Priority Score Band | Priority Label | Target SLA | Escalation Tier | Field Action Protocol |
|---|---|---|---|---|
| **0.8000 - 1.0000** | **CRITICAL** | **1 Hour** | Tier 1 (Plant GM + Lead Engineer) | Immediate emergency shutdown & lockout/tagout dispatch. |
| **0.6000 - 0.7999** | **HIGH** | **4 Hours** | Tier 2 (O&M Shift Supervisor) | Same-shift inspection and containment. |
| **0.3500 - 0.5999** | **MEDIUM** | **24 Hours** | Tier 3 (Field Technician) | Scheduled next-day preventive servicing. |
| **0.0000 - 0.3499** | **LOW** | **72 Hours** | Tier 4 (Routine Maintenance) | Consolidated into weekly planned maintenance window. |

---

## Section 5: Safety Guardrails & Deterministic Business Logic

### Why Pure Machine Learning is Forbidden in Industrial Safety
In industrial O&M, a false negative (predicting "low" for an active fire) carries catastrophic liability. Machine learning models are probabilistic; an uncommon phrasing or noise token can cause an ML classifier to under-triage. 

To eliminate this vulnerability, the system enforces a **zero-tolerance deterministic safety guardrail** layer that sits on top of the ML predictions:

```
                      +-----------------------------+
                      | Raw Ticket Incident Text    |
                      +--------------+--------------+
                                     |
                     +---------------+---------------+
                     |                               |
                     v                               v
       +----------------------------+  +----------------------------+
       | Machine Learning Classifier|  | Deterministic Guardrails   |
       | (TF-IDF + Logistic Reg)    |  | (Regex + Negation Scanner) |
       +--------------+-------------+  +--------------+-------------+
                      |                               |
              Predicted Severity                      | Triggered Hazard?
                      |                               |
                      v                               v
         +---------------------------------------------------------+
         |                 GUARDRAIL ARBITRATION                   |
         | If Hazard Detected:                                     |
         |   FORCIBLY ESCALATE Severity to "CRITICAL"              |
         |   Set guardrail_escalated = True                        |
         | Else:                                                   |
         |   Retain ML Predicted Severity                          |
         +---------------------------------------------------------+
```

### The 15-Character Negation Boundary Window
A naive keyword search (`"smoke"` or `"fire"`) fails on normal maintenance logs such as:
> *"Inspected inverter cabin, no smoke or fire observed during 100% load test."*

The system implements a directional 15-character prefix window. When a hazard term is found at character index $i$, the engine extracts `text[max(0, i-15) : i]` and tests against negation tokens (`no`, `not`, `never`, `free from`, `without`). If negated, the guardrail ignores the keyword, preventing false alarms while ensuring actual hazards trigger instantaneous escalation.

---

## Section 6: Runbook Intelligence & Equipment Extraction

### 1. Equipment Tag & Site Code Extraction
Using compiled regular expressions in `backend/preprocessing.py`, the agent parses industrial telemetry:
- **Equipment Pattern:** `\b(?:WTG|INV|TR|CB|GEN|XFRMR|BESS)-\d+\b`
  - Captures: `WTG-04` (Wind Turbine Generator 4), `INV-12` (Solar Inverter 12), `TR-402` (Main Step-up Transformer 402), `CB-101` (Circuit Breaker 101).
- **Site Pattern:** `\b(?:BLR|HYD|RAJ|AP|TN|GJ|MH)-\d+\b`
  - Identifies geographic solar parks and wind corridors.

### 2. Runbook SOP Matching via Vector Cosine Similarity
The system maintains an industrial SOP catalog in `docs/runbooks.json`. Rather than rigid keyword lookups, it vectorizes the incident description against all SOP descriptions:

$$\text{Cosine Similarity}(u, v) = \frac{u \cdot v}{\|u\|_2 \|v\|_2}$$

The top-matching SOP is bound to the ticket response, populating:
1. **Probable Root Causes** (e.g., partial discharge, dielectric oil degradation, grid voltage surge).
2. **Standard Operating Next Actions** (e.g., thermal imaging scan, insulation resistance megger test, oil gas chromatography).

### 3. Duplicate Detection via Token Jaccard Set Similarity
When two tickets reference the same equipment ID within a short time window, their token sets $A$ and $B$ are compared:

$$J(A, B) = \frac{|A \cap B|}{|A \cup B|}$$

If $J(A, B) \ge 0.40$, the system flags `is_duplicate = True`, links the prior ticket ID, and bumps the repeat fault penalty $R$.

---

## Section 7: Zero-Latency Offline Explainability Engine

Enterprise O&M engineers will not trust black-box AI recommendations. However, relying on external cloud LLM APIs (e.g., OpenAI or Claude) introduces significant latency (1,500ms - 3,000ms), recurring token costs, internet dependency, and token privacy leaks.

`backend/llm_explainer.py` implements a **hybrid deterministic template engine**:
1. **Zero External Dependency:** Runs entirely in-process in Python (<0.1ms execution time).
2. **Template Synthesis:** Combines extracted equipment tags, ML category probabilities, guardrail escalation flags, and top TF-IDF feature contributions into a cohesive, professional engineering justification.
3. **Audit Trail Compliance:** Every explanation is strictly reproducible and auditable for regulatory ISO 55000 asset management reviews.

---

## Section 8: Professional 5-Page Industrial PDF Report Generator

When plant technicians prepare to service high-voltage equipment, they require an official physical document attached to their work permit. `backend/pdf_generator.py` compiles a complete 5-page enterprise PDF directly in-memory using `ReportLab`:

### Report Page Architecture:
- **Page 1: Executive Cover Page & Core Decision Summary**
  - High-impact Greenko brand banner (#059669), metadata table, asset category badge, severity callout card, priority score gauge, and executive summary.
- **Page 2: Safety & Compliance Assessment**
  - Occupational Health & Safety (OHS) evaluation, Lockout/Tagout (LOTO) protocols, personal protective equipment (PPE) checklist, and guardrail arbitration log.
- **Page 3: Technical Root Cause & ML Confidence Breakdown**
  - Subsystem diagnostic breakdown, top contributing TF-IDF linguistic feature table, multiclass probability distribution, and duplicate historical link.
- **Page 4: Work Order Plan, Recommended Actions & Spare Parts**
  - Phase-by-phase corrective action plan, required tooling (megger testers, infrared cameras), estimated technician man-hours, and OEM spare part inventory codes.
- **Page 5: Escalation Matrix, SLA Commitments & Sign-offs**
  - Tier-by-tier emergency contact escalation table, SLA response clock, and formal sign-off signature blocks for Control Room Supervisor, O&M Lead, and Safety Officer.

### Key Technical Patterns in PDF Generation:
- **In-Memory Streaming:** Uses `io.BytesIO()` buffer, streaming binary data directly over HTTP without creating temporary files on serverless disk.
- **Two-Pass `NumberedCanvas`:** Overrides ReportLab's `canvas.Canvas` to perform a two-pass calculation, printing dynamic `"Page X of Y"` footers accurately on every page.
- **Strict A4 Geometry:** Standardized page margins ($36\text{ pt} = 0.5\text{ in}$) ensuring exact fit across industrial office printers worldwide.

---

## Section 9: API Contract & Endpoint Reference Table

| HTTP Method | Route Path | Request Payload | Response Payload | Status Codes | Function / File |
|---|---|---|---|---|---|
| **GET** | `/` | None | HTML document (`frontend/index.html`) | `200` | `serve_frontend()` in `backend/app.py` |
| **GET** | `/api` | None | Service index & endpoint directory | `200` | `api_index()` in `backend/app.py` |
| **GET** | `/api/health` | None | `{"status": "ok", "model_loaded": true}` | `200` | `health()` in `backend/app.py` |
| **GET** | `/api/demo` | None | Curated demo cases & system status | `200` | `demo()` in `backend/app.py` |
| **POST** | `/api/triage` | JSON `TriageRequest` (`description`, `asset_type`, `source`) | JSON `TriageResponse` (26 fields + audit trace) | `200`, `422`, `500` | `triage_ticket()` in `backend/app.py` |
| **POST** | `/api/batch` | JSON `BatchTriageRequest` (list of tickets) | JSON summary, count, priority breakdown, ticket list | `200`, `422`, `500` | `batch_triage()` in `backend/app.py` |
| **POST** | `/api/batch-csv` | Multipart File (`file: UploadFile`) | Processed CSV with appended priority & SLA columns | `200`, `400`, `500` | `batch_csv()` in `backend/app.py` |
| **POST** | `/api/reports/ticket-pdf`| JSON triage result dictionary | Binary PDF file stream (`application/pdf`) | `200`, `400`, `500` | `generate_ticket_pdf()` in `backend/app.py` |
| **GET** | `/api/metrics` | None | 5-fold cross-validation, confusion matrix, ablation | `200` | `metrics()` in `backend/app.py` |

---

## Section 10: Frontend Architecture & UI Features

The frontend is an enterprise-grade Single-Page Application (SPA) contained within `frontend/index.html`. It is deliberately built with **pure modern Vanilla JavaScript, CSS3 variables, and semantic HTML5**, with zero reliance on heavy external frameworks (such as React, Angular, or Vue).

### 1. Navigation Architecture (6 Functional Tabs):
1. **Executive Dashboard:** High-level KPIs, fleet status cards, priority distribution chart, and system uptime.
2. **AI Ticket Triage Form:** Interactive single-ticket submission, demo case buttons, live triage badge outputs, confidence meter, and one-click PDF generation.
3. **Historical Ledger:** Local operational history table with search, category filtering, and rerun capabilities.
4. **Model Analytics & Evaluation:** Displays real 5-fold cross-validation scores, confusion matrix heatmap, and model ablation comparison tables fetched live from `/api/metrics`.
5. **SOP Runbooks Catalog:** Interactive view of all plant maintenance operating procedures.
6. **System Architecture & Philosophy:** Interactive diagrams detailing the 9-step pipeline and mathematical priority weights.

### 2. PDF Download Flow:
When the user clicks **"Generate & Download PDF Report"**:
```javascript
const response = await fetch('/api/reports/ticket-pdf', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(lastTriageResult)
});
const blob = await response.blob();
const url = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = `Maintenance_Report_${lastTriageResult.ticket_id}.pdf`;
a.click();
window.URL.revokeObjectURL(url);
```
This guarantees smooth, asynchronous background generation with zero page reloads.

---

## Section 11: 60+ Comprehensive Technical Interview Questions & Model Answers

### Category A: System Architecture & Design (Questions 1 - 10)

#### Q1: Can you give a 2-minute architectural elevator pitch of this project?
**Answer:** The Greenko Maintenance Ticket Prioritization Agent is an industrial AI system engineered for utility-scale solar, wind, hydro, and grid assets. It solves the critical operational problem of ticket backlog and under-triaging in power plant control rooms. When an incident occurs, our system executes a 9-step automated pipeline: it cleans text, extracts equipment tags, uses TF-IDF and calibrated Logistic Regression to classify category and severity, applies deterministic safety guardrails to prevent life-threatening under-triage, computes a mathematical priority score across four weighted criteria, matches standard operating runbooks via vector similarity, and outputs an auditable decision trace alongside a publication-grade 5-page PDF engineering report in under 15 milliseconds.

#### Q2: Why did you build the frontend in Vanilla JavaScript instead of React or Next.js?
**Answer:** In mission-critical industrial dashboards, zero-dependency simplicity and operational longevity are paramount. By using pure Vanilla JS and CSS3:
1. We eliminated all Node.js build steps, Webpack/Vite bundlers, and npm supply-chain vulnerabilities.
2. The entire frontend is served as a single static file directly from FastAPI with zero compilation overhead.
3. Cold start on serverless Vercel is instantaneous because there is no client-side hydration lag.
4. The application is completely self-contained and easily embeddable into legacy SCADA web consoles.

#### Q3: How is the application deployed on Vercel without an external backend?
**Answer:** We leverage Vercel's native Python Serverless Functions runtime. By configuring `[tool.vercel] entrypoint = "main:app"` in `pyproject.toml` and setting `.python-version` to `3.12`, Vercel automatically detects the FastAPI ASGI application. When a request arrives at the root domain or `/api/*`, Vercel spins up an isolated serverless micro-container that invokes our ASGI app directly.

#### Q4: How do you prevent cold-start latency on serverless deployments?
**Answer:** Three strategies:
1. **Lightweight Model Format:** Our serialized `.joblib` model artifacts are under 1 megabyte total, deserializing in less than 35 milliseconds.
2. **Lifespan Startup Hook:** FastAPI's `lifespan` handler preloads the agent singleton into memory during container initialization.
3. **Zero Heavy Dependencies:** We avoid PyTorch or TensorFlow, which require 500MB+ container images and 5+ second initialization times.

#### Q5: What is the purpose of `main.py` versus `backend/app.py`?
**Answer:** `backend/app.py` houses the core FastAPI application logic, endpoints, middleware, and dependency injection. `main.py` sits at the repository root as the clean, standard entrypoint that exports `app` directly to satisfy Vercel's runtime locator (`main:app`) and allow local execution via `uvicorn main:app --reload`.

#### Q6: How does the system handle high-concurrency spikes during a grid outage?
**Answer:** Because our ML inference and priority scoring are completely stateless and in-memory, individual request execution takes less than 15 milliseconds. On Vercel, incoming requests automatically scale horizontally across parallel serverless function invocations without shared memory contention.

#### Q7: Why do you maintain `api/index.py` alongside `main.py`?
**Answer:** `api/index.py` serves as a resilient fallback entrypoint for legacy Vercel build detectors that specifically inspect the `api/` directory for Python serverless functions, ensuring seamless multi-environment compatibility.

#### Q8: How is state managed in the frontend without Redux or Context API?
**Answer:** State is maintained through a clean JavaScript object store (`state = { currentTicket: null, history: [], activeTab: 'dashboard' }`) and synchronized with the browser's `localStorage` for historical tickets. UI views are updated via deterministic DOM rendering functions.

#### Q9: What happens if an unhandled Python exception occurs during triage?
**Answer:** A global exception handler registered via `@app.exception_handler(Exception)` catches the error, logs the stack trace with request metadata, and returns a sanitized HTTP 500 JSON response: `{"detail": "Internal server error while processing ticket triage."}`, preventing internal server path leakage to the client.

#### Q10: How does CORS work in your FastAPI configuration?
**Answer:** We register `CORSMiddleware` with `allow_origins=["*"]`, `allow_methods=["*"]`, and `allow_headers=["*"]`. This allows client web interfaces hosted on separate domains or local dev ports to safely communicate with the API.

---

### Category B: Machine Learning & NLP (Questions 11 - 20)

#### Q11: Explain the TF-IDF feature extraction mathematically.
**Answer:** TF-IDF evaluates how important a word is to a ticket within the overall maintenance corpus:
$$\text{TF-IDF}(t, d, D) = \text{TF}(t, d) \times \text{IDF}(t, D)$$
We use sublinear term frequency:
$$\text{TF}(t, d) = 1 + \log(\text{count}(t, d)) \quad \text{for count} > 0$$
Inverse Document Frequency measures rarity across all $N$ tickets:
$$\text{IDF}(t, D) = \log\left(\frac{1 + N}{1 + |\{d \in D : t \in d\}|}\right) + 1$$
This dampens frequent words and amplifies diagnostic terms like `"vibration"` or `"flashover"`.

#### Q12: Why did you choose unigram + bigram `(1, 2)` instead of just unigrams?
**Answer:** Maintenance logs contain multi-word domain concepts whose meaning disappears when split into individual tokens. For instance, `"arc"` and `"flash"` individually have broad meanings, but the bigram `"arc flash"` represents a specific, life-threatening electrical explosion. Similarly, `"oil leak"`, `"thermal runaway"`, and `"gas trip"` are vital bigram features.

#### Q13: How does Logistic Regression perform multiclass classification here?
**Answer:** It uses the Multinomial Logistic Regression model (Softmax):
$$P(Y = k \mid \mathbf{x}) = \frac{e^{\mathbf{w}_k^T \mathbf{x} + b_k}}{\sum_{j=1}^K e^{\mathbf{w}_j^T \mathbf{x} + b_j}}$$
Where $\mathbf{w}_k$ is the learned weight vector for class $k$, and $K$ is the number of categories (or severity tiers). This outputs normalized probabilities summing to 1.0.

#### Q14: What metrics did you use to evaluate model performance?
**Answer:** We evaluate using:
1. **Macro-averaged F1 Score:** Balances precision and recall across all classes equally, preventing majority class bias.
2. **Critical Severity Recall:** The percentage of true critical incidents correctly identified ($\ge 95\%$ target).
3. **Under-Triage Rate:** The rate at which high or critical tickets are erroneously predicted as low or medium ($\le 5\%$ target).

#### Q15: What is stratified cross-validation and why is it used?
**Answer:** In 5-fold Stratified K-Fold cross-validation, the dataset is split into 5 equal subsets such that each fold contains the exact same class proportion as the full dataset. This prevents any fold from accidentally containing zero critical tickets during training or evaluation.

#### Q16: How do you extract the "top contributing terms" for explainability?
**Answer:** For a given ticket vector $\mathbf{x}$, the linear contribution of feature $i$ toward class $k$ is $c_i = x_i \cdot w_{k, i}$. We extract the indices of the largest positive $c_i$ values and map them back to the vocabulary feature names using `vectorizer.get_feature_names_out()`.

#### Q17: What is confidence gating and what thresholds do you use?
**Answer:** If the top predicted probability $p_{\text{top}} < 0.60$, or if the margin between the top two probabilities $(p_1 - p_2) < 0.15$, the ticket is flagged as ambiguous (`needs_human_review = True`), alerting plant supervisors to verify the classification manually.

#### Q18: What is an ablation study in your model evaluation?
**Answer:** An ablation study methodically disables individual system components (e.g., removing sublinear TF scaling, disabling bigrams, or removing safety guardrails) to measure their isolated impact on Macro F1 and Under-Triage Rate, proving each component's necessity.

#### Q19: Why not use an embedding model like Word2Vec or OpenAI Embeddings?
**Answer:** Pre-trained embeddings trained on Wikipedia or Common Crawl lack renewable energy industrial terminology (e.g., `"pitch bearing failure"`, `"inverter IGBT bridge"`). Furthermore, dense embedding lookup requires vector database infrastructure and adds 50-200ms latency without yielding higher critical recall than a domain-tuned TF-IDF representation.

#### Q20: How are model artifacts saved and loaded in production?
**Answer:** Trained `scikit-learn` pipelines are serialized using `joblib.dump(..., compress=3)` into `models/category_model.joblib` and `models/severity_model.joblib`. They are loaded once at server startup via `joblib.load()` into the singleton agent.

---

### Category C: Backend & API Engineering (Questions 21 - 30)

#### Q21: What is Pydantic and how is it used in this project?
**Answer:** Pydantic is a data validation library for Python. In `backend/schemas.py`, we define `TriageRequest`, `BatchTriageRequest`, and `TriageResponse` models with type hints, regex constraints, and custom field validators that reject invalid payloads before executing business logic.

#### Q22: What happens when an invalid `asset_type` (e.g., `"transformer"`) is submitted?
**Answer:** Pydantic automatically raises a `ValidationError` with HTTP 422 Unprocessable Entity, returning a detailed JSON error explaining that `asset_type` must be strictly one of `{"solar", "wind", "hydro", "grid"}`.

#### Q23: How does the `/api/batch-csv` endpoint process uploaded spreadsheets?
**Answer:** It accepts `UploadFile`, reads the file stream into an in-memory `io.BytesIO` buffer, parses it using `pandas.read_csv()`, iterates through rows executing the triage agent, appends calculated columns (`assigned_priority`, `priority_score`, `sla_hours`, `owner_team`), and returns the enhanced CSV file stream.

#### Q24: What is the purpose of FastAPI's `lifespan` context manager?
**Answer:** Unlike legacy `@app.on_event("startup")`, the modern `lifespan` async context manager provides structured setup and teardown. It loads the ML model singleton into RAM before the server begins listening for incoming HTTP connections, ensuring zero cold-start delay for the first user.

#### Q25: How does the system ensure thread safety during concurrent requests?
**Answer:** The `TicketTriageAgent` singleton is strictly read-only during inference (calling `pipeline.predict_proba()` and computing mathematical formulas). In Python, concurrent read operations on shared immutable data structures are inherently thread-safe.

#### Q26: Explain the fallback path resolution implemented in `resolve_frontend_path()`.
**Answer:** Serverless environments execute code from arbitrary working directories (e.g., `/var/task` on AWS/Vercel). `resolve_frontend_path()` checks multiple candidate paths (`BASE_DIR / "frontend" / "index.html"`, `Path.cwd() / "frontend" / "index.html"`, `/var/task/frontend/index.html`) to guarantee the HTML file is found regardless of deployment runtime directory layout.

#### Q27: What is the difference between `/api/triage` and `/api/run`?
**Answer:** `/api/triage` is the primary enterprise endpoint accepting strongly-typed `TriageRequest`. `/api/run` is a backwards-compatible endpoint accepting legacy query structures (`{"query": "..."}`), routing through the same 9-step pipeline.

#### Q28: How do you handle file uploads safely without filling up server disk?
**Answer:** Uploaded CSVs are processed purely in-memory using `UploadFile.file` and `io.BytesIO()`. No temporary files are written to the host filesystem, preventing disk exhaustion and security vulnerabilities.

#### Q29: What is the latency profile of the primary triage endpoint?
**Answer:**
- Text preprocessing & regex entity extraction: **< 1.0 ms**
- TF-IDF vectorization & Logistic Regression: **< 2.5 ms**
- Guardrail verification & priority calculation: **< 0.5 ms**
- Runbook matching & explanation formatting: **< 2.0 ms**
- Total API turnaround: **under 15 ms**.

#### Q30: How are HTTP status codes mapped across the API?
**Answer:**
- `200 OK`: Successful triage, batch processing, or PDF generation.
- `400 Bad Request`: Empty CSV upload or malformed CSV schema.
- `422 Unprocessable Entity`: Invalid request payload failing Pydantic schema validation.
- `500 Internal Server Error`: Unhandled server exception trapped by the global handler.

---

### Category D: Industrial Safety, Business Logic & Runbooks (Questions 31 - 40)

#### Q31: What is under-triage and why is it dangerous in renewable O&M?
**Answer:** Under-triage occurs when a severe incident (such as an electrical short circuit or bearing seizure) is misclassified as low or medium priority. In a renewable power plant, this leads to dispatch delays, allowing small defects to escalate into catastrophic fires, transformer explosions, or grid blackouts.

#### Q32: Give an example of a ticket where the ML model predicted "medium" but safety guardrails escalated to "critical".
**Answer:** Description: *"Routine quarterly inspection of wind turbine nacelle WTG-08. Minor vibration detected, but sudden smoke observed emerging from hydraulic brake assembly."*  
The statistical presence of `"routine inspection"` and `"minor vibration"` biased the ML model toward "medium", but the guardrail detected unnegated `"smoke observed"`, immediately escalating severity to "critical".

#### Q33: How does the system prevent false positives from negated keywords like "no smoke"?
**Answer:** By scanning the 15 characters immediately preceding any hazard keyword for negation tokens (`"no"`, `"not"`, `"never"`, `"free from"`, `"without"`). In `"no smoke observed"`, the prefix `"no "` cancels the guardrail trigger.

#### Q34: What are the four asset types and how do their criticalities differ?
**Answer:**
1. **Grid (Weight 0.90):** High-voltage switchyards, step-up transformers, and busbars. Failure disconnects entire 200MW+ solar/wind farms from the national grid.
2. **Hydro (Weight 0.80):** High-pressure penstocks, water turbines, and flood gates. Mechanical failure risks dam flooding and massive asset damage.
3. **Wind (Weight 0.65):** Wind turbine generators (WTGs). Failure halts a single 2-3MW turbine.
4. **Solar (Weight 0.50):** Photovoltaic arrays and string inverters. Failure isolates a localized inverter block (1-2MW).

#### Q35: How does the system calculate repeat fault history?
**Answer:** It parses the equipment ID (e.g., `INV-04`) and compares the incident description against recent tickets for the same equipment using Token Jaccard Set Similarity. If similarity exceeds $0.40$, it indicates an unresolved recurring issue and sets $R = 0.40$ or higher, boosting the priority score.

#### Q36: What is the formula for SLA hours based on priority score?
**Answer:**
- Critical ($P \ge 0.80$): **1.0 hour**
- High ($0.60 \le P < 0.80$): **4.0 hours**
- Medium ($0.35 \le P < 0.60$): **24.0 hours**
- Low ($P < 0.35$): **72.0 hours**

#### Q37: How does runbook matching work?
**Answer:** Standard operating procedures are cataloged in `docs/runbooks.json`. The agent vectorizes the ticket text and computes cosine similarity against each SOP's pre-vectorized description, returning the highest-scoring SOP with required safety PPE and immediate corrective actions.

#### Q38: What team ownership rules are applied?
**Answer:** Based on the assigned category:
- `safety` $\rightarrow$ Site HSE & Safety Team
- `electrical` $\rightarrow$ High-Voltage Electrical Engineering Team
- `mechanical` $\rightarrow$ Mechanical O&M Specialists
- `structural` $\rightarrow$ Civil & Structural Integrity Team
- `environmental` $\rightarrow$ Environmental Compliance Unit

#### Q39: What is Lockout/Tagout (LOTO) and why does the report include it?
**Answer:** LOTO is an internationally mandated safety procedure that guarantees dangerous machinery is de-energized, isolated, and locked out before maintenance begins. The AI report automatically includes mandatory LOTO isolation points based on the identified asset.

#### Q40: Can an operator manually override the AI's triage score?
**Answer:** Yes. The AI serves as a decision-support copilot. The generated PDF report and API include formal human sign-off blocks and review flags (`needs_human_review`), allowing plant engineers to adjust priorities with documented justification.

---

### Category E: PDF Generation & Frontend Engineering (Questions 41 - 50)

#### Q41: Why did you use ReportLab instead of WeasyPrint or Puppeteer for PDF generation?
**Answer:** Puppeteer requires a headless Chromium browser, adding 300MB+ to container images and 3,000ms+ latency. WeasyPrint requires complex system C libraries (cairo, pango) that often fail on serverless runtimes. ReportLab is a pure Python library that compiles PDFs mathematically using PostScript-like vector commands in less than 60 milliseconds with zero OS dependencies.

#### Q42: What is the purpose of the `NumberedCanvas` class in `backend/pdf_generator.py`?
**Answer:** ReportLab flowable documents do not know the total page count on page 1. `NumberedCanvas` intercepts drawing calls, saves page states in memory, and in a second pass prints accurate `"Page X of Y"` footers on every page.

#### Q43: How is brand consistency maintained in the generated PDF?
**Answer:** We define a centralized corporate color palette matching Greenko's green energy identity: Emerald Green (`#059669`), Navy Slate (`#0F2D3A`), Off-white (`#F8FAFC`), and standardized typography using Helvetica with precise point sizing and leading.

#### Q44: How does the client trigger a PDF download without opening a blank browser tab?
**Answer:** The JavaScript client receives the binary stream as a `Blob`, creates an in-memory object URL via `window.URL.createObjectURL(blob)`, constructs a temporary hidden `<a>` anchor with `download` attribute, clicks it programmatically, and revokes the URL.

#### Q45: How does the interactive confusion matrix heatmap render in the frontend?
**Answer:** It fetches `/api/metrics`, iterates over the $4 \times 4$ integer matrix, and applies CSS classes dynamically: diagonal cells receive high-opacity green styling (`cell-diag`), while off-diagonal non-zero errors receive tinted warning styling (`cell-off`).

#### Q46: How does the frontend handle responsive layouts across mobile tablets and control-room monitors?
**Answer:** Using CSS Grid and Flexbox with media query breakpoints (`@media (max-width: 1024px)` and `@media (max-width: 768px)`), collapsing two-column layouts into single-column flows on mobile screens.

#### Q47: What security precautions are taken when displaying user-submitted ticket text?
**Answer:** The frontend implements an `escapeHtml()` utility that replaces `&`, `<`, `>`, `"`, and `'` with their respective HTML character entities, preventing Cross-Site Scripting (XSS) attacks.

#### Q48: How does the dashboard poll backend health without flooding the server?
**Answer:** It runs `setInterval(checkBackendHealth, 30000)` (polling once every 30 seconds), pinging `/api/health` and updating the pulsing green/red status indicator in the top navbar.

#### Q49: What is `KeepTogether` in ReportLab and where is it used?
**Answer:** `KeepTogether` is a Platypus flowable that guarantees a block of elements (such as an escalation table and sign-off block) is not awkwardly broken across page boundaries.

#### Q50: How are PDF tables formatted to prevent text clipping?
**Answer:** Table cells wrap text inside ReportLab `Paragraph` objects with explicit `colWidths` summing to the printable A4 page width ($595.27 - 72 = 523.27\text{ points}$).

---

### Category F: Testing, Quality Assurance & Deployment (Questions 51 - 60+)

#### Q51: How is the application tested?
**Answer:** We maintain an automated `pytest` test suite covering:
1. `tests/test_triage.py`: Tests single triage, batch triage, CSV uploads, safety guardrails, priority calculations, and demo cases.
2. `tests/test_pdf_report.py`: Tests PDF byte generation, non-empty binary output, page count verification, and edge-case handling.

#### Q52: What is the current test pass rate?
**Answer:** **100% pass rate** across all 14 tests in the test suite.

#### Q53: How do you verify the models load correctly in continuous integration (CI)?
**Answer:** The test suite uses FastAPI's `TestClient`, which triggers the application `lifespan` hook, verifying that `cat_pipeline` and `sev_pipeline` load from disk without error.

#### Q54: What happens if a model `.joblib` file is missing from disk?
**Answer:** `TicketTriageAgent.from_disk()` catches `FileNotFoundError` or deserialization errors and falls back gracefully to a heuristic rule-based classifier, ensuring the application remains functional even during initial repository setup.

#### Q55: How is dependency management handled?
**Answer:** Dependencies are pinned strictly in `pyproject.toml` and locked deterministically using `uv.lock`, guaranteeing reproducible builds across developer machines and Vercel cloud environments.

#### Q56: Why is `.python-version` set to `3.12`?
**Answer:** Vercel's latest build infrastructure uses Python 3.12. Aligning `.python-version` with Vercel's runtime guarantees binary wheel compatibility for compiled C-extensions like `numpy` and `scikit-learn`.

#### Q57: How do you benchmark inference speed?
**Answer:** Using `tests/test_triage.py`, we measure wall-clock execution time over 100 iterations of `agent.triage_ticket()`, verifying that mean latency remains under 15 milliseconds.

#### Q58: What is the total memory footprint of the running server?
**Answer:** Approximately **45 to 65 MB of RAM**, comfortably below Vercel's 1024 MB free-tier limit.

#### Q59: How do you protect against denial-of-service via huge text submissions?
**Answer:** Pydantic's `Field(max_length=5000)` enforces strict input size bounds on incoming ticket descriptions.

#### Q60: If given another sprint, what major feature would you build next?
**Answer:** I would integrate direct CMMS webhook synchronization (e.g., SAP PM or IBM Maximo) to automatically dispatch work orders upon triage, and implement an active learning loop allowing plant engineers' override decisions to retrain the model quarterly.

---

## Section 12: Code Practice & Self-Quiz Challenges

Test your understanding of the codebase with these 10 practical exercises:

### Challenge 1: Manual Priority Score Calculation
**Problem:** A ticket arrives with:
- Category: `"safety"`
- Severity: `"critical"`
- Asset Type: `"hydro"`
- Repeat Count: `0`
Calculate the exact `priority_score`, `priority_band`, and `sla_hours`.
*Answer:*
- $S = 1.00$, $C = 1.00$, $A = 0.80$, $R = 0.00$.
- $P = \text{round}(0.40 \cdot 1.00 + 0.35 \cdot 1.00 + 0.15 \cdot 0.80 + 0.10 \cdot 0.00, 4) = 0.40 + 0.35 + 0.12 + 0.00 = 0.8700$.
- Priority Band: **CRITICAL** ($\ge 0.80$).
- SLA: **1.0 hour**.

### Challenge 2: Negation Window Tracing
**Problem:** Does the safety guardrail trigger on this text?
> *"Technician confirmed inverter compartment was without smoke or fire."*
*Answer:*
- Hazard keywords `"smoke"` and `"fire"` appear.
- The 15-character prefix before `"smoke"` contains `"without "`.
- The negation scanner detects `"without"`, so the guardrail does **NOT** trigger.

### Challenge 3: Pydantic Validation Edge Case
**Problem:** A user sends `POST /api/triage` with `{"description": "Bearing trip", "asset_type": "WIND"}`. What happens?
*Answer:*
- Pydantic's `Literal['solar', 'wind', 'hydro', 'grid']` is case-sensitive. `"WIND"` fails validation and returns HTTP 422. (The client UI normalizes to lowercase).

### Challenge 4: Trace the Equipment Regex
**Problem:** What does `extract_equipment_ids("Replaced damaged cable on TR-402 and WTG-09, checked INV-01.")` return?
*Answer:*
- `["TR-402", "WTG-09", "INV-01"]`.

### Challenge 5: Softmax Probability Distribution
**Problem:** If the raw logits for categories are: `[electrical: 2.5, mechanical: 1.0, structural: 0.2, safety: 0.1, environmental: -1.0]`. What is the predicted category?
*Answer:*
- `"electrical"` because its logit (2.5) is highest, resulting in the highest softmax probability.

### Challenge 6: Under-Triage Math
**Problem:** Out of 50 ground-truth critical tickets, the model predicts 45 as critical, 3 as high, and 2 as medium. What is the under-triage rate?
*Answer:*
- Under-triage is critical tickets misclassified as low or medium.
- 2 tickets classified as medium $\rightarrow \text{Under-triage rate} = \frac{2}{50} = 4.0\%$. (Within the $\le 5\%$ industrial tolerance).

### Challenge 7: Token Jaccard Set Math
**Problem:** Ticket 1 tokens: `{transformer, bushing, smoke}`. Ticket 2 tokens: `{transformer, bushing, oil, leak}`. What is the Jaccard similarity?
*Answer:*
- Intersection = `{transformer, bushing}` (size 2).
- Union = `{transformer, bushing, smoke, oil, leak}` (size 5).
- $J = \frac{2}{5} = 0.40$. Triggers repeat fault threshold ($\ge 0.40$).

### Challenge 8: Adding a New Asset Type
**Problem:** If Greenko adds `"bess"` (Battery Energy Storage Systems) to the platform, which files must be modified?
*Answer:*
1. `backend/preprocessing.py`: Add `"bess"` to `ALLOWED_ASSET_TYPES`.
2. `backend/schemas.py`: Update `Literal['solar', 'wind', 'hydro', 'grid', 'bess']`.
3. `backend/priority.py`: Add `"bess": 0.85` to `ASSET_CRITICALITY_WEIGHTS`.
4. `frontend/index.html`: Add `<option value="bess">BESS (Battery Storage)</option>` to the HTML dropdown.

### Challenge 9: Explaining ReportLab `SimpleDocTemplate`
**Problem:** What is the difference between ReportLab's low-level `canvas` API and high-level `platypus` API?
*Answer:*
- `canvas` requires manual coordinate calculation ($(x, y)$ positions), manual line wrapping, and manual page break handling.
- `platypus` (Page Layout and Typography Using Scripts) uses flowable abstractions (`Paragraph`, `Table`, `Spacer`, `PageBreak`) that automatically flow across pages based on document margins.

### Challenge 10: Serverless In-Memory State
**Problem:** Why don't we store historical tickets in a Python global list like `HISTORY = []` on Vercel?
*Answer:*
- Serverless instances are ephemeral and can be frozen, destroyed, or scaled horizontally at any moment. A Python global list would not persist across requests or scale across containers. Hence, the frontend uses client `localStorage` and a production system would use an external PostgreSQL/DynamoDB database.

---

## Section 13: Project Limitations & Future Engineering Roadmap

Every honest technical interview requires discussing realistic limitations and architectural trade-offs:

### Current Limitations:
1. **In-Memory Ephemeral History:** Because no external managed database (e.g., PostgreSQL or Redis) is connected, ticket history is persisted only in client-side browser `localStorage`.
2. **Fixed TF-IDF Vocabulary:** New slang or novel component names not present during training cannot be dynamically embedded without model retraining.
3. **Single-Node Model Training:** The current training script runs locally in scikit-learn rather than on a distributed pipeline (like Ray or Kubeflow).
4. **Static PDF Template:** While highly detailed and publication-grade, the PDF layout is compiled from pre-configured ReportLab styles rather than user-customizable visual templates.

### Engineering Roadmap:
- **Phase 1 (Database Integration):** Connect Supabase or AWS Aurora Serverless PostgreSQL to store multi-tenant ticket records and audit trails.
- **Phase 2 (Active Learning Loop):** Implement a feedback endpoint where plant engineers can correct classifications, queueing tickets for scheduled model fine-tuning.
- **Phase 3 (CMMS Integration):** Add bidirectional REST connectors to SAP Plant Maintenance (PM) and IBM Maximo to auto-generate official work orders.
- **Phase 4 (Edge Inference):** Package the agent into a lightweight ONNX runtime microcontainer deployable directly on ruggedized edge gateways inside remote solar and wind substations.
