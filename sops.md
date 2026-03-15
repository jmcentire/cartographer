# Cartographer — Standard Operating Procedures

## Language & Runtime

- Python 3.12+
- Synchronous (no async)

## Dependencies

- **click** — CLI framework
- **pydantic** — data models and config validation
- **pyyaml** — YAML parsing and generation

Optional:
- **psycopg2-binary** — Postgres introspection
- **redis** — Redis introspection
- **confluent-kafka** — Kafka introspection
- **pymongo** — MongoDB introspection
- **uvicorn + starlette** — HTTP API
- **mcp** — MCP server

## Project Structure

```
src/cartographer/
  cli/main.py           — Click CLI entry point
  config/loader.py      — cartographer.yaml parsing
  discovery/
    scanner.py          — Source scanner orchestrator
    pact_keys.py        — PACT key detection
    env_vars.py         — Environment variable / backend hint detection
    sensitive_fields.py — PII/financial/auth field pattern matching
    plugins/
      base.py           — ScannerPlugin ABC
      python_scanner.py — AST-based Python scanner
      typescript_scanner.py — Regex-based TS scanner
      javascript_scanner.py — JS scanner (extends TS + CommonJS)
      ruby_scanner.py   — ActiveRecord/Sequel/Rails detection
      go_scanner.py     — GORM/sqlx/net-http detection
      java_scanner.py   — JPA/Spring detection
  drafters/
    base.py             — Drafter ABC
    constrain_drafter.py
    pact_drafter.py
    ledger_drafter.py
    baton_drafter.py
    sentinel_drafter.py
  compatibility/
    base.py             — CompatibilityChecker ABC
    runner.py           — Orchestrates all checkers
    pact_checker.py
    baton_checker.py
    ledger_checker.py
    arbiter_checker.py
    sentinel_checker.py
  report/
    generator.py        — Text and JSON report formatting
  models.py             — Core Pydantic models
```

## Code Standards

- Type hints on all function signatures
- `from __future__ import annotations` in every module
- Use `pathlib.Path` for file operations
- No hardcoded classification patterns — load from YAML or DEFAULT_PATTERNS dict
- Every discovery item must have a `confidence` field

## Testing

- pytest
- Test files in `tests/`
- Smoke tests via `pact adopt`

## Output

- Draft artifacts → `.cartographer/drafts/<tool>/`
- Compatibility reports → `.cartographer/reports/`
- All drafts have `_draft: true` and `_generated_by: cartographer`
