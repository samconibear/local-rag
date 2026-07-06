"""
File search MCP server

Lets a client search a designated root directory by filename pattern,
content (grep-style), file extension, or modification time, plus get
basic metadata. All operations are scoped to ROOT_DIR.
"""

import sys
from pathlib import Path
import fs
from tools import mcp

fs.ROOT_DIR = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()

if not fs.ROOT_DIR.is_dir():
    print(f"Error: {fs.ROOT_DIR} is not a directory", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    print(f"File search server rooted at: {fs.ROOT_DIR}", file=sys.stderr)
    mcp.run(transport="stdio")
