"""Baton compatibility checker."""

from __future__ import annotations

from pathlib import Path

import yaml

from cartographer.compatibility.base import CompatibilityChecker
from cartographer.config.loader import CartographerConfig
from cartographer.models import CheckResult, Severity


class BatonChecker(CompatibilityChecker):
    @property
    def tool_name(self) -> str:
        return "baton"

    def check(self, config: CartographerConfig, base_dir: Path) -> list[CheckResult]:
        results: list[CheckResult] = []

        baton_path = _find_baton_config(config, base_dir)
        if baton_path is None:
            results.append(CheckResult(
                check_id="baton_yaml_exists",
                target="baton.yaml",
                severity=Severity.INFO,
                status="INFO",
                message="no baton.yaml found",
                tool="baton",
            ))
            return results

        try:
            with open(baton_path) as f:
                baton = yaml.safe_load(f)
        except Exception:
            results.append(CheckResult(
                check_id="baton_yaml_valid",
                target=str(baton_path),
                severity=Severity.FAIL,
                status="FAIL",
                message="Invalid YAML",
                tool="baton",
            ))
            return results

        if not isinstance(baton, dict):
            return results

        # baton_yaml_version_current
        version = str(baton.get("version", "1.0"))
        min_version = config.compatibility.min_baton_schema_version
        if _version_lt(version, min_version):
            results.append(CheckResult(
                check_id="baton_yaml_version_current",
                target=str(baton_path),
                severity=Severity.FAIL,
                status="FAIL",
                message=f"version {version}, requires {min_version}",
                tool="baton",
            ))
        else:
            results.append(CheckResult(
                check_id="baton_yaml_version_current",
                target=str(baton_path),
                severity=Severity.FAIL,
                status="PASS",
                message=f"version {version}",
                tool="baton",
            ))

        # Check nodes
        nodes = baton.get("nodes", [])
        for node in nodes:
            if not isinstance(node, dict):
                continue
            name = node.get("name", "unknown")

            if "data_access" not in node:
                results.append(CheckResult(
                    check_id="all_nodes_have_data_access",
                    target=f"node: {name}",
                    severity=Severity.WARN,
                    status="WARN",
                    message="data_access not declared",
                    tool="baton",
                ))

            if "authority" not in node:
                results.append(CheckResult(
                    check_id="all_nodes_have_authority_declared",
                    target=f"node: {name}",
                    severity=Severity.WARN,
                    status="WARN",
                    message="authority not declared",
                    tool="baton",
                ))

            protocol = node.get("protocol", "")
            if protocol == "http" and "openapi_spec" not in node:
                results.append(CheckResult(
                    check_id="openapi_spec_present_for_http_nodes",
                    target=f"node: {name}",
                    severity=Severity.WARN,
                    status="WARN",
                    message="no openapi_spec configured",
                    tool="baton",
                ))

        # Global config checks
        global_cfg = baton.get("global", {})
        if not isinstance(global_cfg, dict):
            global_cfg = {}

        if "arbiter" not in global_cfg:
            results.append(CheckResult(
                check_id="arbiter_endpoint_configured",
                target=str(baton_path),
                severity=Severity.INFO,
                status="INFO",
                message="arbiter endpoint not configured",
                tool="baton",
            ))

        if "ledger" not in global_cfg:
            results.append(CheckResult(
                check_id="ledger_endpoint_configured",
                target=str(baton_path),
                severity=Severity.INFO,
                status="INFO",
                message="ledger endpoint not configured",
                tool="baton",
            ))

        if "audit_channel" not in global_cfg:
            results.append(CheckResult(
                check_id="audit_channel_port_configured",
                target=str(baton_path),
                severity=Severity.WARN,
                status="WARN",
                message="audit_channel not configured",
                tool="baton",
            ))

        return results


def _find_baton_config(config: CartographerConfig, base_dir: Path) -> Path | None:
    if config.stack.baton_config:
        p = Path(config.stack.baton_config)
        return p if p.exists() else base_dir / p
    for name in ["baton.yaml", "baton.yml"]:
        candidate = base_dir / name
        if candidate.exists():
            return candidate
    return None


def _version_lt(a: str, b: str) -> bool:
    """Simple version comparison."""
    try:
        a_parts = [int(x) for x in a.split(".")]
        b_parts = [int(x) for x in b.split(".")]
        return a_parts < b_parts
    except ValueError:
        return a < b
