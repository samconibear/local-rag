from __future__ import annotations

from pathlib import Path

from markitdown import MarkItDown
from markitdown_pdf_pages import PdfConverterWithPage

from rag.models import ParsedChunk

from ._base import BaseParser, ParseError

_md = MarkItDown()
_md.register_converter(PdfConverterWithPage())


class PdfParser(BaseParser):
    _EXTENSIONS = [".pdf"]

    def parse(self, path: Path) -> list[ParsedChunk]:
        try:
            result = _md.convert(str(path))
        except Exception as exc:
            raise ParseError(f"Cannot parse PDF {path}: {exc}") from exc

        chunks: list[ParsedChunk] = []
        char_offset = 0

        for page in result.markdown_with_pages:
            text = page["markdown"]
            chunks.append(
                ParsedChunk(
                    text=text,
                    source_path=str(path),
                    page_number=page["page_number"],
                    char_offset=char_offset,
                    section_title=None,
                )
            )
            char_offset += len(text)

        return chunks
