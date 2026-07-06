from __future__ import annotations

from pathlib import Path

from ._base import BaseParser


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: list[BaseParser] = [
            cls() for cls in _all_subclasses(BaseParser)
        ]

    def get_parser(self, path: Path) -> BaseParser | None:
        for parser in self._parsers:
            if parser.accept(path):
                return parser
        return None


def _all_subclasses(cls: type) -> list[type]:
    result = []
    for sub in cls.__subclasses__():
        result.append(sub)
        result.extend(_all_subclasses(sub))
    return result


registry = ParserRegistry()
