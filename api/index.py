"""
Vercel Serverless Function entrypoint for FastAPI.
Exposes the ASGI app instance directly for Vercel Python runtime.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app import app

__all__ = ["app"]
