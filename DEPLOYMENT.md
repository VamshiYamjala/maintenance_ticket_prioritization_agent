# DEPLOYMENT.md — Unified Vercel Deployment Guide

**Project:** Greenko O&M Maintenance Ticket Prioritization Agent  
**Target Platform:** **Vercel** (Single Unified Project: Frontend + FastAPI + Scikit-Learn ML Backend)  
**Deployment Model:** Serverless Python ASGI Function + Vercel Global Edge CDN  
**Public Architecture:** Single Origin, Single Domain (`https://<your-project>.vercel.app`)

---

## 1. Unified Architecture Overview

The application is deployed as **one single Vercel project** serving both the enterprise web UI and the Python FastAPI / Scikit-learn triage pipeline under the exact same domain:

```text
User Browser / Client
        |
        v
https://<project-name>.vercel.app
        |
        +---> / (Root) ---------------------> FastAPI serves frontend/index.html
        |
        +---> /api/health ------------------> FastAPI GET /api/health
        |
        +---> /api/triage ------------------> FastAPI POST /api/triage (ML + Guardrail Agent)
        |
        +---> /api/metrics -----------------> FastAPI GET /api/metrics (Evaluation Results)
        |
        +---> /api/demo --------------------> FastAPI GET /api/demo (Rehearsed Demo Cases)
        |
        +---> /api/run ---------------------> FastAPI POST /api/run (Starter Compatible)
        |
        +---> /api/batch -------------------> FastAPI POST /api/batch (JSON Batch)
        |
        +---> /api/batch-csv ---------------> FastAPI POST /api/batch-csv (CSV Upload)
        |
        v
Vercel Serverless Function (api/index.py:app)
        |
        +---> In-Memory Warm Model Loading (models/*.joblib: ~980 KB total)
        +---> Fallback Read-Only Safety Handling (tmp-dir retraining if missing)
        +---> Runbook Knowledge Base (data/runbook.json)
        +---> 9-Step Agent Pipeline (backend/agent.py)
```

---

## 2. Platform Configuration Files in Repository

1. **`vercel.json`**:
   Configures routing so that all incoming traffic (`/(.*)`) routes cleanly to the FastAPI application entrypoint `api/index.py` without conflicting catch-all issues.
   ```json
   {
     "$schema": "https://openapi.vercel.sh/vercel.json",
     "rewrites": [
       {
         "source": "/(.*)",
         "destination": "/api/index.py"
       }
     ]
   }
   ```

2. **`pyproject.toml`**:
   Configures package dependencies and explicitly sets the Vercel function entrypoint:
   ```toml
   [project]
   name = "greenko-maintenance-ticket-prioritization-agent"
   version = "1.0.0"
   description = "Greenko O&M Maintenance Ticket Prioritization Agent"
   requires-python = ">=3.11"
   dependencies = [
       "fastapi==0.115.0",
       "uvicorn==0.30.6",
       "pandas==2.2.2",
       "numpy==1.26.4",
       "scikit-learn==1.5.1",
       "pydantic==2.8.2",
       "python-multipart==0.0.9",
       "joblib==1.6.0",
       "httpx==0.28.1",
       "pytest==9.2.0"
   ]

   [tool.vercel]
   entrypoint = "api/index.py"
   ```

3. **`api/index.py`**:
   Vercel serverless entrypoint that adds the repository root to `sys.path` and exports the ASGI `app` instance from `backend.app`.

4. **`.python-version`**:
   Pins Python to `3.12.3`, which is natively supported by Vercel's Python runtime and ensures wheel compatibility with `numpy==1.26.4` and `scikit-learn==1.5.1`.

5. **`.vercelignore`**:
   Excludes `.venv/`, `__pycache__/`, `.pytest_cache/`, `tests/`, and `.git/` from the deployed serverless bundle to keep function deployment rapid and light.

---

## 3. Serverless Compatibility Adaptations

- **Read-Only Filesystem Handling (`backend/agent.py`):**
  In Vercel serverless environments, the project directory is read-only at runtime. The models (`models/*.joblib`) are committed directly to Git (`~980 KB` total). If an instance is initialized in an environment where models are absent, `TicketTriageAgent.from_disk()` catches `OSError` / `PermissionError` and safely trains in `/tmp` without attempting to write to the read-only deployment directory.
- **In-Memory Model Caching:**
  FastAPI's `lifespan` hook loads `TicketTriageAgent` into global memory once on cold start, reusing the trained scikit-learn pipelines across subsequent warm requests.
- **Same-Origin Relative Communication:**
  The frontend in `frontend/index.html` uses relative endpoints (`/api/triage`, `/api/health`, `/api/metrics`, etc.) without any external hostnames, ports, or environment query params.
- **Duplicate Detection in Serverless:**
  Duplicate checking operates on an in-memory rolling buffer (last 50 tickets). Note that because serverless function instances may scale horizontally or restart, shared cross-instance duplicate memory is not guaranteed. Permanent ticket deduplication requires a future database integration (e.g. Postgres / CMMS).

---

