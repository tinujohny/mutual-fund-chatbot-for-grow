"""
Phase 3 - Scheduler / refresh pipeline.

This package contains utilities to:
- Re-crawl Groww public pages used in Phase 1.
- Rebuild the Phase 1 embeddings / TF-IDF index.
- Optionally run a small regression-style evaluation over Phase 2
  to ensure nothing broke after a refresh.
"""

