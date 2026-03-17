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


def _concept_page_boost(query_lower: str, url: str) -> int:
    """
    Strong boosts for Groww /p/ concept pages when the question is clearly about that topic.
    Stops generic category URLs (e.g. multi-cap-funds) from winning over the right article.
    """
    u = url.lower()
    b = 0
    if "expense" in query_lower and "ratio" in query_lower and "expense-ratio" in u:
        b += 80
    if "exit" in query_lower and "load" in query_lower and "exit-load" in u:
        b += 80
    if "riskometer" in query_lower and "riskometer" in u:
        b += 80
    if "benchmark" in query_lower and "/p/benchmark" in u:
        b += 80
    if ("elss" in query_lower and ("lock" in query_lower or "lock-in" in query_lower or "lockin" in query_lower)) and (
        "elss" in u or "lock" in u
    ):
        b += 60
    if ("minimum" in query_lower or "min " in query_lower) and "sip" in query_lower:
        if "minimum-investment" in u or "start-sip" in u or "sip-systematic" in u or "how-to-start-a-sip" in u:
            b += 70
    if ("capital" in query_lower and "gain" in query_lower) or "capital-gains" in query_lower:
        if "capital-gain" in u or "capital_gain" in u:
            b += 80
    return b


def _is_concept_style_query(query_lower: str) -> bool:
    return any(
        phrase in query_lower
        for phrase in (
            "expense ratio",
            "exit load",
            "riskometer",
            "benchmark",
            "elss lock",
            "minimum sip",
            "capital gain",
            "capital-gains",
        )
    )


def _score_chunk(ch: TextChunk, query: str) -> int:
    """
    Lightweight relevance score without ML deps.

    Key idea: prefer chunks whose *URL/title* match the query, so fund-specific
    questions cite the correct Groww fund page (slug match), not a category page.
    """
    q_lower = (query or "").lower()
    q_tokens = [t for t in _tokens(query) if len(t) > 2]
    if not q_tokens:
        return 0

    text = (ch.text or "").lower()
    title = (ch.title or "").lower()
    url = (ch.url or "").lower()

    score = 0

    # Concept questions must hit the right Groww article, not a fund category listing.
    score += _concept_page_boost(q_lower, url)
    if _is_concept_style_query(q_lower):
        if "/p/" in url:
            score += 15
        # Penalize generic MF category paths (equity-funds/multi-cap etc.) for concept Qs
        if "/mutual-funds/" in url and "/p/" not in url:
            tail = url.split("/mutual-funds/")[-1].split("?")[0]
            is_scheme_page = "fund-direct" in tail or "direct-growth" in tail or "direct-plan" in tail
            if not is_scheme_page and any(
                x in url for x in ("equity-funds", "debt-funds", "hybrid-funds", "multi-cap", "large-cap", "mid-cap", "small-cap")
            ):
                score -= 35

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

    # Prefer Groww mutual fund *scheme* detail pages when query names a specific fund (not pure concept).
    if not _is_concept_style_query(q_lower):
        if any(t in q_tokens for t in ["sip", "hdfc", "sbi", "groww", "axis", "icici"]):
            tail = url.split("/mutual-funds/")[-1] if "/mutual-funds/" in url else ""
            if tail and ("fund-direct" in tail or "direct-growth" in tail):
                score += 4

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

