from __future__ import annotations

from pathlib import Path

from rag.models import ParsedChunk

from ._base import BaseParser, ParseError

MAX_CHUNK_CHARS = 2048


class PlainTextParser(BaseParser):
    _EXTENSIONS = [".txt", ".rst", ".log"]

    def parse(self, path: Path) -> list[ParsedChunk]:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            raise ParseError(f"Cannot read {path}: {exc}") from exc

        chunks: list[ParsedChunk] = []
        offset = 0
        while offset < len(text):
            chunk_text = text[offset : offset + MAX_CHUNK_CHARS]
            chunks.append(
                ParsedChunk(
                    text=chunk_text,
                    source_path=str(path),
                    page_number=None,
                    char_offset=offset,
                    section_title=None,
                )
            )
            offset += MAX_CHUNK_CHARS

        return chunks