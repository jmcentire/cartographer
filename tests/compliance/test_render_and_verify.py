from __future__ import annotations

import importlib.util

from cartographer.compliance.registry import ControlDef
from cartographer.compliance.render.static import render_static_tests
from cartographer.compliance.verify import verify_baseline, write_baseline
from cartographer.config.loader import CartographerConfig


def test_static_renderer_writes_importable_pytest(tmp_path):
    registry = tmp_path / ".ledger" / "registry"
    registry.mkdir(parents=True)
    (registry / "users.yaml").write_text(
        """
fields:
  - name: email
    classification: PII
    annotations: [gdpr_erasable]
    erasure_method: anonymize
"""
    )
    control = ControlDef(
        id="GDPR-ART17-ERASURE",
        family="privacy",
        framework_ref="Art.17",
        title="erasure",
        detection={"method": "ledger_obligation", "tier": "PII", "required_annotation": "gdpr_erasable", "required_field_key": "erasure_method"},
        validation_test={
            "style": "static_assertion",
            "assertion": "ledger_annotation_has_companion_field",
            "params": {"annotation": "gdpr_erasable", "companion": "erasure_method", "tier": "PII"},
        },
    )

    paths = render_static_tests([control], tmp_path / "tests" / "compliance")

    assert len(paths) == 1
    spec = importlib.util.spec_from_file_location("generated_compliance_test", paths[0])
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.test_gdpr_art17_erasure()


def test_verify_fails_when_baseline_pass_regresses(tmp_path):
    controls = tmp_path / "compliance" / "controls"
    controls.mkdir(parents=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("audit()\n")
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
"""
    )
    config = CartographerConfig(compliance={"frameworks": ["local"]})
    write_baseline(config, tmp_path)

    (tmp_path / "src" / "app.py").write_text("pass\n")
    ok, regressions = verify_baseline(config, tmp_path)

    assert ok is False
    assert any("LOCAL-AUDIT" in regression for regression in regressions)
