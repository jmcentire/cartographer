"""Configuration loader for cartographer.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class SourceConfig(BaseModel):
    dirs: list[str] = Field(default_factory=lambda: ["./src", "./lib", "./app"])
    languages: list[str] = Field(
        default_factory=lambda: ["python", "typescript", "javascript", "ruby", "go", "java"]
    )
    exclude: list[str] = Field(
        default_factory=lambda: ["node_modules", ".venv", "dist", "build"]
    )


class BackendConfig(BaseModel):
    id: str
    type: str
    connection_hint: str
    owner_component_hint: str | None = None
    schema_registry_url: str | None = None


class InfrastructureConfig(BaseModel):
    backends: list[BackendConfig] = Field(default_factory=list)


class ServiceConfig(BaseModel):
    base_urls: list[str] = Field(default_factory=list)
    openapi_paths: list[str] = Field(default_factory=list)


class TargetsConfig(BaseModel):
    source: SourceConfig = Field(default_factory=SourceConfig)
    infrastructure: InfrastructureConfig = Field(default_factory=InfrastructureConfig)
    services: ServiceConfig = Field(default_factory=ServiceConfig)


class StackConfig(BaseModel):
    pact_project_dir: str | None = None
    baton_config: str | None = None
    ledger_registry: str | None = None
    arbiter_registry: str | None = None
    constrain_sessions: str | None = None
    sentinel_manifest: str | None = None


class CompatibilityConfig(BaseModel):
    pact_key_format: str = r"PACT:[a-zA-Z0-9_]+:[a-zA-Z0-9_]+"
    min_pact_version: str | None = None
    min_baton_schema_version: str = "2.0"


class CartographerConfig(BaseModel):
    version: str = "1.0"
    targets: TargetsConfig = Field(default_factory=TargetsConfig)
    stack: StackConfig = Field(default_factory=StackConfig)
    output_dir: str = ".cartographer/drafts/"
    compatibility: CompatibilityConfig = Field(default_factory=CompatibilityConfig)


DEFAULT_CONFIG_NAME = "cartographer.yaml"


def find_config(start: Path | None = None) -> Path | None:
    """Find cartographer.yaml in the given directory or current directory."""
    search = start or Path.cwd()
    candidate = search / DEFAULT_CONFIG_NAME
    if candidate.exists():
        return candidate
    return None


def load_config(path: Path | None = None) -> CartographerConfig:
    """Load configuration from a YAML file, or return defaults."""
    if path is None:
        path = find_config()
    if path is None or not path.exists():
        return CartographerConfig()
    with open(path) as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}
    return CartographerConfig(**raw)


def write_default_config(path: Path) -> None:
    """Write a default cartographer.yaml to the given path."""
    config = CartographerConfig()
    data = config.model_dump(exclude_none=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
