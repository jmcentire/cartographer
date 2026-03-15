# === Cartographer Models (src_cartographer_models) v1 ===
#  Dependencies: pydantic, enum, typing
# Core data models for the Cartographer system. Defines Pydantic models for discovery results (models, routes, components, environment variables, sensitive fields), compatibility checking (check results and reports), and draft artifact generation. Includes enumerations for confidence levels, severity, component types, and backend types.

# Module invariants:
#   - All Pydantic models inherit from BaseModel
#   - All enum values are string-based
#   - Confidence levels are ordered: HIGH > MEDIUM > LOW
#   - CompatibilityReport.total == score_pass + score_warn + score_fail when properly maintained
#   - score_pct property returns value in range [0.0, 100.0]

class Confidence(Enum):
    """Enumeration of confidence levels for discovered entities"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class Severity(Enum):
    """Enumeration of severity levels for compatibility checks"""
    FAIL = "FAIL"
    WARN = "WARN"
    INFO = "INFO"

class ComponentType(Enum):
    """Enumeration of component types in the system"""
    SERVICE = "SERVICE"
    LIBRARY = "LIBRARY"
    WORKER = "WORKER"
    EGRESS = "EGRESS"
    INGRESS = "INGRESS"

class BackendType(Enum):
    """Enumeration of supported backend/datastore types"""
    POSTGRES = "POSTGRES"
    MYSQL = "MYSQL"
    SQLITE = "SQLITE"
    MONGODB = "MONGODB"
    REDIS = "REDIS"
    S3 = "S3"
    DYNAMODB = "DYNAMODB"
    KAFKA = "KAFKA"
    RABBITMQ = "RABBITMQ"
    SQS = "SQS"

class DiscoveredField:
    """Represents a field discovered in a data model"""
    name: str                                # required
    type: str | None = None                  # optional
    confidence: Confidence                   # required
    note: str | None = None                  # optional
    classification_hint: str | None = None   # optional

class DiscoveredModel:
    """Represents a data model discovered in source code"""
    name: str                                # required
    source_file: str                         # required
    line: int                                # required
    orm: str | None = None                   # optional
    fields: list[DiscoveredField] = []       # optional
    confidence: Confidence = Confidence.HIGH # optional

class DiscoveredRoute:
    """Represents an HTTP route/endpoint discovered in source code"""
    path: str                                # required
    method: str                              # required
    handler: str                             # required
    source_file: str                         # required
    line: int                                # required
    framework: str                           # required
    confidence: Confidence = Confidence.HIGH # optional

class DiscoveredComponent:
    """Represents a component discovered in source code"""
    name: str                                # required
    source_file: str                         # required
    line: int                                # required
    type: ComponentType = ComponentType.SERVICE # optional
    public_methods: list[str] = []           # optional
    dependencies: list[str] = []             # optional
    confidence: Confidence = Confidence.HIGH # optional
    note: str | None = None                  # optional

class DiscoveredPactKey:
    """Represents a Pact key discovered in source code"""
    key: str                                 # required
    source_file: str                         # required
    line: int                                # required
    confidence: Confidence = Confidence.HIGH # optional

class DiscoveredEnvVar:
    """Represents an environment variable reference discovered in source code"""
    name: str                                # required
    source_file: str                         # required
    line: int                                # required
    backend_hint: str | None = None          # optional
    confidence: Confidence = Confidence.MEDIUM # optional

class DiscoveredSensitiveField:
    """Represents a potentially sensitive field discovered via pattern matching"""
    field_name: str                          # required
    source_file: str                         # required
    line: int                                # required
    pattern_matched: str                     # required
    classification_hint: str                 # required
    confidence: Confidence = Confidence.LOW  # optional

class DiscoveryResult:
    """Aggregated results from all discovery scanners"""
    models: list[DiscoveredModel] = []       # optional
    routes: list[DiscoveredRoute] = []       # optional
    components: list[DiscoveredComponent] = [] # optional
    pact_keys: list[DiscoveredPactKey] = []  # optional
    env_vars: list[DiscoveredEnvVar] = []    # optional
    sensitive_fields: list[DiscoveredSensitiveField] = [] # optional

class CheckResult:
    """Result of a single compatibility check"""
    check_id: str                            # required
    target: str                              # required
    severity: Severity                       # required
    status: str                              # required, PASS, WARN, or FAIL
    message: str                             # required
    tool: str                                # required, pact, ledger, baton, arbiter, or sentinel

class CompatibilityReport:
    """Compatibility report aggregating multiple check results with scoring"""
    generated: str                           # required
    checks: list[CheckResult] = []           # optional
    score_pass: int = 0                      # optional
    score_warn: int = 0                      # optional
    score_fail: int = 0                      # optional
    total: int = 0                           # optional
    recommendations: list[str] = []          # optional

class DraftField:
    """A field in a draft artifact with confidence annotation"""
    value: Any                               # required
    confidence: Confidence                   # required
    note: str | None = None                  # optional

class DraftArtifact:
    """Base for all draft artifacts"""
    _draft: bool = True                      # optional
    _generated_by: str = cartographer        # optional
    tool: str                                # required
    artifact_type: str                       # required
    path: str                                # required
    content: dict[str, Any] = {}             # optional

def score_pct(
    self: CompatibilityReport,
) -> float:
    """
    Calculates the percentage of passing checks in a compatibility report. Returns 100.0 if no checks exist (total == 0), otherwise computes (score_pass / total * 100) rounded to 1 decimal place.

    Preconditions:
      - self.total >= 0
      - self.score_pass >= 0

    Postconditions:
      - 0.0 <= return_value <= 100.0
      - return_value rounded to 1 decimal place

    Side effects: none
    Idempotent: yes
    """
    ...

def has_failures(
    self: CompatibilityReport,
) -> bool:
    """
    Checks whether the compatibility report contains any failures. Returns true if score_fail is greater than 0, false otherwise.

    Preconditions:
      - self.score_fail >= 0

    Postconditions:
      - return_value == true if self.score_fail > 0 else false

    Side effects: none
    Idempotent: yes
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['Confidence', 'Severity', 'ComponentType', 'BackendType', 'DiscoveredField', 'DiscoveredModel', 'DiscoveredRoute', 'DiscoveredComponent', 'DiscoveredPactKey', 'DiscoveredEnvVar', 'DiscoveredSensitiveField', 'DiscoveryResult', 'CheckResult', 'CompatibilityReport', 'DraftField', 'DraftArtifact', 'score_pct', 'has_failures']
