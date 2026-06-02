"""Ledger compatibility checker."""

from __future__ import annotations

from pathlib import Path

import yaml

from cartographer.compatibility.base import CompatibilityChecker
from cartographer.config.loader import CartographerConfig
from cartographer.models import CheckResult, Severity


class LedgerChecker(CompatibilityChecker):
    @property
    def tool_name(self) -> str:
        return "ledger"

    def check(self, config: CartographerConfig, base_dir: Path) -> list[CheckResult]:
        results: list[CheckResult] = []

        registry_path = _find_registry(config, base_dir)
        if registry_path is None:
            results.append(CheckResult(
                check_id="ledger_registry_exists",
                target=".ledger/registry/",
                severity=Severity.INFO,
                status="INFO",
                message="no ledger registry found",
                tool="ledger",
            ))
            return results

        # Load all schema files
        schemas: list[tuple[Path, dict]] = []
        for f in sorted(registry_path.rglob("*.yaml")):
            try:
                with open(f) as fh:
                    data = yaml.safe_load(fh)
                if isinstance(data, dict):
                    schemas.append((f, data))
            except Exception:
                pass

        for schema_path, schema in schemas:
            fields = schema.get("fields", [])
            if not isinstance(fields, list):
                continue

            missing_classification = 0
            for field in fields:
                if isinstance(field, dict) and "classification" not in field:
                    missing_classification += 1

            if missing_classification == 0:
                results.append(CheckResult(
                    check_id="all_fields_have_classification",
                    target=str(schema_path),
                    severity=Severity.FAIL,
                    status="PASS",
                    message="all fields have classification",
                    tool="ledger",
                ))
            else:
                results.append(CheckResult(
                    check_id="all_fields_have_classification",
                    target=str(schema_path),
                    severity=Severity.FAIL if missing_classification > len(fields) // 2 else Severity.WARN,
                    status="FAIL" if missing_classification > len(fields) // 2 else "WARN",
                    message=f"{missing_classification} fields missing classification",
                    tool="ledger",
                ))

            # Check annotation conflicts
            annotations = {}
            for field in fields:
                if not isinstance(field, dict):
                    continue
                name = field.get("name", "")
                if _has_annotation(field, "gdpr_erasable") and _has_annotation(field, "immutable"):
                    results.append(CheckResult(
                        check_id="no_annotation_conflicts",
                        target=f"{schema_path}:{name}",
                        severity=Severity.FAIL,
                        status="FAIL",
                        message="field is both gdpr_erasable and immutable",
                        tool="ledger",
                    ))

            # GDPR erasure check
            for field in fields:
                if not isinstance(field, dict):
                    continue
                if _has_annotation(field, "gdpr_erasable"):
                    if "erasure_method" not in field:
                        results.append(CheckResult(
                            check_id="gdpr_erasable_has_erasure_method",
                            target=f"{schema_path}:{field.get('name', '')}",
                            severity=Severity.WARN,
                            status="WARN",
                            message="gdpr_erasable field has no erasure_method",
                            tool="ledger",
                        ))

            # Audit retention check
            for field in fields:
                if not isinstance(field, dict):
                    continue
                if _has_annotation(field, "audit_field"):
                    if "retention_policy" not in field:
                        results.append(CheckResult(
                            check_id="audit_fields_have_retention_policy",
                            target=f"{schema_path}:{field.get('name', '')}",
                            severity=Severity.WARN,
                            status="WARN",
                            message="audit field has no retention_policy",
                            tool="ledger",
                        ))

        return results


def _find_registry(config: CartographerConfig, base_dir: Path) -> Path | None:
    if config.stack.ledger_registry:
        p = Path(config.stack.ledger_registry)
        return p if p.is_absolute() and p.exists() else (base_dir / p if (base_dir / p).exists() else None)
    for name in [".ledger/registry", ".ledger"]:
        candidate = base_dir / name
        if candidate.exists():
            return candidate
    return None


def _has_annotation(field: dict, annotation: str) -> bool:
    annotations = field.get("annotations", [])
    if isinstance(annotations, list):
        for item in annotations:
            if item == annotation:
                return True
            if isinstance(item, dict) and item.get("name") == annotation:
                return True
    return field.get(annotation) is True
