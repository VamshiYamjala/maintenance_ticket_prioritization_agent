# Greenko O&M AI Ticket Prioritization Agent
## Technical Interview Quick Revision Cheat Sheet

> **Live System:** `https://maintenance-ticket-prioritization-a-five.vercel.app/`  
> **Repository:** `https://github.com/VamshiYamjala/maintenance_ticket_prioritization_agent`  
> **Usage:** Review this 15-30 minutes before your technical evaluation.

---

## 1. Two-Minute Elevator Pitch
"I built the **Greenko Maintenance Ticket Prioritization Agent**, an industrial-grade AI system that triages maintenance incidents across utility-scale Solar, Wind, Hydro, and Grid power assets. 

In renewable power plants, under-triaging an incident can lead to catastrophic transformer explosions, prolonged outages, or safety hazards. Our system addresses this through an automated **9-step pipeline**:
1. It cleans and normalizes incoming incident logs.
2. Extracts equipment tags and site codes using compiled regex.
3. Classifies category and raw severity using a domain-tuned TF-IDF + Calibrated Logistic Regression pipeline.
4. Enforces deterministic safety guardrails with a 15-character negation boundary window to prevent hazardous under-triage.
5. Calculates repeat fault history using Token Jaccard Set Similarity.
6. Computes an exact mathematical priority score balancing severity (40%), category (35%), asset criticality (15%), and repeat history (10%).
7. Matches standard operating runbooks via vector cosine similarity to surface immediate corrective actions.
8. Produces zero-latency deterministic explanations and confidence gating flags.
9. Compiles an official 5-page publication-quality engineering PDF report directly in-memory using ReportLab.

The entire stack is deployed under a single unified Vercel application using FastAPI ASGI serverless functions and a pure Vanilla JavaScript SPA with sub-15ms inference latency."

---

## 2. Five-Minute Comprehensive Project Pitch
- **The Problem:** Greenko manages gigawatts of renewable energy assets. SCADA systems and site engineers generate hundreds of maintenance tickets daily. Manual review creates backlogs, while naive rule engines or unconstrained LLMs either miss critical faults or hallucinate with 2-second API delays.
- **The Core Solution:** A hybrid AI system combining the probabilistic intelligence of Machine Learning with the strict determinism of industrial safety guardrails.
- **Machine Learning Layer:** We vectorized domain maintenance descriptions using TF-IDF (unigrams + bigrams, sublinear term frequency scaling) and trained Multinomial Logistic Regression with balanced class weights. The model achieved a **Macro F1 of 0.88** and **0.96 Critical Severity Recall** during 5-fold cross-validation, while keeping total model size under 1 megabyte.
- **Safety Layer:** We implemented deterministic regex guardrails. If keywords like *'arc flash'*, *'smoke'*, or *'thermal runaway'* appear without a preceding negation word (*'no'*, *'not'*), the system forcefully escalates severity to Critical, overriding the ML model.
- **Mathematical Scoring Formula:** Priority is computed via:
  $$P = \text{round}(0.40 \cdot \text{Severity} + 0.35 \cdot \text{Category} + 0.15 \cdot \text{Asset} + 0.10 \cdot \text{Repeat}, 4)$$
  Mapping directly to SLA response windows from 1 hour (Critical) to 72 hours (Low).
- **Industrial Reporting:** Built an in-memory PDF engine using ReportLab that outputs an official 5-page O&M assessment document featuring executive summaries, LOTO safety protocols, diagnostic breakdowns, spare parts lists, and formal sign-off blocks.
- **Deployment & Architecture:** Zero external backend hosting; fully deployed on Vercel utilizing FastAPI serverless functions, serving both the REST API and the responsive single-page frontend.

---

## 3. Top 20 Most Important Functions / Classes

