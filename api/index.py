"""
===============================================================================
FILE: api/index.py
===============================================================================
1. WHAT THIS FILE DOES:
   Secondary Vercel Serverless Function entrypoint. Exposes the ASGI `app` object
   from inside the `api/` directory for Vercel environments that scan `api/*.py`.

2. WHY THIS FILE IS NEEDED:
   Provides backwards compatibility with legacy Vercel Python builders that
   look inside `api/index.py` while ensuring `sys.path` contains the repository
   root for absolute imports (`backend.*`).

3. WHICH OTHER FILES USE IT:
   - Vercel runtime fallback.

4. WHAT INPUT IT RECEIVES:
   - ASGI HTTP connection events.

5. WHAT OUTPUT IT PRODUCES:
   - Exports the ASGI `app` callable from `backend.app`.
===============================================================================
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
