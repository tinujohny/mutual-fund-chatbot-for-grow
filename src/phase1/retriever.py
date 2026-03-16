from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .ingest import TextChunk, load_chunks


@dataclass
class RetrievalIndex:
    """
    Lightweight retrieval index without external ML dependencies.
    Just holds the list of chunks; search uses simple keyword scoring.
    """

    chunks: List[TextChunk]


def build_index() -> RetrievalIndex:
    """Build a simple in-memory index over all chunks."""
    chunks = load_chunks()
    return RetrievalIndex(chunks=chunks)


def load_index() -> RetrievalIndex:
    """
    Load the retrieval index.

    For simplicity on Streamlit and other constrained environments, we rebuild
    the index from chunks each time this is called. Callers should cache this
    (e.g. via st.cache_resource or FastAPI startup) to avoid repeated work.
    """
    return build_index()


def _score_chunk(text: str, query: str) -> int:
    """
    Very simple relevance score: counts how many query tokens appear
    in the chunk text (case-insensitive).
    """
    q_tokens = [t for t in query.lower().split() if len(t) > 2]
    if not q_tokens:
        return 0
    t_lower = text.lower()
    score = 0
    for tok in q_tokens:
        if tok in t_lower:
            score += 1
    return score


def search(index: RetrievalIndex, query: str, k: int = 5) -> List[Tuple[TextChunk, float]]:
    """
    Return top-k chunks with simple keyword-based scores.
    This avoids heavy dependencies like scikit-learn and works well enough
    for a few thousand chunks.
    """
    scores: List[Tuple[int, TextChunk]] = []
    for ch in index.chunks:
        s = _score_chunk(ch.text, query)
        if s > 0:
            scores.append((s, ch))

    # Sort by descending score; use stable order as tiebreaker.
    scores.sort(key=lambda pair: -pair[0])
    top = scores[:k]
    return [(ch, float(s)) for s, ch in top]