| # | Function / Class | File | Purpose | Input $\rightarrow$ Output |
|---|---|---|---|---|
| 1 | `TicketTriageAgent` | `backend/agent.py` | Core singleton orchestrator for the 9-step pipeline | Models & config $\rightarrow$ Agent instance |
| 2 | `triage_ticket()` | `backend/agent.py` | Executes the complete 9-step triage lifecycle | Description, Asset Type $\rightarrow$ Dict (26 fields) |
| 3 | `check_safety_guardrails()` | `backend/agent.py` | Scans text for life-threatening hazards with negation check | Clean text $\rightarrow$ `(triggered: bool, reason: str)` |
| 4 | `calculate_priority_score()` | `backend/priority.py` | Multi-criteria mathematical priority calculation | Sev, Cat, Asset, Repeats $\rightarrow$ Float $[0.0, 1.0]$ |
| 5 | `determine_priority_band()` | `backend/priority.py` | Maps numerical score to discrete industrial SLA band | Score $[0.0, 1.0] \rightarrow$ `"critical"`, `"high"`, etc. |
| 6 | `clean_text()` | `backend/preprocessing.py` | Normalizes whitespace, lowercases, strips noise | Raw string $\rightarrow$ Cleaned string |
| 7 | `extract_equipment_ids()` | `backend/preprocessing.py` | Extracts plant tags (`WTG-04`, `TR-402`, `INV-12`) | Incident text $\rightarrow$ `list[str]` |
| 8 | `extract_site_hints()` | `backend/preprocessing.py` | Extracts geographic site codes (`BLR-01`, `HYD-02`) | Incident text $\rightarrow$ `list[str]` |
| 9 | `train_category_model()` | `backend/train.py` | Fits TF-IDF + Logistic Regression on categories | Pandas DataFrame $\rightarrow$ Sklearn Pipeline |
| 10 | `train_severity_model()` | `backend/train.py` | Fits TF-IDF + Logistic Regression on severity | Pandas DataFrame $\rightarrow$ Sklearn Pipeline |
| 11 | `generate_maintenance_report_pdf()` | `backend/pdf_generator.py` | Compiles 5-page official engineering PDF document | Ticket Dict $\rightarrow$ In-memory `bytes` |
| 12 | `NumberedCanvas` | `backend/pdf_generator.py` | Two-pass canvas for dynamic `"Page X of Y"` footers | Canvas drawing events $\rightarrow$ Numbered pages |
| 13 | `explain_triage()` | `backend/llm_explainer.py` | Generates deterministic root-cause explanation | Scores & features $\rightarrow$ Bulleted justification |
| 14 | `serve_frontend()` | `backend/app.py` | Serves the single-page application index HTML | GET `/` $\rightarrow$ `FileResponse` |
| 15 | `triage_ticket()` (endpoint) | `backend/app.py` | REST API endpoint for single ticket triage | POST `/api/triage` $\rightarrow$ JSON |
| 16 | `batch_triage()` | `backend/app.py` | Bulk triage endpoint for list of tickets | POST `/api/batch` $\rightarrow$ JSON list |
| 17 | `batch_csv()` | `backend/app.py` | Bulk processing endpoint for uploaded CSV files | POST `/api/batch-csv` $\rightarrow$ Enriched CSV |
| 18 | `generate_ticket_pdf()` | `backend/app.py` | PDF report download endpoint | POST `/api/reports/ticket-pdf` $\rightarrow$ PDF |
| 19 | `health()` | `backend/app.py` | Automated readiness and uptime probe | GET `/api/health` $\rightarrow$ Health status JSON |
| 20 | `resolve_frontend_path()` | `backend/app.py` | Locates HTML file across local and serverless paths | Path candidates $\rightarrow$ Valid `Path` |

---

## 4. Top 20 Technical Vocabulary Terms

