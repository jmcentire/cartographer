"""Best-effort ingestion helpers for project compliance evidence."""

from __future__ import annotations

from pathlib import Path


def parse_evidence_index(path: Path) -> dict[str, str]:
    """Extract simple markdown table rows of evidence keys to paths."""

    if not path.exists():
        return {}
    index: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "|" not in line or "---" in line:
            continue
        cells = [cell.strip(" `") for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        key, value = cells[0], cells[-1]
        if key and value and ("/" in value or value.endswith(".md")):
            index[key.lower().replace(" ", "_")] = value
    return index
