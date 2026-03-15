"""PACT key scanner — detects PACT key strings in source files."""

from __future__ import annotations

import re
from pathlib import Path

from cartographer.models import Confidence, DiscoveredPactKey


class PactKeyScanner:
    def __init__(self, pattern: str = r"PACT:[a-zA-Z0-9_]+:[a-zA-Z0-9_]+"):
        self._re = re.compile(pattern)

    def scan(self, file_path: Path, content: str) -> list[DiscoveredPactKey]:
        results: list[DiscoveredPactKey] = []
        for i, line in enumerate(content.split("\n"), 1):
            for match in self._re.finditer(line):
                results.append(
                    DiscoveredPactKey(
                        key=match.group(0),
                        source_file=str(file_path),
                        line=i,
                        confidence=Confidence.HIGH,
                    )
                )
        return results
