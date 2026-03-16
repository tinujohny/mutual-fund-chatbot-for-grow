from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Set

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from .config import (
    AUTO_DISCOVER_MAX_URLS,
    CHUNK_OVERLAP_CHARS,
    CHUNK_SIZE_CHARS,
    CRAWL_TARGETS,
    HTTP_TIMEOUT,
)


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CHUNKS_PATH = DATA_DIR / "chunks.jsonl"


@dataclass
class TextChunk:
    id: str
    url: str
    label: str
    title: str
    text: str
    scraped_at: str  # ISO8601


def _fetch_html(url: str) -> str:
    """Fetch a page from Groww using httpx."""
    with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def _extract_main_text(html: str) -> tuple[str, str]:
    """
    Extract a reasonably clean text representation from Groww HTML.

    Returns (title, text).
    """
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Heuristic: remove nav/footer/script/style to avoid noise.
    for selector in ["nav", "footer", "script", "style"]:
        for tag in soup.find_all(selector):
            tag.decompose()

    body = soup.body or soup
    text = body.get_text(separator="\n", strip=True)

    # Collapse excessive newlines.
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return title, "\n".join(lines)


def _discover_additional_groww_links(html: str, base_url: str) -> List[str]:
    """
    Very lightweight auto-discovery:
    - Finds a limited number of additional Groww URLs from the seed page.
    - Prioritises:
        * /mutual-funds/* fund/factsheet pages
        * Links whose text suggests MF knowledge (taxation, SIP, ELSS, etc.)
    """
    soup = BeautifulSoup(html, "html.parser")
    discovered: List[str] = []
    seen: Set[str] = set()

    def add_url(u: str) -> None:
        if u in seen:
            return
        # Only keep groww.in links.
        parsed = urlparse(u)
        if parsed.netloc and "groww.in" not in parsed.netloc:
            return
        seen.add(u)
        discovered.append(u)

    # First pass: mutual-fund detail pages under /mutual-funds/
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        if "/mutual-funds/" in parsed.path and parsed.path != "/mutual-funds":
            add_url(full)
        if len(discovered) >= AUTO_DISCOVER_MAX_URLS:
            break

    # Second pass: MF knowledge / FAQ links (how to invest, SIP, taxation, ELSS, capital gains).
    if len(discovered) < AUTO_DISCOVER_MAX_URLS:
        keywords = ["how to invest", "sip", "taxation", "elss", "capital-gains", "capital gains"]
        for a in soup.find_all("a", href=True):
            text = (a.get_text(strip=True) or "").lower()
            if not text:
                continue
            if not any(kw in text for kw in keywords):
                continue
            href = a["href"]
            full = urljoin(base_url, href)
            add_url(full)
            if len(discovered) >= AUTO_DISCOVER_MAX_URLS:
                break

    return discovered


def _chunk_text(text: str, base_id: str, url: str, label: str, title: str, scraped_at: str) -> List[TextChunk]:
    chunks: List[TextChunk] = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(len(text), start + CHUNK_SIZE_CHARS)
        chunk_text = text[start:end]
        chunk_id = f"{base_id}-{idx}"
        chunks.append(
            TextChunk(
                id=chunk_id,
                url=url,
                label=label,
                title=title,
                text=chunk_text,
                scraped_at=scraped_at,
            )
        )
        if end == len(text):
            break
        start = end - CHUNK_OVERLAP_CHARS
        idx += 1
    return chunks


def crawl_and_write_chunks(target_urls: Iterable[str] | None = None) -> List[TextChunk]:
    """
    Crawl the configured Groww pages and write chunks.jsonl.
    Returns the list of chunks in memory as well.
    """
    DATA_DIR.mkdir(exist_ok=True)

    targets = CRAWL_TARGETS
    if target_urls is not None:
        url_set = set(target_urls)
        targets = [t for t in CRAWL_TARGETS if t.url in url_set]

    all_chunks: List[TextChunk] = []
    scraped_at = datetime.now(timezone.utc).isoformat()

    visited_urls: Set[str] = set()

    # First, crawl the explicit seed targets.
    for t in targets:
        html = _fetch_html(t.url)
        visited_urls.add(t.url)
        title, text = _extract_main_text(html)
        base_id = t.label or t.url.replace("https://", "").replace("/", "_")
        chunks = _chunk_text(
            text=text,
            base_id=base_id,
            url=t.url,
            label=t.label,
            title=title,
            scraped_at=scraped_at,
        )
        all_chunks.extend(chunks)

        # Auto-discover a few more Groww links from this seed page.
        extra_links = _discover_additional_groww_links(html, t.url)
        for extra_url in extra_links:
            if extra_url in visited_urls:
                continue
            visited_urls.add(extra_url)
            try:
                extra_html = _fetch_html(extra_url)
            except Exception:
                continue
            extra_title, extra_text = _extract_main_text(extra_html)
            base_id_extra = extra_url.replace("https://", "").replace("/", "_")
            extra_chunks = _chunk_text(
                text=extra_text,
                base_id=base_id_extra,
                url=extra_url,
                label="auto-discovered",
                title=extra_title,
                scraped_at=scraped_at,
            )
            all_chunks.extend(extra_chunks)

    with CHUNKS_PATH.open("w", encoding="utf-8") as f:
        for ch in all_chunks:
            f.write(json.dumps(asdict(ch), ensure_ascii=False) + "\n")

    return all_chunks


def load_chunks() -> List[TextChunk]:
    if not CHUNKS_PATH.exists():
        # On first run (e.g. Streamlit Cloud), build the knowledge base once.
        crawl_and_write_chunks()
    chunks: List[TextChunk] = []
    with CHUNKS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            raw = json.loads(line)
            chunks.append(TextChunk(**raw))
    return chunks


if __name__ == "__main__":
    crawl_and_write_chunks()
    print(f"Wrote chunks to {CHUNKS_PATH}")

