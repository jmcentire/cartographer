"""Pact compatibility checker."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from cartographer.compatibility.base import CompatibilityChecker
from cartographer.config.loader import CartographerConfig
from cartographer.models import CheckResult, Severity


class PactChecker(CompatibilityChecker):
    @property
    def tool_name(self) -> str:
        return "pact"

    def check(self, config: CartographerConfig, base_dir: Path) -> list[CheckResult]:
        results: list[CheckResult] = []
        pact_dir = config.stack.pact_project_dir
        if pact_dir is None:
            # Try common locations
            for candidate in [".pact", "contracts", "pact"]:
                if (base_dir / candidate).exists():
                    pact_dir = str(base_dir / candidate)
                    break

        # Check contracts
        if pact_dir:
            pact_path = Path(pact_dir)
            if pact_path.is_absolute():
                contract_dir = pact_path
            else:
                contract_dir = base_dir / pact_path
            results.extend(self._check_contracts(contract_dir))

        # Check source files for PACT keys and handlers
        pact_key_re = re.compile(config.compatibility.pact_key_format)
        results.extend(self._check_source(config, base_dir, pact_key_re))

        return results

    def _check_contracts(self, contract_dir: Path) -> list[CheckResult]:
        results: list[CheckResult] = []
        if not contract_dir.exists():
            return results

        for yaml_file in sorted(contract_dir.rglob("*.yaml")):
            try:
                with open(yaml_file) as f:
                    contract = yaml.safe_load(f)
            except Exception:
                results.append(CheckResult(
                    check_id="contract_valid_yaml",
                    target=str(yaml_file),
                    severity=Severity.FAIL,
                    status="FAIL",
                    message="Invalid YAML",
                    tool="pact",
                ))
                continue

            if not isinstance(contract, dict):
                continue

            # contract_has_data_access
            if "data_access" not in contract:
                results.append(CheckResult(
                    check_id="contract_has_data_access",
                    target=str(yaml_file),
                    severity=Severity.FAIL,
                    status="FAIL",
                    message="missing data_access field",
                    tool="pact",
                ))
            else:
                da = contract["data_access"]
                rationale = da.get("rationale", "") if isinstance(da, dict) else ""
                if isinstance(rationale, str) and len(rationale.strip()) < 10:
                    results.append(CheckResult(
                        check_id="contract_data_access_rationale_not_vague",
                        target=str(yaml_file),
                        severity=Severity.WARN,
                        status="WARN",
                        message="data_access.rationale is vague",
                        tool="pact",
                    ))
                else:
                    results.append(CheckResult(
                        check_id="contract_has_data_access",
                        target=str(yaml_file),
                        severity=Severity.FAIL,
                        status="PASS",
                        message="data_access present",
                        tool="pact",
                    ))

            # contract_has_authority
            if "authority" not in contract:
                results.append(CheckResult(
                    check_id="contract_has_authority",
                    target=str(yaml_file),
                    severity=Severity.FAIL,
                    status="FAIL",
                    message="missing authority field",
                    tool="pact",
                ))
            else:
                results.append(CheckResult(
                    check_id="contract_has_authority",
                    target=str(yaml_file),
                    severity=Severity.FAIL,
                    status="PASS",
                    message="authority present",
                    tool="pact",
                ))

        return results

    def _check_source(
        self,
        config: CartographerConfig,
        base_dir: Path,
        pact_key_re: re.Pattern,
    ) -> list[CheckResult]:
        results: list[CheckResult] = []
        source_dirs = config.targets.source.dirs
        exclude = config.targets.source.exclude

        py_files: list[Path] = []
        for d in source_dirs:
            src = base_dir / d
            if not src.exists():
                continue
            for f in src.rglob("*.py"):
                if any(part in exclude for part in f.parts):
                    continue
                py_files.append(f)

        for f in py_files:
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            # source_has_pact_key
            keys = pact_key_re.findall(content)
            if not keys:
                # Only flag if this looks like a substantive module
                if "class " in content or "def " in content:
                    results.append(CheckResult(
                        check_id="source_has_pact_key",
                        target=str(f),
                        severity=Severity.FAIL,
                        status="FAIL",
                        message="no PACT key found in any method",
                        tool="pact",
                    ))
            else:
                # Validate key format
                for key in keys:
                    if not pact_key_re.fullmatch(key):
                        results.append(CheckResult(
                            check_id="pact_key_format_valid",
                            target=str(f),
                            severity=Severity.FAIL,
                            status="FAIL",
                            message=f"malformed PACT key: {key}",
                            tool="pact",
                        ))

            # source_has_event_handler
            if "class " in content:
                if "event_handler" not in content:
                    results.append(CheckResult(
                        check_id="source_has_event_handler",
                        target=str(f),
                        severity=Severity.FAIL,
                        status="FAIL",
                        message="no event_handler parameter",
                        tool="pact",
                    ))
                elif "log_handler" not in content:
                    results.append(CheckResult(
                        check_id="source_has_log_handler",
                        target=str(f),
                        severity=Severity.WARN,
                        status="WARN",
                        message="event_handler present but log_handler missing",
                        tool="pact",
                    ))

        return results
