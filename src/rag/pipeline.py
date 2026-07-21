from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import fs

from enum import StrEnum, auto
from rag import embedder
from rag.chunker import chunk
from rag.parsers import registry
from rag.parsers._base import ParseError
from rag.vector_store import FaissVectorStore

class IndexState(StrEnum):
    IDLE = auto()
    RUNNING = auto()
    FAILED = auto()

@dataclass
class IndexStatus:
    state: str = IndexState.IDLE
    files_indexed: int = 0
    files_remaining: int = 0
    files_failed: int = 0
    failed_files: list[dict] = field(default_factory=list)
    last_completed: str | None = None
    job_id: str | None = None


_status = IndexStatus()
_lock = threading.Lock()
_store: FaissVectorStore | None = None
_chunk_size: int = 512
_chunk_overlap: int = 64
_exclude_patterns: list[str] = []


def init(
    store: FaissVectorStore,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    exclude_patterns: list[str] | None = None,
) -> None:
    global _store, _chunk_size, _chunk_overlap, _exclude_patterns
    _store = store
    _chunk_size = chunk_size
    _chunk_overlap = chunk_overlap
    _exclude_patterns = exclude_patterns or []


def get_status() -> dict:
    with _lock:
        return {
            "state": _status.state,
            "files_indexed": _status.files_indexed,
            "files_remaining": _status.files_remaining,
            "files_failed": _status.files_failed,
            "failed_files": _status.failed_files,
            "last_completed": _status.last_completed,
            "job_id": _status.job_id,
        }


def start_reindex() -> dict:
    """Start a background reindex. Returns error dict if already running."""
    with _lock:
        if _status.state == IndexState.RUNNING:
            return {"error": "reindex already running", "job_id": _status.job_id}
        job_id = str(uuid.uuid4())
        _status.state = IndexState.RUNNING
        _status.job_id = job_id
        _status.files_indexed = 0
        _status.files_remaining = 0
        _status.files_failed = 0
        _status.failed_files = []

    thread = threading.Thread(target=_run_reindex, args=(job_id,), daemon=True)
    thread.start()
    return {"status": "started", "job_id": job_id}


def _should_exclude(path: Path) -> bool:
    from fnmatch import fnmatch
    for pattern in _exclude_patterns:
        if fnmatch(path.name, pattern) or fnmatch(str(path), pattern):
            return True
    return False


def _run_reindex(job_id: str) -> None:
    store = _store
    if store is None:
        with _lock:
            _status.state = IndexState.FAILED
        return

    try:
        all_files = [p for p in fs.iter_files() if not _should_exclude(p)]
        indexed = store.indexed_paths()

        to_index: list[Path] = []
        for path in all_files:
            try:
                stat = path.stat()
            except OSError:
                continue
            entry = indexed.get(str(path))
            if entry is None or entry["mtime"] != stat.st_mtime or entry["size"] != stat.st_size:
                to_index.append(path)

        # Purge paths no longer on disk
        current_paths = {str(p) for p in all_files}
        for indexed_path in list(indexed.keys()):
            if indexed_path not in current_paths:
                store.delete_by_path(indexed_path)

        with _lock:
            _status.files_remaining = len(to_index)

        for path in to_index:
            if _status.job_id != job_id:
                return  # superseded

            _process_file(store, path)

            with _lock:
                _status.files_indexed += 1
                _status.files_remaining -= 1

        with _lock:
            _status.state = IndexState.IDLE
            _status.last_completed = datetime.now(timezone.utc).isoformat()
            _status.failed_files = store.failed_files()
            _status.files_failed = len(_status.failed_files)

    except Exception as exc:
        with _lock:
            _status.state = IndexState.FAILED
            _status.job_id = job_id


def _process_file(store: FaissVectorStore, path: Path) -> None:
    parser = registry.get_parser(path)
    if parser is None:
        return

    try:
        parsed_chunks = parser.parse(path)
    except ParseError as exc:
        store.record_failure(str(path), str(exc))
        with _lock:
            _status.files_failed += 1
        return

    if not parsed_chunks:
        return

    embedding_chunks = chunk(parsed_chunks, _chunk_size, _chunk_overlap)
    if not embedding_chunks:
        return

    texts = [c.text for c in embedding_chunks]
    vectors = embedder.embed_batch(texts)

    stat = path.stat()
    store.upsert(
        chunks=embedding_chunks,
        vectors=vectors,
        source_path=str(path),
        mtime=stat.st_mtime,
        size=stat.st_size,
    )
