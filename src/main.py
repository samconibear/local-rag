"""
File search MCP server

Lets a client search a designated root directory by filename pattern,
content (grep-style), file extension, or modification time, plus get
basic metadata and semantic (embedding-based) search. All operations
are scoped to ROOT_DIR.
"""

import argparse
import sys
from pathlib import Path

import fs
from rag import embedder, pipeline
from rag.vector_store import FaissVectorStore
from tools import mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="File search MCP server")
    parser.add_argument("root_dir", nargs="?", default=None, help="Directory to search/index")
    parser.add_argument("--index-dir", required=True, help="Directory to store FAISS index and SQLite metadata")
    parser.add_argument("--embedding-model", default="all-MiniLM-L6-v2", help="sentence-transformers model name")
    parser.add_argument("--chunk-size", type=int, default=512, help="Approximate tokens per chunk")
    parser.add_argument("--chunk-overlap", type=int, default=64, help="Overlap between consecutive chunks (tokens)")
    parser.add_argument("--exclude-patterns", default="", help="Comma-separated glob patterns to skip")
    args = parser.parse_args()

    fs.ROOT_DIR = Path(args.root_dir).resolve() if args.root_dir else Path.cwd().resolve()
    if not fs.ROOT_DIR.is_dir():
        print(f"Error: {fs.ROOT_DIR} is not a directory", file=sys.stderr)
        sys.exit(1)

    exclude_patterns = [p.strip() for p in args.exclude_patterns.split(",") if p.strip()]

    print(f"File search server rooted at: {fs.ROOT_DIR}", file=sys.stderr)
    print(f"Index directory: {args.index_dir}", file=sys.stderr)

    embedder.init(args.embedding_model)

    store = FaissVectorStore(Path(args.index_dir))
    pipeline.init(
        store=store,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        exclude_patterns=exclude_patterns,
    )
    pipeline.start_reindex()

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
