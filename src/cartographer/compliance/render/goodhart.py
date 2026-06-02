"""Render Goodhart-style JSON suites for controls that need behavioral tests."""

from __future__ import annotations

import json
from pathlib import Path
import re

from cartographer.compliance.registry import ControlDef


def render_goodhart_suites(controls: list[ControlDef], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for control in controls:
        if control.validation_test is None or control.validation_test.style != "goodhart_json":
            continue
        path = out_dir / f"{_slug(control.id)}_suite.json"
        payload = {
            "component_id": control.id,
            "contract_version": "1.0",
            "test_cases": [
                {
                    "id": f"{control.id}-behavior",
                    "description": control.title,
                    "function": control.validation_test.assertion,
                    "category": "compliance",
                    "assertions": [control.validation_test.params],
                }
            ],
        }
        path.write_text(json.dumps(payload, indent=2))
        paths.append(path)
    return paths


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value.lower()).strip("_")
