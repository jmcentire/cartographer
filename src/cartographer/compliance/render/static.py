"""Render static pytest controls."""

from __future__ import annotations

from pathlib import Path
import re

from cartographer.compliance.registry import ControlDef


def render_static_tests(controls: list[ControlDef], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for control in controls:
        if control.validation_test is None or control.validation_test.style != "static_assertion":
            continue
        path = out_dir / f"test_{_slug(control.id)}.py"
        path.write_text(_render_control(control))
        paths.append(path)
    return paths


def _render_control(control: ControlDef) -> str:
    vt = control.validation_test
    assert vt is not None
    params = dict(vt.params)
    args = ", ".join(f"{key}={value!r}" for key, value in sorted(params.items()))
    call = f"ASSERTIONS[{vt.assertion!r}](BASE_DIR{', ' if args else ''}{args})"
    return f'''"""Generated compliance test for {control.id}."""

from pathlib import Path

from cartographer.compliance.render.assertions import ASSERTIONS


BASE_DIR = Path(__file__).resolve().parents[2]


def test_{_slug(control.id)}():
    """{control.title}"""
    {call}
'''


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value.lower()).strip("_")
