from __future__ import annotations

from pathlib import Path

from ._base import BaseParser


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: list[BaseParser] = [
            cls() for cls in self._all_subclasses()
        ]
    
    def _all_subclasses(self) -> list[type]:
        result = []
        for sub_class in BaseParser.__subclasses__():
            result.append(sub_class)
            result.extend(self._all_subclasses(sub_class))
        return result

    def get_parser(self, path: Path) -> BaseParser | None:
        for parser in self._parsers:
            if parser.accept(path):
                return parser
        return None





registry = ParserRegistry()
