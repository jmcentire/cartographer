"""Java source scanner — regex-based detection of JPA/Hibernate entities and Spring routes."""

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

# JPA/Hibernate entity detection
JPA_ENTITY_RE = re.compile(r"@Entity")
JPA_TABLE_RE = re.compile(r'@Table\(\s*name\s*=\s*"(\w+)"')
JPA_COLUMN_RE = re.compile(r'@Column\(.*?name\s*=\s*"(\w+)".*?\)\s*\n\s*private\s+(\w+)\s+(\w+)')

# Spring route detection
SPRING_MAPPING_RE = re.compile(
    r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)"
    r'\(\s*(?:value\s*=\s*)?["\']([^"\']*)["\']',
)

# MyBatis mapper detection
MYBATIS_MAPPER_RE = re.compile(r"@Mapper")

# Java class detection
JAVA_CLASS_RE = re.compile(r"(?:public\s+)?class\s+(\w+)")


class JavaScanner(ScannerPlugin):
    def scan(self, file_path: Path, content: str) -> DiscoveryResult:
        result = DiscoveryResult()

        self._scan_jpa(file_path, content, result)
        self._scan_spring_routes(file_path, content, result)
        self._scan_classes(file_path, content, result)

        return result

    def _scan_jpa(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        if not JPA_ENTITY_RE.search(content):
            return

        # Find the class name
        class_match = JAVA_CLASS_RE.search(content)
        if not class_match:
            return

        name = class_match.group(1)
        line = content[: class_match.start()].count("\n") + 1

        table_match = JPA_TABLE_RE.search(content)
        fields: list[DiscoveredField] = []
        for col_match in JPA_COLUMN_RE.finditer(content):
            fields.append(
                DiscoveredField(
                    name=col_match.group(3),
                    type=col_match.group(2).lower(),
                    confidence=Confidence.HIGH,
                )
            )

        result.models.append(
            DiscoveredModel(
                name=name,
                source_file=str(file_path),
                line=line,
                orm="jpa",
                fields=fields,
                confidence=Confidence.HIGH,
            )
        )

    def _scan_spring_routes(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        for match in SPRING_MAPPING_RE.finditer(content):
            mapping_type = match.group(1)
            path = match.group(2)
            line = content[: match.start()].count("\n") + 1

            method_map = {
                "GetMapping": "GET",
                "PostMapping": "POST",
                "PutMapping": "PUT",
                "DeleteMapping": "DELETE",
                "PatchMapping": "PATCH",
                "RequestMapping": "ANY",
            }
            method = method_map.get(mapping_type, "ANY")

            result.routes.append(
                DiscoveredRoute(
                    path=path,
                    method=method,
                    handler=f"handler@{line}",
                    source_file=str(file_path),
                    line=line,
                    framework="spring",
                    confidence=Confidence.HIGH,
                )
            )

    def _scan_classes(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        for match in JAVA_CLASS_RE.finditer(content):
            name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            if any(m.name == name for m in result.models):
                continue
            result.components.append(
                DiscoveredComponent(
                    name=name,
                    source_file=str(file_path),
                    line=line,
                    type=ComponentType.LIBRARY,
                    confidence=Confidence.LOW,
                    note="Java class detected",
                )
            )
