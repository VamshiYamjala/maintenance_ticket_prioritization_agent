"""
Root application entrypoint for Vercel and local runners.
Exposes the ASGI FastAPI application `app` directly at the repository root.
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
