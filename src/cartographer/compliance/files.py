"""Shared file selection for compliance source evidence."""

from __future__ import annotations

from pathlib import Path
import fnmatch


DEFAULT_EXCLUDED_DIRS = frozenset(
    {
        ".cartographer",
        ".git",
        ".kin",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "venv",
    }
)

DEFAULT_EXCLUDED_PREFIXES = (
    "compliance/controls/",
    "src/cartographer/compliance/frameworks/",
    "tests/compliance/",
)


def matching_files(base_dir: Path, include_glob: str | list[str], exclude_globs: list[str] | None = None) -> list[Path]:
    matches: list[Path] = []
    include_globs = [include_glob] if isinstance(include_glob, str) else list(include_glob)
    exclude_globs = exclude_globs or []
    for path in base_dir.rglob("*"):
        if not path.is_file():
            continue

        rel_path = path.relative_to(base_dir)
        rel = rel_path.as_posix()
        if _excluded_by_default(rel_path, rel):
            continue
        if any(fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(path.name, pattern) for pattern in exclude_globs):
            continue
        if any(fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(path.name, pattern) for pattern in include_globs):
            matches.append(path)
    return matches


def _excluded_by_default(rel_path: Path, rel: str) -> bool:
    if any(part in DEFAULT_EXCLUDED_DIRS for part in rel_path.parts):
        return True
    if any(part.startswith("src_cartographer_") for part in rel_path.parts):
        return True
    return any(rel.startswith(prefix) for prefix in DEFAULT_EXCLUDED_PREFIXES)
