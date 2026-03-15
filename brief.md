# CARTOGRAPHER — Claude Code Brief

## Role in the Stack

Cartographer is the adoption and compatibility tool. It answers two questions:

1. **Discovery**: given an existing codebase, running services, and live data backends,
   what draft artifacts can be produced for Constrain, Pact, Ledger, Arbiter, Baton,
   and Sentinel?

2. **Compatibility check**: given a codebase that was built without the stack (or with
   an earlier version), what is missing, what is wrong, and what needs to change to
   bring it into compliance?

Cartographer does not make changes. It discovers, drafts, and reports. Humans and
the other tools make changes.

## This Is a New Tool

Build from scratch.

```
cartographer/
  cli/              # CLI entry point
  discovery/        # Source code, runtime, and infrastructure scanners
  drafters/         # Artifact drafters for each tool in the stack
  compatibility/    # Compatibility checkers for each tool
  report/           # Report generation
  config/           # cartographer.yaml
  api/              # HTTP API
```

## Configuration

```yaml
# cartographer.yaml

version: "1.0"

# What to scan
targets:
  source:
    dirs: ["./src", "./lib", "./app"]
    languages: [python, typescript, javascript, ruby, go, java]
    exclude: ["node_modules", ".venv", "dist", "build"]

  infrastructure:
    # Live backends to introspect (connection hints, no credentials)
    backends: []      # populated by engineer before running

  services:
    # Running services to probe
    base_urls: []
    openapi_paths: []  # paths to existing OpenAPI spec files

# Stack tool locations (for compatibility checking)
stack:
  pact_project_dir: null
  baton_config: null          # path to baton.yaml
  ledger_registry: null       # path to .ledger/registry/
  arbiter_registry: null      # path to .arbiter/registry/
  constrain_sessions: null    # path to .constrain/sessions/
  sentinel_manifest: null     # path to .sentinel/manifest.json

# Output directory for draft artifacts
output_dir: ".cartographer/drafts/"

# Compatibility check config
compatibility:
  pact_key_format: "PACT:[a-zA-Z0-9_]+:[a-zA-Z0-9_]+"
  min_pact_version: null      # semver string, optional
  min_baton_schema_version: "2.0"
```

## Discovery Modes

### `cartographer discover`

Full discovery run. Scans source code, probes live backends (if configured),
and produces draft artifacts for all tools.

```bash
cartographer discover                          # full discovery
cartographer discover --only ledger            # just ledger drafts
cartographer discover --only pact,baton        # subset
cartographer discover --no-live                # source only, no live probing
```

### `cartographer check`

Compatibility check against an existing or partially-configured stack.
Does not produce new drafts. Reports gaps and violations.

```bash
cartographer check                             # check everything
cartographer check --tool pact                 # check one tool
cartographer check --strict                    # exit non-zero on any warning
```

## Discovery: Source Code Scanner

The source scanner introspects existing code to extract structure without running it.

### What it finds

**Classes and modules** — potential Pact components
```python
# Detects: class definitions, module exports, public methods
# Produces: draft component list for Pact decomposition
```

**Database access patterns** — potential Ledger schemas
```python
# Detects: ORM model definitions (SQLAlchemy, Django ORM, ActiveRecord,
#          Sequelize, TypeORM, Mongoose, Prisma, etc)
# Detects: raw SQL strings (for table/column extraction)
# Detects: Redis client calls (for key pattern extraction)
# Detects: Kafka producer/consumer calls (for topic extraction)
# Produces: draft Ledger schema files per detected backend type
```

**API endpoint definitions** — potential Baton nodes
```python
# Detects: Flask/FastAPI/Express/Rails/Spring routes
# Detects: existing OpenAPI specs
# Produces: draft baton.yaml node definitions
```

**Existing PACT keys** — Sentinel compatibility
```python
# Detects: strings matching PACT key format in source files
# Produces: draft Sentinel manifest entries
```

**Configuration and secrets patterns** — backend connection hints
```python
# Detects: environment variable names suggesting backend connections
#          (DATABASE_URL, REDIS_URL, KAFKA_BROKERS, AWS_S3_BUCKET, etc)
# Produces: backend connection hints for Ledger (never credential values)
```

