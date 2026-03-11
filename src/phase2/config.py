from __future__ import annotations

"""
Configuration for Phase 2 (Groq-backed RAG-only assistant).

Loads environment variables from a .env file at project root if present.
Expected keys:
- GROQ_API_KEY
- (optional) GROQ_MODEL
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# Load .env from project root (one level above src/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Fallback: allow default dotenv search if needed
    load_dotenv()


GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Default Groq chat model.
# The earlier `llama3-8b-8192` model has been decommissioned; use a current one.
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# Number of chunks to retrieve from the Phase 1 index.
TOP_K = 5


