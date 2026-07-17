from __future__ import annotations

import pytest
import time

from cartographer.compliance.detectors import evaluate_control
from cartographer.compliance.render.assertions import source_pattern_present
from cartographer.compliance.registry import ControlDef
from cartographer.compliance.runner import run_compliance
from cartographer.config.loader import CartographerConfig


def test_ledger_obligation_passes_when_annotation_has_companion(tmp_path):
    registry = tmp_path / ".ledger" / "registry"
    registry.mkdir(parents=True)
    (registry / "users.yaml").write_text(
        """
fields:
  - name: email
    classification: PII
    annotations: [gdpr_erasable, encrypted_at_rest]
    erasure_method: anonymize
"""
    )
    control = ControlDef(
        id="GDPR-ART17-ERASURE",
        family="privacy",
        framework_ref="Art.17",
        title="erasure",
        detection={"method": "ledger_obligation", "tier": "PII", "required_annotation": "gdpr_erasable", "required_field_key": "erasure_method"},
    )

    result = evaluate_control(control, CartographerConfig(), tmp_path)

    assert result.verdict == "present"


def test_ledger_obligation_accepts_named_annotation_objects(tmp_path):
    registry = tmp_path / ".ledger" / "registry"
    registry.mkdir(parents=True)
    (registry / "users.yaml").write_text(
        """
fields:
  - name: email
    classification: PII
    annotations:
      - name: gdpr_erasable
      - name: encrypted_at_rest
    erasure_method: anonymize
"""
    )
    control = ControlDef(
        id="GDPR-ART17-ERASURE",
        family="privacy",
        framework_ref="Art.17",
        title="erasure",
        detection={"method": "ledger_obligation", "tier": "PII", "required_annotation": "gdpr_erasable", "required_field_key": "erasure_method"},
    )

    result = evaluate_control(control, CartographerConfig(), tmp_path)

    assert result.verdict == "present"


def test_ledger_tier_encrypted_reports_partial(tmp_path):
    registry = tmp_path / ".ledger" / "registry"
    registry.mkdir(parents=True)
    (registry / "users.yaml").write_text(
        """
fields:
  - name: email
    classification: PII
    annotations: [encrypted_at_rest]
  - name: phone
    classification: PII
"""
    )
    control = ControlDef(
        id="HIPAA-PHI-ENCRYPTION",
        family="security",
        framework_ref="164.312",
        title="encryption",
        detection={"method": "ledger_tier_encrypted", "tier": "PII"},
    )

    result = evaluate_control(control, CartographerConfig(), tmp_path)

    assert result.verdict == "partial"
    assert "phone" in result.uncovered[0]


def test_evidence_doc_detects_stale_artifact(tmp_path):
    evidence = tmp_path / "docs" / "dpia.md"
    evidence.parent.mkdir()
    evidence.write_text("old")
    old = time.time() - (10 * 86400)
    evidence.touch()
    import os

    os.utime(evidence, (old, old))
    config = CartographerConfig(
        compliance={
            "evidence_index": {"dpia": "docs/dpia.md"},
        }
    )
    control = ControlDef(
        id="GDPR-ART35-DPIA",
        family="accountability",
        framework_ref="Art.35",
        title="dpia",
        detection={"method": "evidence_doc", "evidence_path_key": "dpia", "max_age_days": 1},
    )

    result = evaluate_control(control, config, tmp_path)

    assert result.verdict == "partial"
    assert "stale" in result.message