**Data structures with sensitive-looking fields** — classification hints
```python
# Detects: field names matching patterns: email, password, ssn, phone,
#          credit_card, address, dob, ip_address, user_id + common PII patterns
# Detects: fields with type annotations suggesting sensitivity
# Produces: classification hints (LOW confidence — human must confirm)
```

### Language Support

| Language   | ORM/Framework Detection                                    |
|------------|------------------------------------------------------------|
| Python     | SQLAlchemy, Django ORM, Peewee, Tortoise, Pydantic models  |
| TypeScript | TypeORM, Prisma, Sequelize, Mongoose, Drizzle              |
| JavaScript | Same as TypeScript + CommonJS patterns                     |
| Ruby       | ActiveRecord, Sequel                                       |
| Go         | GORM, sqlx, database/sql raw queries                       |
| Java       | JPA/Hibernate, MyBatis, JDBC raw queries                   |

### Confidence Levels

Every discovered item has a confidence level:

```python
class Confidence(Enum):
    HIGH   = "high"    # structural evidence: ORM model definition, explicit type
    MEDIUM = "medium"  # pattern match: field name, import pattern
    LOW    = "low"     # heuristic: naming convention, comment content
```

Low-confidence items are included in draft artifacts but marked with `_confidence: low`
and a `_note` explaining why. They require human confirmation before being registered.

## Discovery: Live Backend Introspection

When `backends` are configured in `cartographer.yaml`, Cartographer probes them
to extract structure. This is the same inference capability as `ledger schema infer`
but invoked from Cartographer and targeted at producing Ledger draft schemas.

```yaml
# In cartographer.yaml
targets:
  infrastructure:
    backends:
      - id: users_db
        type: postgres
        connection_hint: "postgres://readonly@host:5432/dbname"
        owner_component_hint: user_service  # optional
      - id: session_cache
        type: redis
        connection_hint: "redis://host:6379/0"
      - id: event_bus
        type: kafka
        connection_hint: "kafka://broker:9092"
        schema_registry_url: "http://schema-registry:8081"
```

All introspection uses read-only operations. Cartographer never writes to live backends.

## Discovery: Running Service Probing

When `services` are configured, Cartographer probes running services for their
OpenAPI specs and derives Baton node definitions from them.

```bash
# Probe a running service
cartographer discover --service http://localhost:8001

# Use existing OpenAPI spec files
cartographer discover --openapi ./specs/user_service.yaml
```

From an OpenAPI spec, Cartographer produces:
- Draft Baton node definition (port, protocol, health path)
- Draft Pact contract (interface from OpenAPI operations)
- Draft Ledger classification hints (response field names)

## Draft Artifact Production

All drafts are written to `output_dir` (default: `.cartographer/drafts/`).
Draft artifacts are NOT registered with any tool automatically. The engineer
reviews and registers them using each tool's own commands.

### Draft: Constrain artifacts

When no Constrain session exists for the system:

```
.cartographer/drafts/constrain/
  prompt_draft.md              # system description inferred from code + README
  constraints_draft.yaml       # constraints inferred from error handlers, validations
  component_map_draft.yaml     # components from source scanner
  trust_policy_draft.yaml      # minimal trust policy (all at floor)
  schema_hints_draft.yaml      # from backend introspection
```

These are conversation-starter artifacts. They are not substitutes for running
Constrain — they reduce the time a Constrain session takes by pre-populating
discoverable facts.

### Draft: Pact artifacts

```
.cartographer/drafts/pact/
  contracts/
    <component_id>_draft.yaml  # one per detected component
  task_draft.md                # task description from README + source
```

Draft contracts contain:
- Interface derived from public method signatures
- Empty `data_access` (must be filled by human)
- Empty `authority` (must be filled by human)
- No tests (Pact generates these)
- `_confidence` and `_note` on every field

### Draft: Ledger artifacts

```
.cartographer/drafts/ledger/
  backends/
    <backend_id>_draft.yaml    # one per detected backend
  schemas/
    <backend_id>_<unit>_draft.yaml  # one per detected storage unit
```

