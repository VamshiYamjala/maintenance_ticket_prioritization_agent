"""
===============================================================================
FILE: main.py
===============================================================================
1. WHAT THIS FILE DOES:
   Root application entrypoint for Vercel Serverless Functions and local ASGI
   runners (uvicorn). It configures the Python search path (`sys.path`) and
   exports the FastAPI ASGI `app` object directly at the root module level.

2. WHY THIS FILE IS NEEDED:
   Vercel's zero-configuration FastAPI runtime requires an entrypoint string
   such as `main:app` specified in `pyproject.toml` ([tool.vercel] entrypoint = "main:app").
   Having this at the root guarantees that Vercel finds the ASGI callable instantly
   without path confusion.

3. WHICH OTHER FILES USE IT:
   - pyproject.toml: Defines `entrypoint = "main:app"`.
   - Vercel CLI / Serverless Runner: Imports `app` from `main.py` on cold starts.
   - Local Uvicorn: Can be launched via `uvicorn main:app --reload`.

4. WHAT INPUT IT RECEIVES:
   - ASGI HTTP connection events from the web server runtime.

5. WHAT OUTPUT IT PRODUCES:
   - Passes control to `backend.app:app` to generate HTTP responses.
===============================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app import app

__all__ = ["app"]
