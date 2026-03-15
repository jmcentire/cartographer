"""Report generator — produces human-readable and machine-readable compatibility reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from cartographer.models import CheckResult, CompatibilityReport, Severity


def build_report(checks: list[CheckResult]) -> CompatibilityReport:
    """Build a CompatibilityReport from check results."""
    score_pass = sum(1 for c in checks if c.status == "PASS")
    score_warn = sum(1 for c in checks if c.status == "WARN")
    score_fail = sum(1 for c in checks if c.status == "FAIL")
    total = score_pass + score_warn + score_fail

    recommendations = _generate_recommendations(checks)

    return CompatibilityReport(
        generated=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        checks=checks,
        score_pass=score_pass,
        score_warn=score_warn,
        score_fail=score_fail,
        total=total,
        recommendations=recommendations,
    )


def format_text(report: CompatibilityReport) -> str:
    """Format report as human-readable text."""
    lines = [
        "CARTOGRAPHER COMPATIBILITY REPORT",
        f"generated: {report.generated}",
        "",
    ]

    # Group by tool
    by_tool: dict[str, list[CheckResult]] = {}
    for check in report.checks:
        by_tool.setdefault(check.tool.upper(), []).append(check)

    for tool, checks in sorted(by_tool.items()):
        lines.append(f"{tool} COMPATIBILITY")
        for check in checks:
            status = check.status.ljust(6)
            target = check.target
            # Truncate long paths
            if len(target) > 40:
                target = "..." + target[-37:]
            lines.append(f"  {target:<42} {status} {check.message}")
        lines.append("")

    # Overall score
    lines.append(
        f"OVERALL SCORE: {report.score_pct}% compliant "
        f"({report.score_pass}/{report.total} checks passing)"
    )
    lines.append(
        f"  FAIL: {report.score_fail}   WARN: {report.score_warn}   PASS: {report.score_pass}"
    )
    lines.append("")

    if report.recommendations:
        lines.append("RECOMMENDED NEXT STEPS (in order):")
        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"  {i}. {rec}")

    return "\n".join(lines)


def format_json(report: CompatibilityReport) -> str:
    """Format report as JSON."""
    data = {
        "generated": report.generated,
        "score": {
            "pass": report.score_pass,
            "warn": report.score_warn,
            "fail": report.score_fail,
            "total": report.total,
            "percent": report.score_pct,
        },
        "checks": [
            {
                "check_id": c.check_id,
                "target": c.target,
                "status": c.status,
                "severity": c.severity.value,
                "message": c.message,
                "tool": c.tool,
            }
            for c in report.checks
        ],
        "recommendations": report.recommendations,
    }
    return json.dumps(data, indent=2)


def save_report(report: CompatibilityReport, output_dir: Path, fmt: str = "text") -> Path:
    """Save report to file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    if fmt == "json":
        path = output_dir / f"report_{timestamp}.json"
        path.write_text(format_json(report))
    else:
        path = output_dir / f"report_{timestamp}.txt"
        path.write_text(format_text(report))

    # Also write "latest" symlink-equivalent
    latest = output_dir / f"report_latest.{fmt if fmt == 'json' else 'txt'}"
    content = format_json(report) if fmt == "json" else format_text(report)
    latest.write_text(content)

    return path


def _generate_recommendations(checks: list[CheckResult]) -> list[str]:
    """Generate ordered recommendations — FAILs before WARNs."""
    recs: list[tuple[int, str]] = []

    fail_checks = [c for c in checks if c.status == "FAIL"]
    warn_checks = [c for c in checks if c.status == "WARN"]

    # Deduplicate by check_id
    seen: set[str] = set()

    for check in fail_checks:
        if check.check_id in seen:
            continue
        seen.add(check.check_id)
        rec = _recommendation_for(check)
        if rec:
            recs.append((0, rec))

    for check in warn_checks:
        if check.check_id in seen:
            continue
        seen.add(check.check_id)
        rec = _recommendation_for(check)
        if rec:
            recs.append((1, rec))

    recs.sort(key=lambda x: x[0])
    return [r[1] for r in recs]


def _recommendation_for(check: CheckResult) -> str | None:
    """Generate a recommendation string for a check result."""
    recommendations: dict[str, str] = {
        "baton_yaml_version_current": "Update baton.yaml to schema version 2.0 (run: baton migrate-config)",
        "source_has_pact_key": f"Add PACT keys to: {check.target}",
        "source_has_event_handler": f"Add event_handler and log_handler to {check.target}",
        "contract_has_data_access": f"Add data_access field to {check.target}",
        "contract_has_authority": f"Add authority field to {check.target}",
        "all_fields_have_classification": f"Add field classifications to {check.target}",
        "access_graph_exists": "Run: pact build to regenerate access_graph.json",
        "all_source_pact_keys_in_manifest": "Update Sentinel manifest with missing PACT keys",
        "all_manifest_entries_have_contract_path": "Add contract_path to Sentinel manifest entries",
        "all_manifest_entries_have_test_path": "Add test_path to Sentinel manifest entries",
        "all_manifest_entries_have_source_path": "Add source_path to Sentinel manifest entries",
        "audit_channel_port_configured": "Configure audit_channel in baton.yaml global config",
        "gdpr_erasable_has_erasure_method": "Add erasure_method to GDPR-erasable Ledger fields",
        "no_annotation_conflicts": f"Resolve annotation conflict in {check.target}",
    }
    return recommendations.get(check.check_id, f"Fix: {check.check_id} — {check.message}")