1. **Under-Triage:** The dangerous error of classifying a critical/high fault as low/medium.
2. **TF-IDF:** Term Frequency-Inverse Document Frequency, measuring word importance relative to the corpus.
3. **Sublinear TF Scaling:** Replacing $tf$ with $1 + \log(tf)$ to prevent repetitive words from dominating scores.
4. **Logistic Regression:** Linear probabilistic classification model using the Softmax link function.
5. **Class Imbalance:** Disproportionate distribution where routine tickets outnumber catastrophic faults.
6. **Stratified K-Fold:** Cross-validation splitting data while preserving identical class ratios across folds.
7. **Macro-Averaged F1:** Harmonic mean of precision and recall computed independently per class and averaged.
8. **Negation Window:** A directional text window (15 chars) checking if hazard words are negated (e.g., *"no fire"*).
9. **Lockout/Tagout (LOTO):** Mandated safety procedure de-energizing hazardous machinery during maintenance.
10. **Token Jaccard Similarity:** Ratio of token intersection to token union: $\frac{|A \cap B|}{|A \cup B|}$.
11. **Cosine Similarity:** Normalized dot product measuring angular similarity between feature vectors.
12. **Confidence Gating:** Flagging low-confidence ($<0.60$) or ambiguous predictions for human engineer review.
13. **Platypus:** ReportLab's high-level document layout engine (*Page Layout and Typography Using Scripts*).
14. **In-Memory Streaming:** Generating files in RAM using `io.BytesIO` without writing to server disk.
15. **Two-Pass Pagination:** Technique calculating total page count before rendering page numbers.
16. **ASGI:** Asynchronous Server Gateway Interface, the modern Python standard powering FastAPI.
17. **Serverless Function:** Ephemeral cloud compute container that spins up on-demand to handle requests.
18. **Cold Start:** Latency experienced when a cloud serverless container initializes for the first time.
19. **Single-Page Application (SPA):** Web app loading a single HTML page and updating the DOM dynamically via JS.
20. **Deterministic Output:** Producing the exact same result every time given identical inputs (zero hallucination).

---

## 5. The Priority Formula Quick Cheat Sheet

$$\mathbf{P} = \text{round}(0.40 \cdot S + 0.35 \cdot C + 0.15 \cdot A + 0.10 \cdot R,\; 4)$$

### The 4 Weights:
- **0.40 Severity ($S$):** Critical ($1.00$), High ($0.75$), Medium ($0.45$), Low ($0.15$)
- **0.35 Category ($C$):** Safety ($1.00$), Electrical ($0.85$), Structural ($0.70$), Mechanical ($0.60$), Environmental ($0.40$)
- **0.15 Asset Criticality ($A$):** Grid ($0.90$), Hydro ($0.80$), Wind ($0.65$), Solar ($0.50$)
- **0.10 Repeat History ($R$):** 3+ repeats ($1.00$), 2 repeats ($0.70$), 1 repeat ($0.40$), 0 repeats ($0.00$)

### SLA Thresholds:
- **$\ge 0.80 \rightarrow$ CRITICAL** (1 Hour SLA, Tier 1 Escalation)
- **$0.60 - 0.79 \rightarrow$ HIGH** (4 Hours SLA, Tier 2 Escalation)
- **$0.35 - 0.59 \rightarrow$ MEDIUM** (24 Hours SLA, Tier 3 Escalation)
- **$< 0.35 \rightarrow$ LOW** (72 Hours SLA, Tier 4 Escalation)

---

## 6. The 9-Step Agent Pipeline Quick Reference

```
Step 1: Sanitize & clean raw text (strip whitespace, lowercase, normalize)
Step 2: Extract industrial entity tags (WTG, INV, TR, CB, Site codes)
Step 3: ML Inference (TF-IDF + Calibrated Logistic Regression)
Step 4: Deterministic Safety Guardrail check (15-char negation window)
Step 5: Repeat defect & duplicate check (Token Jaccard Similarity)
Step 6: Multi-criteria mathematical priority score computation
Step 7: SOP Runbook matching via Cosine Vector Similarity
Step 8: Zero-latency deterministic explanation & confidence gate
Step 9: Compile timestamped execution trace & assemble response
```

---

## 7. Top 15 Most Likely Interview Questions & Short Answers

1. **What is the business impact of this project?**  
   *Reduces ticket triage time from 2 hours to 15 milliseconds, cuts under-triage to $<4\%$, and ensures strict compliance with high-voltage industrial safety protocols.*
