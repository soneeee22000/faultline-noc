"""Loads KEY=VALUE lines from a local, git-ignored .env file without printing them."""

import os
from pathlib import Path

COMMENT_PREFIX = "#"
QUOTES = "\"'"


def load_env_file(path: Path) -> None:
    """Set variables from a .env file that are not already set; a missing file is fine."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.strip().partition("=")
        if separator and name and not name.startswith(COMMENT_PREFIX):
            os.environ.setdefault(name.strip(), value.strip().strip(QUOTES))
