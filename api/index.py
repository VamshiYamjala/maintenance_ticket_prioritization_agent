"""
===============================================================================
FILE: api/index.py
===============================================================================
Vercel serverless function entrypoint.
Exports the ASGI `app` object from `backend.app`.
===============================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app import app

__all__ = ["app"]
