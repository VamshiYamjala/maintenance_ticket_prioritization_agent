"""
FastAPI application for the Maintenance Ticket Prioritization Agent.

Serves both the REST API (/api/*) and the single-page frontend (/) so Railway
runs a single service.
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("triage_api")

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_INDEX = BASE_DIR / "frontend" / "index.html"
EVAL_RESULTS_PATH = BASE_DIR / "docs" / "evaluation_results.json"


def resolve_frontend_path() -> Path:
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


_agent: TicketTriageAgent | None = None


def get_agent() -> TicketTriageAgent:
    global _agent
    if _agent is None:
        logger.info("Loading TicketTriageAgent from disk...")
        _agent = TicketTriageAgent.from_disk()
    return _agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_agent()
    logger.info("TicketTriageAgent ready.")
    yield


app = FastAPI(
    title="AI Agent for Maintenance Ticket Prioritization",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error while processing ticket triage."},
    )


@app.get("/")
@app.get("/index.html")
@app.get("/api/index.py")
def serve_frontend() -> FileResponse:
    target = resolve_frontend_path()
    if not target.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return FileResponse(target)


@app.get("/api/health")
def health() -> dict[str, Any]:
    agent = get_agent()
    eval_path = resolve_eval_path()
    return {
        "status": "ok",
        "model_loaded": agent.cat_pipeline is not None and agent.sev_pipeline is not None,
        "eval_results_available": eval_path.exists(),
    }


@app.get("/api/demo")
def demo() -> dict[str, Any]:
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


@app.post("/api/run")
def run_case(query: LegacyRunQuery) -> dict[str, Any]:
    """Starter-compatible endpoint; runs the full triage agent."""
    try:
        desc = query.resolved_description()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    agent = get_agent()
    result = agent.run(description=desc, asset_type=query.asset_type, ticket_id=query.ticket_id)
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


@app.post("/api/triage")
def triage_ticket(req: TriageRequest) -> dict[str, Any]:
    """Strict triage endpoint with full Pydantic validation."""
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


@app.post("/api/batch")
def triage_batch(req: BatchTriageRequest) -> dict[str, Any]:
    """Batch triage for a JSON list of tickets."""
    agent = get_agent()
    results = [
        agent.run(description=t.description, asset_type=t.asset_type, ticket_id=t.ticket_id)
        for t in req.tickets
    ]
    return {"count": len(results), "results": results}


@app.post("/api/batch-csv")
async def triage_batch_csv(file: UploadFile = File(...)) -> dict[str, Any]:
    """Batch triage for an uploaded CSV with columns: asset_type, description (optional ticket_id)."""
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


@app.get("/api/metrics")
def get_metrics() -> dict[str, Any]:
    eval_path = resolve_eval_path()
    if not eval_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Evaluation results not found. Run 'python -m backend.evaluate' first.",
        )
    return json.loads(eval_path.read_text(encoding="utf-8"))


@app.post("/api/reports/ticket-pdf")
def create_ticket_pdf(payload: dict[str, Any]) -> Response:
    """
    Generate and download a professional 5-page enterprise PDF report
    for the provided ticket triage result.
    """
    if not payload or not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="Valid ticket triage result dictionary is required.",
        )

    # Sanitize ticket ID for filename
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