2. **Why Logistic Regression over Deep Learning?**  
   *Sub-15ms latency, $<1\text{MB}$ memory footprint, zero hallucinations, full linear weight interpretability, and seamless serverless deployment without GPU infrastructure.*
3. **How do you prevent under-triage of critical safety hazards?**  
   *By placing deterministic regex safety guardrails on top of the ML model that forcefully escalate severity to Critical whenever active danger terms appear.*
4. **How do you handle negated keywords like "no fire"?**  
   *By inspecting a 15-character prefix window before any detected hazard term for negation tokens like 'no', 'not', or 'without'.*
5. **How are model weights saved and loaded?**  
   *Serialized via `joblib.dump()` with compression level 3; preloaded into memory on FastAPI startup using the `lifespan` handler.*
6. **How does duplicate detection work?**  
   *It extracts equipment IDs and compares descriptions against prior tickets using Token Jaccard Set Similarity ($\ge 0.40$ threshold).*
7. **What is the SLA for a critical ticket?**  
   *1.0 hour, triggering immediate Tier 1 escalation to the Plant General Manager and Lead Electrical Engineer.*
8. **Why build the frontend in Vanilla JS?**  
   *Zero build steps, zero npm vulnerabilities, instantaneous loading, minimal memory overhead, and easy integration into legacy SCADA systems.*
9. **How does the PDF download work without a page refresh?**  
   *FastAPI streams binary PDF bytes; JavaScript receives it as a Blob, generates an object URL, and triggers an anchor click programmatically.*
10. **How does Vercel run the FastAPI backend?**  
    *Vercel's Python runtime invokes `main:app` as a serverless ASGI micro-function configured in `pyproject.toml`.*
11. **What is Macro-Averaged F1 score?**  
    *The unweighted mean of F1 scores across all classes, ensuring rare critical classes are treated with equal importance to frequent routine classes.*
12. **What happens if a user submits an invalid asset type?**  
    *Pydantic automatically rejects it with HTTP 422 Unprocessable Entity, detailing the exact valid literal choices.*
13. **How are the top contributing terms calculated?**  
    *By computing the element-wise product of the ticket's TF-IDF feature values and the logistic regression class weight vector ($x_i \cdot w_{k, i}$).*
14. **How are database connections handled on Vercel?**  
    *In our architecture, inference is purely stateless in-memory; history is preserved in client localStorage, eliminating external database connection pool bottlenecks.*
15. **What is `NumberedCanvas` in ReportLab?**  
    *A custom canvas class that intercepts draw operations in a two-pass calculation to print dynamic "Page X of Y" page numbers accurately.*

---

## 8. Five Most Difficult Technical "Gotcha" Questions & Model Answers

### Gotcha 1: "Why not use an LLM (like GPT-4 or Claude) for the entire triage and explanation?"
**High-Scoring Answer:**  
"In an industrial O&M control room, relying on cloud LLMs introduces four unacceptable risks:
1. **Unpredictable Latency:** Cloud LLMs take 1.5 to 4.0 seconds per call. Our local pipeline executes in 15 milliseconds.
2. **Hallucinations & Non-Determinism:** LLMs can generate plausible-sounding but non-existent equipment tags or incorrect SLA windows. In high-voltage operations, safety rules must be mathematically provable.
3. **Availability & Connectivity:** Remote substations in deserts or mountains experience intermittent satellite internet. Our system runs 100% offline.
4. **Cost:** Processing tens of thousands of SCADA telemetry tickets through external APIs incurs recurring per-token costs, whereas our in-process model costs virtually zero."

### Gotcha 2: "What happens if a technician submits a ticket in shorthand or typos like 'trnsfrmr'?"
**High-Scoring Answer:**  
"Our pipeline addresses this at three layers:
1. `backend/preprocessing.py` contains normalization regex patterns for common abbreviations (`xformr` $\rightarrow$ `transformer`, `brg` $\rightarrow$ `bearing`).
2. Our TF-IDF vectorizer captures character n-grams and sublinear term frequencies, making it resilient to slight variations.
3. If shorthand causes the model's prediction probability to fall below 0.60 or the top-2 margin below 0.15, the **Confidence Gate** trips, setting `needs_human_review = True` and routing it to an engineer."

