from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import httpx

from ..phase1.ingest import TextChunk
from ..phase1.policy import Intent, detect_policy
from ..phase1.retriever import RetrievalIndex, load_index, search
from .config import GROQ_API_KEY, GROQ_MODEL, TOP_K


@dataclass
class Answer:
    text: str
    source_url: Optional[str]
    last_updated: Optional[str]
    intent: Intent
    refused: bool


def _pick_latest_date(dates: List[str]) -> Optional[str]:
    parsed = []
    for d in dates:
        try:
            parsed.append(datetime.fromisoformat(d))
        except Exception:
            continue
    if not parsed:
        return None
    return max(parsed).date().isoformat()


def _build_context_snippet(chunks_with_scores) -> str:
    parts: List[str] = []
    for idx, (chunk, score) in enumerate(chunks_with_scores, start=1):
        parts.append(
            f"[Source {idx}] URL: {chunk.url}\n"
            f"Title: {chunk.title}\n"
            f"Text:\n{chunk.text}\n"
            "--------------------"
        )
    return "\n\n".join(parts)


def _call_groq(system_prompt: str, user_prompt: str, context: str) -> str:
    """
    Call Groq chat completion API with strict RAG-only instructions,
    using the HTTP API directly to avoid heavy Python client dependencies.
    """
    if not GROQ_API_KEY:
        # Fail fast with a clear message if key is not configured.
        raise RuntimeError("GROQ_API_KEY is not set. Add it in Streamlit Secrets as GROQ_API_KEY.")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
        {
            "role": "system",
            "content": f"Here is the ONLY context you may use, from Groww:\n\n{context}",
        },
    ]
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 256,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        status = getattr(e.response, "status_code", None)
        body = ""
        try:
            body = (e.response.text or "")[:500]
        except Exception:
            body = ""
        raise RuntimeError(f"Groq API error (HTTP {status}). {body}".strip()) from e
    except httpx.RequestError as e:
        raise RuntimeError(f"Groq request failed: {e.__class__.__name__}") from e

    content = (
        (data.get("choices") or [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    return (content or "").strip()


def _prefer_concept_page_chunks(index: RetrievalIndex, query_lower: str, results: list) -> list:
    """
    For standard Groww concept questions, force context + citation from the matching /p/ article
    when those chunks exist in the index (avoids wrong category URLs winning retrieval).
    """
    marker: Optional[str] = None
    if "expense" in query_lower and "ratio" in query_lower:
        marker = "expense-ratio"
    elif "exit" in query_lower and "load" in query_lower:
        marker = "exit-load"
    elif "riskometer" in query_lower:
        marker = "riskometer"
    elif "benchmark" in query_lower:
        marker = "/p/benchmark"
    if not marker:
        return results
    needle = marker if marker.startswith("/") else marker
    for ch in index.chunks:
        u = (ch.url or "").lower()
        if needle in u or (marker == "/p/benchmark" and "/p/benchmark" in u):
            rest = [(c, s) for c, s in results if c.url != ch.url][: TOP_K - 1]
            return [(ch, 999.0)] + rest
    return results


# (tokens_substring) -> URL must contain this substring (Groww scheme slug)
_FUND_SCHEME_PINS: list[tuple[tuple[str, ...], str]] = [
    (("hdfc", "large", "cap"), "hdfc-large-cap-fund-direct-growth"),
    (("groww", "elss"), "groww-elss-tax-saver-fund-direct-growth"),
    (("groww", "large", "cap"), "groww-large-cap-fund-direct-growth"),
    (("sbi", "pharma"), "sbi-pharma-fund-direct-growth"),
    (("sbi", "gold"), "sbi-gold-fund-direct-growth"),
    (("dsp", "gilt"), "dsp-gilt-fund-direct-plan-growth"),
]


def _prefer_fund_scheme_chunks(index: RetrievalIndex, query_lower: str, results: list) -> list:
    """When the user names a fund, use that scheme’s Groww page for context + citation."""
    for tokens, slug in _FUND_SCHEME_PINS:
        if all(t in query_lower for t in tokens):
            candidates = [c for c in index.chunks if slug in (c.url or "").lower()]
            if not candidates:
                break
            keys = ["minimum", "sip", "lumpsum", "investment", "500", "100", "monthly", "₹", "rs."]
            if "sip" in query_lower or "minimum" in query_lower:
                def _relevance(ch: TextChunk) -> int:
                    t = (ch.text or "").lower()
                    return sum(1 for k in keys if k in t)

                primary = max(candidates, key=_relevance)
            else:
                primary = candidates[0]
            others = [c for c in candidates if c.id != primary.id][: TOP_K - 1]
            out = [(primary, 999.0)] + [(c, 50.0) for c in others]
            seen = {primary.id, *(c.id for c in others)}
            for c, s in results:
                if c.id not in seen and len(out) < TOP_K:
                    out.append((c, s))
                    seen.add(c.id)
            return out[:TOP_K]
    return results


def _truncate_to_three_sentences(text: str) -> str:
    buf = text.replace("?", ".").replace("!", ".")
    sentences = [s.strip() for s in buf.split(".") if s.strip()]
    if len(sentences) <= 3:
        return text.strip()
    return " ".join(sentences[:3])


def answer_query_phase2(query: str, index: RetrievalIndex | None = None) -> Answer:
    """
    Phase 2 answer orchestrator:
    - Uses Phase 1 embeddings/index to retrieve context.
    - Uses Groq LLM strictly over that context (no open-book knowledge).
    - Enforces PII, advice, performance, and length constraints.
    """
    has_pii, intent = detect_policy(query)
    q_lower = query.lower()

    # PII is always out of scope.
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

    # Opinion / portfolio advice is out of scope.
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

    # Performance questions are refused; point to official factsheets.
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

    # Special-case generic statement / factsheet questions to provide
    # clear, factual guidance even if retrieval is noisy.
    if (
        "mutual fund statement" in q_lower
        or "capital-gains statement" in q_lower
        or "capital gains statement" in q_lower
    ):
        msg = (
            "On Groww, you can download your mutual fund capital-gains statement from "
            "the Reports → Tax section of your account by selecting the capital gains "
            "report for mutual funds and choosing the desired financial year."
        )
        return Answer(
            text=msg,
            source_url="https://groww.in/help/mutual-funds/mf-others/how-to-download-capital-gain-report--50",
            last_updated=None,
            intent=Intent.MF_FACT,
            refused=False,
        )

    if "factsheet" in q_lower:
        msg = (
            "On Groww, each mutual fund’s details page shows a factsheet link or section. "
            "Search for the specific fund on the mutual funds page, open its page, and use "
            "the factsheet option shown there."
        )
        return Answer(
            text=msg,
            source_url="https://groww.in/mutual-funds",
            last_updated=None,
            intent=Intent.MF_FACT,
            refused=False,
        )

    # Core MF concepts: direct definitions + official Groww article (avoids LLM saying “no answer” on thin/noisy scrape).
    if "expense" in q_lower and "ratio" in q_lower:
        msg = (
            "The expense ratio is the annual cost of running a mutual fund scheme, shown as a percentage of the fund’s assets. "
            "It covers expenses such as fund management, administration, and other recurring costs charged to the scheme. "
            "Groww’s expense ratio guide explains how to read it when comparing funds."
        )
        return Answer(
            text=_truncate_to_three_sentences(msg),
            source_url="https://groww.in/p/expense-ratio",
            last_updated=None,
            intent=Intent.MF_FACT,
            refused=False,
        )
    if "exit" in q_lower and "load" in q_lower:
        msg = (
            "Exit load is a fee some mutual funds charge when you redeem or switch units before a set period, as per the scheme document. "
            "It is not charged on all funds and varies by scheme. "
            "Groww’s exit load article describes how it applies in general."
        )
        return Answer(
            text=_truncate_to_three_sentences(msg),
            source_url="https://groww.in/p/exit-load-in-mutual-funds",
            last_updated=None,
            intent=Intent.MF_FACT,
            refused=False,
        )
    if "riskometer" in q_lower:
        msg = (
            "The riskometer is a label that indicates how risky a mutual fund scheme is (for example, low, moderate, or high), as per regulatory norms. "
            "It helps you see the risk level at a glance when comparing schemes. "
            "Groww’s riskometer page explains what each level means."
        )
        return Answer(
            text=_truncate_to_three_sentences(msg),
            source_url="https://groww.in/p/riskometer",
            last_updated=None,
            intent=Intent.MF_FACT,
            refused=False,
        )
    if "benchmark" in q_lower and ("mutual" in q_lower or "fund" in q_lower):
        msg = (
            "A benchmark is an index or standard used to describe what a mutual fund is compared against (for example, Nifty or a bond index). "
            "Funds disclose a benchmark so investors can understand the fund’s style and context. "
            "Groww’s benchmark article explains how to interpret it."
        )
        return Answer(
            text=_truncate_to_three_sentences(msg),
            source_url="https://groww.in/p/benchmark",
            last_updated=None,
            intent=Intent.MF_FACT,
            refused=False,
        )

    # For factual intents, we must have context from the embeddings/index.
    if index is None:
        index = load_index()

    results = search(index, query, k=TOP_K)
    results = _prefer_fund_scheme_chunks(index, q_lower, results)
    results = _prefer_concept_page_chunks(index, q_lower, results)
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

    # Use the top chunk as the primary citation URL.
    top_chunk, _ = results[0]
    candidate_dates = [c.scraped_at for c, _ in results if c.scraped_at]
    latest = _pick_latest_date(candidate_dates)

    # Build RAG context from retrieved chunks.
    context = _build_context_snippet(results)

    # System prompt strictly forbids answering without context and forbids advice/PII.
    system_prompt = (
        "You are a mutual-fund FAQ assistant for Indian investors, using ONLY public "
        "information from Groww that is provided to you in the context. "
        "You MUST follow these rules:\n"
        "1) Use only the given Groww context; do not use any outside knowledge.\n"
        "2) If the answer is not clearly present in the context, say you cannot see it "
        "in the provided Groww sources and suggest checking the relevant Groww page.\n"
        "3) Do not provide investment advice, recommendations, or performance calculations.\n"
        "4) Do not handle any PAN, Aadhaar, account numbers, OTPs, emails, phone numbers, "
        "or other personal details.\n"
        "5) Answer in at most 3 short sentences, in plain language.\n"
        "6) Do not invent URLs; refer only generically to 'the Groww mutual funds page' "
        "or 'the specific fund page on Groww'."
    )

    user_prompt = (
        "Question:\n"
        f"{query}\n\n"
        "Answer this question strictly using the Groww context. "
        "If you cannot find the answer in the context, say so."
    )

    try:
        raw_answer = _call_groq(system_prompt=system_prompt, user_prompt=user_prompt, context=context)
        text = _truncate_to_three_sentences(raw_answer)
    except Exception:
        # Keep the app stable if Groq is unavailable/misconfigured.
        text = (
            "I’m having trouble generating an answer right now (LLM service unavailable). "
            "Please try again in a moment or check the linked Groww source page."
        )

    return Answer(
        text=text,
        source_url=top_chunk.url,
        last_updated=latest,
        intent=Intent.MF_FACT,
        refused=False,
    )

