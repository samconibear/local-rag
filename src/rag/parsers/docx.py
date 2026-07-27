from __future__ import annotations

from pathlib import Path

from markitdown import MarkItDown

from rag.models import ParsedChunk
from ._base import BaseParser, ParseError

_md = MarkItDown()


class DocxParser(BaseParser):
    _EXTENSIONS = [".docx", ".pptx", ".xlsx", ".xls", ".doc", ".odt", ".odp", ".ods"]

    def parse(self, path: Path) -> list[ParsedChunk]:
        try:
            result = _md.convert(str(path))
        except Exception as exc:
            raise ParseError(f"Cannot parse {path}: {exc}") from exc

        text = result.text_content
        if not text:
            return []

        return [
            ParsedChunk(
                text=text,
                source_path=str(path),
                page_number=None,
                char_offset=0,
                section_title=None,
            )
        ]
