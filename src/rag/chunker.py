from __future__ import annotations

from rag.models import EmbeddingChunk, ParsedChunk

# Approximate token count as chars / 4
_CHARS_PER_TOKEN = 4


def chunk(
    parsed: list[ParsedChunk],
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[EmbeddingChunk]:
    """Split ParsedChunks into fixed-size overlapping EmbeddingChunks."""
    size_chars = chunk_size * _CHARS_PER_TOKEN
    overlap_chars = chunk_overlap * _CHARS_PER_TOKEN

    results: list[EmbeddingChunk] = []
    for pc in parsed:
        text = pc.text
        if not text:
            continue

        if len(text) <= size_chars:
            results.append(
                EmbeddingChunk(
                    text=text,
                    source_path=pc.source_path,
                    page_number=pc.page_number,
                    char_offset=pc.char_offset,
                    section_title=pc.section_title,
                )
            )
            continue

        start = 0
        while start < len(text):
            end = start + size_chars
            results.append(
                EmbeddingChunk(
                    text=text[start:end],
                    source_path=pc.source_path,
                    page_number=pc.page_number,
                    char_offset=pc.char_offset + start,
                    section_title=pc.section_title,
                )
            )
            start += size_chars - overlap_chars

    return results
