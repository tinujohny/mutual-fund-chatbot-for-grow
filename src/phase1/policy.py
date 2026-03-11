from __future__ import annotations

import re
from enum import Enum
from typing import Tuple


class Intent(str, Enum):
    MF_FACT = "mf_fact"
    ADVICE_PORTFOLIO = "advice_portfolio"
    PERFORMANCE = "performance"
    OUT_OF_SCOPE = "out_of_scope"


PII_PATTERNS = [
    re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),  # PAN-like
    re.compile(r"\b\d{12}\b"),  # Aadhaar-like
    re.compile(r"\b\d{10}\b"),  # phone-like
    re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),  # email
]


def contains_pii(text: str) -> bool:
    lowered = text.lower()
    if any(term in lowered for term in ["account number", "demat", "otp"]):
        return True
    return any(p.search(text) for p in PII_PATTERNS)


def classify_intent(query: str) -> Intent:
    q = query.lower()

    # Advice / portfolio questions
    advice_keywords = [
        "should i buy",
        "should i sell",
        "which fund is best",
        "recommend",
        "suggest fund",
        "which mutual fund",
        "where should i invest",
        "what should i invest in",
        "is this good fund",
    ]
    if any(kw in q for kw in advice_keywords):
        return Intent.ADVICE_PORTFOLIO

    # Performance / returns
    perf_keywords = [
        "returns",
        "cagr",
        "xirr",
        "performance",
        "highest return",
        "more return",
        "compare",
    ]
    if any(kw in q for kw in perf_keywords):
        return Intent.PERFORMANCE

    # Very simple MF factual heuristics
    fact_keywords = [
        "expense ratio",
        "exit load",
        "minimum sip",
        "min sip",
        "sip amount",
        "riskometer",
        "benchmark",
        "elss",
        "lock-in",
        "capital-gains statement",
        "capital gains statement",
        "tax saving",
        "what is sip",
        "how to invest in mutual funds",
    ]
    if any(kw in q for kw in fact_keywords):
        return Intent.MF_FACT

    # Default: treat as MF_FACT but may fail at retrieval
    return Intent.MF_FACT


def detect_policy(query: str) -> Tuple[bool, Intent]:
    """
    Returns (has_pii, intent).
    """
    return contains_pii(query), classify_intent(query)

