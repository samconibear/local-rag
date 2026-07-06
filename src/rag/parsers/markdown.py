from rag.models import ParsedChunk
from ._base import BaseParser, ParseError

from pathlib import Path

from langchain_text_splitters import MarkdownHeaderTextSplitter

class MarkdownParser(BaseParser):
    _EXTENSIONS = [".md", ".markdown"]

    _splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2")],
        strip_headers=False,
    )

    def parse(self, path: Path) -> list[ParsedChunk]:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            raise ParseError(f"Cannot read {path}: {exc}") from exc

        try:
            docs = self._splitter.split_text(source)
        except Exception as exc:
            raise ParseError(f"Cannot parse markdown {path}: {exc}") from exc

        if not docs:
            return []

        chunks: list[ParsedChunk] = []
        search_start = 0

        for doc in docs:
            chunk_text = doc.page_content
            metadata = doc.metadata

            section_title = metadata.get("h2") or metadata.get("h1") or None

            # The splitter may trim leading/trailing whitespace from page_content.
            # Search for the first line of the chunk (the heading) to anchor the
            # offset, then walk back to the true start in the source.
            first_line = chunk_text.split("\n", 1)[0].strip()
            idx = source.find(first_line, search_start) if first_line else -1
            if idx == -1:
                idx = source.find(first_line) if first_line else -1
            char_offset = idx if idx != -1 else search_start

            chunks.append(
                ParsedChunk(
                    text=chunk_text,
                    source_path=str(path),
                    page_number=None,
                    char_offset=char_offset,
                    section_title=section_title,
                )
            )

            if idx != -1:
                search_start = idx + len(chunk_text)

        return chunks