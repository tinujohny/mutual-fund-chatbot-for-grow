#!/usr/bin/env python3
"""
Audit data/chunks.jsonl against Phase 1 CRAWL_TARGETS.

Run from project root:
  python3 scripts/audit_chunks.py

Shows: seed URLs missing from chunks, chunk counts per seed, non-Groww URLs.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data" / "chunks.jsonl"
sys.path.insert(0, str(ROOT))

from src.phase1.config import CRAWL_TARGETS  # noqa: E402


def norm_url(u: str) -> str:
    return unquote((u or "").strip()).rstrip("/").lower()


def main() -> None:
    if not CHUNKS.exists():
        print(f"Missing {CHUNKS} — run crawl first (python -m src.phase1.ingest).")
        sys.exit(1)

    url_counts: Counter[str] = Counter()
    all_norm: set[str] = set()
    bad_host: list[str] = []

    with CHUNKS.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            u = json.loads(line).get("url") or ""
            nu = norm_url(u)
            url_counts[u] += 1
            all_norm.add(nu)
            if u and "groww.in" not in u.lower():
                bad_host.append(u)

    seeds = [norm_url(t.url) for t in CRAWL_TARGETS]
    missing = [t for t in CRAWL_TARGETS if norm_url(t.url) not in all_norm]

    print("=== chunks.jsonl audit ===")
    print(f"Total chunks: {sum(url_counts.values())}")
    print(f"Unique URLs: {len(url_counts)}")
    print(f"Seed targets in config: {len(CRAWL_TARGETS)}")
    print()

    if missing:
        print("MISSING seed URLs (no chunk with this URL — re-run ingest or fix crawl):")
        for t in missing:
            print(f"  - {t.url}  ({t.label})")
        print()
    else:
        print("All seed URLs present in chunks.\n")

    print("Chunk count per seed target:")
    for t in CRAWL_TARGETS:
        n = sum(c for u, c in url_counts.items() if norm_url(u) == norm_url(t.url))
        flag = "OK" if n else "EMPTY"
        print(f"  [{flag}] {n:3d}  {t.url}")
    print()

    if bad_host:
        print("Non-Groww URLs (unexpected):")
        for u in sorted(set(bad_host))[:20]:
            print(f"  {u}")
        if len(set(bad_host)) > 20:
            print(f"  ... and {len(set(bad_host)) - 20} more")
    else:
        print("All chunk URLs are on groww.in.")

    # Quick FAQ coverage hints
    hints = [
        ("expense-ratio", "/p/expense-ratio"),
        ("exit-load", "exit-load"),
        ("HDFC Large Cap scheme", "hdfc-large-cap-fund-direct-growth"),
        ("capital gains help", "capital-gain"),
        ("riskometer", "riskometer"),
    ]
    print("\nFAQ link checks (substring in any chunk URL):")
    for name, sub in hints:
        ok = any(sub in u.lower() for u in url_counts)
        print(f"  [{'OK' if ok else 'MISS'}] {name}: contains {sub!r}")


if __name__ == "__main__":
    main()