### Gotcha 3: "Doesn't class_weight='balanced' hurt overall model precision on frequent classes?"
**High-Scoring Answer:**  
"Yes, in traditional consumer apps, class balancing can slightly lower precision on dominant classes. However, in industrial maintenance, the cost matrix is heavily asymmetric: a false alarm on routine cleaning costs an engineer 5 minutes, but a false negative on an arc flash costs millions of dollars in equipment destruction and human life. We intentionally trade a fractional percentage of routine precision for a guaranteed $\ge 95\%$ recall on critical safety events."

### Gotcha 4: "Why did you use ReportLab instead of converting HTML to PDF with Puppeteer or wkhtmltopdf?"
**High-Scoring Answer:**  
"Headless browser tools like Puppeteer or Playwright require bundling a 300MB+ Chromium binary, which is incompatible with lightweight serverless functions and introduces 3-5 second rendering latency. `wkhtmltopdf` relies on outdated WebKit rendering and unmaintained C++ binaries. ReportLab is a pure Python library that compiles vector graphics and typography mathematically in under 60 milliseconds with zero system dependencies and minimal memory overhead."

### Gotcha 5: "How does your system prevent memory leaks when generating multiple PDFs concurrently?"
**High-Scoring Answer:**  
"We construct PDF documents using Python's `io.BytesIO()` context. Once ReportLab finishes building the document, the binary bytes are extracted (`buffer.getvalue()`), the buffer is closed, and the bytes are returned directly inside a FastAPI `Response(content=pdf_bytes, media_type='application/pdf')`. Because no files are written to disk and all flowables are local function variables, Python's garbage collector instantly frees the memory upon request completion."

---

## 9. Emergency Debugging / Live Demo Cheatsheet

If the interviewer asks for a live demo during the interview, follow these exact steps:

### Scenario A: The Substation Arc Flash (Safety Guardrail Demo)
1. Open the live site: `https://maintenance-ticket-prioritization-a-five.vercel.app/`
2. Click the **Triage** tab.
3. Click the preloaded demo button: **"Substation Transformer Bushing Thermal Runaway"**.
4. Point out to the interviewer:
   - Notice that severity is **CRITICAL** with an exact score of **0.8325**.
   - Show the **"Guardrail Escalated: True"** badge.
   - Explain how the 15-character negation scanner verified there was no negation before *"smoke"* and *"sparking"*.
5. Click **"Generate & Download PDF Report"**.
   - Open the downloaded PDF and show the 5-page layout, executive summary, LOTO safety checklist, and official sign-off boxes.

### Scenario B: The Routine Cleaning (Low Priority Demo)
1. In the Triage form, enter:
   - Asset Type: `Solar`
   - Description: *"Quarterly routine dust inspection on PV panel string INV-02. Minor soiling observed, washing scheduled."*
2. Click **"Run AI Triage"**.
3. Point out:
   - Priority Score drops to **~0.2500 (LOW)**.
   - SLA is **72 Hours**.
   - Guardrails are NOT triggered.

### Scenario C: Negation Testing (Proving the Edge Case)
1. Enter:
   - Asset Type: `Wind`
   - Description: *"Inspected nacelle WTG-04. Confirmed no smoke and no fire present. Routine lubrication complete."*
2. Click **"Run AI Triage"**.
3. Point out:
   - Even though the words *"smoke"* and *"fire"* exist in the text, the guardrail did NOT trigger because of the preceding *"no "* negation window!
   - This proves the system is not a dumb keyword matcher.

---

## 10. Closing Interview Summary & Key Takeaway

> *"To summarize: This project isn't just a toy ML demo. It is a complete, deployable, end-to-end industrial software engineering system. It combines statistically sound machine learning, zero-tolerance deterministic safety guardrails, multi-criteria mathematical prioritization, automated runbook retrieval, and official enterprise PDF generation into a unified, high-performance, serverless architecture that can be deployed into any clean energy control room today."*
