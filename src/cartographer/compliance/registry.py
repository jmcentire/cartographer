"""Declarative compliance control registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from cartographer.config.loader import CartographerConfig


ControlSeverity = Literal["must", "should"]
ControlStatus = Literal["auto", "control-ready", "audit-ready", "attested", "authorized", "certified"]


class DetectionDef(BaseModel):
    """Flexible detector config keyed by ``method``."""

    model_config = ConfigDict(extra="allow")

    method: str


class ValidationTestDef(BaseModel):
    model_config = ConfigDict(extra="allow")

    style: str = "static_assertion"
    assertion: str
    params: dict[str, Any] = Field(default_factory=dict)


class ControlDef(BaseModel):
    """A framework control with a mechanical or evidence-based detection."""

    id: str
    family: str
    framework_ref: str
    title: str
    description: str = ""
    severity: ControlSeverity = "must"
    classification_tier: str | None = None
    applicability: dict[str, Any] = Field(default_factory=dict)
    detection: DetectionDef
    corroborating_detection: list[DetectionDef] = Field(default_factory=list)
    validation_test: ValidationTestDef | None = None
    evidence_owner: str | None = None
    status: ControlStatus = "auto"
    references: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def id_must_be_stable(cls, value: str) -> str:
        if not value or any(ch.isspace() for ch in value):
            raise ValueError("control id must be non-empty and contain no spaces")
        return value


class FrameworkProfile(BaseModel):
    framework: str
    framework_version: str | None = None
    controls: list[ControlDef] = Field(default_factory=list)


def packaged_framework_dir() -> Path:
    return Path(__file__).resolve().parent / "frameworks"


def load_frameworks(
    config: CartographerConfig,
    base_dir: Path,
    frameworks: list[str] | None = None,
) -> list[FrameworkProfile]:
    """Load packaged controls and merge project YAML over them by control id."""

    wanted = [f.lower() for f in (frameworks or config.compliance.frameworks)]
    profiles: dict[str, FrameworkProfile] = {}

    for path in sorted(packaged_framework_dir().glob("*.yaml")):
        profile = _load_profile(path)
        profiles[profile.framework] = profile

    controls_dir = _resolve(base_dir, config.compliance.controls_dir)
    if controls_dir.exists():
        for path in sorted(controls_dir.glob("*.yaml")):
            profile = _load_profile(path)
            existing = profiles.get(profile.framework)
            if existing is None:
                profiles[profile.framework] = profile
            else:
                profiles[profile.framework] = _merge_profiles(existing, profile)

    selected = [p for slug, p in sorted(profiles.items()) if not wanted or slug in wanted]
    return selected


def append_project_control(config: CartographerConfig, base_dir: Path, control: ControlDef, framework: str) -> Path:
    """Append a reviewed control to the project's local control file."""

    controls_dir = _resolve(base_dir, config.compliance.controls_dir)
    controls_dir.mkdir(parents=True, exist_ok=True)
    path = controls_dir / f"{framework}.local.yaml"
    payload: dict[str, Any]
    if path.exists():
        payload = yaml.safe_load(path.read_text()) or {}
        if not isinstance(payload, dict):
            payload = {}
    else:
        payload = {"framework": framework, "controls": []}
    payload.setdefault("framework", framework)
    payload.setdefault("controls", [])
    payload["controls"].append(control.model_dump(exclude_none=True))
    path.write_text(yaml.safe_dump(payload, sort_keys=False))
    return path


def control_ids(profiles: list[FrameworkProfile]) -> set[str]:
    return {control.id for profile in profiles for control in profile.controls}


def _load_profile(path: Path) -> FrameworkProfile:
    raw = yaml.safe_load(path.read_text()) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"framework file must be a mapping: {path}")
    profile = FrameworkProfile(**raw)
    profile.framework = profile.framework.lower()
    return profile


def _merge_profiles(base: FrameworkProfile, override: FrameworkProfile) -> FrameworkProfile:
    by_id = {control.id: control for control in base.controls}
    for control in override.controls:
        by_id[control.id] = control
    return FrameworkProfile(
        framework=base.framework,
        framework_version=override.framework_version or base.framework_version,
        controls=list(by_id.values()),
    )


def _resolve(base_dir: Path, path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else base_dir / p
