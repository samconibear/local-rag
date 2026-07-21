from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import faiss
import numpy as np

from rag.models import EmbeddingChunk, SearchResult

_DDL = """
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    page_number INTEGER,
    section_title TEXT,
    char_offset INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS indexed_files (
    source_path TEXT PRIMARY KEY,
    mtime REAL NOT NULL,
    size INTEGER NOT NULL,
    last_indexed TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS failed_files (
    source_path TEXT PRIMARY KEY,
    error TEXT NOT NULL,
    attempted_at TEXT NOT NULL
);
"""


class FaissVectorStore:
    def __init__(self, index_dir: Path, dims: int = 384) -> None:
        self._index_dir = index_dir
        self._dims = dims
        self._index_path = index_dir / "index.faiss"
        self._db_path = index_dir / "metadata.db"

        index_dir.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._db.executescript(_DDL)
        self._db.commit()

        if self._index_path.exists():
            self._index = faiss.read_index(str(self._index_path))
        else:
            self._index = faiss.IndexIDMap(faiss.IndexFlatIP(dims))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upsert(
        self,
        chunks: list[EmbeddingChunk],
        vectors: list[list[float]],
        source_path: str,
        mtime: float,
        size: int,
    ) -> None:
        np_vectors = np.array(vectors, dtype=np.float32)
        now = datetime.now(timezone.utc).isoformat()

        with self._db:
            self._delete_chunks_for_path(source_path)

            ids: list[int] = []
            for chunk in chunks:
                cur = self._db.execute(
                    "INSERT INTO chunks (source_path, chunk_text, page_number, section_title, char_offset) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (chunk.source_path, chunk.text, chunk.page_number, chunk.section_title, chunk.char_offset),
                )
                ids.append(cur.lastrowid)

            self._db.execute(
                "INSERT OR REPLACE INTO indexed_files (source_path, mtime, size, last_indexed) VALUES (?, ?, ?, ?)",
                (source_path, mtime, size, now),
            )
            self._db.execute("DELETE FROM failed_files WHERE source_path = ?", (source_path,))

        faiss_ids = np.array(ids, dtype=np.int64)
        self._index.add_with_ids(np_vectors, faiss_ids)
        self._save_index()

    def search(self, query_vector: list[float], k: int) -> list[SearchResult]:
        if self._index.ntotal == 0:
            return []

        np_query = np.array([query_vector], dtype=np.float32)
        scores, ids = self._index.search(np_query, min(k, self._index.ntotal))

        results: list[SearchResult] = []
        for score, faiss_id in zip(scores[0], ids[0]):
            if faiss_id == -1:
                continue
            row = self._db.execute(
                "SELECT source_path, chunk_text, page_number, section_title, char_offset FROM chunks WHERE id = ?",
                (int(faiss_id),),
            ).fetchone()
            if row is None:
                continue
            results.append(
                SearchResult(
                    source_path=row[0],
                    chunk_text=row[1],
                    score=float(score),
                    page_number=row[2],
                    section_title=row[3],
                    char_offset=row[4],
                )
            )
        return results

    def delete_by_path(self, source_path: str) -> None:
        ids = [
            row[0]
            for row in self._db.execute(
                "SELECT id FROM chunks WHERE source_path = ?", (source_path,)
            ).fetchall()
        ]
        if ids:
            self._index.remove_ids(np.array(ids, dtype=np.int64))
            self._save_index()

        with self._db:
            self._delete_chunks_for_path(source_path)
            self._db.execute("DELETE FROM indexed_files WHERE source_path = ?", (source_path,))

    def record_failure(self, source_path: str, error: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO failed_files (source_path, error, attempted_at) VALUES (?, ?, ?)",
                (source_path, error, now),
            )

    def indexed_paths(self) -> dict[str, dict]:
        rows = self._db.execute("SELECT source_path, mtime, size FROM indexed_files").fetchall()
        return {row[0]: {"mtime": row[1], "size": row[2]} for row in rows}

    def failed_files(self) -> list[dict]:
        rows = self._db.execute("SELECT source_path, error, attempted_at FROM failed_files").fetchall()
        return [{"path": row[0], "error": row[1], "attempted_at": row[2]} for row in rows]

    def clear(self) -> None:
        self._index = faiss.IndexIDMap(faiss.IndexFlatIP(self._dims))
        self._save_index()
        with self._db:
            self._db.execute("DELETE FROM chunks")
            self._db.execute("DELETE FROM indexed_files")
            self._db.execute("DELETE FROM failed_files")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _delete_chunks_for_path(self, source_path: str) -> None:
        self._db.execute("DELETE FROM chunks WHERE source_path = ?", (source_path,))

    def _save_index(self) -> None:
        faiss.write_index(self._index, str(self._index_path))