Classification fields in draft schemas are always marked `_confidence: low`
unless derived from a built-in annotation map (e.g., Stripe). Field names and
types are HIGH confidence when from ORM introspection, MEDIUM when from sampling.

### Draft: Baton artifacts

```
.cartographer/drafts/baton/
  baton_draft.yaml             # complete draft topology
```

Derived from: detected service endpoints, OpenAPI specs, service probing results.
Edges inferred from: import relationships, HTTP client call detection, explicit
configuration.

### Draft: Sentinel artifacts

```
.cartographer/drafts/sentinel/
  manifest_draft.json          # all detected PACT keys with source locations
```

If no PACT keys are found, the manifest is empty with a note that PACT key
emission is not yet implemented.

## Compatibility Check

`cartographer check` evaluates an existing codebase against each tool's requirements.
It does not require the tools to be installed — it checks the artifacts and code
directly.

### Output Format

```
CARTOGRAPHER COMPATIBILITY REPORT
generated: 2026-03-15T14:32:00Z

PACT COMPATIBILITY
  contracts/auth_module.yaml      PASS   data_access present, authority present
  contracts/user_service.yaml     WARN   data_access.rationale is vague
  contracts/payment.yaml          FAIL   missing authority field
  src/auth_module.py              FAIL   no PACT key found in any method
  src/user_service.py             WARN   event_handler param present but
                                         log_handler missing
  src/payment.py                  FAIL   no event_handler, no log_handler

LEDGER COMPATIBILITY
  users_db / users                PASS   all fields have classification
  users_db / sessions             WARN   3 fields missing classification
  event_bus / user.events         FAIL   no schema registered for this topic
  stripe_api                      WARN   built-in annotations not applied

BATON COMPATIBILITY
  baton.yaml schema version       FAIL   version 1.0, requires 2.0
  node: user_service              WARN   data_access not declared
  node: auth_service              PASS
  node: payment_service           FAIL   no openapi_spec configured

ARBITER COMPATIBILITY
  access_graph.json               FAIL   not found — run pact build first
  trust ledger                    PASS   present and readable

SENTINEL COMPATIBILITY
  manifest.json                   WARN   12 components registered,
                                         but 3 PACT keys in source not in manifest
  src/legacy_handler.py           INFO   no PACT keys found — unmonitored code

OVERALL SCORE: 61% compliant (18/29 checks passing)
  FAIL: 6   WARN: 5   PASS: 18

RECOMMENDED NEXT STEPS (in order):
  1. Update baton.yaml to schema version 2.0
     (run: baton migrate-config)
  2. Add PACT keys to: src/auth_module.py, src/user_service.py, src/payment.py
  3. Add event_handler and log_handler to payment.py
  4. Register missing Ledger schema for kafka topic: user.events
  5. Apply Stripe built-in annotations: ledger builtins apply stripe
  6. Run: pact build to regenerate access_graph.json
```

### Check Modules

Each check module is independent and runnable separately:

```bash
cartographer check --tool pact
cartographer check --tool ledger
cartographer check --tool baton
cartographer check --tool arbiter
cartographer check --tool sentinel
```

#### Pact Checks

```python
pact_checks = [
    # Contract checks
    ("contract_has_data_access",    FAIL),   # missing field
    ("contract_data_access_rationale_not_vague", WARN),  # vague string
    ("contract_has_authority",      FAIL),   # missing field
    ("contract_schema_version_current", WARN),  # old schema

    # Source code checks
    ("source_has_pact_key",         FAIL),   # no PACT: key in any method
    ("source_has_event_handler",    FAIL),   # no event_handler parameter
    ("source_has_log_handler",      WARN),   # no log_handler parameter
    ("pact_key_format_valid",       FAIL),   # malformed PACT key
    ("pact_key_matches_contract_id",WARN),   # key component_id != contract id

    # Emission checks
    ("event_handler_called_on_invoke", WARN), # handler present but not called
    ("event_handler_called_on_complete",WARN),
]
```

#### Ledger Checks

