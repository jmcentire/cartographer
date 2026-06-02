"""Risk-to-control helper."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from cartographer.compliance.registry import ControlDef, append_project_control, control_ids, load_frameworks
from cartographer.config.loader import CartographerConfig


def draft_risk_control(
    config: CartographerConfig,
    base_dir: Path,
    framework: str,
    description: str,
) -> ControlDef:
    """Draft a conservative mechanical control without requiring an LLM call."""

    existing = control_ids(load_frameworks(config, base_dir))
    base_id = f"{framework.upper()}-{_topic(description)}"
    control_id = base_id
    i = 2
    while control_id in existing:
        control_id = f"{base_id}-{i}"
        i += 1
    pattern = re.escape(_keyword(description))
    forbid = _is_absence_risk(description)
    detection = (
        {"method": "source_grep", "none_of": [pattern], "include_glob": "**/*"}
        if forbid
        else {"method": "source_grep", "any_of": [pattern], "include_glob": "**/*"}
    )
    assertion = "source_pattern_absent" if forbid else "source_pattern_present"
    return ControlDef(
        id=control_id,
        family="Project Risk",
        framework_ref="Project-defined",
        title=description[:96],
        description=description,
        severity="must",
        classification_tier=None,
        applicability={},
        detection=detection,
        validation_test={
            "style": "static_assertion",
            "assertion": assertion,
            "params": {"pattern": pattern, "include_glob": "**/*"},
        },
        evidence_owner=None,
        status="auto",
        references=[],
    )


def control_to_yaml(control: ControlDef, framework: str) -> str:
    return yaml.safe_dump({"framework": framework, "controls": [control.model_dump(exclude_none=True)]}, sort_keys=False)


def adopt_control(config: CartographerConfig, base_dir: Path, control: ControlDef, framework: str) -> Path:
    return append_project_control(config, base_dir, control, framework)


def _topic(description: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", description.upper())
    stop = {"THE", "AND", "FOR", "WITH", "THAT", "THIS", "JUST", "MUST", "SHOULD", "DATA"}
    kept = [word for word in words if word not in stop][:4]
    return "-".join(kept or ["NEW-RISK"])


def _keyword(description: str) -> str:
    words = re.findall(r"[A-Za-z0-9_]+", description)
    return max(words, key=len) if words else description


def _is_absence_risk(description: str) -> bool:
    lowered = description.lower()
    return any(phrase in lowered for phrase in ["must not", "not appear", "exclude", "excluded", "never"])
