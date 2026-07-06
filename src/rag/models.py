from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParsedChunk:
    text: str
    source_path: str
    page_number: int | None
    char_offset: int
    section_title: str | None


@dataclass
class EmbeddingChunk:
    text: str
    source_path: str
    page_number: int | None
    char_offset: int
    section_title: str | None


@dataclass
class SearchResult:
    source_path: str
    chunk_text: str
    score: float
    page_number: int | None
    section_title: str | None
    char_offset: int