```python
ledger_checks = [
    ("all_detected_backends_registered", FAIL),
    ("all_detected_tables_have_schema",  FAIL),
    ("all_fields_have_classification",   FAIL),
    ("no_annotation_conflicts",          FAIL),
    ("gdpr_erasable_has_erasure_method", WARN),
    ("audit_fields_have_retention_policy",WARN),
    ("encrypted_fields_never_in_spans",  INFO),  # can't check without running
    ("stripe_builtin_applied",           WARN),   # if stripe backend present
]
```

#### Baton Checks

```python
baton_checks = [
    ("baton_yaml_version_current",       FAIL),
    ("all_nodes_have_data_access",       WARN),
    ("all_nodes_have_authority_declared",WARN),
    ("openapi_spec_present_for_http_nodes",WARN),
    ("arbiter_endpoint_configured",      INFO),
    ("ledger_endpoint_configured",       INFO),
    ("audit_channel_port_configured",    WARN),
]
```

#### Sentinel Checks

```python
sentinel_checks = [
    ("all_source_pact_keys_in_manifest", WARN),
    ("all_manifest_entries_have_contract_path", FAIL),
    ("all_manifest_entries_have_test_path",     FAIL),
    ("all_manifest_entries_have_source_path",   FAIL),
    ("pact_configured",                  INFO),
    ("arbiter_configured",               INFO),
]
```

## Incremental Adoption Workflow

Cartographer supports a structured workflow for bringing an existing project into
compliance incrementally. This is not a one-shot operation.

```bash
# Step 1: Discover what exists
cartographer discover --no-live

# Step 2: Check current compliance
cartographer check

# Step 3: Review drafts
ls .cartographer/drafts/

# Step 4: Register what you've reviewed (per tool)
ledger schema add .cartographer/drafts/ledger/schemas/users_db_users_draft.yaml
pact adopt .cartographer/drafts/pact/contracts/

# Step 5: Check again — score should improve
cartographer check

# Step 6: Repeat until compliant
```

The `cartographer adopt` command automates steps 4-5 for items above a confidence
threshold:

```bash
cartographer adopt --confidence high           # auto-register HIGH confidence items only
cartographer adopt --tool ledger --confidence medium  # ledger items at medium+
cartographer adopt --dry-run                   # show what would be registered
```

`cartographer adopt` calls each tool's registration command with the draft artifact.
It does not skip human review for classification fields — those are always MEDIUM or
LOW confidence and require explicit `--confidence medium` or `--confidence low` to adopt.

## `baton migrate-config`

A dedicated subcommand to upgrade an existing `baton.yaml` from schema version 1.0
to 2.0. This is the most common compatibility fix for existing Baton users.

```bash
baton migrate-config                           # upgrade baton.yaml in place
baton migrate-config --dry-run                 # show diff without writing
baton migrate-config --output baton.v2.yaml    # write to new file
```

The migration:
1. Adds `version: "2.0"` to the file
2. Adds `global.arbiter` section with null values
3. Adds `global.ledger` section with null values
4. Adds `global.audit_channel` section with defaults
5. Adds empty `data_access` and `authority` stubs to each node (with `_note: fill this`)
6. Preserves all existing configuration unchanged

## HTTP API

```
POST /discover
  Body: { targets, output_dir }  → starts async discovery job
GET  /discover/<job_id>          → poll status and results

POST /check
  Body: { stack, checks }        → run compatibility check
GET  /check/<job_id>             → poll status

GET  /drafts                     → list all draft artifacts
GET  /drafts/<tool>              → list drafts for one tool
GET  /drafts/<tool>/<artifact>   → single draft content

POST /adopt
  Body: { tool, artifact, confidence_floor }
  → register artifact with target tool

GET  /report/latest              → most recent check report
GET  /report/<job_id>            → specific report

GET  /status                     → tool connectivity status
```

## CLI

```bash
cartographer init                              # initialize config
cartographer discover [--only <tools>] [--no-live]
cartographer check [--tool <tool>] [--strict]
cartographer report                            # show latest check report
cartographer adopt [--confidence <level>] [--tool <tool>] [--dry-run]
cartographer drafts list [--tool <tool>]
cartographer drafts show <tool> <artifact>
cartographer serve                             # start API server
```

## Functional Assertions

