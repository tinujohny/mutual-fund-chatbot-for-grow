from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from .policy import Intent, detect_policy
from .retriever import RetrievalIndex, load_index, search


@dataclass
class Answer:
    text: str
    source_url: str | None
    last_updated: str | None
    intent: Intent
    refused: bool


def _pick_latest_date(dates: List[str]) -> str | None:
    parsed = []
    for d in dates:
        try:
            parsed.append(datetime.fromisoformat(d))
        except Exception:
            continue
    if not parsed:
        return None
    return max(parsed).date().isoformat()


def _extract_relevant_sentences(text: str, query: str, max_sentences: int = 3) -> str:
    """
    Very lightweight relevance: keep up to max_sentences that contain
    any keyword from the query, otherwise fall back to the first few sentences.
    """
    sentences = []
    for sep in [".", "?", "!"]:
        text = text.replace(sep, ".")
    for raw in text.split("."):
        sent = raw.strip()
        if sent:
            sentences.append(sent)

    if not sentences:
        return ""

    q_tokens = [t for t in query.lower().split() if len(t) > 3]
    scored: List[tuple[int, str]] = []
    for s in sentences:
        score = 0
        s_low = s.lower()
        for t in q_tokens:
            if t in s_low:
                score += 1
        scored.append((score, s))

    scored.sort(key=lambda x: (-x[0], sentences.index(x[1])))
    top = [s for score, s in scored if score > 0][:max_sentences]
    if not top:
        top = sentences[:max_sentences]

    return ". ".join(top)


def answer_query(query: str, index: RetrievalIndex | None = None) -> Answer:
    has_pii, intent = detect_policy(query)

    if has_pii:
        msg = (
            "I’m a facts-only assistant and can’t process personal details like PAN, "
            "Aadhaar, account numbers, OTPs, emails, or phone numbers. "
            "Please remove them and ask again using only general questions."
        )
        return Answer(
            text=msg,
            source_url="https://groww.in/mutual-funds",
            last_updated=None,
            intent=intent,
            refused=True,
        )

    if intent == Intent.ADVICE_PORTFOLIO:
        msg = (
            "I’m a facts-only assistant and can’t provide investment advice or "
            "personalized recommendations. You can explore mutual fund basics and "
            "categories on Groww’s mutual funds page."
        )
        return Answer(
            text=msg,
            source_url="https://groww.in/mutual-funds",
            last_updated=None,
            intent=intent,
            refused=True,
        )

    if intent == Intent.PERFORMANCE:
        msg = (
            "I can’t calculate or compare mutual fund returns. For performance and "
            "historical returns, please refer to the official factsheet and "
            "performance section of the specific fund on Groww."
        )
        return Answer(
            text=msg,
            source_url="https://groww.in/mutual-funds",
            last_updated=None,
            intent=intent,
            refused=True,
        )

    if index is None:
        index = load_index()

    results = search(index, query, k=5)
    if not results:
        msg = (
            "I couldn’t find this information in the current public Groww sources. "
            "Please check the relevant mutual fund page or help section on Groww directly."
        )
        return Answer(
            text=msg,
            source_url="https://groww.in/mutual-funds",
            last_updated=None,
            intent=intent,
            refused=False,
        )

    # Take the top-ranked chunk as the main citation.
    top_chunk, _ = results[0]
    candidate_dates = [c.scraped_at for c, _ in results if c.scraped_at]
    latest = _pick_latest_date(candidate_dates)

    snippet = _extract_relevant_sentences(top_chunk.text, query, max_sentences=3)
    if not snippet:
        snippet = top_chunk.text[:400].strip()

    # Ensure the answer is at most 3 sentences by construction.
    text = snippet

    return Answer(
        text=text,
        source_url=top_chunk.url,
        last_updated=latest,
        intent=intent,
        refused=False,
    )

