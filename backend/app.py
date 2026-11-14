"""
===============================================================================
FILE: backend/app.py
===============================================================================
1. WHAT THIS FILE DOES:
   FastAPI web application and REST API server for the Greenko O&M Maintenance
   Ticket Prioritization Agent. Exposes all public endpoints:
     - GET / : Serves the Single-Page Application (frontend/index.html)
     - GET /api/health : Health check & model readiness probe
     - GET /api/demo : Demo cases & pre-configured rehearsed tickets
     - POST /api/triage : Primary validated triage endpoint with 9-step audit trace
     - POST /api/run : Legacy/starter compatible endpoint
     - POST /api/batch : Bulk triage for list of tickets (JSON payload)
     - POST /api/batch-csv : Bulk triage for uploaded CSV files
     - POST /api/reports/ticket-pdf : Generates official 5-page enterprise PDF report
     - GET /api/metrics : Serves real 5-fold CV & benchmark evaluation results

2. WHY THIS FILE IS NEEDED:
   Provides the unified backend interface that connects the browser client,
   monitoring tools, and external CMMS systems to the Machine Learning agent
   and ReportLab PDF engine.

3. WHICH OTHER FILES USE IT:
   - main.py: Imports `app` from this file to export the root ASGI application.
   - api/index.py: Imports `app` from this file for Vercel serverless functions.
   - tests/test_triage.py & tests/test_pdf_report.py: Imports `app` for testing.

4. WHAT INPUT IT RECEIVES:
   - HTTP requests (JSON payloads, multipart CSV files, query parameters).

5. WHAT OUTPUT IT PRODUCES:
   - JSON responses, HTML file response, and binary PDF file streams.
===============================================================================
"""

from __future__ import annotations

import datetime
import io
import json
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from backend.agent import TicketTriageAgent
from backend.pdf_generator import generate_maintenance_report_pdf
from backend.preprocessing import ALLOWED_ASSET_TYPES
from backend.schemas import BatchTriageRequest, LegacyRunQuery, TriageRequest

# Configure standardized logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("triage_api")

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_INDEX = BASE_DIR / "frontend" / "index.html"
EVAL_RESULTS_PATH = BASE_DIR / "docs" / "evaluation_results.json"


def resolve_frontend_path() -> Path:
    """Resolve the location of frontend/index.html across local and Vercel environments."""
    if FRONTEND_INDEX.exists():
        return FRONTEND_INDEX
    for candidate in [
        BASE_DIR / "frontend" / "index.html",
        Path.cwd() / "frontend" / "index.html",
        Path("/var/task/frontend/index.html"),
    ]:
        if candidate.exists():
            return candidate
    return FRONTEND_INDEX


def resolve_eval_path() -> Path:
    """Resolve the location of docs/evaluation_results.json across environments."""
    if EVAL_RESULTS_PATH.exists():
        return EVAL_RESULTS_PATH
    for candidate in [
        BASE_DIR / "docs" / "evaluation_results.json",
        Path.cwd() / "docs" / "evaluation_results.json",
        Path("/var/task/docs/evaluation_results.json"),
    ]:
        if candidate.exists():
            return candidate
    return EVAL_RESULTS_PATH


# Global agent singleton instance (cached in memory for microsecond response times)
_agent: TicketTriageAgent | None = None


