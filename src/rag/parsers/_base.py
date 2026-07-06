from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar
from rag.models import ParsedChunk

class ParseError(Exception):
    pass


class BaseParser(ABC):
    _EXTENSIONS: ClassVar[list[str]]

    def accept(self, path: Path) -> bool:
        return path.suffix.lower() in self._EXTENSIONS

    @abstractmethod
    def parse(self, path: Path) -> list[ParsedChunk]:
        pass