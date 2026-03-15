"""TypeScript/JavaScript source scanner — regex-based detection of ORM models, routes, and components."""

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

# Prisma model detection
PRISMA_MODEL_RE = re.compile(r"model\s+(\w+)\s*\{", re.MULTILINE)
PRISMA_FIELD_RE = re.compile(r"^\s+(\w+)\s+(\w+)(\[\])?\s*(\?)?", re.MULTILINE)

# TypeORM entity detection
TYPEORM_ENTITY_RE = re.compile(r"@Entity\(\s*(?:['\"](\w+)['\"])?\s*\)")
TYPEORM_COLUMN_RE = re.compile(r"@Column\(\s*\{?\s*(?:type:\s*['\"](\w+)['\"])?\s*\}?\s*\)\s*\n\s*(\w+)")

# Sequelize model detection
SEQUELIZE_DEFINE_RE = re.compile(r"\.define\(\s*['\"](\w+)['\"]")
SEQUELIZE_INIT_RE = re.compile(r"(\w+)\.init\(\s*\{")

# Mongoose schema detection
MONGOOSE_SCHEMA_RE = re.compile(r"new\s+(?:mongoose\.)?Schema\(\s*\{", re.MULTILINE)
MONGOOSE_MODEL_RE = re.compile(r"(?:mongoose\.)?model\(\s*['\"](\w+)['\"]")

# Drizzle table detection
DRIZZLE_TABLE_RE = re.compile(r"(?:pgTable|mysqlTable|sqliteTable)\(\s*['\"](\w+)['\"]")

# Express route detection
EXPRESS_ROUTE_RE = re.compile(
    r"(?:app|router)\.(get|post|put|delete|patch|options|head)\(\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)

# Class/export detection
CLASS_RE = re.compile(r"(?:export\s+)?class\s+(\w+)")
EXPORT_FUNCTION_RE = re.compile(r"export\s+(?:async\s+)?function\s+(\w+)")


class TypeScriptScanner(ScannerPlugin):
    def scan(self, file_path: Path, content: str) -> DiscoveryResult:
        result = DiscoveryResult()

        # Prisma schema files
        if file_path.suffix == ".prisma" or file_path.name == "schema.prisma":
            self._scan_prisma(file_path, content, result)
            return result

        self._scan_typeorm(file_path, content, result)
        self._scan_sequelize(file_path, content, result)
        self._scan_mongoose(file_path, content, result)
        self._scan_drizzle(file_path, content, result)
        self._scan_express_routes(file_path, content, result)
        self._scan_classes(file_path, content, result)

        return result

    def _scan_prisma(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        blocks = content.split("model ")
        for block in blocks[1:]:
            name_match = re.match(r"(\w+)\s*\{", block)
            if not name_match:
                continue
            name = name_match.group(1)
            line = content[: content.index(f"model {name}")].count("\n") + 1
            fields: list[DiscoveredField] = []
            brace_content = block.split("{", 1)[1].split("}", 1)[0] if "{" in block else ""
            for field_line in brace_content.strip().split("\n"):
                field_line = field_line.strip()
                if not field_line or field_line.startswith("//") or field_line.startswith("@@"):
                    continue
                parts = field_line.split()
                if len(parts) >= 2 and not parts[0].startswith("@"):
                    fields.append(
                        DiscoveredField(
                            name=parts[0],
                            type=parts[1].rstrip("?[]"),
                            confidence=Confidence.HIGH,
                        )
                    )
            result.models.append(
                DiscoveredModel(
                    name=name,
                    source_file=str(file_path),
                    line=line,
                    orm="prisma",
                    fields=fields,
                    confidence=Confidence.HIGH,
                )
            )

    def _scan_typeorm(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        for match in TYPEORM_ENTITY_RE.finditer(content):
            table_name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            # Find the class definition after the decorator
            remaining = content[match.end() :]
            class_match = re.search(r"class\s+(\w+)", remaining)
            name = class_match.group(1) if class_match else (table_name or "Unknown")
            fields = _extract_typeorm_fields(content[match.start() :])
            result.models.append(
                DiscoveredModel(
                    name=name,
                    source_file=str(file_path),
                    line=line,
                    orm="typeorm",
                    fields=fields,
                    confidence=Confidence.HIGH,
                )
            )

    def _scan_sequelize(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        for match in SEQUELIZE_DEFINE_RE.finditer(content):
            name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            result.models.append(
                DiscoveredModel(
                    name=name,
                    source_file=str(file_path),
                    line=line,
                    orm="sequelize",
                    confidence=Confidence.HIGH,
                )
            )
        for match in SEQUELIZE_INIT_RE.finditer(content):
            name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            result.models.append(
                DiscoveredModel(
                    name=name,
                    source_file=str(file_path),
                    line=line,
                    orm="sequelize",
                    confidence=Confidence.MEDIUM,
                )
            )

    def _scan_mongoose(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        for match in MONGOOSE_MODEL_RE.finditer(content):
            name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            result.models.append(
                DiscoveredModel(
                    name=name,
                    source_file=str(file_path),
                    line=line,
                    orm="mongoose",
                    confidence=Confidence.HIGH,
                )
            )

    def _scan_drizzle(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        for match in DRIZZLE_TABLE_RE.finditer(content):
            name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            result.models.append(
                DiscoveredModel(
                    name=name,
                    source_file=str(file_path),
                    line=line,
                    orm="drizzle",
                    confidence=Confidence.HIGH,
                )
            )

    def _scan_express_routes(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        for match in EXPRESS_ROUTE_RE.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            line = content[: match.start()].count("\n") + 1
            result.routes.append(
                DiscoveredRoute(
                    path=path,
                    method=method,
                    handler=f"anonymous@{line}",
                    source_file=str(file_path),
                    line=line,
                    framework="express",
                    confidence=Confidence.HIGH,
                )
            )

    def _scan_classes(
        self, file_path: Path, content: str, result: DiscoveryResult
    ) -> None:
        for match in CLASS_RE.finditer(content):
            name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            result.components.append(
                DiscoveredComponent(
                    name=name,
                    source_file=str(file_path),
                    line=line,
                    type=ComponentType.LIBRARY,
                    confidence=Confidence.MEDIUM,
                    note="TypeScript/JavaScript class detected",
                )
            )


def _extract_typeorm_fields(text: str) -> list[DiscoveredField]:
    fields: list[DiscoveredField] = []
    for match in TYPEORM_COLUMN_RE.finditer(text[:2000]):
        col_type = match.group(1) or "unknown"
        name = match.group(2)
        fields.append(
            DiscoveredField(name=name, type=col_type, confidence=Confidence.HIGH)
        )
    return fields
