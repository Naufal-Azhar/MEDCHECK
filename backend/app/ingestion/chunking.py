"""Deterministic text chunking for healthcare documents."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    content: str
    metadata: dict[str, object]


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(
    text: str,
    max_words: int = 180,
    overlap_words: int = 30,
) -> list[TextChunk]:
    """Split text into word-based overlapping chunks.

    Word boundaries are intentionally used for this first implementation so
    chunks remain readable and deterministic before embedding is introduced.
    """
    if max_words <= 0:
        raise ValueError("max_words must be greater than zero")
    if overlap_words < 0 or overlap_words >= max_words:
        raise ValueError("overlap_words must be between zero and max_words - 1")

    normalized = _normalize_text(text)
    if not normalized:
        return []

    words = normalized.split(" ")
    step = max_words - overlap_words
    chunks: list[TextChunk] = []

    for start in range(0, len(words), step):
        end = min(start + max_words, len(words))
        content = " ".join(words[start:end]).strip()
        if content:
            chunks.append(
                TextChunk(
                    chunk_index=len(chunks),
                    content=content,
                    metadata={
                        "chunking_method": "word_window",
                        "start_word": start,
                        "end_word": end,
                        "max_words": max_words,
                        "overlap_words": overlap_words,
                    },
                )
            )
        if end == len(words):
            break

    return chunks
