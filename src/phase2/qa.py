from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from groq import Groq

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
    Call Groq chat completion API with strict RAG-only instructions.
    """
    if not GROQ_API_KEY:
        # Fail fast with a clear message if key is not configured.
        raise RuntimeError("GROQ_API_KEY is not set in the environment.")

    client = Groq(api_key=GROQ_API_KEY)

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
        {
            "role": "system",
            "content": f"Here is the ONLY context you may use, from Groww:\n\n{context}",
        },
    ]

    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.0,
        max_tokens=256,
    )
    content = completion.choices[0].message.content or ""
    return content.strip()


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

    # For factual intents, we must have context from the embeddings/index.
    if index is None:
        index = load_index()

    results = search(index, query, k=TOP_K)
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

    raw_answer = _call_groq(system_prompt=system_prompt, user_prompt=user_prompt, context=context)
    text = _truncate_to_three_sentences(raw_answer)

    return Answer(
        text=text,
        source_url=top_chunk.url,
        last_updated=latest,
        intent=Intent.MF_FACT,
        refused=False,
    )

