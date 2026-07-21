from __future__ import annotations

from pydantic import BaseModel, Field


class ParsedChunk(BaseModel):
    text: str
    source_path: str
    page_number: int | None
    char_offset: int
    section_title: str | None


class EmbeddingChunk(BaseModel):
    text: str
    source_path: str
    page_number: int | None
    char_offset: int
    section_title: str | None


class SearchResult(BaseModel):
    source_path: str
    chunk_text: str
    score: float
    page_number: int | None
    section_title: str | None
    char_offset: int