## 4. Step-by-Step Vercel Deployment Guide (USER ACTION)

### Method A: Deploy via Vercel Web Dashboard (Recommended & Easiest)

1. **Push your code to GitHub:**
   Ensure the latest commits on branch `main` are pushed to:
   `https://github.com/VamshiYamjala/maintenance_ticket_prioritization_agent`
2. **Log in to Vercel:**
   Go to [https://vercel.com](https://vercel.com) and log in with your GitHub account (`VamshiYamjala`).
3. **Import Git Repository:**
   - Click **Add New...** &rarr; **Project**.
   - Under **Import Git Repository**, locate `maintenance_ticket_prioritization_agent` and click **Import**.
4. **Configure Project Settings:**
   - **Project Name:** `maintenance-ticket-prioritization-agent` (or keep default).
   - **Framework Preset:** Select **Other** (Vercel automatically detects `pyproject.toml` / `vercel.json` / Python).
   - **Root Directory:** `./` (leave default).
   - **Build Command:** Leave default / empty.
   - **Output Directory:** Leave default / empty.
5. **Environment Variables (Optional):**
   - The application runs 100% offline with deterministic template explanations by default.
   - If you wish to enable an optional external LLM explainer:
     - `LLM_PROVIDER`: `none` (default) or `openai`
     - `LLM_API_KEY`: *(your secret key)*
     - `LLM_MODEL`: `gpt-4o-mini`
6. **Click Deploy:**
   Click **Deploy**. Vercel will install the requirements and build the serverless function. When deployment succeeds, Vercel provides your live URL:
   `https://<project-name>.vercel.app`

---

### Method B: Deploy via Vercel CLI (Alternative from Terminal)

1. Open PowerShell in the project directory:
   ```powershell
   cd C:\Users\vamsh\Downloads\04_maintenance_ticket_prioritization_agent\04_maintenance_ticket_prioritization_agent
   ```
2. Run the Vercel deployment command:
   ```powershell
   npx vercel
   ```
3. Follow the CLI interactive prompts:
   - *Set up and deploy?* &rarr; **Y**
   - *Which scope?* &rarr; Select your Vercel account
   - *Link to existing project?* &rarr; **N**
   - *What's your project's name?* &rarr; `maintenance-ticket-prioritization-agent`
   - *In which directory is your code located?* &rarr; `./`
4. Deploy directly to production:
   ```powershell
   npx vercel --prod
   ```

---

## 5. Post-Deployment Verification Checklist

Once your Vercel deployment URL is live (e.g., `https://maintenance-ticket-prioritization-agent.vercel.app`), verify each endpoint:

### 1. Health Endpoint Check
```powershell
Invoke-RestMethod https://<your-project>.vercel.app/api/health
```
- **Expected Output:**
  ```json
  {"status":"ok","model_loaded":true,"eval_results_available":true}
  ```

### 2. Main Web Application UI
- Open `https://<your-project>.vercel.app/` in your browser.
- Verify the header status badge displays: **`Backend: Ready`** in green.
- Navigate across all tabs:
  - **Dashboard:** Operational metrics and workflow.
  - **AI Ticket Triage:** Click **Demo 1**, **Demo 2**, and **Demo 3** and run triage.
  - **Model Analytics:** Verify cross-validation KPIs, confusion matrix heatmap, and model comparison table.
  - **Runbook & Recommendations:** Verify SOP reference table.
  - **System Architecture:** Verify priority formula weights and limitations.

### 3. API Triage Call Verification
```powershell
Invoke-RestMethod -Method Post -Uri https://<your-project>.vercel.app/api/triage -ContentType "application/json" -Body '{"ticket_id":"VERCEL-TEST","asset_type":"wind","description":"WTG-12 gearbox vibration spike with loud grinding noise and metallic debris suspected"}'
```
- **Expected Output:**
  - `category`: `"gearbox_vibration"`
  - `severity`: `"critical"`
  - `priority_score`: `~92.0`
  - `owner_team`: `"Wind Mechanical & CMS Team"`
  - `sla_hours`: `1`
  - `agent_trace`: 9 execution steps

---

## 6. Serverless Cold-Start Performance & Troubleshooting

| Scenario | Behavior on Vercel | Remedy / Design Handling |
|---|---|---|
| **Cold Start** | First request after inactivity takes ~2–3 seconds while Python packages (`numpy`, `scipy`, `sklearn`) load. | Subsequent warm requests execute in **<15ms**. For presentations, ping `/api/health` 1 minute before presenting. |
| **Model File Availability** | `models/*.joblib` are bundled directly in the Git repository (`~980 KB`). | Verified included via `.vercelignore` whitelist. |
| **Read-Only /tmp** | Project folder is read-only at runtime. | Code catches `OSError` / `PermissionError` and uses in-memory or `/tmp` safely. |
| **404 on API Routes** | Rewrite misconfiguration. | Fixed via catch-all rewrite to `/api/index.py` in `vercel.json`. |
| **Same-Origin Requests** | Frontend and backend share the exact same domain. | No CORS restrictions or environment query flags required. |