def test_source_grep_absence_passes(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("def safe(): return True\n")
    control = ControlDef(
        id="NO-DEBUG",
        family="security",
        framework_ref="local",
        title="no debug",
        detection={"method": "source_grep", "none_of": ["debug=True"], "include_glob": "src/*.py"},
    )

    result = evaluate_control(control, CartographerConfig(), tmp_path)

    assert result.verdict == "present"


def test_source_grep_excludes_matching_globs(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("safe()\n")
    (src / "registry.yaml").write_text("store cvv\n")
    control = ControlDef(
        id="PCIDSS-3-3-SENSITIVE-AUTH-DATA",
        family="security",
        framework_ref="local",
        title="no card data storage",
        detection={
            "method": "source_grep",
            "none_of": ["store.*cvv"],
            "include_glob": "src/*",
            "exclude_glob": ["src/registry.yaml"],
        },
    )

    result = evaluate_control(control, CartographerConfig(), tmp_path)

    assert result.verdict == "present"


def test_source_grep_accepts_multiple_include_globs(tmp_path):
    (tmp_path / "services" / "gateway" / "src").mkdir(parents=True)
    (tmp_path / "services" / "gateway" / "src" / "app.py").write_text("require_mfa()\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("MFA\n")
    control = ControlDef(
        id="MFA-SOURCE",
        family="security",
        framework_ref="local",
        title="mfa source",
        detection={"method": "source_grep", "any_of": ["require_mfa"], "include_glob": ["src/**", "services/*/src/**"]},
    )

    result = evaluate_control(control, CartographerConfig(), tmp_path)

    assert result.verdict == "present"
    assert "services/gateway/src/app.py" in result.target


def test_source_grep_ignores_tool_cache_and_generated_compliance_artifacts(tmp_path):
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".pytest_cache" / "CACHEDIR.TAG").write_text("https\n")
    (tmp_path / ".claude" / "worktrees" / "agent-a" / "src").mkdir(parents=True)
    (tmp_path / ".claude" / "worktrees" / "agent-a" / "src" / "scratch.py").write_text("https\n")
    (tmp_path / "compliance" / "controls").mkdir(parents=True)
    (tmp_path / "compliance" / "controls" / "local.yaml").write_text("https\n")
    (tmp_path / "tests" / "compliance").mkdir(parents=True)
    (tmp_path / "tests" / "compliance" / "test_generated.py").write_text("https\n")
    (tmp_path / "src" / "cartographer" / "compliance" / "frameworks").mkdir(parents=True)
    (tmp_path / "src" / "cartographer" / "compliance" / "frameworks" / "pcidss.yaml").write_text("https\n")
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src" / "app.py").write_text("def app(): return True\n")
    control = ControlDef(
        id="TLS-EVIDENCE",
        family="security",
        framework_ref="local",
        title="tls evidence",
        detection={"method": "source_grep", "any_of": ["https"], "include_glob": "**/*"},
    )

    result = evaluate_control(control, CartographerConfig(), tmp_path)

    assert result.verdict == "missing"


def test_source_grep_ignores_terraform_provider_cache(tmp_path):
    provider = tmp_path / "infra" / ".terraform" / "providers" / "provider"
    provider.parent.mkdir(parents=True)
    provider.write_text("store cvv\n")
    control = ControlDef(
        id="NO-CARD-DATA",
        family="security",
        framework_ref="local",
        title="no card data",
        detection={"method": "source_grep", "none_of": ["store.*cvv"], "include_glob": "**/*"},
    )

    result = evaluate_control(control, CartographerConfig(), tmp_path)

    assert result.verdict == "present"


def test_source_grep_ignores_binary_files(tmp_path):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"\x7fELF\x00store cvv")
    control = ControlDef(
        id="NO-CARD-DATA",
        family="security",
        framework_ref="local",
        title="no card data",
        detection={"method": "source_grep", "none_of": ["store.*cvv"], "include_glob": "**/*"},
    )

    result = evaluate_control(control, CartographerConfig(), tmp_path)

    assert result.verdict == "present"


def test_generated_assertions_ignore_tool_cache_artifacts(tmp_path):
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".pytest_cache" / "CACHEDIR.TAG").write_text("https\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def app(): return True\n")

    with pytest.raises(AssertionError, match="pattern not found"):
        source_pattern_present(tmp_path, "https", "**/*")


def test_pcidss_controls_skip_without_payment_scope_tag(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("totp = 'not real MFA evidence'\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.html").write_text("https://example.com/event-log\n")

    checks = run_compliance(CartographerConfig(), tmp_path, ["pcidss"])

    assert checks
    assert all(check.status == "INFO" for check in checks)
    assert any("missing project tag(s): payment_data" in check.message for check in checks)


def test_pcidss_payment_scope_uses_source_not_docs_for_code_controls(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def app(): return True\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.html").write_text("https://example.com/event-log MFA\n")

    checks = run_compliance(CartographerConfig(compliance={"project_tags": ["payment_data"]}), tmp_path, ["pcidss"])
    by_id = {check.check_id: check for check in checks}

    assert by_id["PCIDSS-4-2-TRANSMISSION-ENCRYPTION"].status == "FAIL"
    assert by_id["PCIDSS-4-2-TRANSMISSION-ENCRYPTION"].target.startswith("src/**,")
    assert by_id["PCIDSS-8-4-MFA"].status == "FAIL"
    assert by_id["PCIDSS-10-2-AUDIT-LOGGING"].status == "FAIL"


def test_route_guard_respects_public_routes_and_user_claims(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text(
        """
from fastapi import FastAPI, Request

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/secure")
def secure(request: Request):
    claims = request.state.user_claims
    return {"sub": claims["sub"]}
"""
    )
    config = CartographerConfig(
        compliance={"public_route_patterns": [r"^/health$"]},
    )
    control = ControlDef(
        id="ACCESS-CONTROL",
        family="security",
        framework_ref="local",
        title="route guards",
        detection={"method": "route_guard"},
    )

    result = evaluate_control(control, config, tmp_path)

    assert result.verdict == "present"
