"""Sentinel compatibility checker."""

from __future__ import annotations

import json
import re
from pathlib import Path

from cartographer.compatibility.base import CompatibilityChecker
from cartographer.config.loader import CartographerConfig
from cartographer.models import CheckResult, Severity


class SentinelChecker(CompatibilityChecker):
    @property
    def tool_name(self) -> str:
        return "sentinel"

    def check(self, config: CartographerConfig, base_dir: Path) -> list[CheckResult]:
        results: list[CheckResult] = []

        manifest_path = _find_manifest(config, base_dir)
        if manifest_path is None:
            results.append(CheckResult(
                check_id="sentinel_manifest_exists",
                target=".sentinel/manifest.json",
                severity=Severity.INFO,
                status="INFO",
                message="no sentinel manifest found",
                tool="sentinel",
            ))
            return results

        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except Exception:
            results.append(CheckResult(
                check_id="sentinel_manifest_valid",
                target=str(manifest_path),
                severity=Severity.FAIL,
                status="FAIL",
                message="Invalid JSON",
                tool="sentinel",
            ))
            return results

        entries = manifest.get("entries", [])
        if not isinstance(entries, list):
            entries = []

        manifest_keys = {e.get("pact_key") for e in entries if isinstance(e, dict)}

        # Check manifest entries have required fields
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            pk = entry.get("pact_key", "unknown")

            if "contract_path" not in entry or entry["contract_path"] is None:
                results.append(CheckResult(
                    check_id="all_manifest_entries_have_contract_path",
                    target=pk,
                    severity=Severity.FAIL,
                    status="FAIL",
                    message="missing contract_path",
                    tool="sentinel",
                ))
            if "test_path" not in entry or entry["test_path"] is None:
                results.append(CheckResult(
                    check_id="all_manifest_entries_have_test_path",
                    target=pk,
                    severity=Severity.FAIL,
                    status="FAIL",
                    message="missing test_path",
                    tool="sentinel",
                ))
            if "source_path" not in entry and "source_file" not in entry:
                results.append(CheckResult(
                    check_id="all_manifest_entries_have_source_path",
                    target=pk,
                    severity=Severity.FAIL,
                    status="FAIL",
                    message="missing source_path",
                    tool="sentinel",
                ))

        # Scan source for PACT keys not in manifest
        pact_key_re = re.compile(config.compatibility.pact_key_format)
        source_keys: set[str] = set()
        source_cfg = config.targets.source
        for d in source_cfg.dirs:
            src = base_dir / d
            if not src.exists():
                continue
            for f in src.rglob("*.py"):
                if any(part in source_cfg.exclude for part in f.parts):
                    continue
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                for match in pact_key_re.finditer(content):
                    source_keys.add(match.group(0))

        missing = source_keys - manifest_keys
        if missing:
            results.append(CheckResult(
                check_id="all_source_pact_keys_in_manifest",
                target=str(manifest_path),
                severity=Severity.WARN,
                status="WARN",
                message=f"{len(missing)} PACT keys in source not in manifest",
                tool="sentinel",
            ))

        # Integration checks
        if config.stack.pact_project_dir:
            results.append(CheckResult(
                check_id="pact_configured",
                target="stack.pact_project_dir",
                severity=Severity.INFO,
                status="PASS",
                message="Pact project configured",
                tool="sentinel",
            ))
        else:
            results.append(CheckResult(
                check_id="pact_configured",
                target="stack.pact_project_dir",
                severity=Severity.INFO,
                status="INFO",
                message="Pact project not configured",
                tool="sentinel",
            ))

        if config.stack.arbiter_registry:
            results.append(CheckResult(
                check_id="arbiter_configured",
                target="stack.arbiter_registry",
                severity=Severity.INFO,
                status="PASS",
                message="Arbiter registry configured",
                tool="sentinel",
            ))
        else:
            results.append(CheckResult(
                check_id="arbiter_configured",
                target="stack.arbiter_registry",
                severity=Severity.INFO,
                status="INFO",
                message="Arbiter registry not configured",
                tool="sentinel",
            ))

        return results


def _find_manifest(config: CartographerConfig, base_dir: Path) -> Path | None:
    if config.stack.sentinel_manifest:
        p = Path(config.stack.sentinel_manifest)
        return p if p.is_absolute() and p.exists() else (base_dir / p if (base_dir / p).exists() else None)
    for name in [".sentinel/manifest.json", "sentinel_manifest.json"]:
        candidate = base_dir / name
        if candidate.exists():
            return candidate
    return None