- FA-CA-001: `cartographer discover` produces draft artifacts in output_dir
- FA-CA-002: Draft artifacts are valid YAML/JSON parseable by target tool
- FA-CA-003: Every draft field has a `_confidence` annotation
- FA-CA-004: Inference never writes to live backends
- FA-CA-005: Inference uses read-only operations only (SCAN not FLUSHALL, SELECT not DROP)
- FA-CA-006: `cartographer check` produces a report with PASS/WARN/FAIL per check
- FA-CA-007: `cartographer check` exit code is 0 on all PASS/WARN, non-zero on any FAIL
- FA-CA-008: `cartographer check --strict` exits non-zero on any WARN or FAIL
- FA-CA-009: Compatibility score (percentage) is correct arithmetic
- FA-CA-010: RECOMMENDED NEXT STEPS are ordered by impact (FAILs before WARNs)
- FA-CA-011: `cartographer adopt --dry-run` produces no side effects
- FA-CA-012: `cartographer adopt --confidence high` registers only HIGH confidence items
- FA-CA-013: Classification fields are never adopted at any confidence level without
             explicit `--confirm-classification` flag
- FA-CA-014: `baton migrate-config` produces valid version 2.0 baton.yaml
- FA-CA-015: `baton migrate-config` preserves all existing node and edge configuration
- FA-CA-016: Source scanner detects SQLAlchemy model definitions in Python
- FA-CA-017: Source scanner detects Prisma schema definitions in TypeScript
- FA-CA-018: Source scanner detects ActiveRecord models in Ruby
- FA-CA-019: Source scanner detects existing PACT keys matching the standard format
- FA-CA-020: Source scanner detects event_handler parameter in Python class constructors
- FA-CA-021: Source scanner detects route definitions in Flask, FastAPI, Express, Rails
- FA-CA-022: Live postgres introspection matches `information_schema.columns` structure
- FA-CA-023: Live MongoDB inference uses SCAN-equivalent (no full collection lock)
- FA-CA-024: SQS/RabbitMQ sampling includes a warning about production queue risk
- FA-CA-025: `cartographer check` runs without any tool being installed or configured
             (it checks artifacts and code, not running services)

## Artifact Contracts

### Consumes (for discovery)
- Source code directories (static analysis)
- Live backend connections (read-only introspection, optional)
- Running service URLs (OpenAPI probing, optional)
- Existing stack artifacts (baton.yaml, pact contracts, etc.) for compatibility check

### Produces (drafts only — never registers directly)
- Draft Constrain artifacts (prompt, constraints, component_map, trust_policy, schema_hints)
- Draft Pact contracts
- Draft Ledger schemas
- Draft Baton topology
- Draft Sentinel manifest
- Compatibility check reports

### What it does NOT do
- It never registers artifacts with any tool without explicit operator action
- It never writes to live backends
- It never modifies existing stack artifacts (only reads them for compatibility check)
- It never makes classification decisions — it suggests, humans confirm

## Notes for Claude Code

- The source scanner is an AST-based static analyzer, not a regex scanner. Use
  `ast` (Python), `typescript-eslint` parser (TS/JS), `tree-sitter` (multi-language)
  or language-specific parsers. Regex-based detection is a fallback for languages
  without AST support.
- The ORM detection layer should be plugin-based — one plugin per ORM/framework.
  This makes it extensible without modifying core scanner logic.
- Classification hints from field name matching should use a curated list of patterns,
  not an LLM. The list should be in a YAML file shipped with Cartographer, not
  hardcoded. Teams can extend it.
- `cartographer check` must work in CI without any running services. All checks that
  require live backends must be clearly marked as optional and skipped when not available.
- The `baton migrate-config` command should be part of Baton, not Cartographer. It
  is documented here because it is the most common migration action Cartographer
  recommends. Implement it in Baton and have Cartographer invoke it via subprocess
  or direct import.
- Draft artifacts should be clearly marked as drafts: add a `_draft: true` top-level
  field and a `_generated_by: cartographer` field. Tools that accept these artifacts
  should strip draft markers before registering.
- The compatibility score is a product metric as much as a technical one. Make it
  easy to embed in CI output and dashboards. Consider a `--format json` flag for
  machine-readable output.
