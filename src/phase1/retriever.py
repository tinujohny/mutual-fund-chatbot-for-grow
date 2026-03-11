from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .ingest import TextChunk, load_chunks


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

INDEX_PATH = DATA_DIR / "tfidf_index.pkl"


@dataclass
class RetrievalIndex:
    vectorizer: TfidfVectorizer
    matrix: np.ndarray
    chunks: List[TextChunk]


def build_index() -> RetrievalIndex:
    chunks = load_chunks()
    texts = [c.text for c in chunks]
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(texts)

    index = RetrievalIndex(vectorizer=vectorizer, matrix=matrix, chunks=chunks)
    with INDEX_PATH.open("wb") as f:
        pickle.dump(index, f)

    return index


def load_index() -> RetrievalIndex:
    """
    Load the TF-IDF index from disk.

    If the pickled format is incompatible (e.g. due to module path changes) or
    the file is missing/corrupted, we automatically rebuild the index to avoid
    startup failures like:
        AttributeError: Can't get attribute 'RetrievalIndex' on module '__main__'
    """
    if not INDEX_PATH.exists():
        return build_index()
    try:
        with INDEX_PATH.open("rb") as f:
            return pickle.load(f)
    except Exception:
        # Fallback: rebuild index from the latest chunks.
        return build_index()


def search(index: RetrievalIndex, query: str, k: int = 5) -> List[Tuple[TextChunk, float]]:
    """Return top-k chunks with similarity scores."""
    q_vec = index.vectorizer.transform([query])
    sims = cosine_similarity(q_vec, index.matrix)[0]
    idxs = np.argsort(-sims)[:k]
    results: List[Tuple[TextChunk, float]] = []
    for i in idxs:
        results.append((index.chunks[int(i)], float(sims[int(i)])))
    return results


if __name__ == "__main__":
    idx = build_index()
    print(f"Built TF-IDF index with {len(idx.chunks)} chunks at {INDEX_PATH}")

