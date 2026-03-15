# Cartographer: Stack Adoption and Compatibility Analysis Tool

## System Context

Cartographer is a discovery and compatibility assessment tool for the Constrain software engineering stack (Constrain, Pact, Ledger, Arbiter, Baton, Sentinel). It analyzes existing codebases, services, and backends to generate draft artifacts and compatibility reports, helping engineering teams understand what needs to change to adopt the stack. The system is used by platform engineers, SREs, and development leads during stack migration planning and compatibility audits.

The tool operates through multiple discovery vectors: AST-based source code scanning with ORM-specific plugins, live backend introspection, and service probing. It generates draft artifacts (constraints, schemas, component maps) and produces detailed compatibility reports showing gaps, conflicts, and migration requirements.

## Consequence Map

**CRITICAL**: Data exposure through backend introspection - if Cartographer accesses production databases or services without proper isolation, it could leak sensitive data or credentials in reports/artifacts.

**HIGH**: Inconsistent discovery leading to incorrect migration plans - if different discovery methods (AST vs backend vs service probing) provide conflicting information, teams may make wrong architectural decisions based on incomplete or contradictory reports.

**HIGH**: Accidental service disruption during probing - if service discovery attempts are too aggressive or frequent, they could impact production service performance or trigger rate limiting.

**MEDIUM**: Stale compatibility reports - if reports aren't properly versioned or timestamped, teams may act on outdated compatibility assessments.

**LOW**: Discovery method bias - over-reliance on one discovery vector (e.g., only AST scanning) may miss runtime-only behaviors or configurations.

## Failure Archaeology

The primary risk identified is the read-only invariant violation - the system must never write to discovered backends or modify existing stack artifacts. Previous static analysis tools have failed by attempting to "fix" discovered issues automatically, leading to production outages. The lesson learned is that discovery tools must maintain strict read-only behavior and require explicit human approval for any artifact registration or backend changes.

## Dependency Landscape

**Upstream Dependencies**: Target codebases, databases, services being analyzed; existing Constrain stack artifacts for compatibility checking.

**Downstream Dependencies**: Human operators who consume reports; artifact registration systems that may receive drafted artifacts after human review.

**Lateral Dependencies**: ORM libraries and database drivers for backend introspection; language parsers for AST analysis; HTTP clients for service probing.

## Boundary Conditions

**In Scope**: Discovery and analysis of existing systems; draft artifact generation; compatibility gap identification; read-only operations only.

**Out of Scope**: Automatic artifact registration; backend modifications; code generation or refactoring; real-time monitoring or alerting.

**Constraints**: Must maintain read-only invariant across all discovery methods; must handle discovery method inconsistencies gracefully; must not impact target service performance.

## Success Shape

A good solution maintains strict read-only behavior while providing comprehensive discovery across multiple vectors. It gracefully handles inconsistencies between discovery methods, generates useful draft artifacts that reduce manual migration work, and produces clear compatibility reports that guide decision-making. The system should be observable (knowing what it discovered and when) and safe (never disrupting target systems).

## Done When

- All components enforce read-only invariant (cannot write to discovered backends)
- Discovery methods (AST, backend, service) operate independently and report conflicts
- Draft artifacts are generated but require explicit human action for registration
- Compatibility reports clearly identify gaps and required changes
- System provides audit trail of discovery operations
- Service probing respects rate limits and doesn't impact target performance
- Reports include confidence levels and discovery method attribution

## Trust and Authority Model

The system handles multiple data classification tiers through discovery operations. PII and FINANCIAL data may be discovered during backend introspection and must be handled with elevated trust requirements and human gates. AUTH data (credentials, tokens) requires the highest protection with extended soak periods. COMPLIANCE data follows regulatory requirements with mandatory human review.

Discovery components have authority over their respective domains - the AST scanner owns code analysis results, the backend introspector owns schema discoveries, and the service prober owns API compatibility findings. Human gates trigger for any FINANCIAL, AUTH, or COMPLIANCE data discovery, and when authoritative components have low trust scores. Canary soak periods extend based on data sensitivity, with COMPLIANCE data requiring 72-hour soak before full deployment.

## Component Topology

The system centers around a CLI orchestrator that coordinates multiple discovery engines. The AST scanner analyzes source code with pluggable ORM support, while the backend introspector safely probes databases and storage systems. A service prober examines running services for API compatibility.

Artifact drafters convert discoveries into Constrain stack formats, and compatibility checkers identify gaps against existing stack artifacts. A report generator produces human-readable analysis, while an HTTP API exposes discovery results. A config loader manages discovery targets and parameters.

Data flows from target systems through discovery engines to artifact drafters and compatibility checkers, ultimately producing reports and draft artifacts. The system maintains strict read-only operation across all discovery vectors while enabling comprehensive stack adoption analysis.