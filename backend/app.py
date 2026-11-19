"""
===============================================================================
FILE: backend/app.py
===============================================================================
1. WHAT THIS FILE DOES:
   FastAPI web service exposing the REST API and serving the HTML user interface:
     - GET  /           : Serves the single-page application (frontend/index.html)
     - GET  /api/health : Readiness and health probe
     - GET  /api/demo   : Provides the 6 official assignment demonstration tickets
     - POST /api/run    : Primary triage endpoint (compatible with candidate_task.md)
     - POST /api/triage : Alias for triage requests

2. WHY THIS FILE IS NEEDED:
   Connects the web frontend and external callers to the modular Python triage pipeline.

3. ARCHITECTURE:
   Lightweight, non-blocking FastAPI ASGI app with in-memory TF-IDF + KNN fitting.
===============================================================================
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.schemas import TicketQuery, TriageResponse
from backend.triage import get_classifier, triage_ticket

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("ticket_api")

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_INDEX = BASE_DIR / "frontend" / "index.html"
DATA_PATH = BASE_DIR / "data" / "maintenance_tickets.csv"


def resolve_frontend_path() -> Path:
    """Resolve frontend/index.html across local development and cloud serverless paths."""
    candidates = [
        FRONTEND_INDEX,
        BASE_DIR / "frontend" / "index.html",
        Path.cwd() / "frontend" / "index.html",
        Path("/var/task/frontend/index.html"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return FRONTEND_INDEX


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to pre-fit ML classifier on startup."""
    logger.info("Initializing TF-IDF + KNN classifier in memory...")
    get_classifier()
    logger.info("Classifier ready for triage.")
    yield


app = FastAPI(
    title="Maintenance Ticket Prioritization Agent",
    description="Intelligent O&M Maintenance Ticket Triage & Routing Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
@app.get("/index.html")
@app.get("/api/index.py")
def serve_frontend() -> FileResponse:
    """Serve the single-page application interface."""
    path = resolve_frontend_path()
    if not path.exists():
        raise HTTPException(status_code=404, detail="frontend/index.html not found.")
    return FileResponse(path, media_type="text/html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Health check probe."""
    return {"status": "ok", "model": "TF-IDF + KNN (1-NN Cosine)", "samples": 6}


@app.get("/api/demo")
def get_demo_tickets() -> list[dict[str, Any]]:
    """
    Return all 6 canonical demo maintenance tickets from the original dataset.
    Used by the frontend to populate one-click demonstration buttons.
    """
    if not DATA_PATH.exists():
        return []
    df = pd.read_csv(DATA_PATH)
    return df.to_dict(orient="records")


@app.post("/api/run", response_model=TriageResponse)
@app.post("/api/triage", response_model=TriageResponse)
def run_triage(query: TicketQuery) -> dict[str, Any]:
    """
    Triage an incoming maintenance ticket.

    Accepts:
      {"text": "high bearing temperature in main gearbox..."}
      OR
      {"description": "...", "asset_type": "wind_turbine", "ticket_id": "T001"}

    Returns:
      Category, severity, escalation status, recommendations, and team routing.
    """
    result = triage_ticket(description=query.text, asset_type=query.asset_type)
    result["ticket_id"] = query.ticket_id
    return result
