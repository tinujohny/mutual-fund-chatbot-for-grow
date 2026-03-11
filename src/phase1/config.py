from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import List


@dataclass(frozen=True)
class CrawlTarget:
    url: str
    label: str


# Phase 1: start with a small, explicit set of Groww public pages.
CRAWL_TARGETS: List[CrawlTarget] = [
    CrawlTarget(
        url="https://groww.in/mutual-funds",
        label="mutual-funds-overview",
    ),
    # Core concept / FAQ pages to support common factual questions.
    CrawlTarget(
        url="https://groww.in/p/expense-ratio",
        label="expense-ratio-concept",
    ),
    CrawlTarget(
        url="https://groww.in/p/exit-load-in-mutual-funds",
        label="exit-load-concept",
    ),
    CrawlTarget(
        url="https://groww.in/p/riskometer",
        label="riskometer-concept",
    ),
    CrawlTarget(
        url="https://groww.in/p/benchmark",
        label="benchmark-concept",
    ),
    CrawlTarget(
        url="https://groww.in/blog/mutual-funds-minimum-investment-100-very-low-minimum-amount",
        label="minimum-sip-concept",
    ),
    CrawlTarget(
        url="https://groww.in/blog/3-steps-follow-elss-lock-period-ends",
        label="elss-lock-in",
    ),
    CrawlTarget(
        url="https://groww.in/help/mutual-funds/mf-others/how-to-download-capital-gain-report--50",
        label="capital-gains-download-help",
    ),
    # Sample specific fund page to support fund-level queries such as
    # minimum SIP, exit load, expense ratio, riskometer, benchmark, etc.
    CrawlTarget(
        url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        label="hdfc-large-cap-direct-growth",
    ),
    # Additional representative fund pages to support fund-level queries
    # (expense ratio, exit load, min SIP, riskometer, benchmark, etc.).
    CrawlTarget(
        url="https://groww.in/mutual-funds/groww-elss-tax-saver-fund-direct-growth",
        label="groww-elss-tax-saver-direct-growth",
    ),
    CrawlTarget(
        url="https://groww.in/mutual-funds/groww-large-cap-fund-direct-growth",
        label="groww-large-cap-direct-growth",
    ),
    CrawlTarget(
        url="https://groww.in/mutual-funds/groww-multi-asset-allocation-fund-direct-growth",
        label="groww-multi-asset-allocation-direct-growth",
    ),
    CrawlTarget(
        url="https://groww.in/mutual-funds/groww-banking-financial-services-fund-direct-growth",
        label="groww-banking-financial-services-direct-growth",
    ),
    CrawlTarget(
        url="https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
        label="hdfc-gold-etf-fof-direct-growth",
    ),
    CrawlTarget(
        url="https://groww.in/mutual-funds/sbi-gold-fund-direct-growth",
        label="sbi-gold-fund-direct-growth",
    ),
    CrawlTarget(
        url="https://groww.in/mutual-funds/sbi-pharma-fund-direct-growth",
        label="sbi-pharma-fund-direct-growth",
    ),
    CrawlTarget(
        url="https://groww.in/mutual-funds/dsp-gilt-fund-direct-plan-growth",
        label="dsp-gilt-fund-direct-growth",
    ),
    CrawlTarget(
        url="https://groww.in/mutual-funds/jm-money-market-fund-direct-growth",
        label="jm-money-market-direct-growth",
    ),
    CrawlTarget(
        url="https://groww.in/mutual-funds/qsif-hybrid-long-short-fund-direct-plan-growth",
        label="qsif-hybrid-long-short-direct-growth",
    ),
]


CHUNK_SIZE_CHARS = 1500
CHUNK_OVERLAP_CHARS = 200


# Timeout for HTTP requests to Groww (seconds)
HTTP_TIMEOUT = 20.0


# How long we consider data to be "fresh" for informational purposes.
FRESHNESS_WINDOW = timedelta(days=7)


# Phase 3 / auto-discovery:
# Maximum number of additional Groww URLs to auto-discover from seed pages
# (e.g., specific mutual fund factsheet pages, MF knowledge-centre articles).
AUTO_DISCOVER_MAX_URLS = 15

