"""
Phase 1 - Core RAG FAQ assistant using public Groww mutual-fund pages.

This package contains:
- config: crawl targets and constants
- ingest: crawl Groww and build text chunks
- retriever: TF-IDF index over chunks
- policy: simple PII and intent detection
- qa: high-level question answering with constraints
- app: FastAPI app exposing a tiny UI and /ask endpoint
"""