def get_agent() -> TicketTriageAgent:
    """Singleton getter: Loads TicketTriageAgent on first call, then reuses in-memory instance."""
    global _agent
    if _agent is None:
        logger.info("Loading TicketTriageAgent from disk...")
        _agent = TicketTriageAgent.from_disk()
    return _agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan handler: Preloads models into memory upon server startup
    so the first incoming user request experiences zero cold-start latency.
    """
    get_agent()
    logger.info("TicketTriageAgent ready.")
    yield


app = FastAPI(
    title="AI Agent for Maintenance Ticket Prioritization",
    description="Greenko O&M Renewable Energy Ticket Prioritization API",
    version="1.0.0",
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing (CORS): allows browser UI to make API fetch calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global catch-all exception handler: Logs unhandled errors and returns standard 500 JSON."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error while processing ticket triage."},
    )


# =============================================================================
# ENDPOINT 1: Single-Page Application (Frontend)
# =============================================================================
@app.get("/")
@app.get("/index.html")
@app.get("/api/index.py")
def serve_frontend() -> FileResponse:
    """
    HTTP Method: GET /
    Purpose: Serves the single-page application HTML interface.
    Input: None
    Output: HTML FileResponse (frontend/index.html)
    """
    target = resolve_frontend_path()
    if not target.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return FileResponse(target)


# =============================================================================
# ENDPOINT 1B: API Directory Index
# =============================================================================
@app.get("/api")
@app.get("/api/")
def api_index() -> dict[str, Any]:
    """
    HTTP Method: GET /api
    Purpose: Provides service overview and endpoint catalog for API discovery.
    """
    return {
        "service": "Greenko O&M Maintenance Ticket Prioritization Agent API",
        "version": "1.0.0",
        "endpoints": {
            "frontend": "/",
            "health": "/api/health",
            "demo": "/api/demo",
            "triage": "/api/triage",
            "batch": "/api/batch",
            "batch_csv": "/api/batch-csv",
            "pdf_report": "/api/reports/ticket-pdf",
            "metrics": "/api/metrics",
            "docs": "/docs",
        },
    }


# =============================================================================
# ENDPOINT 2: Health Check
# =============================================================================
@app.get("/api/health")
def health() -> dict[str, Any]:
    """
    HTTP Method: GET /api/health
    Purpose: Automated uptime and readiness probe for cloud monitoring.
    Input: None
    Output: {"status": "ok", "model_loaded": bool, "eval_results_available": bool}
    """
    agent = get_agent()
    eval_path = resolve_eval_path()
    return {
        "status": "ok",
        "model_loaded": agent.cat_pipeline is not None and agent.sev_pipeline is not None,
        "eval_results_available": eval_path.exists(),
    }


# =============================================================================
# ENDPOINT 3: Preloaded Demo Tickets
# =============================================================================
@app.get("/api/demo")
def demo() -> dict[str, Any]:
    """
    HTTP Method: GET /api/demo
    Purpose: Returns case study overview and 3 pre-configured demo tickets.
    Input: None
    Output: JSON dictionary with sample tickets.
    """
    return {
        "case_study": "AI Agent for Maintenance Ticket Prioritization",
        "status": "ready",
        "expected_outcome": (
            "A ticket triage system that assigns severity, category, probable root cause, "
            "and next action using NLP and rule/tool-based agent logic."
        ),
        "sample_tickets": [
            {
                "ticket_id": "DEMO-01",
                "asset_type": "solar",
                "description": "Inverter 4 tripping repeatedly after noon, high temperature alarm visible at Block 2",
            },
            {
                "ticket_id": "DEMO-02",
                "asset_type": "wind",
                "description": "WTG-12 gearbox vibration spike with loud grinding noise and metallic debris suspected",
            },
            {
                "ticket_id": "DEMO-03",
                "asset_type": "grid",
                "description": "Arc flash sparks observed inside 33kV switchgear bay 1 during switching; area evacuated",
            },
        ],
    }


# =============================================================================
# ENDPOINT 4: Primary AI Ticket Triage
# =============================================================================
@app.post("/api/triage")
def triage_ticket(req: TriageRequest) -> dict[str, Any]:
    """
    HTTP Method: POST /api/triage
    Purpose: Primary strict triage endpoint with Pydantic validation.
    Input: JSON payload conforming to TriageRequest schema:
           {"ticket_id": str, "asset_type": "solar"|"wind"|"hydro"|"grid", "description": str}
    Output: Complete triage dictionary with category, severity, priority, SLA, and 9-step agent_trace.
    """
    agent = get_agent()
    result = agent.run(description=req.description, asset_type=req.asset_type, ticket_id=req.ticket_id)
    logger.info(
        "Triaged ticket=%s asset=%s category=%s severity=%s priority=%.1f review=%s",
        result["ticket_id"],
        result["asset_type"],
        result["category"],
        result["severity"],
        result["priority_score"],
        result["needs_human_review"],
    )
    return result


# =============================================================================
# ENDPOINT 5: Starter / Legacy Run Query
# =============================================================================
@app.post("/api/run")
def run_case(query: LegacyRunQuery) -> dict[str, Any]:
    """
    HTTP Method: POST /api/run
    Purpose: Backward-compatible endpoint matching starter project schema (query.text or query.description).
    """
    try:
        desc = query.resolved_description()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    agent = get_agent()
    result = agent.run(description=desc, asset_type=query.asset_type, ticket_id=query.ticket_id)
    return result


# =============================================================================
# ENDPOINT 6: Batch JSON Triage
# =============================================================================
@app.post("/api/batch")
def triage_batch(req: BatchTriageRequest) -> dict[str, Any]:
    """
    HTTP Method: POST /api/batch
    Purpose: Triages a batch list of up to 100 tickets in a single HTTP request.
    Input: {"tickets": [TriageRequest, ...]}
    Output: {"count": int, "results": [triage_dict, ...]}
    """
    agent = get_agent()
    results = [
        agent.run(description=t.description, asset_type=t.asset_type, ticket_id=t.ticket_id)
        for t in req.tickets
    ]
    return {"count": len(results), "results": results}


# =============================================================================
# ENDPOINT 7: Batch CSV Upload Triage
# =============================================================================
@app.post("/api/batch-csv")
async def triage_batch_csv(file: UploadFile = File(...)) -> dict[str, Any]:
    """
    HTTP Method: POST /api/batch-csv
    Purpose: Upload a CSV spreadsheet with columns [asset_type, description] (and optional ticket_id)
             and receive structured triage results for all rows.
    """
    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw), comment="#")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid CSV file: {exc}") from exc

    required = {"asset_type", "description"}
    missing = required - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns: {sorted(missing)}",
        )
    if len(df) == 0:
        raise HTTPException(status_code=400, detail="CSV contains 0 data rows.")
    if len(df) > 100:
        raise HTTPException(status_code=400, detail="Batch CSV limited to 100 rows per request.")

    agent = get_agent()
    results: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        asset = str(row["asset_type"]).strip().lower()
        desc = str(row["description"]).strip()
        if asset not in ALLOWED_ASSET_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Row {idx + 1} has invalid asset_type '{asset}'. Allowed: {ALLOWED_ASSET_TYPES}",
            )
        if len(desc) < 5:
            raise HTTPException(
                status_code=400,
                detail=f"Row {idx + 1} description must be at least 5 characters.",
            )
        tid = str(row["ticket_id"]) if "ticket_id" in df.columns and pd.notna(row["ticket_id"]) else f"CSV-{idx + 1}"
        results.append(agent.run(description=desc, asset_type=asset, ticket_id=tid))

    return {"count": len(results), "results": results}


# =============================================================================
# ENDPOINT 8: Offline Metrics & Cross-Validation Results
# =============================================================================
@app.get("/api/metrics")
def get_metrics() -> dict[str, Any]:
    """
    HTTP Method: GET /api/metrics
    Purpose: Serves the real pre-computed 5-fold cross-validation metrics, model comparisons,
             and confusion matrices from docs/evaluation_results.json.
    """
    eval_path = resolve_eval_path()
    if not eval_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Evaluation results not found. Run 'python -m backend.evaluate' first.",
        )
    return json.loads(eval_path.read_text(encoding="utf-8"))


# =============================================================================
# ENDPOINT 9: PDF Report Generation & Download
# =============================================================================
@app.post("/api/reports/ticket-pdf")
def create_ticket_pdf(payload: dict[str, Any]) -> Response:
    """
    HTTP Method: POST /api/reports/ticket-pdf
    Purpose: Generates and downloads an official 5-page enterprise PDF report
             from the current ticket triage result.
    Input: Triage result dictionary.
    Output: Binary application/pdf stream with Content-Disposition attachment header.
    """
    if not payload or not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="Valid ticket triage result dictionary is required.",
        )

    # Sanitize ticket ID for clean filename
    raw_tid = str(payload.get("ticket_id") or "ADHOC").strip()
    safe_tid = re.sub(r"[^A-Za-z0-9_-]", "_", raw_tid)[:30] or "TICKET"
    date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    filename = f"Maintenance_Report_{safe_tid}_{date_str}.pdf"

    try:
        pdf_bytes = generate_maintenance_report_pdf(payload)
    except Exception as exc:
        logger.exception("Failed to generate PDF report: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate maintenance report PDF: {exc}",
        ) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
