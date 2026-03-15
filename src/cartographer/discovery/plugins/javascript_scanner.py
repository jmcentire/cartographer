"""JavaScript scanner — delegates to TypeScript scanner with CommonJS additions."""

from __future__ import annotations

import re
from pathlib import Path

from cartographer.discovery.plugins.typescript_scanner import TypeScriptScanner
from cartographer.models import (
    Confidence,
    ComponentType,
    DiscoveredComponent,
    DiscoveryResult,
)

MODULE_EXPORTS_RE = re.compile(r"module\.exports\s*=\s*(?:class\s+)?(\w+)")


class JavaScriptScanner(TypeScriptScanner):
    def scan(self, file_path: Path, content: str) -> DiscoveryResult:
        result = super().scan(file_path, content)

        # Additional CommonJS pattern detection
        for match in MODULE_EXPORTS_RE.finditer(content):
            name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            # Avoid duplicating if class already found
            if not any(c.name == name for c in result.components):
                result.components.append(
                    DiscoveredComponent(
                        name=name,
                        source_file=str(file_path),
                        line=line,
                        type=ComponentType.LIBRARY,
                        confidence=Confidence.MEDIUM,
                        note="CommonJS module.exports detected",
                    )
                )

        return result
