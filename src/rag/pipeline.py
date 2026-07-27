import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum, auto
from fnmatch import fnmatch
from pathlib import Path

import fs
from rag.chunker import chunk
from rag.embedder import Embedder
from rag.parsers import registry
from rag.parsers._base import ParseError
from rag.vector_store import FaissVectorStore


class IndexState(StrEnum):
    IDLE = auto()
    RUNNING = auto()
    FAILED = auto()


@dataclass
class IndexStatus:
    state: IndexState = IndexState.IDLE
    files_indexed: int = 0
    files_remaining: int = 0
    files_failed: int = 0
    failed_files: list[dict] = field(default_factory=list)
    last_completed: str | None = None
    job_id: str | None = None


class Pipeline:
    def __init__(
        self,
        store: FaissVectorStore,
        embedder: Embedder,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        exclude_patterns: list[str] | None = None,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._exclude_patterns = exclude_patterns or []
        self._status = IndexStatus()
        self._lock = threading.Lock()

    def get_status(self) -> dict:
        with self._lock:
            s = self._status
            return {
                "state": s.state,
                "files_indexed": s.files_indexed,
                "files_remaining": s.files_remaining,
                "files_failed": s.files_failed,
                "failed_files": s.failed_files,
                "last_completed": s.last_completed,
                "job_id": s.job_id,
            }

    def search(self, query_vector: list[float], k: int) -> list:
        return self._store.search(query_vector, k)

    def start_reindex(self) -> dict:
        with self._lock:
            if self._status.state == IndexState.RUNNING:
                return {"error": "reindex already running", "job_id": self._status.job_id}
            job_id = str(uuid.uuid4())
            self._status = IndexStatus(state=IndexState.RUNNING, job_id=job_id)

        thread = threading.Thread(target=self._run_reindex, args=(job_id,), daemon=True)
        thread.start()
        return {"status": "started", "job_id": job_id}

    def _should_exclude(self, path: Path) -> bool:
        return any(
            fnmatch(path.name, p) or fnmatch(str(path), p)
            for p in self._exclude_patterns
        )

    def _run_reindex(self, job_id: str) -> None:
        try:
            all_files = [p for p in fs.iter_files() if not self._should_exclude(p)]
            indexed = self._store.indexed_paths()

            to_index: list[Path] = []
            for path in all_files:
                try:
                    stat = path.stat()
                except OSError:
                    continue
                entry = indexed.get(str(path))
                if entry is None or entry["mtime"] != stat.st_mtime or entry["size"] != stat.st_size:
                    to_index.append(path)

            current_paths = {str(p) for p in all_files}
            for indexed_path in list(indexed.keys()):
                if indexed_path not in current_paths:
                    self._store.delete_by_path(indexed_path)

            with self._lock:
                self._status.files_remaining = len(to_index)

            for path in to_index:
                with self._lock:
                    if self._status.job_id != job_id:
                        return

                self._process_file(path)

                with self._lock:
                    self._status.files_indexed += 1
                    self._status.files_remaining -= 1

            with self._lock:
                self._status.state = IndexState.IDLE
                self._status.last_completed = datetime.now(timezone.utc).isoformat()
                self._status.failed_files = self._store.failed_files()
                self._status.files_failed = len(self._status.failed_files)

        except Exception as exc:
            with self._lock:
                self._status.state = IndexState.FAILED

    def _process_file(self, path: Path) -> None:
        parser = registry.get_parser(path)
        if parser is None:
            return

        try:
            parsed_chunks = parser.parse(path)
        except ParseError as exc:
            self._store.record_failure(str(path), str(exc))
            with self._lock:
                self._status.files_failed += 1
            return

        if not parsed_chunks:
            return

        embedding_chunks = chunk(parsed_chunks, self._chunk_size, self._chunk_overlap)
        if not embedding_chunks:
            return

        vectors = self._embedder.embed_batch([c.text for c in embedding_chunks])

        stat = path.stat()
        self._store.upsert(
            chunks=embedding_chunks,
            vectors=vectors,
            source_path=str(path),
            mtime=stat.st_mtime,
            size=stat.st_size,
        )
