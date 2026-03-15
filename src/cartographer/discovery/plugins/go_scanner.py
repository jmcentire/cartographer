"""Go source scanner — regex-based detection of GORM/sqlx models and HTTP handlers."""

from __future__ import annotations

import re
from pathlib import Path

from cartographer.discovery.plugins.base import ScannerPlugin
from cartographer.models import (
    Confidence,
    ComponentType,
    DiscoveredComponent,
    DiscoveredField,
    DiscoveredModel,
    DiscoveredRoute,
    DiscoveryResult,
)

# GORM model detection (struct with gorm tags)
GORM_TAG_RE = re.compile(r'`.*gorm:"([^"]*)".*`')
STRUCT_RE = re.compile(r"type\s+(\w+)\s+struct\s*\{")
STRUCT_FIELD_RE = re.compile(r"\s+(\w+)\s+(\S+)")

# sqlx tag detection
SQLX_TAG_RE = re.compile(r'`.*db:"([^"]*)".*`')

# Raw SQL detection
RAW_SQL_RE = re.compile(r'(?:db\.(?:Query|Exec|QueryRow)|sql\.Open)\s*\(')

# HTTP handler detection (net/http, gin, echo, chi)
HTTP_HANDLE_RE = re.compile(
    r'(?:mux|router|r|e|g|app)\.(Get|Post|Put|Delete|Patch|Handle|HandleFunc)\(\s*"([^"]*)"',
    re.IGNORECASE,
)
GIN_ROUTE_RE = re.compile(
    r'(?:router|r|g|group)\.(GET|POST|PUT|DELETE|PATCH)\(\s*"([^"]*)"',
)


class GoScanner(ScannerPlugin):
    def scan(self, file_path: Path, content: str) -> DiscoveryResult:
        result = DiscoveryResult()

        self._scan_gorm(file_path, content, result)
        self._scan_routes(file_path, content, result)
        self._scan_structs(file_path, content, result)

        return result

    def _scan_gorm(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        # Find structs that have gorm or db tags
        has_gorm = bool(GORM_TAG_RE.search(content))
        has_sqlx = bool(SQLX_TAG_RE.search(content))
        if not has_gorm and not has_sqlx:
            return

        for match in STRUCT_RE.finditer(content):
            name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            # Check if this struct has ORM tags
            struct_end = content.find("}", match.end())
            struct_body = content[match.end() : struct_end] if struct_end > 0 else ""

            orm = None
            if GORM_TAG_RE.search(struct_body):
                orm = "gorm"
            elif SQLX_TAG_RE.search(struct_body):
                orm = "sqlx"

            if orm:
                fields = _extract_go_fields(struct_body)
                result.models.append(
                    DiscoveredModel(
                        name=name,
                        source_file=str(file_path),
                        line=line,
                        orm=orm,
                        fields=fields,
                        confidence=Confidence.HIGH,
                    )
                )

    def _scan_routes(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        for match in HTTP_HANDLE_RE.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            line = content[: match.start()].count("\n") + 1
            if method in ("HANDLE", "HANDLEFUNC"):
                method = "ANY"
            result.routes.append(
                DiscoveredRoute(
                    path=path,
                    method=method,
                    handler=f"handler@{line}",
                    source_file=str(file_path),
                    line=line,
                    framework="net/http",
                    confidence=Confidence.HIGH,
                )
            )

        for match in GIN_ROUTE_RE.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            line = content[: match.start()].count("\n") + 1
            result.routes.append(
                DiscoveredRoute(
                    path=path,
                    method=method,
                    handler=f"handler@{line}",
                    source_file=str(file_path),
                    line=line,
                    framework="gin",
                    confidence=Confidence.HIGH,
                )
            )

    def _scan_structs(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        for match in STRUCT_RE.finditer(content):
            name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            if any(m.name == name for m in result.models):
                continue
            if name[0].isupper():  # Only exported types
                result.components.append(
                    DiscoveredComponent(
                        name=name,
                        source_file=str(file_path),
                        line=line,
                        type=ComponentType.LIBRARY,
                        confidence=Confidence.LOW,
                        note="Go exported struct detected",
                    )
                )


def _extract_go_fields(struct_body: str) -> list[DiscoveredField]:
    fields: list[DiscoveredField] = []
    for line in struct_body.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0][0].isupper():
            fields.append(
                DiscoveredField(
                    name=parts[0],
                    type=parts[1],
                    confidence=Confidence.HIGH,
                )
            )
    return fields
