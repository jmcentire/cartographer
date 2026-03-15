"""Core data models for Cartographer."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Severity(str, Enum):
    FAIL = "FAIL"
    WARN = "WARN"
    INFO = "INFO"


class ComponentType(str, Enum):
    SERVICE = "service"
    LIBRARY = "library"
    WORKER = "worker"
    EGRESS = "egress"
    INGRESS = "ingress"


class BackendType(str, Enum):
    POSTGRES = "postgres"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    REDIS = "redis"
    S3 = "s3"
    DYNAMODB = "dynamodb"
    KAFKA = "kafka"
    RABBITMQ = "rabbitmq"
    SQS = "sqs"


# --- Discovery models ---


class DiscoveredField(BaseModel):
    name: str
    type: str | None = None
    confidence: Confidence
    note: str | None = None
    classification_hint: str | None = None


class DiscoveredModel(BaseModel):
    name: str
    source_file: str
    line: int
    orm: str | None = None
    fields: list[DiscoveredField] = Field(default_factory=list)
    confidence: Confidence = Confidence.HIGH


class DiscoveredRoute(BaseModel):
    path: str
    method: str
    handler: str
    source_file: str
    line: int
    framework: str
    confidence: Confidence = Confidence.HIGH


class DiscoveredComponent(BaseModel):
    name: str
    source_file: str
    line: int
    type: ComponentType = ComponentType.SERVICE
    public_methods: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.HIGH
    note: str | None = None


class DiscoveredPactKey(BaseModel):
    key: str
    source_file: str
    line: int
    confidence: Confidence = Confidence.HIGH


class DiscoveredEnvVar(BaseModel):
    name: str
    source_file: str
    line: int
    backend_hint: str | None = None
    confidence: Confidence = Confidence.MEDIUM


class DiscoveredSensitiveField(BaseModel):
    field_name: str
    source_file: str
    line: int
    pattern_matched: str
    classification_hint: str
    confidence: Confidence = Confidence.LOW


class DiscoveryResult(BaseModel):
    """Aggregated results from all discovery scanners."""

    models: list[DiscoveredModel] = Field(default_factory=list)
    routes: list[DiscoveredRoute] = Field(default_factory=list)
    components: list[DiscoveredComponent] = Field(default_factory=list)
    pact_keys: list[DiscoveredPactKey] = Field(default_factory=list)
    env_vars: list[DiscoveredEnvVar] = Field(default_factory=list)
    sensitive_fields: list[DiscoveredSensitiveField] = Field(default_factory=list)


# --- Compatibility check models ---


class CheckResult(BaseModel):
    check_id: str
    target: str
    severity: Severity
    status: str  # PASS, WARN, FAIL
    message: str
    tool: str  # pact, ledger, baton, arbiter, sentinel


class CompatibilityReport(BaseModel):
    generated: str
    checks: list[CheckResult] = Field(default_factory=list)
    score_pass: int = 0
    score_warn: int = 0
    score_fail: int = 0
    total: int = 0
    recommendations: list[str] = Field(default_factory=list)

    @property
    def score_pct(self) -> float:
        if self.total == 0:
            return 100.0
        return round(self.score_pass / self.total * 100, 1)

    @property
    def has_failures(self) -> bool:
        return self.score_fail > 0


# --- Draft artifact models ---


class DraftField(BaseModel):
    """A field in a draft artifact with confidence annotation."""

    value: Any
    confidence: Confidence
    note: str | None = None


class DraftArtifact(BaseModel):
    """Base for all draft artifacts."""

    _draft: bool = True
    _generated_by: str = "cartographer"
    tool: str
    artifact_type: str
    path: str
    content: dict[str, Any] = Field(default_factory=dict)
