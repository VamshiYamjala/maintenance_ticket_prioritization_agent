# DEPLOYMENT.md — Render (Primary) & Vercel (Evaluated / Not Recommended)

**Deployment Status:** `PENDING (user action)` — verified locally from a clean checkout; live Render deploy requires user login to GitHub and Render.  
**Brief Deviation Note:** The original case-study brief mentions Railway (`Procfile` is kept intact in the repo). Per updated instructions, **Render** is configured as the primary deployment target via `render.yaml` and `.python-version`.

---

## 1. Platform Decision (Evidence-Based)

Measured locally from `.venv\Lib\site-packages` and `models/`:

| Component | Measured Size |
|---|---:|
| `scipy` | 110.74 MB |
| `pandas` | 63.37 MB |
| `scikit-learn` (`sklearn`) | 44.11 MB |
| `numpy` | 28.73 MB |
| `fastapi` + `pydantic` + `starlette` + `uvicorn` + `joblib` + `httpx` | 7.58 MB |
| **Core ML + API runtime (excl. dev tools)** | **~254.5 MB** |
| **Total `.venv` site-packages unzipped** | **348.03 MB** |
| `models/category_pipeline.joblib` | 647.54 KB |
| `models/severity_pipeline.joblib` | 336.29 KB |

### Why Render (Primary)
- Render runs FastAPI as a persistent `uvicorn` web service with no 250 MB serverless bundle cap.
- Supports `.python-version` (`3.12.3`), matching our verified `numpy==1.26.4` and `scikit-learn==1.5.1` wheels.
- Serves both the REST API (`/api/*`) and the single-page UI (`/`) from one service using relative `/api/...` `fetch()` paths.

### Why Not Vercel for This App
- Vercel's standard Python serverless function limit is **250 MB uncompressed** (our core ML + API runtime alone is **~254.5 MB**, exceeding 250 MB without opting into Fluid Compute / Large Functions via `VERCEL_SUPPORT_LARGE_FUNCTIONS=1`).
- Vercel serverless functions also have a **read-only filesystem** outside `/tmp` (so startup auto-training into `models/` would fail if `models/*.joblib` were absent) and suffer heavier cold starts when importing `scipy`/`sklearn`.
- **Standard Alternative (optional):** Deploy `frontend/index.html` as a static site on Vercel and host the FastAPI backend on Render (with `frontend/index.html` pointing to the Render API URL). Because Render already serves `frontend/index.html` cleanly on a single service, no fragile split setup was added.

---

## 2. Render Configuration (Already in Repo)

- **`render.yaml`** (Render Blueprint):
  - **Service Type:** `web` (`python`)
  - **Build Command:** `pip install -r requirements.txt && python -m backend.evaluate`
  - **Start Command:** `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
  - **Health Check Path:** `/api/health`
  - **Environment Variables:**
    - `PYTHON_VERSION=3.12.3` (also pinned in `.python-version`)
    - `LLM_PROVIDER=none` (app works 100% offline with no API key)
    - `LLM_MODEL=gpt-4o-mini` (optional)
    - `LLM_API_KEY` (optional, unset by default)
- **Model Availability:** `models/*.joblib` are small (`983.83 KB` total), AND `render.yaml` runs `python -m backend.evaluate` during build so both `models/*.joblib` and `docs/evaluation_results.json` match the exact Render runtime.

---

## 3. Step-by-Step Git & Render Deployment (USER ACTION)

### Step A: Initialize Git & Push to GitHub (`VamshiYamjala`)
1. Create a new empty repository on GitHub under `VamshiYamjala` (e.g., `greenko-ticket-triage-agent`).
2. Run in PowerShell from the project root:
```powershell
git init
git branch -M main
git add .
git status
# Confirm .venv/ and .env are NOT listed!
git commit -m "Initial commit: Maintenance Ticket Prioritization Agent"
git remote add origin https://github.com/VamshiYamjala/greenko-ticket-triage-agent.git
git push -u origin main
```

### Step B: Deploy on Render (Click-by-Click)
1. Sign in to [https://dashboard.render.com](https://dashboard.render.com) with your GitHub account.
2. Click **New +** -> **Blueprint** (or **Web Service** -> connect `VamshiYamjala/greenko-ticket-triage-agent`).
3. If using **Blueprint**, Render reads `render.yaml` automatically; click **Apply**.
4. If using **Web Service** manually:
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt && python -m backend.evaluate`
   - **Start Command:** `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/api/health`
   - **Instance Type:** `Free`
   - **Environment Variables:** `PYTHON_VERSION` = `3.12.3`, `LLM_PROVIDER` = `none`
5. Click **Create Web Service** and watch **Logs** until you see `Application startup complete.` and `Your service is live`.

---

## 4. Post-Deploy Verification & Tomorrow's Warm-Up Routine

Once Render shows **Live** (replace `<RENDER_URL>`):
1. Open `https://<RENDER_URL>/api/health` -> expect `{"status":"ok","model_loaded":true,"eval_results_available":true}`.
2. Open `https://<RENDER_URL>/` -> click **Demo 1: Solar Inverter** and **Evaluation Metrics** tab.
3. Run one API triage test from PowerShell:
   ```powershell
   Invoke-RestMethod -Method Post -Uri https://<RENDER_URL>/api/triage -ContentType "application/json" -Body '{"ticket_id":"DEMO-01","asset_type":"solar","description":"Inverter 4 tripping repeatedly after noon, high temperature alarm visible at Block 2"}'
   ```

> **Cold-Start Warning (Render Free Tier):** Render free instances spin down after 15 minutes of inactivity; the first request can take **50–60 seconds** to wake up. **Open your Render URL 10 minutes before your presentation** and click Demo 1 once to warm it up. Keep local `uvicorn` ready as backup.

---

## 5. Deployment Troubleshooting Table

| Likely Error | Cause | Fix | Occurred Here? |
|---|---|---|---|
| Build fails compiling `numpy`/`scipy` | Wrong Python version (e.g., 3.13) | Pin `3.12.3` in `.python-version` & `PYTHON_VERSION` | No (prevented) |
| App fails to bind port | Hardcoded port instead of `$PORT` | Use `--host 0.0.0.0 --port $PORT` | No |
| Missing `models/*.joblib` or `evaluation_results.json` | Not generated before start | Run `python -m backend.evaluate` in buildCommand + auto-train fallback | Verified in clean-checkout test |
| `ModuleNotFoundError: backend` | Wrong working directory | Run `uvicorn backend.app:app` from repo root | No |
| `404` on `/` or `/api/metrics` | Relative paths broken | `frontend/index.html` uses relative `/api/...`; `app.py` serves `/` | No |
| `502 Bad Gateway` on wake-up | Free-tier cold start timeout | Wait 60s and refresh; warm up 10 mins before demo | Not run (pending deploy) |
