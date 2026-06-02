from __future__ import annotations

import yaml

from cartographer.compliance.registry import ControlDef, load_frameworks
from cartographer.config.loader import CartographerConfig


def test_packaged_frameworks_load_with_six_controls_each(tmp_path):
    profiles = load_frameworks(CartographerConfig(), tmp_path)

    assert {p.framework for p in profiles} == {
        "ccpa",
        "cjis",
        "fedramp",
        "gdpr",
        "hipaa",
        "iso27001",
        "pcidss",
        "soc2",
    }
    assert all(len(profile.controls) >= 6 for profile in profiles)
    assert all(isinstance(control, ControlDef) for profile in profiles for control in profile.controls)


def test_project_controls_override_packaged_control_by_id(tmp_path):
    controls = tmp_path / "compliance" / "controls"
    controls.mkdir(parents=True)
    (controls / "gdpr.local.yaml").write_text(
        yaml.safe_dump(
            {
                "framework": "gdpr",
                "controls": [
                    {
                        "id": "GDPR-ART17-ERASURE",
                        "family": "override",
                        "framework_ref": "local",
                        "title": "Local erasure override",
                        "severity": "should",
                        "detection": {"method": "source_grep", "any_of": ["erase"], "include_glob": "**/*.py"},
                    }
                ],
            }
        )
    )

    profiles = load_frameworks(CartographerConfig(compliance={"frameworks": ["gdpr"]}), tmp_path)

    controls_by_id = {control.id: control for control in profiles[0].controls}
    assert controls_by_id["GDPR-ART17-ERASURE"].title == "Local erasure override"
    assert controls_by_id["GDPR-ART17-ERASURE"].severity == "should"
