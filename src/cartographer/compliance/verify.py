"""Compliance baseline and regression verification."""

from __future__ import annotations

import json
from pathlib import Path

from cartographer.compliance.runner import run_compliance
from cartographer.config.loader import CartographerConfig
from cartographer.report.generator import build_report


def baseline_path(config: CartographerConfig, base_dir: Path) -> Path:
    path = Path(config.compliance.baseline)
    return path if path.is_absolute() else base_dir / path


def write_baseline(
    config: CartographerConfig,
    base_dir: Path,
    frameworks: list[str] | None = None,
    with_llm: bool = False,
) -> Path:
    report = build_report(run_compliance(config, base_dir, frameworks, with_llm=with_llm))
    path = baseline_path(config, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_baseline_payload(report), indent=2))
    return path


def verify_baseline(
    config: CartographerConfig,
    base_dir: Path,
    frameworks: list[str] | None = None,
    with_llm: bool = False,
) -> tuple[bool, list[str]]:
    path = baseline_path(config, base_dir)
    if not path.exists():
        return False, [f"baseline missing: {path}"]

    baseline = json.loads(path.read_text())
    report = build_report(run_compliance(config, base_dir, frameworks, with_llm=with_llm))
    current = {check.check_id: check.status for check in report.checks}
    regressions: list[str] = []

    for check_id, status in (baseline.get("checks") or {}).items():
        now = current.get(check_id, "ABSENT")
        if status == "PASS" and now != "PASS":
            regressions.append(f"{check_id}: PASS -> {now}")

    baseline_score = float(baseline.get("score_pct", 100.0))
    if report.score_pct < baseline_score:
        regressions.append(f"score_pct: {baseline_score} -> {report.score_pct}")

    return not regressions, regressions


def _baseline_payload(report) -> dict:
    return {
        "generated": report.generated,
        "score_pct": report.score_pct,
        "checks": {check.check_id: check.status for check in report.checks},
    }
