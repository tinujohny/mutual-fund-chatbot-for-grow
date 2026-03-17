from __future__ import annotations

from dataclasses import dataclass
import re
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


_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> List[str]:
    return _WORD_RE.findall((s or "").lower())


def _score_chunk(ch: TextChunk, query: str) -> int:
    """
    Lightweight relevance score without ML deps.

    Key idea: prefer chunks whose *URL/title* match the query, so fund-specific
    questions cite the correct Groww fund page (slug match), not a category page.
    """
    q_tokens = [t for t in _tokens(query) if len(t) > 2]
    if not q_tokens:
        return 0

    text = (ch.text or "").lower()
    title = (ch.title or "").lower()
    url = (ch.url or "").lower()

    score = 0

    # Title and URL are strong signals for "correct citation".
    for tok in q_tokens:
        if tok in url:
            score += 5
        if tok in title:
            score += 3
        if tok in text:
            score += 1

    # Extra boost for matching fund slugs: "hdfc large cap" -> "hdfc-large-cap"
    q_slug = "-".join(q_tokens)
    if q_slug and q_slug in url:
        score += 12

    # Prefer Groww mutual fund detail pages when query mentions a fund.
    if any(t in q_tokens for t in ["fund", "mutual", "sip", "expense", "ratio", "exit", "load", "riskometer", "benchmark"]):
        if "/mutual-funds/" in url and "/mutual-funds" not in url.rstrip("/"):
            score += 2

    return score


def search(index: RetrievalIndex, query: str, k: int = 5) -> List[Tuple[TextChunk, float]]:
    """
    Return top-k chunks with simple keyword-based scores.
    This avoids heavy dependencies like scikit-learn and works well enough
    for a few thousand chunks.
    """
    scores: List[Tuple[int, TextChunk]] = []
    for ch in index.chunks:
        s = _score_chunk(ch, query)
        if s > 0:
            scores.append((s, ch))

    # Sort by descending score; use stable order as tiebreaker.
    scores.sort(key=lambda pair: -pair[0])
    top = scores[:k]
    return [(ch, float(s)) for s, ch in top]

