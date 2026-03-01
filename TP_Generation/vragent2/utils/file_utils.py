"""
File & path utilities shared across modules.

Extracted from GenerateTestPlanModified helper methods.
"""

from __future__ import annotations

import json
import os
import shutil
from typing import Any, Dict, List, Optional


# Characters illegal in Windows filenames
_ILLEGAL_CHARS = '<>:"/\\|?*'


def sanitize_filename(name: str) -> str:
    """Replace illegal filename characters with underscores."""
    for ch in _ILLEGAL_CHARS:
        name = name.replace(ch, "_")
    return name


def ensure_dir(path: str, *, clean: bool = False) -> str:
    """Create *path* if missing.  If *clean* is True, remove it first."""
    if clean and os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)
    return path


def load_json(path: str) -> Any:
    """Load a JSON file and return the parsed object."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: str, data: Any, *, indent: int = 2) -> None:
    """Write *data* as pretty-printed JSON."""
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=indent, ensure_ascii=False)


def load_text(path: str) -> Optional[str]:
    """Read a text file; return ``None`` on failure."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().replace("\ufeff", "")
    except Exception:
        return None


def find_files(directory: str, suffix: str) -> List[str]:
    """Return absolute paths of files ending with *suffix* under *directory*."""
    results: List[str] = []
    if not os.path.isdir(directory):
        return results
    for fname in os.listdir(directory):
        if fname.endswith(suffix):
            results.append(os.path.join(directory, fname))
    return results
