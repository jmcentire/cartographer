"""Small assertion helpers used by rendered compliance tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

import yaml

from cartographer.compliance.files import matching_files


def load_ledger_fields(base_dir: Path) -> list[dict[str, Any]]:
    registry = _first_existing(base_dir, [".ledger/registry", ".ledger"])
    if registry is None:
        return []
    fields: list[dict[str, Any]] = []
    for path in sorted(registry.rglob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        if isinstance(data, dict) and isinstance(data.get("fields"), list):
            fields.extend(f for f in data["fields"] if isinstance(f, dict))
    return fields


def ledger_annotation_has_companion_field(base_dir: Path, annotation: str, companion: str, tier: str | None = None) -> None:
    fields = _fields_for_tier(load_ledger_fields(base_dir), tier)
    in_scope = [field for field in fields if _has_annotation(field, annotation)]
    assert in_scope, f"no Ledger fields carry annotation {annotation}"
    missing = [field.get("name", "<unnamed>") for field in in_scope if companion not in field]
    assert not missing, f"fields missing {companion}: {missing}"


def ledger_tier_all_encrypted(base_dir: Path, tier: str) -> None:
    fields = _fields_for_tier(load_ledger_fields(base_dir), tier)
    assert fields, f"no Ledger fields for tier {tier}"
    missing = [field.get("name", "<unnamed>") for field in fields if not _has_annotation(field, "encrypted_at_rest")]
    assert not missing, f"fields missing encrypted_at_rest: {missing}"


def source_pattern_present(base_dir: Path, pattern: str, include_glob: str | list[str] = "**/*", exclude_glob: str | list[str] | None = None) -> None:
    for path in matching_files(base_dir, include_glob, _as_list(exclude_glob)):
        if re.search(pattern, path.read_text(encoding="utf-8", errors="replace"), re.MULTILINE):
            return
    raise AssertionError(f"pattern not found: {pattern}")


def source_pattern_absent(base_dir: Path, pattern: str, include_glob: str | list[str] = "**/*", exclude_glob: str | list[str] | None = None) -> None:
    matches = []
    for path in matching_files(base_dir, include_glob, _as_list(exclude_glob)):
        if re.search(pattern, path.read_text(encoding="utf-8", errors="replace"), re.MULTILINE):
            matches.append(str(path))
    assert not matches, f"forbidden pattern found in: {matches}"


def every_route_has_guard(base_dir: Path, guard_patterns: list[str]) -> None:
    from cartographer.config.loader import CartographerConfig
    from cartographer.discovery.scanner import scan_source

    routes = scan_source(CartographerConfig(), base_dir).routes
    uncovered = []
    for route in routes:
        path = Path(route.source_file)
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        window = "\n".join(lines[max(0, route.line - 31): route.line + 30])
        if not any(re.search(pattern, window) for pattern in guard_patterns):
            uncovered.append(f"{route.method} {route.path}")
    assert not uncovered, f"routes without guard evidence: {uncovered}"


def config_key_equals(base_dir: Path, path: str, key: str, value: Any) -> None:
    data = yaml.safe_load((base_dir / path).read_text()) or {}
    current = data
    for part in key.split("."):
        assert isinstance(current, dict) and part in current, f"missing key {key}"
        current = current[part]
    assert str(current) == str(value), f"{key}={current!r}, expected {value!r}"


def evidence_present_and_fresh(base_dir: Path, evidence_path_key: str, max_age_days: int, evidence_index: dict[str, str]) -> None:
    assert evidence_path_key in evidence_index, f"missing evidence key {evidence_path_key}"
    path = base_dir / evidence_index[evidence_path_key]
    assert path.exists(), f"missing evidence document: {path}"
    age_days = (datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) / 86400
    assert age_days <= max_age_days, f"evidence stale: {age_days:.0f}d > {max_age_days}d"


def control_id_referenced_in_code(base_dir: Path, control_id: str) -> None:
    source_pattern_present(base_dir, re.escape(control_id), "**/*")


ASSERTIONS = {
    "ledger_annotation_has_companion_field": ledger_annotation_has_companion_field,
    "ledger_tier_all_encrypted": ledger_tier_all_encrypted,
    "source_pattern_present": source_pattern_present,
    "source_pattern_absent": source_pattern_absent,
    "every_route_has_guard": every_route_has_guard,
    "config_key_equals": config_key_equals,
    "evidence_present_and_fresh": evidence_present_and_fresh,
    "control_id_referenced_in_code": control_id_referenced_in_code,
}


def _fields_for_tier(fields: list[dict[str, Any]], tier: str | None) -> list[dict[str, Any]]:
    if not tier:
        return fields
    return [field for field in fields if str(field.get("classification", "")).lower() == tier.lower()]


def _has_annotation(field: dict[str, Any], annotation: str) -> bool:
    annotations = field.get("annotations", [])
    if isinstance(annotations, list):
        for item in annotations:
            if item == annotation:
                return True
            if isinstance(item, dict) and item.get("name") == annotation:
                return True
    return field.get(annotation) is True


def _first_existing(base_dir: Path, paths: list[str]) -> Path | None:
    for path in paths:
        candidate = base_dir / path
        if candidate.exists():
            return candidate
    return None


def _as_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return value
