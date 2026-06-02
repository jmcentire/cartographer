"""Mechanical compliance detectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Callable

import yaml

from cartographer.compliance.files import matching_files
from cartographer.compatibility.ledger_checker import _find_registry
from cartographer.config.loader import CartographerConfig
from cartographer.discovery.scanner import scan_source
from cartographer.compliance.registry import ControlDef, DetectionDef


@dataclass
class DetectionResult:
    verdict: str
    target: str
    message: str
    uncovered: list[str] = field(default_factory=list)


Detector = Callable[[DetectionDef, ControlDef, CartographerConfig, Path, bool], DetectionResult]


def evaluate_control(
    control: ControlDef,
    config: CartographerConfig,
    base_dir: Path,
    with_llm: bool = False,
) -> DetectionResult:
    applicability = _check_applicability(control, config, base_dir)
    if applicability is not None:
        return applicability

    detector = DETECTORS.get(control.detection.method)
    if detector is None:
        return DetectionResult("missing", control.id, f"unknown detector: {control.detection.method}")

    result = detector(control.detection, control, config, base_dir, with_llm)
    if result.verdict != "present":
        return result

    for corroborating in control.corroborating_detection:
        corroborator = DETECTORS.get(corroborating.method)
        if corroborator is None:
            return DetectionResult("partial", result.target, f"unknown corroborating detector: {corroborating.method}")
        cor_result = corroborator(corroborating, control, config, base_dir, with_llm)
        if cor_result.verdict != "present":
            return DetectionResult("partial", cor_result.target, f"corroborating check: {cor_result.message}", cor_result.uncovered)
    return result


def load_ledger_fields(config: CartographerConfig, base_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    registry = _find_registry(config, base_dir)
    if registry is None:
        return []

    fields: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(registry.rglob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text()) or {}
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        raw_fields = data.get("fields", [])
        if not isinstance(raw_fields, list):
            continue
        for field in raw_fields:
            if isinstance(field, dict):
                fields.append((path, field))
    return fields


def ledger_obligation(
    detection: DetectionDef,
    control: ControlDef,
    config: CartographerConfig,
    base_dir: Path,
    with_llm: bool = False,
) -> DetectionResult:
    fields = _ledger_fields_for_tier(config, base_dir, _field(detection, "tier") or control.classification_tier)
    if not fields:
        return DetectionResult("skipped", "ledger", "no matching Ledger fields")

    required_annotation = _field(detection, "required_annotation")
    companion = _field(detection, "required_field_key")
    in_scope = [(p, f) for p, f in fields if not required_annotation or _has_annotation(f, required_annotation)]
    if not in_scope:
        return DetectionResult("missing", "ledger", f"no fields carry annotation {required_annotation}")

    missing = [f"{path}:{field.get('name', '<unnamed>')}" for path, field in in_scope if companion and companion not in field]
    if not missing:
        return DetectionResult("present", "ledger", f"{len(in_scope)} Ledger field(s) satisfy {required_annotation}")
    verdict = "missing" if len(missing) == len(in_scope) else "partial"
    return DetectionResult(verdict, "ledger", f"{len(missing)} field(s) missing {companion}", missing)


def ledger_tier_encrypted(
    detection: DetectionDef,
    control: ControlDef,
    config: CartographerConfig,
    base_dir: Path,
    with_llm: bool = False,
) -> DetectionResult:
    fields = _ledger_fields_for_tier(config, base_dir, _field(detection, "tier") or control.classification_tier)
    if not fields:
        return DetectionResult("skipped", "ledger", "no matching Ledger fields")
    missing = [
        f"{path}:{field.get('name', '<unnamed>')}"
        for path, field in fields
        if not _has_annotation(field, "encrypted_at_rest")
    ]
    if not missing:
        return DetectionResult("present", "ledger", f"{len(fields)} Ledger field(s) encrypted at rest")
    verdict = "missing" if len(missing) == len(fields) else "partial"
    return DetectionResult(verdict, "ledger", f"{len(missing)} field(s) missing encrypted_at_rest", missing)


def source_grep(
    detection: DetectionDef,
    control: ControlDef,
    config: CartographerConfig,
    base_dir: Path,
    with_llm: bool = False,
) -> DetectionResult:
    include = _field(detection, "include_glob") or "**/*"
    exclude = _field(detection, "exclude_glob") or []
    excludes = [exclude] if isinstance(exclude, str) else list(exclude)
    any_of = list(_field(detection, "any_of") or [])
    none_of = list(_field(detection, "none_of") or [])
    files = matching_files(base_dir, include, excludes)

    if any_of:
        for path in files:
            text = _read(path)
            for pattern in any_of:
                if re.search(pattern, text, re.MULTILINE):
                    return DetectionResult("present", str(path), f"matched {pattern}")
        return DetectionResult("missing", _target_label(include), f"none of {any_of} found")

    if none_of:
        matches: list[str] = []
        for path in files:
            text = _read(path)
            for pattern in none_of:
                if re.search(pattern, text, re.MULTILINE):
                    matches.append(f"{path}:{pattern}")
        if matches:
            return DetectionResult("missing", include, f"forbidden pattern(s) found", matches)
        return DetectionResult("present", _target_label(include), "forbidden patterns absent")

    return DetectionResult("skipped", _target_label(include), "no source_grep patterns configured")


def route_guard(
    detection: DetectionDef,
    control: ControlDef,
    config: CartographerConfig,
    base_dir: Path,
    with_llm: bool = False,
) -> DetectionResult:
    routes = scan_source(config, base_dir).routes
    if not routes:
        return DetectionResult("skipped", "routes", "no routes discovered")
    guard_patterns = list(_field(detection, "guard_patterns") or ["Depends", "require_role", "require_auth"])
    guard_patterns.extend(["user_claims", "request.state.user_claims"])
    exclude_patterns = list(_field(detection, "exclude_path_patterns") or [])
    exclude_patterns.extend(config.compliance.public_route_patterns)
    uncovered: list[str] = []
    for route in routes:
        if _route_excluded(route.path, exclude_patterns):
            continue
        path = Path(route.source_file)
        text = _line_window(path, route.line, 30)
        if not any(re.search(pattern, text) for pattern in guard_patterns):
            uncovered.append(f"{route.method} {route.path} ({route.source_file}:{route.line})")
    if not uncovered:
        return DetectionResult("present", "routes", f"{len(routes)} route(s) have guard evidence")
    verdict = "missing" if len(uncovered) == len(routes) else "partial"
    return DetectionResult(verdict, "routes", f"{len(uncovered)} route(s) lack guard evidence", uncovered)


def config_present(
    detection: DetectionDef,
    control: ControlDef,
    config: CartographerConfig,
    base_dir: Path,
    with_llm: bool = False,
) -> DetectionResult:
    path = _resolve(base_dir, str(_field(detection, "path") or ""))
    if not path.exists():
        return DetectionResult("missing", str(path), "config file missing")
    key = _field(detection, "required_key")
    expected = _field(detection, "required_value")
    if not key:
        return DetectionResult("present", str(path), "config file present")
    data = _load_yaml_or_text(path)
    value = _lookup(data, str(key))
    if value is None and str(key) not in _read(path):
        return DetectionResult("missing", str(path), f"required key {key} missing")
    if expected is not None and str(value) != str(expected) and str(expected) not in _read(path):
        return DetectionResult("missing", str(path), f"{key} does not equal {expected}")
    return DetectionResult("present", str(path), f"{key} present")


def companion_config(
    detection: DetectionDef,
    control: ControlDef,
    config: CartographerConfig,
    base_dir: Path,
    with_llm: bool = False,
) -> DetectionResult:
    tool = str(_field(detection, "tool") or "").lower()
    candidates = {
        "baton": [config.stack.baton_config, "baton.yaml"],
        "pact": [config.stack.pact_project_dir, "pact.yaml", ".pact"],
        "ledger": [config.stack.ledger_registry, ".ledger/registry", ".ledger"],
        "sentinel": [config.stack.sentinel_manifest, ".sentinel/manifest.json", "sentinel.yaml"],
        "arbiter": [config.stack.arbiter_registry, ".arbiter", "arbiter.yaml"],
    }.get(tool, [f"{tool}.yaml"])
    for candidate in candidates:
        if candidate and _resolve(base_dir, candidate).exists():
            return DetectionResult("present", candidate, f"{tool} companion config present")
    return DetectionResult("missing", tool, f"{tool} companion config missing")


def evidence_doc(
    detection: DetectionDef,
    control: ControlDef,
    config: CartographerConfig,
    base_dir: Path,
    with_llm: bool = False,
) -> DetectionResult:
    key = str(_field(detection, "evidence_path_key") or "")
    rel = config.compliance.evidence_index.get(key)
    if not rel:
        return DetectionResult("missing", key, "evidence path key missing from config")
    path = _resolve(base_dir, rel)
    if not path.exists():
        return DetectionResult("missing", str(path), "evidence document missing")
    max_age_days = int(_field(detection, "max_age_days") or 365)
    age_days = (datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) / 86400
    if age_days > max_age_days:
        return DetectionResult("partial", str(path), f"evidence document stale ({age_days:.0f}d old)")
    return DetectionResult("present", str(path), "evidence document present and fresh")


def llm_judgment(
    detection: DetectionDef,
    control: ControlDef,
    config: CartographerConfig,
    base_dir: Path,
    with_llm: bool = False,
) -> DetectionResult:
    if not with_llm:
        return DetectionResult("skipped", control.id, "llm_judgment skipped; pass --with-llm to enable")
    return DetectionResult("skipped", control.id, "llm_judgment adapter is configured but no provider call was made")


DETECTORS: dict[str, Detector] = {
    "ledger_obligation": ledger_obligation,
    "ledger_tier_encrypted": ledger_tier_encrypted,
    "source_grep": source_grep,
    "route_guard": route_guard,
    "config_present": config_present,
    "companion_config": companion_config,
    "evidence_doc": evidence_doc,
    "llm_judgment": llm_judgment,
}


def _check_applicability(control: ControlDef, config: CartographerConfig, base_dir: Path) -> DetectionResult | None:
    app = control.applicability
    if app.get("requires_ledger_registry") and _find_registry(config, base_dir) is None:
        return DetectionResult("skipped", "ledger", "control requires Ledger registry")
    tags = set(app.get("tags") or [])
    if tags and not tags.issubset(set(config.compliance.project_tags)):
        return DetectionResult("skipped", control.id, f"missing project tag(s): {', '.join(sorted(tags))}")
    data_tiers = set(str(t).lower() for t in (app.get("data_tiers") or []))
    if data_tiers:
        present = {str(field.get("classification", "")).lower() for _, field in load_ledger_fields(config, base_dir)}
        if not data_tiers.intersection(present):
            return DetectionResult("skipped", "ledger", f"no Ledger fields for tier(s): {', '.join(sorted(data_tiers))}")
    return None


def _ledger_fields_for_tier(config: CartographerConfig, base_dir: Path, tier: str | None) -> list[tuple[Path, dict[str, Any]]]:
    fields = load_ledger_fields(config, base_dir)
    if not tier:
        return fields
    wanted = tier.lower()
    return [(path, field) for path, field in fields if str(field.get("classification", "")).lower() == wanted]


def _has_annotation(field: dict[str, Any], annotation: str) -> bool:
    annotations = field.get("annotations", [])
    if isinstance(annotations, list):
        for item in annotations:
            if item == annotation:
                return True
            if isinstance(item, dict) and item.get("name") == annotation:
                return True
    return field.get(annotation) is True


def _route_excluded(path: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, path) for pattern in patterns)


def _field(model: DetectionDef, name: str) -> Any:
    return getattr(model, name, None)


def _target_label(value: Any) -> str:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value)


def _resolve(base_dir: Path, path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else base_dir / p


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _line_window(path: Path, line: int, radius: int) -> str:
    lines = _read(path).splitlines()
    start = max(0, line - radius - 1)
    end = min(len(lines), line + radius)
    return "\n".join(lines[start:end])


def _load_yaml_or_text(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text()) or {}
    except Exception:
        return path.read_text(errors="replace")


def _lookup(data: Any, dotted: str) -> Any:
    current = data
    for part in dotted.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current
