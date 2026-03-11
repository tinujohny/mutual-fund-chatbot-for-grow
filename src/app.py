from __future__ import annotations

"""
Top-level FastAPI app entrypoint.

By default this exposes the Phase 2 Groq-backed RAG-only app so you can keep
using `uvicorn src.app:app --reload`.

Phase 1 app is still available under `src.phase1.app` if you want to run it
directly.
"""

from .phase2.app import app  # noqa: F401

