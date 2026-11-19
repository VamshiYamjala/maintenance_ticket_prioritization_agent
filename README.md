# Maintenance Ticket Prioritization Agent
**Operations & Maintenance (O&M) Ticket Triage & Routing System**

A clean, modular, and explainable Machine Learning and rule-based system designed to prioritize incoming maintenance tickets for renewable energy assets (Wind, Solar, Substation/Grid, Hydro).

---

## 1. Project Overview & Architecture

The system satisfies the assignment requirements with a lightweight, modular architecture containing 8 single-responsibility Python files:

```
04_maintenance_ticket_prioritization_agent/
├── backend/
│   ├── __init__.py
│   ├── app.py              # FastAPI server (GET /, GET /api/demo, POST /api/run)
│   ├── schemas.py          # Pydantic models for request validation
│   ├── preprocessing.py    # Text cleaning, normalization, asset token integration
│   ├── classifier.py       # TF-IDF (1,2) + Multi-output KNN (1-NN Cosine metric)
│   ├── severity.py         # Ordinal severity scoring (1-4) & safety escalation rules
│   ├── recommendations.py  # Probable root cause & recommended next action catalog
│   ├── routing.py          # Departmental team assignment mapping
│   └── triage.py           # Master coordinator executing the end-to-end pipeline
├── frontend/
│   └── index.html          # Clean single-page interface with 6 demo ticket buttons
├── data/
│   └── maintenance_tickets.csv  # Canonical 6-row training dataset
├── candidate_task.md       # Original assignment requirements
├── case_study.html         # Original case study document
├── evaluation_rubric.md    # Assignment evaluation criteria
├── submission_instructions.md
├── Procfile                # Production deployment runner (Railway / Heroku)
├── pyproject.toml          # Project configuration & dependencies
├── requirements.txt        # Production Python dependencies
└── main.py                 # ASGI application entrypoint
```

---

## 2. Machine Learning Approach (TF-IDF + KNN)

### Why 1-NN with Cosine Similarity?
The authoritative dataset contains 6 canonical training tickets representing distinct renewable energy failure modes:
1. `inverter_thermal` (solar_inverter) -> High internal inverter temperature
2. `gearbox_vibration` (wind_turbine) -> High-speed shaft vibration
3. `inspection_compliance` (wind_turbine) -> Overdue statutory safety inspection
4. `data_gap` (substation) -> RTU communication gateway offline
5. `pitch_system` (wind_turbine) -> Blade pitch angle deviation
6. `grid_curtailment` (solar_inverter) -> SLDC curtailment mismatch

For small, high-signal reference datasets:
- **TfidfVectorizer (`ngram_range=(1,2)`)**: Extracts word unigrams and bigrams, capturing both single keywords (`vibration`, `temperature`) and critical phrases (`pitch angle`, `internal temperature`).
- **KNeighborsClassifier (`n_neighbors=1, metric='cosine', algorithm='brute')`**: Identifies the single most semantically similar reference case using angular cosine distance.
- **In-Memory Fitting**: Models fit in `< 1ms` upon startup directly from `data/maintenance_tickets.csv`, requiring no brittle disk serialization (`.joblib`) and eliminating cold-start latency.

---

## 3. Safety Escalation Guardrail

In industrial energy operations, safety hazards cannot be compromised by statistical uncertainty:
- **Escalate-Only Policy**: Deterministic safety rules can escalate severity (e.g., to `Critical`), but can never downgrade an ML prediction.
- **Negation Awareness**: Scans a 15-character prefix window preceding critical hazard keywords (`smoke`, `fire`, `arc flash`, `explosion`).
  - `"Inverter high temperature with smoke observed"` -> Escalated to **Critical**.
  - `"Inverter high temperature; no smoke observed"` -> Preserves predicted severity without false escalation.

---

## 4. API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the single-page application (`frontend/index.html`). |
| `GET` | `/api/health` | Health check returning model status. |
| `GET` | `/api/demo` | Returns the 6 canonical tickets from `maintenance_tickets.csv`. |
| `POST` | `/api/run` | Main triage endpoint compatible with assignment specification (`{"text": "..."}`). |
| `POST` | `/api/triage` | Alias endpoint accepting structured queries (`{"description": "...", "asset_type": "..."}`). |

### Sample Request
```json
POST /api/run
Content-Type: application/json

{
  "text": "Inverter inverter-04 reported high internal temperature exceeding threshold",
  "asset_type": "solar_inverter"
}
```

### Sample Response
```json
{
  "category": "inverter_thermal",
  "severity": "high",
  "initial_severity": "high",
  "escalated": false,
  "safety_trigger": null,
  "confidence": 0.3633,
  "probable_cause": "Clogged air intake filters, cooling blower fan failure, or degraded thermal paste on IGBT modules.",
  "recommended_action": "Inspect cabinet air filters, verify cooling fan rotation, and perform an infrared thermal scan on power terminals.",
  "assigned_team": "Solar Maintenance Team",
  "processed_text": "inverter inverter-04 reported high internal temperature exceeding threshold asset_solar_inverter"
}
```

---

## 5. Local Setup & Execution

### Prerequisites
- Python 3.11 or 3.12
- `pip`

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Start Application
```bash
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```
Open your browser at **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.

---

## 6. Cloud Deployment

### Railway / Render
The project includes a standard `Procfile`:
```text
web: uvicorn backend.app:app --host 0.0.0.0 --port $PORT
```
Deploy directly by connecting the GitHub repository.

### Vercel
Configured via `pyproject.toml` and root entrypoints `main.py` and `api/index.py`:
- `GET /` serves the user interface directly.
- API endpoints are mounted at `/api/run` and `/api/demo`.
