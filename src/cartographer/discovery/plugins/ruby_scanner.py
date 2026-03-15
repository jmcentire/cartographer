"""Ruby source scanner — regex-based detection of ActiveRecord/Sequel models and Rails routes."""

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

# ActiveRecord model detection
AR_CLASS_RE = re.compile(
    r"class\s+(\w+)\s*<\s*(?:ActiveRecord::Base|ApplicationRecord)"
)
AR_COLUMN_RE = re.compile(
    r"t\.(string|text|integer|bigint|float|decimal|boolean|datetime|date|time|binary|json|uuid|references)\s+[:\"](\w+)"
)

# Sequel model detection
SEQUEL_CLASS_RE = re.compile(r"class\s+(\w+)\s*<\s*Sequel::Model")

# Rails route detection
RAILS_ROUTE_RE = re.compile(
    r"(get|post|put|patch|delete|resources|resource)\s+['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)

# Ruby class detection
RUBY_CLASS_RE = re.compile(r"class\s+(\w+)")


class RubyScanner(ScannerPlugin):
    def scan(self, file_path: Path, content: str) -> DiscoveryResult:
        result = DiscoveryResult()

        self._scan_activerecord(file_path, content, result)
        self._scan_sequel(file_path, content, result)
        self._scan_rails_routes(file_path, content, result)
        self._scan_classes(file_path, content, result)

        return result

    def _scan_activerecord(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        for match in AR_CLASS_RE.finditer(content):
            name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            result.models.append(
                DiscoveredModel(
                    name=name,
                    source_file=str(file_path),
                    line=line,
                    orm="activerecord",
                    confidence=Confidence.HIGH,
                )
            )

        # Also check migration files for field definitions
        for match in AR_COLUMN_RE.finditer(content):
            col_type = match.group(1)
            field_name = match.group(2)
            # These get associated with models during drafting, not here

    def _scan_sequel(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        for match in SEQUEL_CLASS_RE.finditer(content):
            name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            result.models.append(
                DiscoveredModel(
                    name=name,
                    source_file=str(file_path),
                    line=line,
                    orm="sequel",
                    confidence=Confidence.HIGH,
                )
            )

    def _scan_rails_routes(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        if "routes" not in file_path.name.lower() and "config" not in str(file_path):
            return
        for match in RAILS_ROUTE_RE.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            line = content[: match.start()].count("\n") + 1
            if method == "RESOURCES":
                method = "CRUD"
            elif method == "RESOURCE":
                method = "CRUD"
            result.routes.append(
                DiscoveredRoute(
                    path=path,
                    method=method,
                    handler=f"routes@{line}",
                    source_file=str(file_path),
                    line=line,
                    framework="rails",
                    confidence=Confidence.HIGH,
                )
            )

    def _scan_classes(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        for match in RUBY_CLASS_RE.finditer(content):
            name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            # Skip if already found as an ORM model
            if any(m.name == name for m in result.models):
                continue
            result.components.append(
                DiscoveredComponent(
                    name=name,
                    source_file=str(file_path),
                    line=line,
                    type=ComponentType.LIBRARY,
                    confidence=Confidence.MEDIUM,
                    note="Ruby class detected",
                )
            )
