from __future__ import annotations

from click.testing import CliRunner

from cartographer.cli.main import main


def test_compliance_scan_help_lists_command():
    result = CliRunner().invoke(main, ["compliance", "scan", "--help"])

    assert result.exit_code == 0
    assert "Run compliance controls" in result.output


def test_add_risk_drafts_absence_control_for_must_not():
    result = CliRunner().invoke(
        main,
        [
            "compliance",
            "add-risk",
            "--framework",
            "gdpr",
            "--describe",
            "Immigration status must not appear in CSV exports",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "none_of" in result.output
    assert "source_pattern_absent" in result.output


def test_gen_tests_uses_configured_tests_dir(tmp_path, monkeypatch):
    controls = tmp_path / "compliance" / "controls"
    controls.mkdir(parents=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("audit()\n")
    (tmp_path / "cartographer.yaml").write_text(
        """
compliance:
  frameworks: [local]
  tests_dir: generated/compliance
"""
    )
    (controls / "local.yaml").write_text(
        """
framework: local
controls:
  - id: LOCAL-AUDIT
    family: local
    framework_ref: local
    title: audit exists
    severity: must
    detection: {method: source_grep, any_of: ["audit"], include_glob: "src/*.py"}
    validation_test: {style: static_assertion, assertion: source_pattern_present, params: {pattern: "audit", include_glob: "src/*.py"}}
"""
    )

    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["compliance", "gen-tests"])

    assert result.exit_code == 0
    assert (tmp_path / "generated" / "compliance" / "test_local_audit.py").exists()
