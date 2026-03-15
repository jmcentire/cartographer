# === Arbiter Compatibility Checker (src_cartographer_compatibility_arbiter_checker) v1 ===
#  Dependencies: json, pathlib.Path, cartographer.compatibility.base.CompatibilityChecker, cartographer.config.loader.CartographerConfig, cartographer.models.CheckResult, cartographer.models.Severity
# Validates the presence and integrity of Arbiter registry files (access_graph.json and trust_ledger.json) for compatibility checking in the Cartographer system. Checks for registry existence, file accessibility, and JSON validity.

# Module invariants:
#   - tool_name property always returns 'arbiter'
#   - check() always returns a non-empty list of CheckResult objects
#   - All CheckResult objects have tool='arbiter'
#   - Registry search order: configured path, .arbiter/registry, .arbiter
#   - File search order for access_graph.json: registry_path/access_graph.json, base_dir/access_graph.json
#   - File search order for trust_ledger.json: registry_path/trust_ledger.json, base_dir/trust_ledger.json

class ArbiterChecker:
    """Compatibility checker for Arbiter tool that validates registry files and configuration"""
    pass

def _find_registry(
    config: CartographerConfig,
    base_dir: Path,
) -> Path | None:
    """
    Locates the Arbiter registry directory by checking configured path or default locations (.arbiter/registry, .arbiter)

    Preconditions:
      - config.stack is accessible
      - base_dir is a valid Path object

    Postconditions:
      - Returns Path to existing registry directory if found
      - Returns None if no registry found in configured or default locations

    Side effects: none
    Idempotent: no
    """
    ...

def tool_name(
    self: ArbiterChecker,
) -> str:
    """
    Property that returns the tool identifier for this checker

    Postconditions:
      - Always returns the string 'arbiter'

    Side effects: none
    Idempotent: no
    """
    ...

def check(
    self: ArbiterChecker,
    config: CartographerConfig,
    base_dir: Path,
) -> list[CheckResult]:
    """
    Validates Arbiter registry files including access_graph.json and trust_ledger.json for existence and JSON validity. Returns list of CheckResult objects indicating status of each validation.

    Preconditions:
      - config is a valid CartographerConfig instance
      - base_dir is a valid Path object

    Postconditions:
      - Returns non-empty list of CheckResult objects
      - If registry not found, returns single INFO result with check_id='arbiter_registry_exists'
      - If registry found, validates access_graph.json and optionally trust_ledger.json
      - Each CheckResult has tool='arbiter'

    Errors:
      - json_parse_error (Exception): When access_graph.json or trust_ledger.json contains invalid JSON
          handling: Caught and converted to FAIL CheckResult with message 'Invalid JSON'
      - file_read_error (Exception): When file exists but cannot be opened or read
          handling: Caught and converted to FAIL CheckResult

    Side effects: Reads and parses JSON files from filesystem, Checks file existence at multiple potential paths
    Idempotent: no
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['ArbiterChecker', '_find_registry', 'tool_name', 'check']
