import os
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", ".nuxt", ".idea",
    "__pycache__", ".venv", ".env", "site-packages", "*.egg-info",
    "target", ".gradle", ".mvn", ".build", ".terraform", "cdk.out", ".DS_Store",
}

MAX_RESULTS = 200

ROOT_DIR: Path = Path.cwd().resolve()


def resolve_within_root(relative_path: str) -> Path | None:
    candidate = (ROOT_DIR / relative_path).resolve()
    if ROOT_DIR not in candidate.parents and candidate != ROOT_DIR:
        return None
    return candidate


def iter_files():
    for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield Path(dirpath) / name
