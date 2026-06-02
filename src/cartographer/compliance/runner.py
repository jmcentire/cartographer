"""Compliance scan runner."""

from __future__ import annotations

from pathlib import Path

from cartographer.compatibility.base import CompatibilityChecker
from cartographer.compliance.detectors import DetectionResult, evaluate_control
from cartographer.compliance.registry import FrameworkProfile, load_frameworks
from cartographer.config.loader import CartographerConfig
from cartographer.models import CheckResult, Severity


class FrameworkChecker(CompatibilityChecker):
    def __init__(self, profile: FrameworkProfile, with_llm: bool = False) -> None:
        self.profile = profile
        self.with_llm = with_llm

    @property
    def tool_name(self) -> str:
        return self.profile.framework

    def check(self, config: CartographerConfig, base_dir: Path) -> list[CheckResult]:
        return [
            _to_check_result(self.profile.framework, control.id, control.severity, evaluate_control(control, config, base_dir, self.with_llm))
            for control in self.profile.controls
        ]


def run_compliance(
    config: CartographerConfig,
    base_dir: Path,
    frameworks: list[str] | None = None,
    with_llm: bool = False,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    for profile in load_frameworks(config, base_dir, frameworks):
        results.extend(FrameworkChecker(profile, with_llm=with_llm).check(config, base_dir))
    return results


def _to_check_result(
    framework: str,
    check_id: str,
    control_severity: str,
    result: DetectionResult,
) -> CheckResult:
    if result.verdict == "present":
        status = "PASS"
    elif result.verdict == "partial":
        status = "WARN"
    elif result.verdict == "skipped":
        status = "INFO"
    else:
        status = "FAIL" if control_severity == "must" else "WARN"

    severity = Severity.INFO
    if status == "INFO":
        severity = Severity.INFO
    elif status == "FAIL":
        severity = Severity.FAIL
    elif status == "WARN":
        severity = Severity.WARN
    elif control_severity == "must":
        severity = Severity.FAIL
    elif control_severity == "should":
        severity = Severity.WARN

    msg = result.message
    if result.uncovered:
        msg = f"{msg}; uncovered: {', '.join(result.uncovered[:3])}"
    return CheckResult(
        check_id=check_id,
        target=result.target,
        severity=severity,
        status=status,
        message=msg,
        tool=framework,
    )
