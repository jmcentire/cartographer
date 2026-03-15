"""Arbiter compatibility checker."""

from __future__ import annotations

import json
from pathlib import Path

from cartographer.compatibility.base import CompatibilityChecker
from cartographer.config.loader import CartographerConfig
from cartographer.models import CheckResult, Severity


class ArbiterChecker(CompatibilityChecker):
    @property
    def tool_name(self) -> str:
        return "arbiter"

    def check(self, config: CartographerConfig, base_dir: Path) -> list[CheckResult]:
        results: list[CheckResult] = []

        registry_path = _find_registry(config, base_dir)
        if registry_path is None:
            results.append(CheckResult(
                check_id="arbiter_registry_exists",
                target=".arbiter/registry/",
                severity=Severity.INFO,
                status="INFO",
                message="no arbiter registry found",
                tool="arbiter",
            ))
            return results

        # Check access_graph.json
        access_graph = registry_path / "access_graph.json"
        if not access_graph.exists():
            # Also check parent
            access_graph = base_dir / "access_graph.json"

        if not access_graph.exists():
            results.append(CheckResult(
                check_id="access_graph_exists",
                target="access_graph.json",
                severity=Severity.FAIL,
                status="FAIL",
                message="not found — run pact build first",
                tool="arbiter",
            ))
        else:
            try:
                with open(access_graph) as f:
                    json.load(f)
                results.append(CheckResult(
                    check_id="access_graph_exists",
                    target=str(access_graph),
                    severity=Severity.FAIL,
                    status="PASS",
                    message="present and readable",
                    tool="arbiter",
                ))
            except Exception:
                results.append(CheckResult(
                    check_id="access_graph_valid",
                    target=str(access_graph),
                    severity=Severity.FAIL,
                    status="FAIL",
                    message="Invalid JSON",
                    tool="arbiter",
                ))

        # Check trust ledger
        trust_ledger = registry_path / "trust_ledger.json"
        if not trust_ledger.exists():
            trust_ledger = base_dir / "trust_ledger.json"

        if trust_ledger.exists():
            try:
                with open(trust_ledger) as f:
                    json.load(f)
                results.append(CheckResult(
                    check_id="trust_ledger_readable",
                    target=str(trust_ledger),
                    severity=Severity.FAIL,
                    status="PASS",
                    message="present and readable",
                    tool="arbiter",
                ))
            except Exception:
                results.append(CheckResult(
                    check_id="trust_ledger_valid",
                    target=str(trust_ledger),
                    severity=Severity.FAIL,
                    status="FAIL",
                    message="Invalid JSON",
                    tool="arbiter",
                ))

        return results


def _find_registry(config: CartographerConfig, base_dir: Path) -> Path | None:
    if config.stack.arbiter_registry:
        p = Path(config.stack.arbiter_registry)
        return p if p.is_absolute() and p.exists() else (base_dir / p if (base_dir / p).exists() else None)
    for name in [".arbiter/registry", ".arbiter"]:
        candidate = base_dir / name
        if candidate.exists():
            return candidate
    return None
